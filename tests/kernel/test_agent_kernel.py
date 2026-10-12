"""AgentKernel 1.0 — lifecycle, syscalls, delegation, checkpoints, scheduling.

Hermetic: stub agent runtime (default), no network, no credentials.
"""

from __future__ import annotations

import time

import pytest

from kernel.core.kernel import AgentKernel
from kernel.core.syscalls import register_builtin_capabilities
from kernel.core.types import (
    AgentLifecycleState,
    CapabilityDescriptor,
    ICapabilityProvider,
    Intent,
    KernelConfig,
    ResourceBudget,
)


def _kernel():
    k = AgentKernel(KernelConfig(enable_event_bus=False, checkpoint_interval_seconds=0,
                                 health_check_interval_seconds=3600))
    k.boot()
    return k


def _minimal_budget():
    return ResourceBudget(cpu_cores=0.1, ram_mb=64, disk_mb=64, network_mbps=1.0,
                          llm_tokens_per_minute=1000, browser_sessions=0,
                          computer_sessions=0, device_sessions=0, agent_slots=0,
                          automation_slots=0)


def test_boot_and_health():
    k = _kernel()
    try:
        assert k.is_running()
        h = k.health()
        assert h["booted"] is True
        assert h["agents"]["total"] == 0
    finally:
        k._shutdown_flag = True


def test_intent_admission_and_validation():
    k = _kernel()
    try:
        ok = Intent(actor="human", objective="do a thing")
        r = k.intent_manager.admit(ok)
        assert r.allowed

        bad = Intent(actor="human", objective="")
        r2 = k.intent_manager.admit(bad)
        assert not r2.allowed

        past = Intent(actor="human", objective="late", deadline=time.time() - 10)
        r3 = k.intent_manager.admit(past)
        assert not r3.allowed
    finally:
        k._shutdown_flag = True


def test_agent_lifecycle_created_to_ready():
    k = _kernel()
    try:
        intent = Intent(actor="human", objective="lifecycle test")
        intent.requested_resources = _minimal_budget()
        intent.budget = _minimal_budget()
        p = k.create_agent_process(intent)
        assert p.state == AgentLifecycleState.ADMITTED
        assert k.start_agent(p.agent_id) is True
        assert p.state == AgentLifecycleState.READY
        assert k.pause_agent(p.agent_id) is False  # READY cannot pause
    finally:
        k._shutdown_flag = True


def test_capability_syscall_success_and_denial():
    k = _kernel()
    try:
        class Echo(ICapabilityProvider):
            def get_descriptor(self):
                return desc
            def invoke(self, inv):
                return {"echo": inv.inputs}
            def verify(self, inv, res):
                return True

        desc = CapabilityDescriptor(capability_id="test.echo", version="1.0",
                                    provider="test", description="echo")
        k.register_capability(desc, Echo())

        intent = Intent(actor="human", objective="cap test",
                        requested_capabilities=["test.echo"])
        intent.requested_resources = _minimal_budget()
        intent.budget = _minimal_budget()
        p = k.create_agent_process(intent)
        k.start_agent(p.agent_id)
        inv = k.invoke_capability(p.agent_id, "test.echo", {"a": 1}, intent_id=intent.intent_id)
        assert inv.status == "completed"
        assert inv.result == {"echo": {"a": 1}}

        desc2 = CapabilityDescriptor(capability_id="test.other", version="1.0",
                                     provider="test", description="other")
        k.register_capability(desc2, Echo())
        inv2 = k.invoke_capability(p.agent_id, "test.other", {}, intent_id=intent.intent_id)
        assert inv2.status == "denied"
    finally:
        k._shutdown_flag = True


def test_delegation_subset_enforced():
    k = _kernel()
    try:
        intent = Intent(actor="human", objective="parent",
                        requested_capabilities=["cap.a"])
        intent.requested_resources = _minimal_budget()
        intent.budget = _minimal_budget()
        p = k.create_agent_process(intent)
        child_intent = Intent(actor="agent", objective="child",
                              requested_capabilities=["cap.a", "cap.b"])
        grant = k.authority_manager.delegate_authority(p.agent_id, "child1", child_intent)
        assert grant.capabilities == ["cap.a"]
    finally:
        k._shutdown_flag = True


def test_checkpoint_create_and_list():
    k = _kernel()
    try:
        intent = Intent(actor="human", objective="cp test")
        intent.requested_resources = _minimal_budget()
        intent.budget = _minimal_budget()
        p = k.create_agent_process(intent)
        cp = k.create_checkpoint(p.agent_id)
        assert cp.agent_id == p.agent_id
        assert k.checkpoint_manager.get_checkpoint(cp.checkpoint_id) is not None
    finally:
        k._shutdown_flag = True


def test_syscall_catalog_registers():
    k = _kernel()
    try:
        counts = register_builtin_capabilities(k)
        assert counts["tools"] > 0
        assert counts["syscalls"] > 0
        assert k.capability_manager.get_descriptor("fs.read") is not None
        assert k.capability_manager.get_descriptor("agent.spawn") is not None
        assert k.capability_manager.get_descriptor("device.control") is not None
    finally:
        k._shutdown_flag = True


def test_emergency_stop_denies_and_resumes():
    k = _kernel()
    try:
        register_builtin_capabilities(k)
        intent = Intent(actor="human", objective="estop",
                        requested_capabilities=["memory.read"])
        intent.requested_resources = _minimal_budget()
        intent.budget = _minimal_budget()
        p = k.create_agent_process(intent)
        k.start_agent(p.agent_id)
        assert k.is_stopped() is False
        k.emergency_stop(reason="test")
        assert k.is_stopped() is True
        inv = k.invoke_capability(p.agent_id, "memory.read", {"key": "k"})
        assert inv.status == "denied"
        k.emergency_resume()
        assert k.is_stopped() is False
    finally:
        k._shutdown_flag = True


def test_memory_scoping():
    k = _kernel()
    try:
        from kernel.core.memory_manager import MemoryScope
        assert k.memory_manager.write("alice", MemoryScope.WORKING, "k", "v") is True
        assert k.memory_manager.read("alice", MemoryScope.WORKING, "k") == "v"
        assert k.memory_manager.read("bob", MemoryScope.WORKING, "k") is None
    finally:
        k._shutdown_flag = True


def test_sdk_smoke():
    from kernel.core.sdk import KernelSDK
    k = _kernel()
    try:
        sdk = KernelSDK(k)
        intent = Intent(actor="human", objective="sdk hello")
        intent.requested_resources = _minimal_budget()
        intent.budget = _minimal_budget()
        p = sdk.spawn("sdk hello")
        assert p.agent_id
        assert sdk.inspect(p.agent_id) is not None
        assert "available" in sdk.status() or "kernel" in sdk.status()
    finally:
        k._shutdown_flag = True
