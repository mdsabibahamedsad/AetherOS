"""Master 59 consolidation: errors, envelope, adapters, honesty, concurrency.

Hermetic: stub runtime, bus off, tmp capsule roots, no net/creds/hw.
"""

from __future__ import annotations

import threading

import pytest

from kernel.core import (
    AetherosError,
    AuthorizationError,
    CapabilityDeniedError,
    ExpiredError,
    Intent,
    IntentEnvelope,
    KernelConfig,
    PolicyDeniedError,
    QuarantineError,
    RateLimitError,
    ResourceBudget,
    ResourceLimitError,
    ValidationError,
    error_codes,
    from_builtin,
)
from kernel.core.kernel import AgentKernel


def _kernel(tmp_path=None):
    kw = dict(enable_event_bus=False, checkpoint_interval_seconds=0,
              health_check_interval_seconds=3600)
    if tmp_path is not None:
        kw["checkpoint_dir"] = str(tmp_path)
    k = AgentKernel(KernelConfig(**kw))
    k.boot()
    return k


# -- error taxonomy (§35) ----------------------------------------------------------


def test_error_codes_stable_and_unique():
    codes = error_codes()
    assert len(codes) == len(set(codes))
    assert "policy_denied" in codes and "model_unavailable" in codes


def test_error_round_trip_serialization():
    err = PolicyDeniedError(message="nope", trace_id="t1", capsule_id="c1",
                            agent_id="a1", intent_id="i1", hint="ask human",
                            details={"k": "v"})
    data = err.to_dict()
    back = AetherosError.from_dict(data)
    assert isinstance(back, PolicyDeniedError)
    assert back.code == "policy_denied" and str(back) == "[policy_denied] nope"
    assert back.trace_id == "t1" and back.details == {"k": "v"}


def test_from_builtin_mapping():
    assert isinstance(from_builtin(PermissionError("policy denied x")), PolicyDeniedError)
    assert isinstance(from_builtin(PermissionError("quota exceeded")), ResourceLimitError)
    assert isinstance(from_builtin(PermissionError("quarantined!")), QuarantineError)
    assert isinstance(from_builtin(PermissionError("grant expired")), ExpiredError)
    assert isinstance(from_builtin(PermissionError("rate limit hit")), RateLimitError)
    assert isinstance(from_builtin(ValueError("bad")), ValidationError)
    assert isinstance(from_builtin(KeyError("k")), ValidationError)
    assert isinstance(from_builtin(RuntimeError("zzz")), AetherosError)
    assert isinstance(from_builtin(AuthorizationError()), AuthorizationError)


def test_zero_budget_and_zeroed_allocation(tmp_path):
    z = ResourceBudget.zero()
    assert all(float(getattr(z, f)) == 0.0 for f in ResourceBudget.__dataclass_fields__)
    k = _kernel(tmp_path)
    try:
        alloc = k.resource_manager.allocate("agent_probe", ResourceBudget.zero())
        assert all(float(getattr(alloc.used, f)) == 0.0
                   for f in ResourceBudget.__dataclass_fields__)
    finally:
        k._shutdown_flag = True


# -- intent envelope + normalization (§5) --------------------------------------------


def test_intent_envelope_seal_verify_tamper():
    intent = Intent(actor="human", objective="do work")
    env = IntentEnvelope(intent=intent).seal()
    assert env.version == "1.0" and env.verify() is True
    env.intent.objective = "do EVIL work"
    assert env.verify() is False
    env2 = IntentEnvelope(intent=intent)
    assert env2.verify() is False  # unsealed never verifies
    env3 = IntentEnvelope(intent=intent, version="9.9").seal()
    assert env3.verify() is False  # version pinned


def test_normalize_extracts_only_explicit_caps():
    from kernel.core.intent_manager import IntentManager
    intent = IntentManager.normalize_natural_language(
        "please delete everything cap:fs.delete urgently")
    assert intent.objective.startswith("please delete")
    assert intent.requested_capabilities == ["fs.delete"]
    plain = IntentManager.normalize_natural_language("delete all files now")
    assert plain.requested_capabilities == []  # never guessed from prose


# -- verification honesty --------------------------------------------------------------


def test_attest_without_provider_is_unverified(tmp_path):
    k = _kernel(tmp_path)
    try:
        from kernel.core.types import CapabilityDescriptor, CapabilityInvocation
        desc = CapabilityDescriptor(capability_id="hw.x", version="1.0",
                                    provider="t", description="x",
                                    verification_strategy="attest")
        ctx = k.capability_invoker._verification_strategies["attest"]
        out = ctx(type("C", (), {"descriptor": desc,
                                 "invocation": CapabilityInvocation(result={"a": 1})})())
        assert out["verified"] is False
    finally:
        k._shutdown_flag = True


def test_unconfigured_models_not_selectable(tmp_path):
    from kernel.core.model_manager import (
        ModelCapability, ModelProfile, ModelProvider, ModelSelection)
    k = _kernel(tmp_path)
    try:
        from kernel.core.types import DataClassification
        k.model_manager.register_model(ModelProfile(
            model_id="ghost-1", name="ghost", provider=ModelProvider.CUSTOM,
            capabilities=[ModelCapability.TEXT], availability=0.0))
        k.model_manager.register_model(ModelProfile(
            model_id="real-1", name="real", provider=ModelProvider.LOCAL,
            capabilities=[ModelCapability.TEXT], availability=1.0, local=True,
            privacy_level=DataClassification.SECRET))
        k.model_manager.register_model(ModelProfile(
            model_id="pub-1", name="pub", provider=ModelProvider.LOCAL,
            capabilities=[ModelCapability.TEXT], availability=1.0, local=True,
            privacy_level=DataClassification.PUBLIC))
        picked = k.model_manager.select_model(ModelSelection(
            required_capabilities=[ModelCapability.TEXT]))
        assert picked is not None and picked.model_id == "real-1"
        secret_pick = k.model_manager.select_model(ModelSelection(
            required_capabilities=[ModelCapability.TEXT],
            privacy_requirement=DataClassification.SECRET))
        assert secret_pick is not None and secret_pick.model_id == "real-1"
        assert secret_pick.model_id != "pub-1"  # PUBLIC-cleared never takes SECRET
    finally:
        k._shutdown_flag = True


# -- task adapter (§6) ----------------------------------------------------------------------


def test_import_graph_preserves_deps_and_status(tmp_path):
    from kernel.core.task_adapter import export_status_map, import_graph
    from kernel.task_graph import GraphStatus, TaskGraph
    k = _kernel(tmp_path)
    try:
        graph = TaskGraph("legacy")
        a = graph.add_node("a", "first")
        b = graph.add_node("b", "second", dependencies=[a.id])
        graph.update_status(a.id, GraphStatus.COMPLETED)
        tasks = import_graph(graph, k.task_manager, "agent_x", "intent_x")
        assert len(tasks) == 2
        by_goal = {t.goal: t for t in tasks}
        assert by_goal["b"].depends_on == [by_goal["a"].task_id]
        assert by_goal["a"].status.value == "completed"
        assert by_goal["a"].metadata["migrated_from"] == "legacy_task_graph"
        assert by_goal["a"].metadata["legacy_node_id"] == a.id
        assert "pending" in export_status_map()
    finally:
        k._shutdown_flag = True


# -- memory_os bridge (§15) ---------------------------------------------------------------------


def test_memory_os_bridge_round_trip():
    from agent.memory_os.manager import MemoryManager as MemoryOsManager
    from kernel.core.memory_os_bridge import MemoryOsProvider
    manager = MemoryOsManager()
    provider = MemoryOsProvider(manager, actor_id="test", owner="test")
    provider.write("task", "bridge-key", "bridge-value")
    assert provider.read("task", "bridge-key") == "bridge-value"
    hits = provider.search("task", "bridge-value", 5)
    assert any(h["content"] == "bridge-value" for h in hits)
    assert provider.delete("task", "bridge-key") is True
    assert provider.read("task", "bridge-key") is None
    assert provider.delete("task", "bridge-key") is False
    assert provider.scope_map()["task"] == "task"
    assert provider.scope_map()["agent"] == "user"


def test_register_memory_os_provider(tmp_path):
    from agent.memory_os.manager import MemoryManager as MemoryOsManager
    from kernel.core.memory_os_bridge import register_memory_os_provider
    k = _kernel(tmp_path)
    try:
        name = register_memory_os_provider(k, MemoryOsManager(), actor_id="t")
        assert name == "memory_os"
        stats = k.memory_manager.get_stats()
        assert stats is not None
    finally:
        k._shutdown_flag = True


# -- concurrency (§40) -------------------------------------------------------------------------------


def test_concurrent_scheduler_admits(tmp_path):
    k = _kernel(tmp_path)
    try:
        errors: list = []
        created: list = []

        def make_one(i: int) -> None:
            try:
                intent = Intent(actor="human", objective=f"concurrent {i}")
                intent.requested_resources = ResourceBudget.zero()
                intent.budget = ResourceBudget.zero()
                proc = k.create_agent_process(intent)
                created.append(proc.agent_id)
            except Exception as exc:  # noqa: BLE001 - collected, asserted empty
                errors.append(exc)

        threads = [threading.Thread(target=make_one, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert not errors
        assert len(created) == 16
        assert len(set(created)) == 16
    finally:
        k._shutdown_flag = True


def test_concurrent_capsule_creates_have_unique_roots(tmp_path):
    k = _kernel(tmp_path)
    try:
        errors: list = []
        roots: list = []

        def make_one(i: int) -> None:
            try:
                cap = k.hypervisor.create_capsule(
                    Intent(actor="human", objective=f"cc {i}"), "minimal")
                roots.append(k.hypervisor._filesystems[cap.capsule_id].root)
            except Exception as exc:  # noqa: BLE001 - collected, asserted empty
                errors.append(exc)

        threads = [threading.Thread(target=make_one, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        assert not errors
        assert len(set(roots)) == 8
    finally:
        k._shutdown_flag = True


def test_receipt_chain_intact_under_threads(tmp_path):
    from kernel.core.types import CapabilityDescriptor, ICapabilityProvider

    class Echo(ICapabilityProvider):
        def get_descriptor(self):
            return desc
        def invoke(self, inv):
            return {"echo": True}
        def verify(self, inv, res):
            return True

    desc = CapabilityDescriptor(capability_id="test.echo", version="1.0",
                                provider="test", description="echo",
                                required_resources=ResourceBudget.zero())
    k = _kernel(tmp_path)
    try:
        k.register_capability(desc, Echo())
        cap = k.hypervisor.create_capsule(
            Intent(actor="human", objective="chain"),
            "minimal", extra_capabilities=["test.echo"])
        k.hypervisor.start_capsule(cap.capsule_id)
        assert "test.echo" in cap.capabilities
        errors: list = []

        def invoke_many() -> None:
            try:
                for _ in range(10):
                    k.hypervisor.invoke(cap.capsule_id, "test.echo", {"n": 1})
            except Exception as exc:  # noqa: BLE001 - collected, asserted empty
                errors.append(exc)

        threads = [threading.Thread(target=invoke_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        assert not errors
        receipts = k.hypervisor._receipts.get(cap.capsule_id, [])
        assert len(receipts) == 40
        # Hash chain links verify end-to-end (no lost/interleaved links).
        for prev, cur in zip([None] + receipts, receipts):
            assert cur.previous_hash == (prev.receipt_hash if prev else "")
    finally:
        k._shutdown_flag = True
