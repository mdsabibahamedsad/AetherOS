"""Typed IPC logic for agent.network.* (Master 46 section 130).

Pure functions over AgentGateway with strict input validation.
The tui_gateway server registers thin wrappers; Electron renderers
never touch network credentials — all authz happens here in main/backend.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_AGENT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
_DATA_SCOPES = ("public", "internal", "private", "sensitive", "highly_sensitive")
_TRUST_SETABLE = ("user_trusted", "organization_trusted", "fully_trusted",
                  "blocked", "revoked", "verified", "unverified")


def _check_agent_id(agent_id: Any) -> str:
    if not isinstance(agent_id, str) or not _AGENT_ID_RE.match(agent_id):
        raise ValueError(f"invalid agent id: {agent_id!r}")
    return agent_id


def _gateway():
    from .gateway import AgentGateway

    return AgentGateway()


def list_agents() -> Dict[str, Any]:
    gw = _gateway()
    return {"agents": [
        {"agent_id": r["agent_id"], "trust": gw.trust.level(r["agent_id"]),
         "health": r["health"], "source": r["source"],
         "latency_ms": r["latency_ms"], "removed": r["removed"]}
        for r in gw.registry.list()
    ]}


def discover(params: Dict[str, Any]) -> Dict[str, Any]:
    from .discovery import discover_from_url

    url = str(params.get("url", ""))
    if not url.startswith(("https://", "http://")):
        raise ValueError("url must start with https:// (http:// only in dev mode)")
    gw = _gateway()
    result = discover_from_url(url, gw.transport_config,
                               organization_id=str(params.get("organization_id", "")))
    if result.errors:
        return {"ok": False, "errors": result.errors}
    agent_id = gw.adopt_discovery(result)
    return {"ok": True, "agent_id": agent_id, "warnings": result.warnings,
            "verification": result.verification}


def info(params: Dict[str, Any]) -> Dict[str, Any]:
    agent_id = _check_agent_id(params.get("id", ""))
    gw = _gateway()
    rec = gw.registry.get_including_removed(agent_id)
    if rec is None:
        raise KeyError(f"unknown agent: {agent_id}")
    return {"agent_id": agent_id, "trust": gw.trust.level(agent_id),
            "health": rec.health, "removed": rec.removed,
            "source": rec.source, "provenance": rec.provenance,
            "latency_ms": rec.latency_ms, "card": rec.card,
            "identity": rec.identity}


def verify(params: Dict[str, Any]) -> Dict[str, Any]:
    from .agent_card import parse_agent_card, validate_agent_card

    agent_id = _check_agent_id(params.get("id", ""))
    gw = _gateway()
    rec = gw.registry.get(agent_id)
    if rec is None:
        raise KeyError(f"unknown agent: {agent_id}")
    card = parse_agent_card(rec.card)
    errors, warnings = validate_agent_card(card)
    checks = {"tls_ok": card.url.startswith("https://"),
              "issuer_ok": bool(rec.provenance),
              "expired": False,
              "endpoint_mismatch": any("endpoint substitution" in w for w in warnings),
              "card_errors": errors}
    label = gw.verify_agent(agent_id, checks)
    return {"agent_id": agent_id, "label": label,
            "errors": errors, "warnings": warnings}


def set_trust(params: Dict[str, Any]) -> Dict[str, Any]:
    agent_id = _check_agent_id(params.get("id", ""))
    level = str(params.get("level", ""))
    if level not in _TRUST_SETABLE:
        raise ValueError(f"invalid trust level: {level!r}")
    gw = _gateway()
    if level == "revoked":
        gw.revoke(agent_id, by="user:ipc")
    else:
        gw.set_trust(agent_id, level, by="user:ipc")
    return {"agent_id": agent_id, "trust": gw.trust.level(agent_id)}


def block(params: Dict[str, Any]) -> Dict[str, Any]:
    agent_id = _check_agent_id(params.get("id", ""))
    gw = _gateway()
    gw.set_trust(agent_id, "blocked", by="user:ipc")
    return {"agent_id": agent_id, "trust": "blocked"}


def revoke(params: Dict[str, Any]) -> Dict[str, Any]:
    agent_id = _check_agent_id(params.get("id", ""))
    gw = _gateway()
    gw.revoke(agent_id, by="user:ipc")
    return {"agent_id": agent_id, "trust": "revoked"}


def connect(params: Dict[str, Any]) -> Dict[str, Any]:
    import time

    from .transport import TransportError

    agent_id = _check_agent_id(params.get("id", ""))
    gw = _gateway()
    if gw.registry.get(agent_id) is None:
        raise KeyError(f"unknown agent: {agent_id}")
    t0 = time.time()
    try:
        raw = gw._transport_for(agent_id).fetch_agent_card()
        latency = (time.time() - t0) * 1000
        gw.registry.record_heartbeat(agent_id, "online", latency_ms=latency, success=True)
        return {"agent_id": agent_id, "health": "online",
                "latency_ms": round(latency, 1), "name": raw.get("name", "")}
    except TransportError as e:
        gw.registry.record_heartbeat(agent_id, "unavailable", success=False)
        return {"agent_id": agent_id, "health": "unavailable",
                "error": str(e), "kind": e.kind}


def disconnect(params: Dict[str, Any]) -> Dict[str, Any]:
    agent_id = _check_agent_id(params.get("id", ""))
    gw = _gateway()
    gw._transports.pop(agent_id, None)
    return {"agent_id": agent_id, "disconnected": True}


def delegate(params: Dict[str, Any]) -> Dict[str, Any]:
    agent_id = _check_agent_id(params.get("id", ""))
    purpose = str(params.get("task", ""))
    if not purpose or len(purpose) > 8000:
        raise ValueError("task purpose must be 1..8000 chars")
    scope = str(params.get("data_scope", "internal"))
    if scope not in _DATA_SCOPES:
        raise ValueError(f"invalid data_scope: {scope!r}")
    permissions = params.get("permissions", ["agent.task.submit"])
    if not isinstance(permissions, list) or not permissions:
        raise ValueError("permissions must be a non-empty list")
    gw = _gateway()
    task = gw.delegate(agent_id, purpose, {"text": purpose},
                       permissions=[str(p) for p in permissions][:16],
                       data_scope=scope, origin_agent="local:ipc",
                       owner=str(params.get("owner", "ipc")),
                       require_approval=not params.get("auto_approve", False))
    return {"task_id": task.task_id, "status": task.status}


def tasks(params: Dict[str, Any]) -> Dict[str, Any]:
    gw = _gateway()
    status = params.get("status") or None
    return {"tasks": [t.to_dict() for t in gw.tasks.list(status=status)],
            "queue": gw.tasks.queue_depth()}


def cancel(params: Dict[str, Any]) -> Dict[str, Any]:
    task_id = str(params.get("task", ""))
    if not task_id:
        raise ValueError("task id required")
    gw = _gateway()
    task = gw.cancel(task_id)
    return {"task_id": task.task_id, "status": task.status}


def activity(params: Dict[str, Any]) -> Dict[str, Any]:
    gw = _gateway()
    try:
        limit = min(int(params.get("limit", 100) or 100), 500)
    except (TypeError, ValueError):
        raise ValueError("limit must be an integer")
    return {"events": gw.audit.tail(limit)}


def security(params: Dict[str, Any]) -> Dict[str, Any]:
    gw = _gateway()
    trusted = blocked = pending = 0
    for r in gw.registry.list():
        level = gw.trust.level(r["agent_id"])
        if level in ("user_trusted", "organization_trusted", "fully_trusted"):
            trusted += 1
        elif level in ("blocked", "revoked"):
            blocked += 1
        else:
            pending += 1
    return {"trusted": trusted, "blocked": blocked, "pending": pending,
            "queue": gw.tasks.queue_depth()}


IPC_METHODS = {
    "agent.network.list": lambda p: list_agents(),
    "agent.network.discover": discover,
    "agent.network.info": info,
    "agent.network.verify": verify,
    "agent.network.trust": set_trust,
    "agent.network.block": block,
    "agent.network.revoke": revoke,
    "agent.network.connect": connect,
    "agent.network.disconnect": disconnect,
    "agent.network.delegate": delegate,
    "agent.network.tasks": tasks,
    "agent.network.cancel": cancel,
    "agent.network.activity": activity,
    "agent.network.security": security,
}
