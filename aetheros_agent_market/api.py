"""Versioned marketplace API contracts (spec section 70).

v1 function API: GET /agents, /agents/{id}, /services, /services/{id},
/offers, POST /quotes, /contracts, /delegations, GET /delegations/{id},
/transactions, /reputation, /trust. Schema-validated I/O, tenant-aware
via organization_id filters, server-derived economics (client-provided
price/trust/reputation/settlement/verdicts are NEVER trusted).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import schemas as S
from .flow import MarketplaceFlow

API_VERSION = "v1"


def _paginate(items: List[Any], limit: int, offset: int) -> Dict[str, Any]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return {"items": items[offset:offset + limit], "total": len(items),
            "limit": limit, "offset": offset, "api_version": API_VERSION}


class MarketplaceAPI:
    """Thin validated facade over MarketplaceFlow + engines."""

    def __init__(self, flow: MarketplaceFlow) -> None:
        self.flow = flow

    # -- agents -----------------------------------------------------------
    def get_agents(self, organization_id: str = "", limit: int = 50,
                   offset: int = 0) -> Dict[str, Any]:
        agents = self.flow.registry.discover_agents(
            {"organization_id": organization_id} if organization_id else {})
        return _paginate(agents, limit, offset)

    def get_agent(self, identity_id: str) -> Dict[str, Any]:
        if not identity_id or len(identity_id) > 128:
            raise ValueError("invalid identity id")
        rec = self.flow.registry.get_agent(identity_id)
        if rec is None:
            raise KeyError(f"unknown agent: {identity_id}")
        trust = self.flow.trust.profile(rec.get("agent_id", ""))
        reputation = self.flow.reputation.profile(rec.get("agent_id", "")).to_dict()
        return {"agent": rec, "trust": trust, "reputation": reputation,
                "api_version": API_VERSION}

    # -- services / offers --------------------------------------------------
    def get_services(self, agent_id: str = "", pricing_model: str = "",
                     limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        filters: Dict[str, Any] = {"status": "published"}
        if agent_id:
            filters["agent_id"] = agent_id
        if pricing_model:
            filters["pricing_model"] = pricing_model
        return _paginate(self.flow.registry.discover_services(filters), limit, offset)

    def get_service(self, service_id: str) -> Dict[str, Any]:
        if not service_id or len(service_id) > 128:
            raise ValueError("invalid service id")
        rec = self.flow.registry.get_service(service_id)
        if rec is None:
            raise KeyError(f"unknown service: {service_id}")
        return {"service": rec,
                "listing": self.flow.registry.verify_listing(service_id),
                "scan": self.flow.scanner.get(service_id),
                "api_version": API_VERSION}

    def get_offers(self, service_id: str = "") -> Dict[str, Any]:
        offers = [o for o in self.flow.registry._offers.values()
                  if not service_id or o.get("service_id") == service_id]
        return {"offers": offers, "api_version": API_VERSION}

    # -- quotes / contracts / delegations -------------------------------------
    def post_quotes(self, body: Dict[str, Any]) -> Dict[str, Any]:
        quote = S.Quote.from_dict(body)
        recorded = self.flow.quotes.record_quote(quote)
        return {"quote": recorded.to_dict(), "api_version": API_VERSION}

    def post_contracts(self, body: Dict[str, Any]) -> Dict[str, Any]:
        contract = S.DelegationContract.from_dict(body)
        created = self.flow.contracts.create(contract)
        return {"contract": created.to_dict(), "api_version": API_VERSION}

    def post_delegations(self, body: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("task", "selection"):
            if key not in body:
                raise ValueError(f"missing field: {key}")
        if not isinstance(body["task"], dict) or not isinstance(body["selection"], dict):
            raise ValueError("task/selection must be objects")
        return self.flow.delegate(body["task"], body["selection"],
                                  approved_by=str(body.get("approved_by", "")),
                                  auto=bool(body.get("auto", False)))

    def get_delegation(self, delegation_id: str) -> Dict[str, Any]:
        if not delegation_id or len(delegation_id) > 128:
            raise ValueError("invalid delegation id")
        raw = self.flow._delegations.get(delegation_id)
        if raw is None:
            raise KeyError(f"unknown delegation: {delegation_id}")
        events = self.flow.events.list(delegation_id=delegation_id)
        return {"delegation": raw, "events": events, "api_version": API_VERSION}

    # -- transactions / reputation / trust --------------------------------------
    def get_transactions(self, contract_id: str = "") -> Dict[str, Any]:
        entries = self.flow.ledger.entries(limit=100000)
        items = [e.to_dict() for e in entries
                 if not contract_id or e.contract_id == contract_id][:200]
        return {"entries": items, "accounting": self.flow.accounting.summary(),
                "api_version": API_VERSION}

    def get_reputation(self, agent_id: str) -> Dict[str, Any]:
        if not agent_id or len(agent_id) > 160:
            raise ValueError("invalid agent id")
        return {"reputation": self.flow.reputation.profile(agent_id).to_dict(),
                "api_version": API_VERSION}

    def get_trust(self, agent_id: str) -> Dict[str, Any]:
        if not agent_id or len(agent_id) > 160:
            raise ValueError("invalid agent id")
        return {"trust": self.flow.trust.profile(agent_id),
                "api_version": API_VERSION}
