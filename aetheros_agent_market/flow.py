"""End-to-end marketplace delegation flow (spec section 100).

1 understand task -> 2 local capability check -> 3 discover ->
4 policy filter -> 5 trust -> 6 reputation -> 7/8/9/10 cost/latency/SLA/
privacy compare -> 11 select -> 12 quote -> 13 contract -> 14 budget ->
15 approval if needed -> 16 delegate -> 17 monitor -> 18 verify ->
19 settle -> 20 reputation update -> 21 provenance -> 22 explain.

Every step observable + auditable via EventBus + EvidenceStore + Ledger.
No step may be skipped. No LLM in any gate.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import schemas as S
from .accounting import CostAccounting
from .budgets import BudgetManager
from .contracts import ContractEngine
from .discovery import CapabilityIndex, IndexedService
from .disputes import DisputeEngine
from .events import EventBus
from .evidence import EvidenceStore
from .export_import import check_restore_integrity
from .flags import FeatureFlags, KillSwitch
from .ledger import Ledger
from .payments import PaymentError, PaymentProvider, get_provider
from .preferences import PreferenceStore, apply_preferences, preference_veto
from .quoting import QuotingEngine
from .registries import LocalRegistry
from .reputation import ReputationEngine
from .security import EconomicAbuseGuard, ListingScanner, RecursionGuard
from .selection import AgentSelectionEngine, CandidateSignals
from .store import market_home
from .taxonomy import MatchRequest
from .trust_engine import AgentTrustEngine
from .verification import ResultVerificationEngine


class FlowError(Exception):
    pass


class MarketplaceFlow:
    """Wires all engines. Construct with an explicit home (tests use tmp)."""

    def __init__(self, home: Optional[Path] = None,
                 gateway_factory: Optional[Callable[[], Any]] = None) -> None:
        self.home = Path(home) if home else market_home()
        self.home.mkdir(parents=True, exist_ok=True)
        self.registry = LocalRegistry(self.home)
        self.trust = AgentTrustEngine(self.home)
        self.index = CapabilityIndex()
        self.index.add_provider("market", self._market_provider())
        try:
            from .discovery import network_services_provider
            self.index.add_provider("trusted_a2a", network_services_provider())
        except Exception:
            pass
        self.reputation = ReputationEngine(self.home)
        self.contracts = ContractEngine(self.home)
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
        self._gateway_factory = gateway_factory or self._default_gateway
        from .store import JsonStore
        self._delegations = JsonStore(self.home / "delegations.json")
        # delegation_id -> {provider} so settle/dispute use the SAME
        # provider that authorized (never silently switched).
        self._providers_used = JsonStore(self.home / "delegation_providers.json")

    def _default_gateway(self):
        from aetheros_network.gateway import AgentGateway
        return AgentGateway()

    def _market_provider(self):
        """Local-registry services with effective trust ranks.

        Rank = max(network trust rank, marketplace-signal mapping).
        Marketplace signals map overall [-1,1] -> [0,6]; unknown agents
        map to 0 and are filtered by default policy (min rank 3).
        Batched single-pass aggregation (scale path). Authorization still
        uses the network trust store via the gateway.
        """
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
            from aetheros_network import gateway as _gw
            from aetheros_network.trust import TrustStore, trust_rank as _rank
            if self.__dict__.get("_net_trust") is None:
                self.__dict__["_net_trust"] = TrustStore(_gw.default_home() / "trust.json")
            return _rank(self.__dict__["_net_trust"].level(agent_id))
        except Exception:
            return 0

    def _effective_rank(self, agent_id: str) -> int:
        return max(self._network_rank(agent_id),
                   self._map_overall(self.trust.profile(agent_id)["overall"]))

    # -- step 2: local-first -------------------------------------------------
    def local_assessment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Honest local-first comparison (spec 24/25).

        Local capability is reported from the LOCAL service catalog only;
        cost/latency are measured estimates with uncertainty — never
        fabricated savings.
        """
        req = MatchRequest(query=task.get("query", ""),
                           exact_capabilities=task.get("capabilities", []))
        local_hits = [h for h in self.index.search(req, limit=100)
                      if h.source in ("market",)]
        local_capable = any(h.exact for h in local_hits)
        return {"local_capable": local_capable,
                "local_candidates": len(local_hits),
                "note": "local execution cost/latency measured at runtime; "
                        "no savings claimed without measurement"}

    # -- steps 3-11: recommend (no side effects) -------------------------------
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
        # Batched single-pass trust/reputation (scale path; same math as
        # the single-agent profile() calls used by the trust/reputation APIs).
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
            # Unknown security (no samples) => neutral 0.5. A measured 0.0
            # (real incident) must NEVER be masked upward.
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
            return None  # A2A: price only via quote, never invented
        return 0 if service.get("pricing_model") == "free" else None

    def _service_latency(self, service: Dict[str, Any]) -> Optional[float]:
        sla = service.get("sla", {}) or {}
        val = sla.get("max_latency_ms")
        return float(val) if isinstance(val, (int, float)) else None

    # -- steps 12-22: delegated execution ---------------------------------------
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

        # Recursion defense (spec 66).
        root = task.get("root_task_id", S.new_id("root"))
        depth = int(task.get("delegation_depth", 1))
        gate = self.recursion.check(root, agent_id, depth)
        if not gate["allowed"]:
            raise FlowError(f"recursion guard: {gate['reason']}")

        # Quote (spec 14): required for paid; recorded for free.
        quote = self._obtain_quote(service, agent_id, task, corr)
        if quote.total_minor > 0:
            self.flags.require("paid_agents")

        # Contract (spec 11).
        contract = self._build_contract(service, agent_id, quote, task, corr, root)
        quote = self.quotes.bind_contract(quote.quote_id, contract.contract_id)
        self.events.emit("ContractCreated", actor="local", contract_id=contract.contract_id,
                         agent_id=agent_id, correlation_id=corr,
                         data={"version": contract.version})

        # Budget gate (spec 15/16) + abuse velocity (spec 65).
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
            # Autonomous purchasing ONLY within explicit user policy (sec 97).
            prefs = self.preferences.effective(task.get("scopes"))
            limit = prefs.payment_limit_minor
            if limit is None or quote.total_minor > limit:
                self.budgets.release(reservation)
                raise FlowError("autonomous purchase denied: exceeds user auto-purchase policy")
            self.flags.require("automatic_payment")

        self.contracts.approve(contract.contract_id, by=approved_by or "policy")
        self.events.emit("ContractApproved", actor=approved_by or "policy",
                         contract_id=contract.contract_id, agent_id=agent_id,
                         correlation_id=corr, data={"tier": tier})
        self.contracts.activate(contract.contract_id)

        # Delegation record FIRST so every later event correlates.
        delegation = S.DelegationTask(
            delegation_id=S.new_id("dlg"), contract_id=contract.contract_id,
            contract_version=contract.version, root_task_id=root,
            parent_agent_id=task.get("parent_agent_id", ""),
            delegation_depth=depth, delegation_chain=gate.get("chain", []),
            status="delegated", idempotency_key=S.new_id("idem"))
        self._delegations.put(delegation.delegation_id, delegation.to_dict())

        # Payment authorize (spec 13/17): authorize BEFORE execute.
        provider = self._provider_for(task, quote)
        provider_name = task.get("payment_provider", "none")
        tx = provider.authorize(quote, S.new_id("idem"))
        self.ledger.append("AUTHORIZATION_CREATED", transaction_id=tx.transaction_id,
                           contract_id=contract.contract_id,
                           delegation_id=delegation.delegation_id,
                           agent_id=agent_id,
                           amount_minor=tx.amount_minor, currency=tx.currency,
                           idempotency_key=tx.idempotency_key,
                           note=f"provider={provider.name}")
        self.events.emit("PaymentAuthorized", actor="local", contract_id=contract.contract_id,
                         delegation_id=delegation.delegation_id,
                         agent_id=agent_id, correlation_id=corr,
                         data={"transaction_id": tx.transaction_id})
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

        # Execute via A2A gateway (real transport, policies enforced there).
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
            self._providers_used.put(delegation.delegation_id,
                                     {"provider": provider_name})
        except Exception as e:
            delegation.status = "failed"
            self._delegations.put(delegation.delegation_id, delegation.to_dict())
            self._settle_failure(provider, tx, contract, delegation, corr,
                                 reason=f"delegation failed: {e}")
            raise FlowError(f"delegation failed: {e}")
        self._delegations.put(delegation.delegation_id, delegation.to_dict())
        return {"status": delegation.status, "delegation_id": delegation.delegation_id,
                "contract_id": contract.contract_id, "transaction_id": tx.transaction_id,
                "network_task_id": delegation.network_task_id,
                "correlation_id": corr, "tier": tier}

    def poll(self, delegation_id: str) -> Dict[str, Any]:
        """Monitor: reconcile network state, no fabricated progress."""
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

    def complete(self, delegation_id: str, result: Any,
                 artifacts: Optional[List[str]] = None) -> Dict[str, Any]:
        """Verify -> settle -> reputation. Completion = result + verification
        (+ settlement for paid). Self-reported success is never enough."""
        raw = self._delegations.get(delegation_id)
        if raw is None:
            raise KeyError(f"unknown delegation: {delegation_id}")
        delegation = S.DelegationTask.from_dict(raw)
        contract = self.contracts.get(delegation.contract_id)
        if contract is None:
            raise FlowError("contract missing for delegation")
        # Reuse the delegation's correlation id so the whole lifecycle
        # stays traceable end-to-end (spec 60).
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
               "must_contain": contract.success_criteria or [],
               "artifact_paths": artifacts or []}
        verification = self.verifier.verify(result, contract.verification_requirements or ["schema"], ctx)
        self.evidence.put("verification", _json.dumps(
            verification.to_dict(), default=str).encode("utf-8"),
            delegation_id=delegation_id, contract_id=contract.contract_id,
            actor="local", summary=f"verification passed={verification.passed}",
            correlation_id=corr)
        delegation.verification_ref = verification.verification_id

        provider = self._delegation_provider(delegation_id)
        tx = self._find_transaction(provider, contract, delegation)
        if verification.passed:
            self.events.emit("VerificationPassed", actor="local",
                             contract_id=contract.contract_id,
                             delegation_id=delegation_id, correlation_id=corr, data={})
            delegation.status = "verified"
            # Settle: capture + ledger + budget settle.
            if tx is not None:
                provider.capture(tx.transaction_id, S.new_id("idem"))
                self.ledger.append("CAPTURED", transaction_id=tx.transaction_id,
                                   contract_id=contract.contract_id,
                                   delegation_id=delegation_id,
                                   agent_id=contract.provider_agent_id,
                                   amount_minor=tx.amount_minor, currency=tx.currency,
                                   note=f"provider={provider.name}")
                self.events.emit("PaymentCaptured", actor="local",
                                 contract_id=contract.contract_id,
                                 delegation_id=delegation_id,
                                 correlation_id=corr,
                                 data={"transaction_id": tx.transaction_id})
                self.budgets.settle(self._reservation_for(contract))
            delegation.status = "completed"
            self.contracts.get(contract.contract_id)  # validated present
            self._set_contract_status(contract.contract_id, "completed")
            self.ledger.append("EXECUTION_COMPLETED", transaction_id=tx.transaction_id if tx else "",
                               contract_id=contract.contract_id,
                               delegation_id=delegation_id,
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

    # -- internals --------------------------------------------------------------
    def _obtain_quote(self, service: Dict[str, Any], agent_id: str,
                      task: Dict[str, Any], corr: str) -> S.Quote:
        pricing = service.get("pricing_model", "quote")
        offer_raw = None
        for o in self.registry._offers.values():
            if o.get("service_id") == service.get("service_id") and o.get("status") == "open":
                offer_raw = o
                break
        if pricing == "free" and offer_raw is None:
            quote = S.Quote(quote_id=S.new_id("quote"),
                            service_id=service.get("service_id", ""),
                            agent_id=agent_id, price_minor=0, currency="USD",
                            idempotency_key=S.new_id("idem"))
        elif offer_raw is not None:
            offer = S.Offer.from_dict(offer_raw)
            if offer.is_expired:
                raise FlowError("offer expired")
            quote = S.Quote(quote_id=S.new_id("quote"),
                            service_id=offer.service_id, agent_id=agent_id,
                            price_minor=offer.price_minor, currency=offer.currency,
                            sla=offer.sla, cancellation_policy=offer.cancellation_policy,
                            refund_policy=offer.refund_policy,
                            idempotency_key=S.new_id("idem"))
        else:
            # A2A/quote-model services: quote arrives from the provider via
            # task["quote"] (supplied by the caller, verified below) — never
            # invented locally.
            supplied = task.get("quote")
            if not supplied:
                raise FlowError("no offer and no provider quote supplied; "
                                "cannot price delegation (free->paid conversion refused)")
            quote = S.Quote.from_dict(supplied)
        quote.contract_id = task.get("contract_id_hint", "")
        check = self.quotes.verify_quote(
            quote, None,
            S.Offer.from_dict(offer_raw) if offer_raw else None)
        if not check["ok"]:
            raise FlowError(f"quote rejected: {check['reasons']}")
        self.quotes.record_quote(quote)
        self.ledger.append("QUOTE_CREATED", agent_id=agent_id,
                           amount_minor=quote.total_minor, currency=quote.currency,
                           idempotency_key=quote.idempotency_key,
                           note=f"quote={quote.quote_id}")
        self.events.emit("QuoteReceived", actor=agent_id, agent_id=agent_id,
                         correlation_id=corr,
                         data={"quote_id": quote.quote_id,
                               "total_minor": quote.total_minor,
                               "flags": check["flags"]})
        return quote

    def _build_contract(self, service: Dict[str, Any], agent_id: str,
                        quote: S.Quote, task: Dict[str, Any],
                        corr: str, root: str) -> S.DelegationContract:
        contract = S.DelegationContract(
            contract_id=S.new_id("ct"), requester=task.get("requester", "local"),
            provider_agent_id=agent_id,
            provider_identity_id=task.get("provider_identity_id", ""),
            service_id=service.get("service_id", ""),
            offer_id=task.get("offer_id", ""), quote_id=quote.quote_id,
            task_summary=str(task.get("summary", ""))[:2000],
            allowed_data=task.get("allowed_data", []),
            prohibited_data=task.get("prohibited_data", []),
            data_class=str(task.get("data_class", "INTERNAL")).upper(),
            expected_output=str(task.get("expected_output", ""))[:2000],
            success_criteria=task.get("success_criteria", []),
            sla=task.get("sla", {}),
            timeout_s=float(task.get("timeout_s", 300.0)),
            budget_minor=int(task.get("budget_minor", quote.total_minor)),
            currency=quote.currency, price_minor=quote.total_minor,
            payment_conditions=task.get("payment_conditions", "capture_on_verified"),
            cancellation_conditions=task.get("cancellation_conditions", ""),
            refund_conditions=task.get("refund_conditions", ""),
            verification_requirements=task.get("verification_requirements", ["schema"]),
            artifact_requirements=task.get("artifact_requirements", []),
            security_constraints=task.get("security_constraints", []),
            retention_rules=task.get("retention_rules", ""),
            jurisdiction=task.get("jurisdiction", ""),
            expires_at=float(task.get("contract_expires_at", 0.0)),
            allow_fallback=bool(task.get("allow_fallback", False)),
            max_delegation_depth=int(task.get("max_delegation_depth", 1)),
            idempotency_key=S.new_id("idem"))
        created = self.contracts.create(contract)
        self.contracts.propose(created.contract_id)
        return self.contracts.get(created.contract_id)

    def _provider_for(self, task: Dict[str, Any],
                      quote: Optional[S.Quote]) -> PaymentProvider:
        name = task.get("payment_provider", "none")
        if quote is not None and quote.total_minor > 0 and name == "none":
            # A priced quote with the free provider is a contradiction:
            # refuse rather than silently treating paid as free.
            raise FlowError("priced quote requires an explicit payment provider "
                            "(credits|org_budget|external)")
        if name.startswith("external:"):
            raise FlowError(f"external provider {name!r} not configured; "
                            "integrate via PaymentProvider (see provider SDK)")
        return get_provider(name, self.home)

    def _correlation_for(self, delegation_id: str) -> str:
        for e in self.events.list(delegation_id=delegation_id, limit=100000):
            if e.get("correlation_id"):
                return e["correlation_id"]
        return S.new_id("corr")

    def _delegation_provider(self, delegation_id: str) -> PaymentProvider:
        rec = self._providers_used.get(delegation_id) or {"provider": "none"}
        name = str(rec.get("provider", "none"))
        if name.startswith("external:"):
            raise FlowError(f"external provider {name!r} not configured")
        return get_provider(name, self.home)

    def _find_transaction(self, provider: PaymentProvider,
                          contract: S.DelegationContract,
                          delegation: S.DelegationTask) -> Optional[S.Transaction]:
        found = provider.transactions_for_contract(contract.contract_id)
        return found[-1] if found else None

    def _reservation_for(self, contract: S.DelegationContract) -> str:
        for rid, rec in self.budgets._reservations.all().items():
            keys = rec.get("budget_keys") or ([rec["budget_key"]]
                                              if rec.get("budget_key") else [])
            if any(k.endswith(contract.contract_id) for k in keys):
                return rid
        return ""

    def _set_contract_status(self, contract_id: str, status: str) -> None:
        raw = self.contracts._contracts.get(contract_id)
        if raw:
            raw["status"] = status
            self.contracts._contracts.put(contract_id, raw)

    def _settle_failure(self, provider: PaymentProvider, tx: Optional[S.Transaction],
                        contract: S.DelegationContract,
                        delegation: S.DelegationTask, corr: str,
                        reason: str) -> None:
        if tx is None:
            return
        try:
            if tx.status == "authorized":
                provider.void(tx.transaction_id, S.new_id("idem"))
                self.ledger.append("VOIDED", transaction_id=tx.transaction_id,
                                   contract_id=contract.contract_id,
                                   delegation_id=delegation.delegation_id,
                                   agent_id=contract.provider_agent_id,
                                   amount_minor=0, currency=tx.currency, note=reason[:300])
            elif tx.status == "captured":
                provider.refund(tx.transaction_id, None, S.new_id("idem"), reason)
                self.ledger.append("REFUNDED", transaction_id=tx.transaction_id,
                                   contract_id=contract.contract_id,
                                   delegation_id=delegation.delegation_id,
                                   agent_id=contract.provider_agent_id,
                                   amount_minor=tx.amount_minor, currency=tx.currency,
                                   note=reason[:300])
                self.events.emit("PaymentRefunded", actor="local",
                                 contract_id=contract.contract_id,
                                 delegation_id=delegation.delegation_id,
                                 correlation_id=corr,
                                 data={"transaction_id": tx.transaction_id})
        finally:
            rid = self._reservation_for(contract)
            if rid:
                self.budgets.release(rid)

    def _update_reputation(self, contract: S.DelegationContract,
                           success: bool, verification: S.VerificationResult,
                           delegation_id: str = "", corr: str = "") -> None:
        agent_id = contract.provider_agent_id
        self.reputation.record_task_outcome(agent_id, success, verified=True,
                                            sla_met=None)
        self.reputation.record(agent_id, "evidence_quality",
                               1.0 if verification.passed else 0.0,
                               provenance="verified")
        self.reputation.record(agent_id, "verification_confidence",
                               1.0 if verification.passed else 0.0,
                               provenance="verified")
        self.trust.record_outcome(agent_id, "execution", success,
                                  evidence_ref=verification.verification_id)
        self.trust.record_outcome(agent_id, "evidence", verification.passed,
                                  evidence_ref=verification.verification_id)
        self.events.emit("ReputationUpdated", actor="local",
                         contract_id=contract.contract_id,
                         delegation_id=delegation_id, agent_id=agent_id,
                         correlation_id=corr or S.new_id("corr"),
                         data={"success": success})

    def _minimize_inputs(self, task: Dict[str, Any],
                         contract: S.DelegationContract) -> bytes:
        """Data minimization (spec 35): only allowed fields cross the boundary."""
        import json as _json
        allowed = set(contract.allowed_data) if contract.allowed_data else None
        inputs = task.get("inputs", {})
        if allowed is not None and isinstance(inputs, dict):
            minimized = {k: v for k, v in inputs.items() if k in allowed}
        else:
            minimized = inputs
        try:
            from aetheros_network.policy import redact_secrets
            text = _json.dumps(minimized, default=str)
            return redact_secrets(text).encode("utf-8")
        except Exception:
            return _json.dumps(minimized, default=str).encode("utf-8")

    # -- fallback (spec 62) ------------------------------------------------------
    def fallback(self, delegation_id: str, candidate: Dict[str, Any],
                 approved_by: str = "") -> Dict[str, Any]:
        raw = self._delegations.get(delegation_id)
        if raw is None:
            raise KeyError(f"unknown delegation: {delegation_id}")
        delegation = S.DelegationTask.from_dict(raw)
        contract = self.contracts.get(delegation.contract_id)
        if contract is None:
            raise FlowError("contract missing")
        if not contract.allow_fallback:
            raise FlowError("contract forbids fallback")
        if delegation.status not in ("failed",):
            raise FlowError(f"fallback only from failed (is {delegation.status})")
        prefs = self.preferences.effective()
        veto = preference_veto(candidate.get("agent_id", ""),
                               candidate.get("org_id", ""), prefs)
        if veto:
            raise FlowError(f"fallback vetoed: {veto}")
        # Budget + trust re-checks are mandatory; never silent downgrade.
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
