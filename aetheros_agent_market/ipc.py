"""Typed IPC for marketplace.* (spec section 58).

Pure validated handlers over MarketplaceFlow/MarketplaceAPI. All input
validated at the boundary; sender origin checked by the gateway wrapper;
authz/policy enforced in backend engines. Never exposes raw ipcRenderer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

_ID_MAX = 160


def _check_id(value: Any, name: str = "id") -> str:
    if not isinstance(value, str) or not value or len(value) > _ID_MAX:
        raise ValueError(f"invalid {name}")
    if any(c in value for c in ("\n", "\r", "\x00")):
        raise ValueError(f"invalid {name}")
    return value


def _check_amount(value: Any) -> Optional[int]:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("amount must be a non-negative int (minor units)")
    return value


_flow = None


def get_flow(home: Optional[Path] = None):
    global _flow
    if _flow is None or home is not None:
        from .flow import MarketplaceFlow
        _flow = MarketplaceFlow(home)
    return _flow


def _api():
    from .api import MarketplaceAPI
    return MarketplaceAPI(get_flow())


def search(params: Dict[str, Any]) -> Dict[str, Any]:
    from .taxonomy import MatchRequest
    from .preferences import apply_preferences
    flow = get_flow()
    prefs = flow.preferences.effective()
    req = MatchRequest(
        query=str(params.get("query", ""))[:500],
        exact_capabilities=list(params.get("capabilities", []) or [])[:20],
        protocols=list(params.get("protocols", []) or [])[:10],
        modalities=list(params.get("modalities", []) or [])[:10],
        data_class=str(params.get("data_class", "INTERNAL")).upper()[:20],
        max_price_minor=_check_amount(params.get("max_price_minor")),
        max_latency_ms=params.get("max_latency_ms"),
    )
    req = apply_preferences(req, prefs)
    limit = min(int(params.get("limit", 25) or 25), 100)
    hits = flow.index.search(req, limit=limit)
    return {"hits": [{"service_id": h.service_id, "agent_id": h.agent_id,
                      "source": h.source, "exact": h.exact,
                      "keyword_score": h.keyword_score, "reasons": h.reasons,
                      "service": h.service} for h in hits],
            "query": req.query}


def agent_get(params: Dict[str, Any]) -> Dict[str, Any]:
    return _api().get_agent(_check_id(params.get("id"), "agent identity id"))


def service_get(params: Dict[str, Any]) -> Dict[str, Any]:
    return _api().get_service(_check_id(params.get("id"), "service id"))


def compare(params: Dict[str, Any]) -> Dict[str, Any]:
    from .selection import AgentSelectionEngine
    ids = params.get("agent_ids", []) or params.get("ids", [])
    if not isinstance(ids, list) or not (2 <= len(ids) <= 3):
        raise ValueError("compare requires 2-3 agent ids")
    flow = get_flow()
    rec = flow.recommend({"query": str(params.get("query", ""))[:300],
                          "capabilities": list(params.get("capabilities", []) or [])},
                         limit=50)
    wanted = {_check_id(i) for i in ids}
    found = [c for c in rec["candidates"] if c["agent_id"] in wanted]
    if len(found) < 2:
        raise KeyError("fewer than 2 compared agents are currently selectable")
    from .selection import ScoredCandidate
    cands = [ScoredCandidate(**c) for c in found[:3]]
    engine = AgentSelectionEngine()
    rows = []
    base = engine.compare(cands[0], cands[1])
    rows.append(base)
    if len(cands) == 3:
        rows.append(engine.compare(cands[0], cands[2]))
    return {"compared": [c.to_dict() for c in cands], "matrices": rows}


def quote_create(params: Dict[str, Any]) -> Dict[str, Any]:
    body = params.get("quote")
    if not isinstance(body, dict):
        raise ValueError("quote object required")
    return _api().post_quotes(body)


def contract_create(params: Dict[str, Any]) -> Dict[str, Any]:
    body = params.get("contract")
    if not isinstance(body, dict):
        raise ValueError("contract object required")
    return _api().post_contracts(body)


def contract_approve(params: Dict[str, Any]) -> Dict[str, Any]:
    flow = get_flow()
    contract = flow.contracts.approve(_check_id(params.get("id"), "contract id"),
                                      by=str(params.get("by", "user"))[:120])
    return {"contract": contract.to_dict()}


def delegate(params: Dict[str, Any]) -> Dict[str, Any]:
    return _api().post_delegations(params)


def task_status(params: Dict[str, Any]) -> Dict[str, Any]:
    flow = get_flow()
    did = _check_id(params.get("id"), "delegation id")
    try:
        return flow.poll(did)
    except KeyError:
        return _api().get_delegation(did)["delegation"]


def transaction_get(params: Dict[str, Any]) -> Dict[str, Any]:
    return _api().get_transactions(contract_id=str(params.get("contract_id", ""))[:_ID_MAX])


def reputation_get(params: Dict[str, Any]) -> Dict[str, Any]:
    return _api().get_reputation(_check_id(params.get("id"), "agent id"))


def trust_get(params: Dict[str, Any]) -> Dict[str, Any]:
    return _api().get_trust(_check_id(params.get("id"), "agent id"))


def budget_get(params: Dict[str, Any]) -> Dict[str, Any]:
    flow = get_flow()
    scope = str(params.get("scope", "user"))[:40]
    if scope not in ("global", "user", "workspace", "project", "automation",
                     "agent", "task", "contract"):
        raise ValueError("bad budget scope")
    return flow.budgets.usage(scope, str(params.get("scope_id", ""))[:120])


def policy_get(params: Dict[str, Any]) -> Dict[str, Any]:
    flow = get_flow()
    return {"preferences": flow.preferences.effective().to_dict(),
            "flags": {f: flow.flags.is_enabled(f)
                      for f in ("marketplace", "remote_delegation", "paid_agents",
                                "automatic_negotiation", "automatic_payment",
                                "external_registries", "organization_marketplace")}}


def policy_update(params: Dict[str, Any]) -> Dict[str, Any]:
    from .preferences import AgentPreferences
    flow = get_flow()
    body = params.get("preferences")
    if not isinstance(body, dict):
        raise ValueError("preferences object required")
    prefs = AgentPreferences.from_dict(body)
    # Import-style safety: updates never enable auto-spend silently.
    flow.preferences.put(prefs)
    return {"preferences": flow.preferences.effective().to_dict()}


def dispute_create(params: Dict[str, Any]) -> Dict[str, Any]:
    from . import schemas as S
    flow = get_flow()
    body = params.get("dispute")
    if not isinstance(body, dict):
        raise ValueError("dispute object required")
    for key in ("transaction_id", "contract_id", "agent_id", "reason"):
        if key not in body:
            raise ValueError(f"missing dispute field: {key}")
    d = S.Dispute(dispute_id=body.get("dispute_id", "") or S.new_id("dispute"),
                  transaction_id=str(body["transaction_id"])[:_ID_MAX],
                  contract_id=str(body["contract_id"])[:_ID_MAX],
                  delegation_id=str(body.get("delegation_id", ""))[:_ID_MAX],
                  agent_id=_check_id(body["agent_id"], "agent id"),
                  reason=str(body["reason"])[:60],
                  description=str(body.get("description", ""))[:2000])
    opened = flow.disputes.open(d, opened_by=str(params.get("by", "user"))[:120])
    flow.events.emit("DisputeOpened", actor="user",
                     contract_id=opened.contract_id,
                     delegation_id=opened.delegation_id,
                     agent_id=opened.agent_id,
                     data={"dispute_id": opened.dispute_id, "reason": opened.reason})
    return {"dispute": opened.to_dict()}


IPC_METHODS = {
    "marketplace.search": search,
    "marketplace.agent.get": agent_get,
    "marketplace.service.get": service_get,
    "marketplace.compare": compare,
    "marketplace.quote": quote_create,
    "marketplace.contract.create": contract_create,
    "marketplace.contract.approve": contract_approve,
    "marketplace.delegate": delegate,
    "marketplace.task.status": task_status,
    "marketplace.transaction.get": transaction_get,
    "marketplace.reputation.get": reputation_get,
    "marketplace.trust.get": trust_get,
    "marketplace.budget.get": budget_get,
    "marketplace.policy.get": policy_get,
    "marketplace.policy.update": policy_update,
    "marketplace.dispute.create": dispute_create,
}
