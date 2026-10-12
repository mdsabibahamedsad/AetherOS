"""Retrieval loop guard.

A guard against retrieval spin: repeated near-identical queries within a
short window (which can happen when an agent loops on a failing retrieval)
return an early short-circuit with a note instead of hammering the store,
and repeated identical queries are tracked for observability.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class LoopDecision:
    allowed: bool = True
    reason: str = ""
    repeated: int = 0


class RetrievalLoopGuard:
    """Detects and mitigates retrieval loops per access scope."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        window_seconds: float = 30.0,
        max_repeats: int = 5,
    ) -> None:
        self.enabled = enabled
        self.window_seconds = window_seconds
        self.max_repeats = max_repeats
        self._seen: Dict[str, List[Tuple[str, float]]] = {}  # scope -> [(query, ts)]
        self._lock = None

    def _scope_key(self, *, user_id: str = "", workspace_id: str = "",
                   session_id: str = "", agent_id: str = "") -> str:
        return "|".join([user_id or "", workspace_id or "", session_id or "", agent_id or ""])

    def check(
        self, query: str, *,
        user_id: str = "", workspace_id: str = "", session_id: str = "", agent_id: str = "",
    ) -> LoopDecision:
        if not self.enabled:
            return LoopDecision(allowed=True)
        scope = self._scope_key(user_id=user_id, workspace_id=workspace_id,
                                session_id=session_id, agent_id=agent_id)
        now = time.time()
        history = self._seen.setdefault(scope, [])
        # Prune stale entries.
        history[:] = [(q, ts) for q, ts in history if now - ts <= self.window_seconds]
        norm = " ".join(query.lower().split())
        repeats = sum(1 for q, _ in history if q == norm)
        history.append((norm, now))
        self._seen[scope] = history[-200:]
        if repeats >= self.max_repeats:
            return LoopDecision(
                allowed=False,
                reason=f"retrieval loop guard: same query seen {repeats} times "
                       f"within {self.window_seconds}s",
                repeated=repeats,
            )
        return LoopDecision(allowed=True, repeated=repeats)

    def reset(self, *, user_id: str = "", workspace_id: str = "",
              session_id: str = "", agent_id: str = "") -> None:
        scope = self._scope_key(user_id=user_id, workspace_id=workspace_id,
                                session_id=session_id, agent_id=agent_id)
        self._seen.pop(scope, None)