"""
Context Awareness Engine for AetherOS Intelligence Engine.

Maintains and enriches context for reasoning, planning, and agent execution.
Pulls relevant information from memory, knowledge, session history, and
the current workspace to provide rich context for every decision.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContextFrame:
    """A snapshot of context at a point in time."""
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    workspace_path: str = ""
    goal: str = ""
    active_plan_id: str = ""
    recent_memories: List[Dict[str, Any]] = field(default_factory=list)
    relevant_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    current_task: str = ""
    project_context: Dict[str, Any] = field(default_factory=dict)
    agent_status: Dict[str, str] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextEngine:
    """Maintains enriched context for intelligence operations.

    Gathers context from:
    - Active session and workspace
    - Memory (recent and relevant)
    - Knowledge base
    - Active plan state
    - Agent status
    - Environment information
    """

    def __init__(self) -> None:
        self._history: List[ContextFrame] = []
        self._active_frame: Optional[ContextFrame] = None
        self._max_history = 100

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    def build_context(self, session_id: str = "",
                      workspace_path: str = "",
                      goal: str = "",
                      plan_id: str = "",
                      task: str = "",
                      include_memory: bool = True,
                      include_knowledge: bool = True) -> Dict[str, Any]:
        """Build a rich context frame from all available sources."""
        frame = ContextFrame(
            session_id=session_id,
            workspace_path=workspace_path or str(Path.cwd()),
            goal=goal,
            active_plan_id=plan_id,
            current_task=task,
        )

        if include_memory:
            frame.recent_memories = self._get_recent_memories()

        if include_knowledge:
            frame.relevant_knowledge = self._get_relevant_knowledge(goal)

        frame.project_context = self._get_project_context(frame.workspace_path)
        frame.environment = self._get_environment()

        self._active_frame = frame
        self._history.append(frame)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return self._frame_to_dict(frame)

    def get_active_context(self) -> Dict[str, Any]:
        """Get the most recently built context frame."""
        if self._active_frame:
            return self._frame_to_dict(self._active_frame)
        return self.build_context()

    def enrich_context(self, additional_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich the active context with additional data."""
        if self._active_frame:
            for key, value in additional_context.items():
                if hasattr(self._active_frame, key):
                    setattr(self._active_frame, key, value)
                else:
                    self._active_frame.metadata[key] = value
            return self._frame_to_dict(self._active_frame)
        return self.build_context()

    # ------------------------------------------------------------------
    # Source integrations
    # ------------------------------------------------------------------

    def _get_recent_memories(self) -> List[Dict[str, Any]]:
        """Fetch recent memories from the memory system."""
        try:
            from aetheros_knowledge.store import KnowledgeStore
            store = KnowledgeStore()
            entries = store.list_memory(limit=10)
            return [
                {"key": e.key, "value": str(e.value)[:200],
                 "type": e.memory_type.value if hasattr(e, "memory_type") else "unknown",
                 "importance": getattr(e, "importance", 0.5)}
                for e in entries
            ]
        except Exception as exc:
            logger.debug("Memory fetch failed: %s", exc)
            return []

    def _get_relevant_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Search knowledge base for relevant context."""
        if not query:
            return []
        try:
            from aetheros_knowledge.search.engine import SearchEngine
            engine = SearchEngine()
            results = engine.hybrid_search(query, top_k=5)
            return [
                {"title": r.get("title", ""), "content": r.get("content", "")[:300],
                 "score": r.get("score", 0.0)}
                for r in results
            ]
        except Exception as exc:
            logger.debug("Knowledge search failed: %s", exc)
            return []

    def _get_project_context(self, workspace_path: str) -> Dict[str, Any]:
        """Gather context about the current project/workspace."""
        ws = Path(workspace_path)
        if not ws.exists():
            return {"error": f"Path not found: {workspace_path}"}

        context = {"path": workspace_path, "name": ws.name}
        for cfg in ("pyproject.toml", "package.json", "Cargo.toml",
                    "go.mod", "Gemfile", "requirements.txt", "setup.py"):
            cfg_path = ws / cfg
            if cfg_path.exists():
                context["config"] = cfg
                break
        return context

    def _get_environment(self) -> Dict[str, str]:
        """Gather environment information."""
        import os
        import platform
        return {
            "os": platform.system(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cwd": os.getcwd(),
            "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
        }

    def _frame_to_dict(self, frame: ContextFrame) -> Dict[str, Any]:
        return {
            "timestamp": frame.timestamp,
            "session_id": frame.session_id,
            "workspace_path": frame.workspace_path,
            "goal": frame.goal,
            "active_plan_id": frame.active_plan_id,
            "current_task": frame.current_task,
            "recent_memories": frame.recent_memories[:5],
            "relevant_knowledge": frame.relevant_knowledge[:5],
            "project_context": frame.project_context,
            "environment": frame.environment,
            "metadata": frame.metadata,
        }

    # ------------------------------------------------------------------
    # Context history
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent context frames."""
        return [self._frame_to_dict(f) for f in self._history[-limit:]]

    def clear_history(self) -> None:
        self._history.clear()
        self._active_frame = None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "frames_recorded": len(self._history),
            "has_active_context": self._active_frame is not None,
            "last_update": self._active_frame.timestamp if self._active_frame else None,
        }
