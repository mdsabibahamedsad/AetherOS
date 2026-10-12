"""Revocation propagation (§122-123): revoking authority walks
agent -> sub-agent -> capability token -> tool/session/JIT, with an
emergency mode that strips temporary/background/remote/high-risk
authority per policy. No reliance on UI refresh."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Set

from .models import RevocationRecord


class RevocationAuthority:
    def __init__(self) -> None:
        self.records: List[RevocationRecord] = []
        self._revoked: Set[str] = set()  # "kind:id"
        # dependency edges parent -> children for propagation walks
        self._edges: Dict[str, Set[str]] = {}
        self._listeners: List[Callable[[RevocationRecord], None]] = []

    def on_revoke(self, fn: Callable[[RevocationRecord], None]) -> None:
        self._listeners.append(fn)

    def link(self, parent_kind: str, parent_id: str,
             child_kind: str, child_id: str) -> None:
        self._edges.setdefault(f"{parent_kind}:{parent_id}",
                               set()).add(f"{child_kind}:{child_id}")

    def revoke(self, target_kind: str, target_id: str, reason: str,
               actor: str = "trust-fabric") -> RevocationRecord:
        """Depth-first propagation across the authority graph."""
        seen: List[str] = []
        stack = [f"{target_kind}:{target_id}"]
        while stack:
            node = stack.pop()
            if node in self._revoked:
                continue
            self._revoked.add(node)
            seen.append(node)
            stack.extend(sorted(self._edges.get(node, ())) )
        rec = RevocationRecord(target_kind, target_id, reason, actor,
                               propagated_to=tuple(seen))
        self.records.append(rec)
        for fn in self._listeners:
            try:
                fn(rec)
            except Exception:
                pass
        return rec

    def is_revoked(self, target_kind: str, target_id: str) -> bool:
        return f"{target_kind}:{target_id}" in self._revoked

    def emergency_revoke(self, policy: Optional[Dict[str, bool]] = None
                         ) -> List[RevocationRecord]:
        """Strip classes of authority per emergency policy (§123)."""
        pol = policy or {"temporary": True, "background": True,
                         "remote": True, "high_risk_sessions": True}
        out = []
        for key in sorted(self._edges):
            kind, _ = key.split(":", 1)
            if (kind == "capability" and pol.get("temporary")) or \
               (kind == "automation" and pol.get("background")) or \
               (kind == "remote-agent" and pol.get("remote")) or \
               (kind == "session" and pol.get("high_risk_sessions")):
                k, i = key.split(":", 1)
                out.append(self.revoke(k, i, "emergency revocation",
                                       actor="emergency-controller"))
        return out
