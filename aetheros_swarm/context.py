"""Context packaging with provenance + isolation (sections 19-22, 31-32).

ContextSelector carves a task-specific package from parent context:
goal, task, constraints, scoped memories (Master 41, never the whole
long-term store), research, artifacts, evidence, previous verified
outputs, tool permissions, verification requirements. Every cross-agent
item carries source/source_agent/source_task/timestamp/confidence.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_swarm.models import SwarmTask


@dataclass
class ContextItem:
    content: str
    kind: str = "fact"
    source: str = ""
    source_agent: str = ""
    source_task: str = ""
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}


@dataclass
class AgentContextPackage:
    goal: str = ""
    task: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    memories: List[Dict[str, Any]] = field(default_factory=list)
    research: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    previous_outputs: List[Dict[str, Any]] = field(default_factory=list)
    tool_permissions: List[str] = field(default_factory=list)
    verification: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}

    def token_estimate(self) -> int:
        total = len(self.goal)
        for lst in (self.memories, self.research, self.evidence, self.previous_outputs):
            for item in lst:
                total += len(str(item.get("content", item.get("summary", ""))))
        return max(1, total // 4)


MemoryRecallFn = Callable[..., Dict[str, Any]]


class ContextSelector:
    def __init__(self, memory_recall: Optional[MemoryRecallFn] = None,
                 *, max_memories: int = 5, max_prev_outputs: int = 3) -> None:
        self._recall = memory_recall
        self._max_mem = max_memories
        self._max_prev = max_prev_outputs

    def package(self, task: SwarmTask, *,
                parent_goal: str = "",
                constraints: Optional[List[str]] = None,
                verified_outputs: Optional[List[Dict[str, Any]]] = None,
                project_id: str = "") -> AgentContextPackage:
        pkg = AgentContextPackage(
            goal=task.goal, task={"id": task.id, "type": task.type,
                                  "expected_output": task.expected_output},
            constraints=list(constraints or []),
            tool_permissions=list(task.allowed_tools),
            verification={"required": task.verification.required,
                          "method": task.verification.method})
        # Scoped memory: task/project slice only — never the whole store.
        if self._recall is not None:
            try:
                res = self._recall(task.goal, project_id=project_id or task.metadata.get("project_id", ""),
                                   top_k=self._max_mem)
                for hit in (res.get("included", []) if isinstance(res, dict) else []):
                    pkg.memories.append({
                        "content": str(hit.get("content", ""))[:800],
                        "source": "memory41", "source_task": "",
                        "confidence": hit.get("confidence", 0.5),
                        "id": hit.get("id", "")})
            except Exception:
                pass
        for out in (verified_outputs or [])[:self._max_prev]:
            # Only verified outputs cross the boundary (unverified stay provisional).
            if out.get("verification_status") in ("verified", "oracle_passed", ""):
                pkg.previous_outputs.append({
                    "content": str(out.get("summary", ""))[:800],
                    "source_agent": out.get("agent_id", ""),
                    "source_task": out.get("task_id", ""),
                    "confidence": out.get("confidence", 0.5)})
        return pkg
