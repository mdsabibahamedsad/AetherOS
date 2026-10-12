"""Shared fixtures: isolated homes, seeded registry, stub gateway."""

from __future__ import annotations

import pytest

from aetheros_agent_market import schemas as S


@pytest.fixture
def home(tmp_path):
    h = tmp_path / "market"
    h.mkdir()
    return h


@pytest.fixture
def flow(home):
    from aetheros_agent_market.flow import MarketplaceFlow
    return MarketplaceFlow(home, gateway_factory=StubGateway)


class StubRemote:
    def __init__(self, task_id="rt-stub-1", status="accepted"):
        self.task_id = task_id
        self.status = status
        self.sent = []


class StubGateway:
    """Test-only A2A stand-in. Behaves like AgentGateway.delegate/poll."""

    last = None

    def __init__(self):
        self.sent = []
        StubGateway.last = self

    def delegate(self, agent_id, purpose, message, permissions=None,
                 data_scope="internal", origin_agent="", owner="",
                 require_approval=False):
        self.sent.append({"agent_id": agent_id, "purpose": purpose})
        return StubRemote(task_id=f"rt-{len(self.sent)}", status="accepted")

    def poll(self, task_id):
        return StubRemote(task_id=task_id, status="completed")


def seed_service(flow, agent_id="agent-acme-1", org="acme",
                 pricing="free", caps=("research.web_search",),
                 price_minor=0):
    ident = S.MarketplaceIdentity(
        identity_id=S.new_id("ident"), agent_id=agent_id,
        organization_id=org, display_name="Acme Research",
        issuer="test", verification_status="unverified")
    flow.registry.register_agent(ident)
    svc = S.AgentService(
        service_id=S.new_id("msvc"), agent_id=agent_id,
        name="Acme Research", description="Web search with citations",
        capabilities=[{"capability_id": c, "protocols": ["A2A"],
                       "data_classes": ["PUBLIC", "INTERNAL"]} for c in caps],
        supported_protocols=["A2A"], supported_modalities=["text"],
        availability="available", pricing_model=pricing,
        status="published")
    flow.registry.publish_service(svc)
    if price_minor:
        offer = S.Offer(offer_id=S.new_id("offer"), service_id=svc.service_id,
                        agent_id=agent_id, price_minor=price_minor,
                        currency="USD")
        flow.registry.put_offer(offer)
    # Verified-ish signals so selection has nonzero components.
    flow.trust.record_signal(S.TrustSignal(
        agent_id=agent_id, dimension="identity", source="verification",
        kind="card_verified", value=0.8, confidence=0.9))
    flow.trust.record_signal(S.TrustSignal(
        agent_id=agent_id, dimension="execution", source="outcome",
        kind="task_success", value=0.7, confidence=0.8))
    flow.reputation.record(agent_id, "task_success", 0.9, provenance="verified")
    flow.reputation.record(agent_id, "security", 0.95, provenance="verified")
    flow.reputation.record(agent_id, "evidence_quality", 0.8, provenance="observed")
    return ident, svc
