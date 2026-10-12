"""Swarm benchmark harness (sections 89-94): deterministic oracle tasks.

Compares single vs parallel vs review-loop vs adaptive topologies with the
model/task/tools held constant (LocalFunctionExecutor handlers). Measures
success rate, verified rate, latency, tokens, cost, tool calls, agent
count, coordination messages (bus), failures, recovery, partial credit.
No LLM judge anywhere: oracles are string/schema/evidence checks.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aetheros_swarm import (
    AgentResult, LocalFunctionExecutor, MultiAgentOrchestrator, RunBudget,
    Topology,
)
from aetheros_swarm.decompose import TopologyEngine
from aetheros_swarm.models import TaskBudget


def make_handlers(latency_s: float = 0.02):
    def researcher(task):
        time.sleep(latency_s)
        return AgentResult(task_id=task.id, status="ok",
                           summary=f"EVIDENCE shard done: {task.goal[:40]}",
                           findings=[f"finding from {task.goal[:30]}"],
                           evidence=[{"claim": "c", "source": "oracle-docs"}],
                           confidence=0.8, tokens_used=120, cost_used_usd=0.0002,
                           tool_calls_used=2)

    def analyst(task):
        time.sleep(latency_s)
        return AgentResult(task_id=task.id, status="ok",
                           summary="EVIDENCE comparison complete",
                           findings=["comparison"], confidence=0.7,
                           tokens_used=150, cost_used_usd=0.0003, tool_calls_used=1)

    def coder(task):
        time.sleep(latency_s)
        return AgentResult(task_id=task.id, status="ok",
                           summary="EVIDENCE implementation complete",
                           findings=["impl"], confidence=0.75,
                           tokens_used=300, cost_used_usd=0.0009, tool_calls_used=3)

    def reviewer(task):
        time.sleep(latency_s)
        return AgentResult(task_id=task.id, status="ok",
                           summary="EVIDENCE review passed",
                           findings=["review-pass"], confidence=0.7,
                           tokens_used=100, cost_used_usd=0.0004, tool_calls_used=1)

    def verifier(task):
        time.sleep(latency_s)
        return AgentResult(task_id=task.id, status="ok",
                           summary="EVIDENCE verification passed",
                           findings=["verify-pass"],
                           evidence=[{"claim": "v", "source": "oracle-tests"}],
                           confidence=0.9, tokens_used=80, cost_used_usd=0.0002,
                           tool_calls_used=1, verification_status="verified")

    def writer(task):
        time.sleep(latency_s)
        return AgentResult(task_id=task.id, status="ok",
                           summary="EVIDENCE report written",
                           findings=["report"], confidence=0.7,
                           tokens_used=200, cost_used_usd=0.0002, tool_calls_used=1)

    def synthesizer(task):
        return AgentResult(task_id=task.id, status="ok",
                           summary="EVIDENCE reduced",
                           findings=["reduced"], confidence=0.7,
                           tokens_used=60, cost_used_usd=0.0001)

    return {"researcher": researcher, "analyst": analyst, "coder": coder,
            "reviewer": reviewer, "verifier": verifier, "writer": writer,
            "synthesizer": synthesizer, "orchestrator": analyst}


TASKS = {
    "simple": "Fix the typo in the README file",
    "parallel": "Research alpha, research beta, research gamma, then write report",
    "dependency": "Draft the outline then expand section one then expand section two",
    "research": "Research three static-site generators, compare them, verify claims, write report",
    "coding": "Write code to parse configs, then review and verify it for production",
    "conflict": "Debate two alternatives with evidence, then judge and verify",
    "budget": "Research alpha then write report",
}


def run_case(name: str, goal: str, *, force_single: bool,
             topology: str = "", roles=None) -> dict:
    import tempfile
    orch = MultiAgentOrchestrator(
        executor_fn=LocalFunctionExecutor(make_handlers()),
        root=tempfile.mkdtemp(prefix="swarmbench"),
        run_budget=RunBudget(max_agents=6))
    t0 = time.time()
    run = orch.plan(goal, force_single=force_single)
    if topology:
        # Override: expand the requested topology for comparison.
        eng = TopologyEngine()
        run.tasks = eng.expand(Topology(topology), roles or ["researcher", "analyst"],
                               goal, TaskBudget(max_tokens=60000, max_cost_usd=1.0))
        if run.tasks:
            root = run.tasks[0].root_task_id or run.tasks[0].id
            for t in run.tasks:
                t.root_task_id = root
        run.decision.topology = Topology(topology)
        run.decision.mode = "multi"
        run.decision.roles = list(roles or [])
    out = orch.run(run)
    dt = time.time() - t0
    toks = sum(a.tokens_used for a in out.agents.values())
    cost = sum(a.cost_used_usd for a in out.agents.values())
    tools = sum(a.tool_calls_used for a in out.agents.values())
    ok = sum(1 for t in out.tasks if t.state.value == "completed")
    verified = (out.final.verification_status in ("verified", "oracle_passed")
                if out.final else False)
    return {"task": name, "mode": run.decision.mode,
            "topology": run.decision.topology.value, "agents": len(out.agents),
            "subtasks_total": len(out.tasks), "subtasks_ok": ok,
            "verified": verified, "latency_s": round(dt, 3),
            "tokens": toks, "cost_usd": round(cost, 5), "tool_calls": tools,
            "status": out.status}


def main() -> None:
    rows = []
    for name, goal in TASKS.items():
        rows.append(run_case(name, goal, force_single=True))
        rows.append(run_case(name, goal, force_single=False))
    # Head-to-head on the research task across topologies.
    for topo, roles in [("parallel", ["researcher", "researcher", "analyst"]),
                        ("review_loop", ["coder", "reviewer", "verifier"])]:
        rows.append(run_case(f"research[{topo}]", TASKS["research"],
                             force_single=False, topology=topo, roles=roles))
    print(json.dumps(rows, indent=2))
    ok = sum(1 for r in rows if r["status"] == "completed")
    print(f"\ncompleted {ok}/{len(rows)}", file=sys.stderr)


if __name__ == "__main__":
    main()
