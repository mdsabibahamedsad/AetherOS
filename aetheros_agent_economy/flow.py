"""MarketplaceFlow wrapper with economy extensions (spec 4-8, 100-103).

Wraps the core aetheros_agent_market.MarketplaceFlow and adds:
- PlanOptimizer for intelligent delegation planning
- PlanSimulator for what-if analysis
- CapabilityGraph for live provider discovery
- RiskEngine integration
- AutopilotEngine integration
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_agent_market.flow import MarketplaceFlow as BaseMarketplaceFlow
from aetheros_agent_market.taxonomy import MatchRequest
from aetheros_agent_market.preferences import apply_preferences, preference_veto
from aetheros_agent_market.selection import AgentSelectionEngine, CandidateSignals
from aetheros_agent_market.taxonomy import expand_query_terms
from aetheros_agent_market import schemas as S

from .capabilities import CapabilityRegistry
from .composition import CapabilityCompositionEngine, CapabilityGraph
from .capverify import CapabilityVerificationEngine
from .planner import PlanOptimizer, PlanSimulator
from .reputation import PerformanceProfiler, DiscoveryLearner
from .capverify import CapabilityVerificationEngine
from .contracts2 import CompositeContractEngine, ConditionalSettlementEngine
from .tokens_risk_autopilot import RiskEngine, AutopilotEngine
from .governance import AnomalyDetector, CollusionDetector, MarketplaceHealthEngine, MarketplaceGovernanceEngine
from aetheros_agent_market.store import market_home


class MarketplaceFlow:
    """Extended marketplace flow with economy extensions."""

    def __init__(self, home: Optional[Path] = None,
                 gateway_factory: Optional[Callable[[], Any]] = None) -> None:
        self.home = Path(home) if home else market_home()
        self.home.mkdir(parents=True, exist_ok=True)
        self._base = BaseMarketplaceFlow(home, gateway_factory)
        self.registry = self._base.registry
        self.trust = self._base.trust
        self.index = self._base.index
        self.reputation = self._base.reputation
        self.contracts = self._base.contracts
        self.quotes = self._base.quotes
        self.budgets = self._base.budgets
        self.ledger = self._base.ledger
        self.accounting = self._base.accounting
        self.disputes = self._base.disputes
        self.verifier = self._base.verifier
        self.evidence = self._base.evidence
        self.events = self._base.events
        self.scanner = self._base.scanner
        self.recursion = self._base.recursion
        self.abuse = self._base.abuse
        self.flags = self._base.flags
        self.kill = self._base.kill
        self.preferences = self._base.preferences
        self._delegations = self._base._delegations
        self._providers_used = self._base._providers_used
        self._base._gateway_factory = gateway_factory or self._default_gateway

        # Economy extensions
        self.registry = CapabilityRegistry(self.home)
        self.index = CapabilityIndex()
        self.index.add_provider("market", self._market_provider())
        try:
            from .discovery import network_services_provider
            self.index.add_provider("trusted_a2a", network_services_provider())
        except Exception:
            pass
        self.trust = None  # Use base trust
        self.reputation = None  # Use base reputation
        self.contracts = CompositeContractEngine(self.home)
        self.quotes = QuotingEngine(self.home)
        self.budgets = BudgetManager(self.home)
        self.ledger = Ledger(self.home / "ledger.jsonl")
        self.accounting = CostAccounting(self.home, self.ledger)
        self.disputes = DisputeEngine(self.home)
        self.verifier = ResultVerificationEngine()
        self.evidence = EvidenceStore(self.home)
        self.events = EventBus(self.home)
        self.scanner = ListingScanner(self.home)
        self.recursion = RecursionGuard(self.home)
        self.abuse = EconomicAbuseGuard(self.home)
        self.flags = FeatureFlags(self.home)
        self.kill = KillSwitch(self.home, self.flags)
        self.preferences = PreferenceStore(self.home)
        from .store import JsonStore
        self._delegations = JsonStore(self.home / "delegations.json")
        self._providers_used = JsonStore(self.home / "delegation_providers.json")

        # Economy extensions
        self.optimizer = PlanOptimizer(self)
        self.simulator = PlanSimulator(self)
        self.risk_engine = RiskEngine(self.home, self)
        self.autopilot = AutopilotEngine(self)
        self.anomaly_detector = AnomalyDetector(self.home, self)
        self.collusion_detector = CollusionDetector(self.home, self)
        self.health_engine = MarketplaceHealthEngine(self)
        self.governance = MarketplaceGovernanceEngine(self.home, self)
        self.capability_registry = CapabilityRegistry(self.home)
        self.composition_engine = CapabilityCompositionEngine(self.home, self.capability_registry)
        self.capability_graph = CapabilityGraph(self.capability_registry, self)
        self.capability_verifier = CapabilityVerificationEngine(self.home, self)
        self.composite_contracts = CompositeContractEngine(self.home)
        self.conditional_settlement = ConditionalSettlementEngine(self)
        self._gateway_factory = gateway_factory or self._default_gateway

    def _default_gateway(self):
        from aetheros_network.gateway import AgentGateway
        return AgentGateway()

    def _market_provider(self):
        """Local-registry services with effective trust ranks."""
        def _fn():
            services = self.registry.discover_services({"status": "published"})
            agent_ids = sorted({s.get("agent_id", "") for s in services})
            try:
                summaries = self.trust.summaries(agent_ids)
            except Exception:
                summaries = {}
            out = []
            for svc in services:
                aid = svc.get("agent_id", "")
                mapped = self._map_overall(summaries.get(aid, {}).get("overall", 0.0))
                out.append(IndexedService(
                    service=svc, source="market",
                    trust_rank=max(self._network_rank(aid), mapped),
                    regions=[]))
            return out
        return _fn

    @staticmethod
    def _map_overall(overall: float) -> int:
        try:
            return int(round((max(-1.0, min(1.0, overall)) + 1.0) / 2.0 * 6.0))
        except Exception:
            return 0

    def _network_rank(self, agent_id: str) -> int:
        try:
            from aetheros_network.trust import trust_rank as _rank
            return _rank(self._base.trust.level(agent_id))
        except Exception:
            return 0

    def _effective_rank(self, agent_id: str) -> int:
        return max(self._network_rank(agent_id),
                   self._map_overall(self.trust.profile(agent_id)["overall"]))

    def local_assessment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        req = MatchRequest(query=task.get("query", ""),
                           exact_capabilities=task.get("capabilities", []))
        local_hits = [h for h in self.index.search(req, limit=100)
                      if h.source in ("market",)]
        local_capable = any(h.exact for h in local_hits)
        return {"local_capable": local_capable,
                "local_candidates": len(local_hits),
                "note": "local execution cost/latency measured at runtime; "
                        "no savings claimed without measurement"}

    def recommend(self, task: Dict[str, Any],
                  goal: str = "balanced",
                  limit: int = 5) -> Dict[str, Any]:
        """Discover -> policy -> trust -> reputation -> compare -> select.
        Read-only: no contracts, quotes, payments, or delegations created."""
        self.flags.require("marketplace")
        prefs = self.preferences.effective(task.get("scopes"))
        req = MatchRequest(
            query=task.get("query", ""),
            exact_capabilities=task.get("capabilities", []),
            protocols=task.get("protocols", []),
            modalities=task.get("modalities", []),
            data_class=task.get("data_class", "INTERNAL"),
            max_price_minor=task.get("max_price_minor"),
            max_latency_ms=task.get("max_latency_ms"),
        )
        req = apply_preferences(req, prefs)
        hits = self.index.search(req, limit=100)
        engine = AgentSelectionEngine(goal)
        cands: List[CandidateSignals] = []
        vetoed: List[Dict[str, str]] = []
        hit_agents = sorted({h.service.get("agent_id", "") for h in hits})
        try:
            t_sums = self.trust.summaries(hit_agents)
        except Exception:
            t_sums = {}
        try:
            r_profs = self.reputation.profiles_for(hit_agents)
        except Exception:
            r_profs = {}
        for h in hits:
            org = str(h.service.get("organization_id", ""))
            veto = preference_veto(h.service.get("agent_id", ""), org, prefs)
            if veto:
                vetoed.append({"agent_id": h.service.get("agent_id", ""),
                               "reason": veto})
                continue
            ts = t_sums.get(h.service.get("agent_id", ""), {})
            rp = r_profs.get(h.service.get("agent_id", ""),
                             S.ReputationProfile(agent_id="")).to_dict()
            price = self._service_price(h.service)
            sec = rp.get("security", {})
            sec_value = 0.5 if not sec.get("sample_count") else sec.get("value", 0.0)
            cands.append(CandidateSignals(
                agent_id=h.service.get("agent_id", ""),
                service_id=h.service.get("service_id", ""),
                source=h.source,
                capability_fit=1.0 if h.exact else max(0.1, h.keyword_score),
                trust_overall=ts.get("overall", 0.0),
                trust_confidence=ts.get("confidence", 0.0),
                reliability=rp.get("task_success", {}).get("value", 0.0),
                reliability_confidence=rp.get("task_success", {}).get("confidence", 0.0),
                security=sec_value,
                evidence_quality=rp.get("evidence_quality", {}).get("value", 0.0),
                price_minor=price,
                latency_ms=self._service_latency(h.service),
                sla_ok=True, available=h.service.get("availability") != "unavailable",
                privacy_ok=True, org_id=org,
                preferred=h.service.get("agent_id", "") in prefs.preferred_agents,
            ))
        ranked = engine.rank(cands, budget_minor=task.get("budget_minor"), limit=limit)
        return {"candidates": [s.to_dict() for s in ranked],
                "explanations": [s.explanation() for s in ranked],
                "vetoed": vetoed,
                "local": self.local_assessment(task),
                "goal": goal}

    def _service_price(self, service: Dict[str, Any]) -> Optional[int]:
        for offer in self.registry._offers.values():
            if offer.get("service_id") == service.get("service_id") \
                    and offer.get("status") == "open" and not S.Offer.from_dict(offer).is_expired:
                return int(offer.get("price_minor", 0))
        if service.get("service_id", "").startswith("a2a:"):
            return None
        return 0 if service.get("pricing_model") == "free" else None

    def _service_latency(self, service: Dict[str, Any]) -> Optional[float]:
        sla = service.get("sla", {}) or {}
        val = sla.get("max_latency_ms")
        return float(val) if isinstance(val, (int, float)) else None

    def delegate(self, task: Dict[str, Any], selection: Dict[str, Any],
                 approved_by: str = "", auto: bool = False) -> Dict[str, Any]:
        """Full pipeline with gates. Raises FlowError on any gate failure."""
        corr = S.new_id("corr")
        self.flags.require("remote_delegation")
        if check_restore_integrity(self.home)["safe_mode"]:
            raise FlowError("marketplace safe mode: ledger integrity failure")

        service_id = selection.get("service_id", "")
        svc_raw = self.registry.get_service(service_id)
        a2a_service = selection.get("source") == "trusted_a2a"
        if svc_raw is None and not a2a_service:
            raise FlowError(f"unknown service: {service_id}")
        service = svc_raw or {"service_id": service_id,
                              "agent_id": selection.get("agent_id", ""),
                              "name": service_id, "pricing_model": "quote",
                              "status": "published", "capabilities": []}
        agent_id = selection.get("agent_id", "")

        root = task.get("root_task_id", S.new_id("root"))
        depth = int(task.get("delegation_depth", 1))
        gate = self.recursion.check(root, agent_id, depth)
        if not gate["allowed"]:
            raise FlowError(f"recursion guard: {gate['reason']}")

        _enable = lambda f: None  # placeholder
        _task = lambda **kw: {"summary": "t", "capabilities": [], "data_class": "INTERNAL",
                              "verification_requirements": ["schema"],
                              "payment_provider": "none", "requester": "test"}  # placeholder

        # Quote
        quote = self._obtain_quote(service, agent_id, task, corr)
        if quote.total_minor > 0:
            self.flags.require("paid_agents")

        # Contract
        contract = self._build_contract(service, agent_id, quote, task, corr, root)
        self.events.emit("ContractCreated", actor="local", contract_id=contract.contract_id,
                         agent_id=agent_id, correlation_id=corr,
                         data={"version": contract.version})

        # Budget gate + abuse velocity
        reservation = self.budgets.reserve(quote.total_minor, "task", contract.contract_id)
        ok, reason = self.budgets.check_spend(quote.total_minor, "user")
        if not ok:
            self.budgets.release(reservation)
            raise FlowError(f"budget denied: {reason}")
        vel = self.abuse.check_spend_velocity("user", quote.total_minor)
        if not vel["allowed"]:
            self.budgets.release(reservation)
            raise FlowError(f"economic abuse guard: {vel['reason']}")
        tier = self.budgets.approval_tier(quote.total_minor,
                                          self.budgets.get_budget("user"))
        needs_human = tier in ("HUMAN_APPROVAL",) or \
            (tier == "CONDITIONAL_APPROVAL" and not approved_by) or \
            self.preferences.effective(task.get("scopes")).approvals_required
        if needs_human and not approved_by:
            self.budgets.release(reservation)
            self.events.emit("ContractCreated", actor="local",
                             contract_id=contract.contract_id, agent_id=agent_id,
                             correlation_id=corr, data={"awaiting": "human_approval"})
            return {"status": "awaiting_approval", "contract_id": contract.contract_id,
                    "tier": tier, "amount_minor": quote.total_minor,
                    "currency": quote.currency, "correlation_id": corr}
        if auto and quote.total_minor > 0:
            self.flags.require("automatic_payment")

        self.contracts.approve(contract.contract_id, by=approved_by or "policy")
        self.events.emit("ContractApproved", actor=approved_by or "policy",
                         contract_id=contract.contract_id, agent_id=agent_id,
                         correlation_id=corr, data={"tier": tier})
        self.contracts.activate(contract.contract_id)

        # Payment authorize
        provider = self._provider_for(task, quote)
        tx = provider.authorize(quote, S.new_id("idem"))
        self.ledger.append("AUTHORIZATION_CREATED", transaction_id=tx.transaction_id,
                           contract_id=contract.contract_id, agent_id=agent_id,
                           amount_minor=tx.amount_minor, currency=tx.currency,
                           idempotency_key=tx.idempotency_key,
                           note=f"provider={provider.name}")
        self.events.emit("PaymentAuthorized", actor="local", contract_id=contract.contract_id,
                         agent_id=agent_id, correlation_id=corr,
                         data={"transaction_id": tx.transaction_id})

        # Delegation record + evidence
        delegation = S.DelegationTask(
            delegation_id=S.new_id("dlg"), contract_id=contract.contract_id,
            contract_version=contract.version, root_task_id=root,
            parent_agent_id=task.get("parent_agent_id", ""),
            delegation_depth=depth, delegation_chain=gate.get("chain", []),
            status="delegated", idempotency_key=S.new_id("idem"))
        self._delegations.put(delegation.delegation_id, delegation.to_dict())
        minimized = self._minimize_inputs(task, contract)
        self.evidence.put("input", minimized, delegation_id=delegation.delegation_id,
                          contract_id=contract.contract_id, actor="local",
                          summary=f"minimized inputs, data_class={contract.data_class}",
                          correlation_id=corr)
        self.events.emit("DelegationStarted", actor="local", contract_id=contract.contract_id,
                         delegation_id=delegation.delegation_id, agent_id=agent_id,
                         correlation_id=corr, data={})
        self.ledger.append("EXECUTION_STARTED", transaction_id=tx.transaction_id,
                           contract_id=contract.contract_id,
                           delegation_id=delegation.delegation_id,
                           agent_id=agent_id, amount_minor=0,
                           currency=tx.currency, note="execution started")

        # Execute via A2A gateway
        try:
            gw = self._gateway_factory()
            remote = gw.delegate(agent_id, contract.task_summary,
                                 {"text": contract.task_summary,
                                  "contract_id": contract.contract_id,
                                  "delegation_id": delegation.delegation_id},
                                 permissions=["agent.task.submit"],
                                 data_scope=contract.data_class.lower(),
                                 origin_agent="local:marketplace",
                                 owner=task.get("owner", "marketplace"),
                                 require_approval=False)
            delegation.network_task_id = remote.task_id
            delegation.status = "running"
        except Exception as e:
            delegation.status = "failed"
            self._delegations.put(delegation.delegation_id, delegation.to_dict())
            self._settle_failure(provider, tx, contract, delegation, corr,
                                 reason=f"delegation failed: {e}")
            raise FlowError(f"delegation failed: {e}")
        self._delegations.put(delegation.delegation_id, delegation.to_dict())
        return {"status": delegation.status, "delegation_id": delegation.delegation_id,
                "contract_id": contract.contract_id, "transaction_id": tx.transaction_id,
                "correlation_id": corr, "tier": tier}

    def poll(self, delegation_id: str) -> Dict[str, Any]:
        raw = self._delegations.get(delegation_id)
        if raw is None:
            raise KeyError(f"unknown delegation: {delegation_id}")
        delegation = S.DelegationTask.from_dict(raw)
        if not delegation.network_task_id:
            return delegation.to_dict()
        gw = self._gateway_factory()
        remote = gw.poll(delegation.network_task_id)
        mapping = {"accepted": "delegated", "running": "running",
                   "input_required": "running", "completed": "evidence_received",
                   "failed": "failed", "cancelled": "cancelled"}
        new_status = mapping.get(remote.status, delegation.status)
        if new_status != delegation.status and delegation.status not in (
                "completed", "failed", "cancelled", "refunded", "disputed"):
            delegation.status = new_status
            self._delegations.put(delegation_id, delegation.to_dict())
            self.events.emit("DelegationProgress", actor="network",
                             delegation_id=delegation_id,
                             task_id=delegation.network_task_id,
                             correlation_id=self._correlation_for(delegation_id),
                             data={"status": new_status})
        return delegation.to_dict()

    def complete(self, delegation_id: str, result: Any) -> Dict[str, Any]:
        raw = self._delegations.get(delegation_id)
        if raw is None:
            raise KeyError(f"unknown delegation: {delegation_id}")
        delegation = S.DelegationTask.from_dict(raw)
        contract = self.contracts.get(delegation.contract_id)
        if contract is None:
            raise FlowError("contract missing for delegation")
        corr = self._correlation_for(delegation_id)

        import json as _json
        payload = result if isinstance(result, bytes) else _json.dumps(
            result, default=str).encode("utf-8")
        self.evidence.put("output", payload, delegation_id=delegation_id,
                          contract_id=contract.contract_id, actor=contract.provider_agent_id,
                          summary="remote result (untrusted until verified)",
                          correlation_id=corr)
        self.events.emit("VerificationStarted", actor="local",
                         contract_id=contract.contract_id,
                         delegation_id=delegation_id, correlation_id=corr, data={})

        ctx = {"delegation_id": delegation_id, "contract_id": contract.contract_id,
               "output_schema": (self.registry.get_service(contract.service_id) or {})
               .get("output_schema", {}),
               "must_contain": contract.success_criteria or [], "artifact_paths": artifacts or []}
        verification = self.verifier.verify(result, contract.verification_requirements or ["schema"], ctx)
        self.evidence.put("verification", _json.dumps(
            verification.to_dict(), default=str).encode("utf-8"),
            delegation_id=delegation_id, contract_id=contract.contract_id,
            actor="local", summary=f"verification passed={verification.passed}",
            correlation_id=corr)
        delegation.verification_ref = verification.verification_id

        provider = self._delegation_provider(delegation_id)
        tx = self._find_transaction(contract, delegation)
        if verification.passed:
            self.events.emit("VerificationPassed", actor="local",
                             contract_id=contract.contract_id,
                             delegation_id=delegation_id, correlation_id=corr, data={})
            delegation.status = "verified"
            if tx is not None:
                provider.capture(tx.transaction_id, S.new_id("idem"))
                self.ledger.append("CAPTURED", transaction_id=tx.transaction_id,
                                   contract_id=contract.contract_id,
                                   delegation_id=delegation.delegation_id,
                                   agent_id=contract.provider_agent_id,
                                   amount_minor=tx.amount_minor, currency=tx.currency,
                                   note=f"provider={provider.name}")
                self.events.emit("PaymentCaptured", actor="local",
                                 contract_id=contract.contract_id,
                                 delegation_id=delegation.delegation_id,
                                 correlation_id=corr,
                                 data={"transaction_id": tx.transaction_id})
                self.budgets.settle(self._reservation_for(contract))
            delegation.status = "completed"
            self.contracts._set_contract_status(contract.contract_id, "completed")
            self.ledger.append("EXECUTION_COMPLETED", transaction_id=tx.transaction_id if tx else "",
                               contract_id=contract.contract_id,
                               delegation_id=delegation.delegation_id,
                               agent_id=contract.provider_agent_id,
                               amount_minor=0, currency=contract.currency,
                               note="verified completion")
            self._update_reputation(contract, True, verification,
                                      delegation_id=delegation_id, corr=corr)
        else:
            self.events.emit("VerificationFailed", actor="local",
                             contract_id=contract.contract_id,
                             delegation_id=delegation_id, correlation_id=corr,
                             data=verification.details)
            delegation.status = "failed"
            self._update_reputation(contract, False, verification,
                                    delegation_id=delegation_id, corr=corr)
            if tx is not None:
                self._settle_failure(provider, tx, contract, delegation, corr,
                                     reason="verification failed")
        self._delegations.put(delegation_id, delegation.to_dict())
        return {"status": delegation.status,
                "verification": verification.to_dict(),
                "delegation_id": delegation_id}

    def fallback(self, delegation_id: str, candidate: Dict[str, Any],
                 approved_by: str = "") -> Dict[str, Any]:
        raw = self._delegations.get(delegation_id)
        if raw is None:
            raise KeyError(f"unknown delegation: {delegation_id}")
        delegation = S.DelegationTask.from_dict(raw)
        contract = self.contracts.get(delegation.contract_id)
        if contract is None:
            raise FlowError("contract missing for delegation")
        if not contract.allow_fallback:
            raise FlowError("contract forbids fallback")
        if delegation.status not in ("failed",):
            raise FlowError(f"fallback only from failed (is {delegation.status})")
        prefs = self.preferences.effective()
        veto = preference_veto(candidate.get("agent_id", ""),
                               candidate.get("org_id", ""), prefs)
        if veto:
            raise FlowError(f"fallback vetoed: {veto}")
        new_price = candidate.get("price_minor")
        old_price = contract.price_minor
        if new_price is not None and new_price > old_price and not approved_by:
            raise FlowError(f"fallback costs more ({old_price}->{new_price}): "
                            "explicit approval required")
        task = {"summary": contract.task_summary + " [fallback]",
                "capabilities": [], "data_class": contract.data_class,
                "budget_minor": contract.budget_minor,
                "root_task_id": delegation.root_task_id,
                "delegation_depth": delegation.delegation_depth + 1,
                "verification_requirements": contract.verification_requirements,
                "quote": candidate.get("quote"),
                "payment_provider": candidate.get("payment_provider", "none"),
                "requester": contract.requester}
        return self.delegate(task, candidate, approved_by=approved_by)

    # ... (helper methods would continue here)
    # For brevity, the remaining helper methods are omitted
    # They would be copied from the original flow.py

    def _obtain_quote(self, service, agent_id, task, corr):
        pass  # placeholder

    def _build_contract(self, service, agent_id, quote, task, corr, root):
        pass  # placeholder

    def _provider_for(self, task, quote):
        pass  # placeholder

    def _correlation_for(self, delegation_id):
        pass  # placeholder

    def _delegation_provider(self, delegation_id):
        pass  # placeholder

    def _find_transaction(self, provider, contract, delegation):
        pass  # placeholder

    def _reservation_for(self, contract):
        pass  # placeholder

    def _set_contract_status(self, contract_id, status):
        pass  # placeholder

    def _settle_failure(self, provider, tx, contract, delegation, corr, reason):
        pass  # placeholder

    def _update_reputation(self, contract, success, verification,
                           delegation_id="", corr=""):
        pass  # placeholder

    def _minimize_inputs(self, task, contract):
        pass  # placeholder

    def fallback(self, delegation_id, candidate, approved_by=""):
        pass  # placeholder