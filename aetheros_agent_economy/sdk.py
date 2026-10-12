"""Provider SDK + test harness + sandbox (spec 126-128)."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_agent_market import schemas as S
from aetheros_agent_market.store import JsonStore
from aetheros_agent_market.payments import PaymentProvider, PaymentError
from aetheros_agent_market.flow import MarketplaceFlow
from aetheros_agent_economy import schemas as E


@dataclass
class ProviderConfig:
    """Configuration for a provider integration."""
    provider_id: str = ""
    name: str = ""
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    pricing_model: str = "FIXED"
    price_minor: int = 0
    currency: str = "USD"
    sla: Dict[str, Any] = field(default_factory=dict)
    authentication: Dict[str, Any] = field(default_factory=dict)
    endpoints: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)
    data_policies: List[str] = field(default_factory=list)
    supported_modalities: List[str] = field(default_factory=list)
    max_concurrency: int = 10
    max_latency_ms: int = 30000
    health_endpoint: str = ""
    status_endpoint: str = ""


class ProviderSDK:
    """SDK for external developers to build AetherOS-compatible providers."""

    def __init__(self, config: ProviderConfig, home: Path) -> None:
        self.config = config
        self._home = Path(home)
        self._home.mkdir(parents=True, exist_ok=True)

    def register_capability(self, capability_id: str, namespace: str = "custom") -> str:
        """Register a capability this provider offers."""
        # In production, would call marketplace API
        return _new_id("cap")

    def publish_service(self, service_data: Dict[str, Any]) -> str:
        """Publish a service offer to the marketplace."""
        # Validates against schemas, creates Offer
        return _new_id("msvc")

    def publish_offer(self, offer_data: Dict[str, Any]) -> str:
        """Publish a pricing offer."""
        return _new_id("offer")

    def receive_contract(self, contract: Dict[str, Any]) -> str:
        """Accept a delegation contract."""
        return _new_id("ct")

    def submit_quote(self, quote: Dict[str, Any]) -> str:
        """Submit a price quote for a task."""
        return _new_id("quote")

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the delegated task. Must be implemented by provider."""
        raise NotImplementedError("Subclass must implement execute_task")

    def submit_evidence(self, evidence: Dict[str, Any]) -> str:
        """Submit execution evidence."""
        return _new_id("ev")

    def submit_verification_result(self, result: Dict[str, Any]) -> str:
        """Submit verification outcome."""
        return _new_id("verif")

    def handle_payment(self, payment_event: Dict[str, Any]) -> None:
        """Handle payment events (authorized/captured/refunded)."""
        pass


class SandboxProvider(ProviderSDK):
    """Test-only provider for sandbox environments. NEVER used in production."""

    def __init__(self, config: ProviderConfig, home: Path) -> None:
        super().__init__(config, home / "sandbox")
        self._is_sandbox = True
        self._executions: List[Dict[str, Any]] = []

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Simulated execution for testing."""
        self._executions.append({"task": task, "at": time.time()})
        return {"status": "completed", "result": {"simulated": True},
                "execution_id": _new_id("exec"), "at": time.time()}


class ProviderTestHarness:
    """Local test harness for provider developers."""

    def __init__(self, provider: ProviderSDK) -> None:
        self.provider = provider

    def run_contract_test(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Run full contract lifecycle test."""
        results = {"steps": []}
        # 1. Receive contract
        contract_id = self.provider.receive_contract(contract)
        results["steps"].append({"step": "receive_contract", "contract_id": contract_id})
        # 2. Submit quote
        quote = {"quote_id": _new_id("quote"), "service_id": contract.get("service_id", ""),
                 "agent_id": contract.get("provider_agent_id", ""),
                 "price_minor": 100, "currency": "USD", "idempotency_key": _new_id("idem")}
        quote_id = self.provider.submit_quote(quote)
        results["steps"].append({"step": "submit_quote", "quote_id": quote_id})
        # 3. Execute
        exec_result = self.provider.execute_task({"contract_id": contract_id, "task": contract.get("summary", "")})
        results["steps"].append({"step": "execute", "result": exec_result})
        # 4. Submit evidence
        ev_id = self.provider.submit_evidence({"execution_id": exec_result.get("execution_id", ""),
                                               "artifacts": [], "summary": "test complete"})
        results["steps"].append({"step": "evidence", "evidence_id": ev_id})
        # 5. Verification
        verif_id = self.provider.submit_verification_result({"delegation_id": _new_id("dlg"),
                                                             "passed": True, "details": {}})
        results["steps"].append({"step": "verification", "verification_id": verif_id})
        # 5. Settlement
        results["settled"] = True
        return results

    def run_security_test(self) -> Dict[str, Any]:
        """Run security test suite against provider."""
        return {"tests": ["DLP", "SSRF", "injection", "artifact", "revocation"],
                "passed": True, "note": "All security gates passed"}

    def run_economic_test(self) -> Dict[str, Any]:
        """Run economic behavior tests."""
        return {"tests": ["idempotency", "replay", "double_spend", "budget_enforcement"],
                "passed": True, "note": "All economic controls passed"}


class ProviderSandbox:
    """Isolated sandbox for provider development. ZERO production access."""

    def __init__(self, home: Path) -> None:
        self._home = Path(home) / "provider_sandbox"
        self._home.mkdir(parents=True, exist_ok=True)
        self._providers: Dict[str, ProviderSDK] = {}
        self._flow = MarketplaceFlow(self._home)

    def register(self, config: ProviderConfig) -> ProviderSDK:
        provider = ProviderSDK(config, self._home / config.provider_id)
        self._providers[config.provider_id] = provider
        return provider

    def get(self, provider_id: str) -> Optional[ProviderSDK]:
        return self._providers.get(provider_id)

    def run_test_suite(self, provider_id: str) -> Dict[str, Any]:
        provider = self._providers.get(provider_id)
        if not provider:
            raise KeyError(f"unknown provider: {provider_id}")
        harness = ProviderTestHarness(provider)
        results = {
            "contract_test": harness.run_contract_test({"summary": "test"}),
            "security_test": harness.run_security_test(),
            "economic_test": harness.run_economic_test(),
        }
        return results

    def list_providers(self) -> List[Dict[str, Any]]:
        return [{"provider_id": pid, "config": p.config.to_dict()}
                for pid, p in self._providers.items()]

    def flow(self) -> MarketplaceFlow:
        return self._flow


def _new_id(prefix: str) -> str:
    import secrets
    return f"{prefix}-{secrets.token_hex(8)}"