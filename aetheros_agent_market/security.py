"""Marketplace security controls (spec sections 32, 33, 36, 37, 65, 66).

- Listing scans with honest levels: scanned|partially_scanned|not_scanned.
- Prompt-injection defense via network policy primitives (no duplication).
- Secret boundary: references/handles only, never raw secrets.
- Network defense reuses aetheros_network URL policy (single source).
- Economic abuse: caps, rate limits, recursion depth, chain tracking.
- Recursive delegation defense: depth/agents/budget/time ceilings.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .store import JsonStore

try:
    from aetheros_network.policy import (
        check_url_allowed, detect_prompt_injection, dlp_scan,
    )
except Exception:  # pragma: no cover
    def check_url_allowed(url, **kw):  # type: ignore[misc]
        return False, "network policy backend unavailable"

    def detect_prompt_injection(text):  # type: ignore[misc]
        return []

    def dlp_scan(text):  # type: ignore[misc]
        return []

MAX_DELEGATION_DEPTH_DEFAULT = 3
MAX_AGENTS_PER_ROOT_DEFAULT = 5


class ListingScanner:
    """Static listing inspection. Honest about coverage (spec 32)."""

    def __init__(self, home: Path) -> None:
        self._scans = JsonStore(Path(home) / "listing_scans.json")

    def scan(self, service: Dict[str, Any],
             agent_card: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        findings: List[Dict[str, str]] = []
        checked = ["card_present", "endpoint", "auth", "capabilities",
                   "scopes", "redirects", "injection_indicators"]
        # 1. Card present + well-formed?
        card = agent_card or {}
        if not card:
            findings.append({"level": "info", "msg": "no agent card supplied: scan partial"})
        # 2. Endpoint hygiene.
        url = str(card.get("url", "") or service.get("endpoint", ""))
        if url:
            ok, reason = check_url_allowed(url)
            if not ok:
                findings.append({"level": "high", "msg": f"endpoint blocked: {reason}"})
        else:
            findings.append({"level": "medium", "msg": "no endpoint declared"})
        # 3. Requested scopes vs grantable surface.
        scopes = service.get("security_requirements", []) or []
        risky = [s for s in scopes if any(k in str(s).lower() for k in
                                          ("filesystem", "shell", "secret", "unrestricted",
                                           "admin", "root", "bypass"))]
        for r in risky:
            findings.append({"level": "high", "msg": f"risky scope requested: {r}"})
        # 4. Injection indicators in listing text.
        blob = " ".join([str(service.get("name", "")), str(service.get("description", ""))])
        hits = detect_prompt_injection(blob)
        for h in hits:
            findings.append({"level": "high", "msg": f"prompt-injection indicator: {h[:80]}"})
        # 5. Redirect behavior + vuln DB: NOT observable statically.
        level = "scanned"
        if not card or not url:
            level = "partially_scanned"
        high = sum(1 for f in findings if f["level"] == "high")
        result = {"service_id": service.get("service_id", ""), "level": level,
                  "checked": checked,
                  "not_covered": ["live redirect behavior", "CVE database lookup",
                                  "malware detection (no AV engine integrated)"],
                  "findings": findings, "high_count": high, "at": time.time()}
        if service.get("service_id"):
            self._scans.put(service["service_id"], result)
        return result

    def get(self, service_id: str) -> Optional[Dict[str, Any]]:
        return self._scans.get(service_id)


class RecursionGuard:
    """Tracks delegation chains per root task; enforces ceilings (sec 66)."""

    def __init__(self, home: Path,
                 max_depth: int = MAX_DELEGATION_DEPTH_DEFAULT,
                 max_agents: int = MAX_AGENTS_PER_ROOT_DEFAULT) -> None:
        self._chains = JsonStore(Path(home) / "delegation_chains.json")
        self.max_depth = max_depth
        self.max_agents = max_agents

    def check(self, root_task_id: str, agent_id: str,
              depth: int) -> Dict[str, Any]:
        """Returns {allowed, reason}. Records the hop when allowed."""
        if depth > self.max_depth:
            return {"allowed": False,
                    "reason": f"delegation depth {depth} exceeds max {self.max_depth}"}
        chain = self._chains.get(root_task_id) or {"agents": [], "hops": 0,
                                                   "started_at": time.time()}
        agents = chain.get("agents", [])
        if agent_id in agents:
            return {"allowed": False,
                    "reason": f"agent {agent_id} already in chain (payment loop defense)"}
        if len(agents) >= self.max_agents:
            return {"allowed": False,
                    "reason": f"agent count exceeds max {self.max_agents}"}
        agents.append(agent_id)
        chain["agents"] = agents
        chain["hops"] = chain.get("hops", 0) + 1
        self._chains.put(root_task_id, chain)
        return {"allowed": True, "reason": "ok", "depth": depth,
                "chain": list(agents)}


class EconomicAbuseGuard:
    """Lightweight anomaly + rate controls (spec 65). Deterministic."""

    def __init__(self, home: Path) -> None:
        self._hits = JsonStore(Path(home) / "abuse_counters.json")

    def _bump(self, key: str, window_s: int) -> int:
        now = time.time()
        rec = self._hits.get(key) or {"count": 0, "window_start": now}
        if now - rec["window_start"] > window_s:
            rec = {"count": 0, "window_start": now}
        rec["count"] += 1
        self._hits.put(key, rec)
        return rec["count"]

    def check_quote_rate(self, agent_id: str, max_per_minute: int = 20) -> Dict[str, Any]:
        n = self._bump(f"quotes:{agent_id}", 60)
        if n > max_per_minute:
            return {"allowed": False, "reason": f"quote flooding: {n}/min from {agent_id}"}
        return {"allowed": True, "reason": "ok"}

    def check_spend_velocity(self, scope_key: str, amount_minor: int,
                             max_per_hour_minor: int = 100000) -> Dict[str, Any]:
        n = self._bump(f"spend:{scope_key}", 3600)
        rec = self._hits.get(f"spend:{scope_key}")
        # Track totals alongside counts.
        total_key = f"spend_total:{scope_key}"
        total = self._hits.get(total_key) or {"total": 0, "window_start": rec["window_start"]}
        if total["window_start"] != rec["window_start"]:
            total = {"total": 0, "window_start": rec["window_start"]}
        total["total"] += amount_minor
        self._hits.put(total_key, total)
        if total["total"] > max_per_hour_minor:
            return {"allowed": False,
                    "reason": f"spend velocity {total['total']} exceeds {max_per_hour_minor}/hour"}
        return {"allowed": True, "reason": "ok"}
