"""Compliance abstraction (§86-87): control mappings with honest
statuses (never auto-claims legal compliance) + signed evidence packs."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

STATUS = ("CONTROL_IMPLEMENTED", "CONTROL_PARTIAL", "CONTROL_UNVERIFIED",
          "CONTROL_NOT_APPLICABLE")


class ComplianceEngine:
    def __init__(self) -> None:
        self.controls: Dict[str, Dict[str, Any]] = {}

    def map(self, control_id: str, framework: str, status: str,
            evidence: Optional[List[str]] = None) -> None:
        if status not in STATUS:
            raise ValueError(f"unknown status {status}")
        self.controls[control_id] = {"framework": framework,
                                     "status": status,
                                     "evidence": list(evidence or []),
                                     "at": time.time()}

    def report(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for c in self.controls.values():
            by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        return {"controls": self.controls, "summary": by_status,
                "note": "mapping evidence, not legal certification"}

    def evidence_pack(self, refs: Dict[str, Any]) -> Dict[str, Any]:
        """Audit-ready bundle with content hash (§87)."""
        body = json.dumps(refs, sort_keys=True, default=str)
        return {"pack": refs,
                "sha256": hashlib.sha256(body.encode()).hexdigest(),
                "at": time.time(),
                "contents": ["identity records", "delegations",
                             "policy versions", "approval records",
                             "execution receipts", "audit events",
                             "verification evidence", "incident records",
                             "configuration hashes", "test results"]}
