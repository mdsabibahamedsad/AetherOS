"""Trust scores (§56-57) + privilege graph analysis (§184-186):
advisory scores that NEVER override hard deny, plus graph algorithms
for overbroad delegation, cycles, amplification, orphaned/expired
authority, and unreachable revocation."""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Set, Tuple

from .models import TrustScore

FACTORS = ("identity integrity", "attestation", "history",
           "policy compliance", "failure rate", "verification success",
           "incident history", "provenance completeness",
           "publisher trust", "capability scope", "environment", "age",
           "recency", "anomaly score")


class TrustScoreEngine:
    """Explained, factorized summary. Hard deny always wins (§56)."""

    def __init__(self) -> None:
        self._scores: Dict[str, TrustScore] = {}

    def score(self, identity_id: str,
              factors: Dict[str, float]) -> TrustScore:
        clean = {k: max(0.0, min(1.0, float(v)))
                 for k, v in factors.items() if k in FACTORS}
        avg = sum(clean.values()) / len(clean) if clean else 0.0
        ts = TrustScore(identity_id, round(avg, 3), clean)
        self._scores[identity_id] = ts
        return ts

    def influence(self, score: TrustScore) -> Dict[str, str]:
        """What a score MAY influence — never authorization itself."""
        s = score.score
        return {"approval_friction": "low" if s > 0.8 else "normal",
                "rate_limit_tier": "relaxed" if s > 0.8 else "standard",
                "default_autonomy": "L3" if s > 0.85 else "L2",
                "delegation_eligibility": "yes" if s > 0.7 else "review",
                "hard_policy_override": "NEVER"}

    def posture(self, checks: Dict[str, bool],
                criticals: List[str]) -> Dict[str, str]:
        if any(not checks.get(c, False) for c in criticals):
            level = "CRITICAL"
        elif not all(checks.values()):
            level = "MODERATE"
        else:
            level = "GOOD"
        return {"level": level,
                "note": "summary only — see per-check evidence"}


class PrivilegeGraph:
    """Delegation/authority graph analysis (§185). Nodes are
    'kind:id'; edges carry scope sets."""

    def __init__(self) -> None:
        self.edges: Dict[str, Dict[str, Set[str]]] = {}
        self.expiry: Dict[str, float] = {}

    def grant(self, src: str, dst: str, scopes: List[str],
              expires_at: float = 0.0) -> None:
        self.edges.setdefault(src, {})[dst] = set(scopes)
        self.expiry[f"{src}->{dst}"] = expires_at

    def revoke_edge(self, src: str, dst: str) -> None:
        self.edges.get(src, {}).pop(dst, None)
        self.expiry.pop(f"{src}->{dst}", None)

    def reachable(self, root: str) -> Set[str]:
        seen, stack = set(), [root]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(self.edges.get(node, ()))
        return seen

    def find_cycles(self) -> List[List[str]]:
        cycles = []
        color: Dict[str, int] = {}

        def dfs(node: str, path: List[str]) -> None:
            color[node] = 1
            path.append(node)
            for nxt in self.edges.get(node, ()):
                if color.get(nxt) == 1:
                    cycles.append(path[path.index(nxt):] + [nxt])
                elif not color.get(nxt):
                    dfs(nxt, path)
            path.pop()
            color[node] = 2

        for n in list(self.edges):
            if not color.get(n):
                dfs(n, [])
        return cycles

    def amplification(self) -> List[Dict[str, str]]:
        """Child scope-supersets of parent grants (§188 violation)."""
        out = []
        for src, dsts in self.edges.items():
            src_scopes = self._inherited_scopes(src)
            for dst, scopes in dsts.items():
                extra = set(scopes) - src_scopes
                if extra and src_scopes:
                    out.append({"edge": f"{src}->{dst}",
                                "beyond_parent": sorted(extra)})
        return out

    def _inherited_scopes(self, node: str) -> Set[str]:
        incoming: Set[str] = set()
        for src, dsts in self.edges.items():
            if node in dsts:
                incoming |= dsts[node]
        if incoming:
            return incoming
        # root authority: its own declared grants bound its children
        return set().union(*self.edges.get(node, {}).values()) \
            if self.edges.get(node) else set()

    def orphaned(self, live: Set[str]) -> List[str]:
        nodes = set(self.edges) | {d for dsts in self.edges.values()
                                   for d in dsts}
        return sorted(n for n in nodes if n not in live)

    def expired(self, now: Optional[float] = None) -> List[str]:
        import time as _t
        now = now if now is not None else _t.time()
        return sorted(e for e, exp in self.expiry.items()
                      if exp and exp < now)
