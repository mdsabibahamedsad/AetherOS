"""Canonical marketplace event model (spec section 59).

Typed, versioned, correlated, auditable, deduplicated. Emitted by the
flow engine; stored append-only; consumers dedupe on event_id.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .store import JsonStore

EVENT_TYPES = (
    "MarketplaceDiscovered", "AgentVerified", "ServiceDiscovered",
    "OfferCreated", "QuoteReceived", "ContractCreated", "ContractApproved",
    "DelegationStarted", "DelegationProgress", "EvidenceReceived",
    "VerificationStarted", "VerificationPassed", "VerificationFailed",
    "PaymentAuthorized", "PaymentCaptured", "PaymentRefunded",
    "DisputeOpened", "ReputationUpdated", "AgentSuspended", "AgentRevoked",
)

EVENT_VERSION = "1"


class EventBus:
    def __init__(self, home: Path) -> None:
        self._store = JsonStore(Path(home) / "events.json")
        self._seen: set = set()
        for raw in self._store.values():
            self._seen.add(raw.get("event_id", ""))

    def emit(self, kind: str, actor: str = "",
             contract_id: str = "", delegation_id: str = "",
             task_id: str = "", agent_id: str = "",
             correlation_id: str = "", data: Optional[Dict[str, Any]] = None,
             event_id: str = "") -> Dict[str, Any]:
        if kind not in EVENT_TYPES:
            raise ValueError(f"bad event type: {kind!r}")
        eid = event_id or S.new_id("evt")
        if eid in self._seen:
            # Deduplicated: return the original.
            return self._store.get(eid)
        event = {"event_id": eid, "event_version": EVENT_VERSION,
                 "type": kind, "actor": actor, "contract_id": contract_id,
                 "delegation_id": delegation_id, "task_id": task_id,
                 "agent_id": agent_id,
                 "correlation_id": correlation_id or S.new_id("corr"),
                 "data": data or {}, "at": time.time()}
        self._store.put(eid, event)
        self._seen.add(eid)
        return event

    def list(self, delegation_id: str = "", kind: str = "",
             correlation_id: str = "", limit: int = 500) -> List[Dict[str, Any]]:
        out = []
        for raw in self._store.values():
            if delegation_id and raw.get("delegation_id") != delegation_id:
                continue
            if kind and raw.get("type") != kind:
                continue
            if correlation_id and raw.get("correlation_id") != correlation_id:
                continue
            out.append(raw)
        out.sort(key=lambda e: e.get("at", 0))
        return out[-limit:]
