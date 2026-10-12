"""Task decomposition + topology expansion (sections 8, 11, 58-60).

Heuristic, deterministic TaskDecomposer: splits goals on cue phrases into
a Task DAG (dependencies, join nodes, verification/approval nodes where the
goal demands it). TopologyEngine expands a decision into concrete task
graphs for the 11 patterns. Reuses ExecutionGraphEngine for level/parallel
computation — no duplicate DAG code.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Tuple

from aetheros_swarm.models import SwarmTask, SwarmTaskState, TaskBudget, Topology, VerificationPolicy

_SPLIT = re.compile(r"\s+(?:then|after that|next|finally| and also )\s+", re.I)
_PARALLEL_SPLIT = re.compile(r"\s*(?:,|;|\band\b)\s*")


def _budget_for(role: str, total: TaskBudget, n: int) -> TaskBudget:
    return TaskBudget(max_tokens=max(1000, total.max_tokens // max(1, n)),
                      max_cost_usd=round(total.max_cost_usd / max(1, n), 4),
                      max_duration_s=total.max_duration_s,
                      max_tool_calls=max(3, total.max_tool_calls // max(1, n)),
                      max_retries=total.max_retries)


class TaskDecomposer:
    def decompose(self, goal: str, *, decision_roles: List[str],
                  root_budget: TaskBudget) -> List[SwarmTask]:
        parts = [p.strip(" .") for p in _SPLIT.split(goal) if p.strip(" .")]
        sequential = len(parts) > 1
        if len(parts) <= 1:
            # Try comma/and split for parallel enumeration (independent work).
            alt = [p.strip(" .") for p in _PARALLEL_SPLIT.split(goal)
                   if len(p.strip()) > 12]
            if 2 <= len(alt) <= 6:
                parts = alt
                sequential = False
        parts = parts or [goal]
        n = max(len(parts), len(decision_roles))
        tasks: List[SwarmTask] = []
        root_id = str(uuid.uuid4())
        prev = ""
        for i, part in enumerate(parts):
            role = decision_roles[i % len(decision_roles)] if decision_roles else "coder"
            t = SwarmTask(goal=part, description=part, type="subtask",
                          priority=2, state=SwarmTaskState.CREATED,
                          required_role=role,
                          dependencies=[prev] if (prev and sequential) else [],
                          budget=_budget_for(role, root_budget, n),
                          depth=1)
            t.root_task_id = root_id
            if i > 0:
                t.parent_task_id = tasks[0].id
            tasks.append(t)
            prev = t.id
        if tasks:
            tasks[0].parent_task_id = ""
            tasks[0].root_task_id = root_id
        # Verification tail when the goal demands it.
        low = goal.lower()
        if any(w in low for w in ("verify", "test", "production", "deploy", "audit")):
            tail = SwarmTask(goal=f"Verify: {goal[:80]}", type="verification",
                             priority=3, state=SwarmTaskState.CREATED,
                             required_role="verifier",
                             dependencies=[tasks[-1].id] if tasks else [],
                             verification=VerificationPolicy(required=True, method="oracle"),
                             budget=_budget_for("verifier", root_budget, n + 1),
                             depth=1, root_task_id=root_id)
            tasks.append(tail)
        return tasks


class TopologyEngine:
    """Expand (topology, roles, goal) into an executable task list."""

    def __init__(self, decomposer: TaskDecomposer | None = None) -> None:
        self._decomposer = decomposer or TaskDecomposer()

    def expand(self, topology: Topology, roles: List[str], goal: str,
               root_budget: TaskBudget) -> List[SwarmTask]:
        if topology == Topology.SINGLE:
            t = SwarmTask(goal=goal, description=goal, type="unit",
                          required_role=roles[0] if roles else "coder",
                          budget=root_budget)
            t.root_task_id = t.id
            return [t]
        if topology in (Topology.PARALLEL, Topology.MAP_REDUCE):
            return self._fan_out(roles, goal, root_budget, join=topology == Topology.MAP_REDUCE)
        if topology == Topology.PIPELINE:
            return self._pipeline(roles, goal, root_budget)
        if topology == Topology.REVIEW_LOOP:
            return self._review_loop(roles, goal, root_budget)
        if topology == Topology.DEBATE:
            return self._debate(roles, goal, root_budget)
        if topology in (Topology.HIERARCHICAL, Topology.SUPERVISOR,
                        Topology.SWARM, Topology.HYBRID, Topology.DAG,
                        Topology.SEQUENTIAL):
            base = self._decomposer.decompose(goal, decision_roles=roles, root_budget=root_budget)
            return base

    def _fan_out(self, roles: List[str], goal: str, budget: TaskBudget, *, join: bool) -> List[SwarmTask]:
        root_id = str(uuid.uuid4())
        leaves: List[SwarmTask] = []
        for i, role in enumerate(roles):
            t = SwarmTask(goal=f"{goal} [shard {i + 1}/{len(roles)}]", type="map",
                          required_role=role, depth=1, root_task_id=root_id,
                          budget=_budget_for(role, budget, len(roles) + 1))
            leaves.append(t)
        if not join:
            return leaves
        reduce_task = SwarmTask(goal=f"Reduce {len(leaves)} shards into one result",
                                type="reduce", required_role="synthesizer",
                                dependencies=[t.id for t in leaves], depth=1,
                                root_task_id=root_id,
                                budget=_budget_for("synthesizer", budget, len(roles) + 1))
        return leaves + [reduce_task]

    def _pipeline(self, roles: List[str], goal: str, budget: TaskBudget) -> List[SwarmTask]:
        stages = roles or ["researcher", "analyst", "writer"]
        tasks: List[SwarmTask] = []
        root_id = str(uuid.uuid4())
        prev = ""
        for i, role in enumerate(stages):
            t = SwarmTask(goal=f"Stage {i + 1} ({role}): {goal[:100]}", type="stage",
                          required_role=role, dependencies=[prev] if prev else [],
                          depth=1, root_task_id=root_id,
                          budget=_budget_for(role, budget, len(stages)))
            tasks.append(t)
            prev = t.id
        return tasks

    def _review_loop(self, roles: List[str], goal: str, budget: TaskBudget) -> List[SwarmTask]:
        worker = roles[0] if roles else "coder"
        root_id = str(uuid.uuid4())
        work = SwarmTask(goal=goal, type="work", required_role=worker,
                         depth=1, root_task_id=root_id,
                         budget=_budget_for(worker, budget, 3))
        review = SwarmTask(goal=f"Review: {goal[:100]}", type="review",
                           required_role="reviewer", dependencies=[work.id],
                           depth=1, root_task_id=root_id,
                           budget=_budget_for("reviewer", budget, 3))
        verify = SwarmTask(goal=f"Verify: {goal[:100]}", type="verification",
                           required_role="verifier", dependencies=[review.id],
                           verification=VerificationPolicy(required=True, method="review"),
                           depth=1, root_task_id=root_id,
                           budget=_budget_for("verifier", budget, 3))
        return [work, review, verify]

    def _debate(self, roles: List[str], goal: str, budget: TaskBudget) -> List[SwarmTask]:
        proposers = roles[:2] or ["analyst", "analyst"]
        root_id = str(uuid.uuid4())
        tasks: List[SwarmTask] = []
        for i, role in enumerate(proposers):
            tasks.append(SwarmTask(
                goal=f"Proposal {i + 1}: {goal[:100]}", type="proposal",
                required_role=role, depth=1, root_task_id=root_id,
                budget=_budget_for(role, budget, len(proposers) + 2)))
        judge = SwarmTask(goal=f"Judge proposals: {goal[:100]}", type="judge",
                          required_role="reviewer",
                          dependencies=[t.id for t in tasks], depth=1,
                          root_task_id=root_id,
                          budget=_budget_for("reviewer", budget, len(proposers) + 2))
        return tasks + [judge]
