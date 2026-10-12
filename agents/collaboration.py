"""Agent collaboration — inter-agent delegation, messaging, shared memory, and voting."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from agents.models import AgentConfig
from agents import store

logger = logging.getLogger(__name__)


class CollaborationRole(Enum):
    LEAD = "lead"
    WORKER = "worker"
    REVIEWER = "reviewer"
    OBSERVER = "observer"


@dataclass
class CollaborationTask:
    id: str
    goal: str
    assigned_to: str
    assigned_by: str = ""
    status: str = "pending"
    result: Any = None
    error: str = ""
    created_at: str = ""
    completed_at: str = ""
    priority: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "goal": self.goal,
            "assigned_to": self.assigned_to, "assigned_by": self.assigned_by,
            "status": self.status, "result": self.result, "error": self.error,
            "created_at": self.created_at, "completed_at": self.completed_at,
            "priority": self.priority,
        }


@dataclass
class CollaborationPipeline:
    id: str
    name: str
    steps: list[CollaborationTask] = field(default_factory=list)
    current_step: int = 0
    status: str = "pending"
    result: Any = None
    created_at: str = ""
    completed_at: str = ""


class CollaborationEngine:
    """Coordinates inter-agent collaboration.

    Supports:
        - Task delegation: Agent A assigns a task to Agent B
        - Pipelines: Sequential multi-step workflows across agents
        - Shared memory: Agents can read/write to a shared context
        - File sharing: Agents can exchange files via a shared workspace
        - Reviews: Agents can request and submit reviews
        - Voting: Agents can vote on solutions
    """

    def __init__(self, runtime=None):
        self._runtime = runtime
        self._tasks: dict[str, CollaborationTask] = {}
        self._pipelines: dict[str, CollaborationPipeline] = {}
        self._shared_memory: dict[str, Any] = {}
        self._messages: dict[str, list[dict]] = {}
        self._lock = threading.RLock()
        self._callbacks: dict[str, list[Callable]] = {}
        self._votes: dict[str, list[dict]] = {}

    # ── Task delegation ─────────────────────────────────────────────

    def delegate(self, from_agent: str, to_agent: str, goal: str,
                 priority: int = 0) -> CollaborationTask:
        task = CollaborationTask(
            id=str(uuid.uuid4()),
            goal=goal,
            assigned_to=to_agent,
            assigned_by=from_agent,
            priority=priority,
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        with self._lock:
            self._tasks[task.id] = task

        self._emit("task_created", task.to_dict())

        if self._runtime:
            def on_complete(agent_id: str, result: Any) -> None:
                self.complete_task(task.id, result)

            try:
                self._runtime.start_agent(
                    agent_id=to_agent,
                    goal=goal,
                    callback=on_complete,
                )
                task.status = "running"
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                self._emit("task_failed", task.to_dict())

        return task

    def complete_task(self, task_id: str, result: Any) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.utcnow().isoformat() + "Z"

        self._emit("task_completed", task.to_dict())

        # Advance any pipeline containing this task
        for pipeline in self._pipelines.values():
            for i, step in enumerate(pipeline.steps):
                if step.id == task_id:
                    pipeline.current_step = i + 1
                    if pipeline.current_step >= len(pipeline.steps):
                        pipeline.status = "completed"
                        pipeline.completed_at = datetime.utcnow().isoformat() + "Z"
                        pipeline.result = result
                        self._emit("pipeline_completed", pipeline.to_dict())
                    else:
                        self._run_pipeline_step(pipeline)
                    break

    def get_task(self, task_id: str) -> CollaborationTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, agent_id: str | None = None) -> list[CollaborationTask]:
        if agent_id:
            return [t for t in self._tasks.values()
                    if t.assigned_to == agent_id or t.assigned_by == agent_id]
        return list(self._tasks.values())

    # ── Pipelines ───────────────────────────────────────────────────

    def create_pipeline(self, name: str, steps: list[dict]) -> CollaborationPipeline:
        """Create a sequential pipeline.

        steps: list of dicts with keys: goal, assigned_to, priority
        """
        pipeline = CollaborationPipeline(
            id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        for step_data in steps:
            task = CollaborationTask(
                id=str(uuid.uuid4()),
                goal=step_data["goal"],
                assigned_to=step_data["assigned_to"],
                assigned_by=step_data.get("assigned_by", ""),
                priority=step_data.get("priority", 0),
                created_at=datetime.utcnow().isoformat() + "Z",
            )
            pipeline.steps.append(task)
            with self._lock:
                self._tasks[task.id] = task

        with self._lock:
            self._pipelines[pipeline.id] = pipeline

        self._run_pipeline_step(pipeline)
        return pipeline

    def _run_pipeline_step(self, pipeline: CollaborationPipeline) -> None:
        if pipeline.current_step >= len(pipeline.steps):
            return

        step = pipeline.steps[pipeline.current_step]
        pipeline.status = "running"
        step.status = "running"

        self._emit("pipeline_step", {
            "pipeline_id": pipeline.id,
            "step": pipeline.current_step,
            "total": len(pipeline.steps),
            "task": step.to_dict(),
        })

        if self._runtime:
            def on_complete(agent_id: str, result: Any) -> None:
                self.complete_task(step.id, result)

            try:
                self._runtime.start_agent(
                    agent_id=step.assigned_to,
                    goal=step.goal,
                    callback=on_complete,
                )
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                self._emit("task_failed", step.to_dict())

    def list_pipelines(self) -> list[CollaborationPipeline]:
        return list(self._pipelines.values())

    def get_pipeline(self, pipeline_id: str) -> CollaborationPipeline | None:
        return self._pipelines.get(pipeline_id)

    # ── Shared memory ───────────────────────────────────────────────

    def share_memory(self, key: str, value: Any, namespace: str = "global") -> None:
        ns_key = f"{namespace}:{key}"
        with self._lock:
            self._shared_memory[ns_key] = value
        self._emit("memory_shared", {"key": ns_key, "namespace": namespace})

    def read_shared_memory(self, key: str, namespace: str = "global") -> Any:
        ns_key = f"{namespace}:{key}"
        return self._shared_memory.get(ns_key)

    def list_shared_memory(self, namespace: str = "") -> list[str]:
        if namespace:
            prefix = f"{namespace}:"
            return [k for k in self._shared_memory if k.startswith(prefix)]
        return list(self._shared_memory.keys())

    # ── Messages ────────────────────────────────────────────────────

    def send_message(self, from_agent: str, to_agent: str,
                     content: str, message_type: str = "text") -> dict:
        msg = {
            "id": str(uuid.uuid4()),
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "type": message_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "read": False,
        }
        thread_key = tuple(sorted([from_agent, to_agent]))
        with self._lock:
            self._messages.setdefault(thread_key, []).append(msg)
        self._emit("message_sent", msg)
        return msg

    def get_messages(self, agent_a: str, agent_b: str,
                     limit: int = 50) -> list[dict]:
        thread_key = tuple(sorted([agent_a, agent_b]))
        messages = self._messages.get(thread_key, [])
        return messages[-limit:]

    def get_inbox(self, agent_id: str) -> list[dict]:
        result = []
        for thread_key, msgs in self._messages.items():
            if agent_id in thread_key:
                for msg in msgs:
                    if msg["to"] == agent_id:
                        result.append(msg)
        return sorted(result, key=lambda m: m["timestamp"], reverse=True)

    # ── Reviews ─────────────────────────────────────────────────────

    def request_review(self, from_agent: str, reviewer_agent: str,
                       artifact: Any, context: str = "") -> str:
        review_id = str(uuid.uuid4())
        review_task = {
            "id": review_id,
            "type": "review",
            "from": from_agent,
            "reviewer": reviewer_agent,
            "artifact": artifact,
            "context": context,
            "status": "pending",
            "result": None,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        if self._runtime:
            goal = f"Review the following artifact and provide feedback:\n\n{json.dumps(artifact, indent=2) if isinstance(artifact, dict) else artifact}\n\nContext: {context}"

            def on_review_complete(agent_id: str, result: Any) -> None:
                review_task["status"] = "completed"
                review_task["result"] = result
                self._emit("review_completed", review_task)

            try:
                self._runtime.start_agent(
                    agent_id=reviewer_agent,
                    goal=goal,
                    callback=on_review_complete,
                )
                review_task["status"] = "running"
            except Exception as e:
                review_task["status"] = "failed"
                review_task["result"] = str(e)

        self._emit("review_requested", review_task)
        return review_id

    # ── Voting ──────────────────────────────────────────────────────

    def create_vote(self, topic: str, options: list[str],
                    created_by: str) -> str:
        vote_id = str(uuid.uuid4())
        vote = {
            "id": vote_id,
            "topic": topic,
            "options": options,
            "created_by": created_by,
            "votes": {},
            "status": "open",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        with self._lock:
            self._votes[vote_id] = vote
        self._emit("vote_created", vote)
        return vote_id

    def cast_vote(self, vote_id: str, agent_id: str, option: str) -> bool:
        with self._lock:
            vote = self._votes.get(vote_id)
            if not vote or vote["status"] != "open":
                return False
            if option not in vote["options"]:
                return False
            vote["votes"][agent_id] = option
        self._emit("vote_cast", {"vote_id": vote_id, "agent_id": agent_id, "option": option})
        return True

    def get_vote_results(self, vote_id: str) -> dict | None:
        return self._votes.get(vote_id)

    # ── Event system ────────────────────────────────────────────────

    def on(self, event: str, callback: Callable) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error("Collab event '%s' callback error: %s", event, e)
