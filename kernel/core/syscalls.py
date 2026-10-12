"""
AetherOS Agent Kernel 1.0 — Canonical Capability Syscall Catalog.

Maps the Master-57 syscall surface (§8) onto:
  1. existing AetherOS tools (via ToolManager / tools registry) — reused, not duplicated
  2. kernel-native handlers (agent.spawn, agent.delegate, memory.*, checkpoint.*)
  3. explicit UNAVAILABLE stubs for hardware/physical capabilities that cannot
     execute in this environment (fail-closed; never fake success).

Usage:
    from kernel.core.syscalls import register_builtin_capabilities
    counts = register_builtin_capabilities(kernel)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from kernel.core.types import (
    CapabilityDescriptor,
    CapabilityInvocation,
    CapabilityRiskLevel,
    DataClassification,
    ICapabilityProvider,
    ResourceBudget,
)

logger = logging.getLogger(__name__)

# Canonical syscall -> existing AetherOS tool(s), first hit wins.
# Tools are registered as `tool.<name>` by ToolManager.discover_tools().
_SYSCALL_TOOL_MAP: Dict[str, List[str]] = {
    "fs.read": ["read_file"],
    "fs.write": ["write_file"],
    "fs.delete": ["write_file"],
    "fs.list": ["search_files"],
    "fs.search": ["search_files"],
    "fs.patch": ["patch"],
    "process.execute": ["process", "execute_code"],
    "terminal.execute": ["terminal"],
    "network.request": ["web_extract", "web_search"],
    "research.search": ["web_search", "session_search"],
    "research.fetch": ["web_extract", "document_extract"],
    "browser.navigate": ["browser_navigate"],
    "browser.click": ["browser_click"],
    "browser.type": ["browser_type"],
    "browser.screenshot": ["browser_snapshot", "screen_capture"],
    "browser.extract": ["browser_snapshot", "web_extract"],
    "computer.observe": ["screen_capture", "screen_understand", "computer_use"],
    "computer.screenshot": ["screen_capture", "computer_use"],
    "computer.click": ["computer_use"],
    "computer.type": ["computer_use"],
    "memory.read": ["memory", "memory2_get", "memory2_search"],
    "memory.write": ["memory", "memory2_create"],
    "memory.search": ["memory2_search", "memory"],
    "automation.create": ["automation_create", "automation_build"],
    "automation.execute": ["automation_run"],
    "agent.delegate": ["delegate_task"],
    "message.send": ["discord", "integration_webhook"],
    "vision.analyze": ["vision_analyze", "screen_understand"],
    "audio.transcribe": ["text_to_speech"],
}

# Capabilities that MUST NOT execute without real hardware / credentials.
# They are registered as explicit BLOCKED stubs (fail-closed).
_HARDWARE_GATED = [
    "device.control",
    "robot.navigate",
    "robot.manipulate",
    "device.pair",
]


class _AliasProvider(ICapabilityProvider):
    """Routes a canonical syscall to an existing tool capability."""

    def __init__(self, syscall: str, target_capability: str, tool_provider: ICapabilityProvider,
                 descriptor: CapabilityDescriptor):
        self.syscall = syscall
        self.target = target_capability
        self._tool_provider = tool_provider
        self._descriptor = descriptor

    def get_descriptor(self) -> CapabilityDescriptor:
        return self._descriptor

    def invoke(self, invocation: CapabilityInvocation) -> Any:
        invocation.inputs = dict(invocation.inputs or {})
        return self._tool_provider.invoke(invocation)

    def verify(self, invocation: CapabilityInvocation, result: Any) -> bool:
        try:
            return bool(self._tool_provider.verify(invocation, result))
        except Exception:
            return result is not None


class _UnavailableProvider(ICapabilityProvider):
    """Fail-closed stub: always raises, never fakes success."""

    def __init__(self, descriptor: CapabilityDescriptor, reason: str):
        self._descriptor = descriptor
        self._reason = reason

    def get_descriptor(self) -> CapabilityDescriptor:
        return self._descriptor

    def invoke(self, invocation: CapabilityInvocation) -> Any:
        raise RuntimeError(f"BLOCKED ({self._descriptor.capability_id}): {self._reason}")

    def verify(self, invocation: CapabilityInvocation, result: Any) -> bool:
        return False


class _KernelNativeProvider(ICapabilityProvider):
    """Wraps a plain callable as a kernel-native capability."""

    def __init__(self, descriptor: CapabilityDescriptor, fn):
        self._descriptor = descriptor
        self._fn = fn

    def get_descriptor(self) -> CapabilityDescriptor:
        return self._descriptor

    def invoke(self, invocation: CapabilityInvocation) -> Any:
        return self._fn(invocation)

    def verify(self, invocation: CapabilityInvocation, result: Any) -> bool:
        return result is not None


def _alias_descriptor(syscall: str, tool_desc: CapabilityDescriptor) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=syscall,
        version="1.0",
        provider="aetheros.kernel.syscalls",
        description=f"Kernel syscall {syscall} (via {tool_desc.capability_id})",
        inputs=dict(tool_desc.inputs or {}),
        outputs=dict(tool_desc.outputs or {}),
        side_effects=list(tool_desc.side_effects or [CapabilityRiskLevel.READ_ONLY]),
        required_authority=[syscall],
        required_resources=tool_desc.required_resources,
        required_credentials=list(tool_desc.required_credentials or []),
        network_access=tool_desc.network_access,
        filesystem_access=tool_desc.filesystem_access,
        device_access=tool_desc.device_access,
        data_classification=tool_desc.data_classification,
        reversibility=tool_desc.reversibility,
        idempotency=tool_desc.idempotency,
        latency_class=tool_desc.latency_class,
        cost_class=tool_desc.cost_class,
        sandbox_support=tool_desc.sandbox_support,
        verification_strategy=tool_desc.verification_strategy,
        tags=["syscall", syscall.split(".")[0]],
    )


def register_builtin_capabilities(kernel) -> Dict[str, int]:
    """Register the canonical syscall catalog on a booted kernel.

    Returns counts {tools, syscalls, native, unavailable}.
    Idempotent: re-registration overwrites the same capability ids.
    """
    counts = {"tools": 0, "syscalls": 0, "native": 0, "unavailable": 0}

    # 1. Existing tools -> tool.* capabilities (reuse, no duplication)
    try:
        counts["tools"] = kernel.tool_manager.discover_tools()
    except Exception as exc:
        logger.warning("syscalls: tool discovery failed: %s", exc)

    cap_mgr = kernel.capability_manager

    # 2. Canonical syscall aliases -> first available backing tool
    for syscall, candidates in _SYSCALL_TOOL_MAP.items():
        for tool_name in candidates:
            tool_cap = f"tool.{tool_name}"
            tool_desc = cap_mgr.get_descriptor(tool_cap)
            provider = cap_mgr.get_provider(tool_cap)
            if tool_desc is not None and provider is not None:
                alias = _alias_descriptor(syscall, tool_desc)
                cap_mgr.register(alias, _AliasProvider(syscall, tool_cap, provider, alias))
                counts["syscalls"] += 1
                break

    # 3. Kernel-native capabilities (agent lifecycle, memory scope, checkpoints)
    def _spawn(inv: CapabilityInvocation):
        from kernel.core.types import Intent as _Intent
        objective = (inv.inputs or {}).get("objective", "spawned subtask")
        intent = _Intent(actor=f"agent:{inv.agent_id}", objective=str(objective),
                         requested_capabilities=list((inv.inputs or {}).get("capabilities", [])))
        parent = kernel.get_agent_process(inv.agent_id)
        grant = kernel.authority_manager.delegate_authority(
            inv.agent_id, "pending-child", intent,
            parent_grant_id=parent.authority.grant_id if parent and parent.authority else None,
        ) if parent else None
        # Create the child process under the delegated grant
        from kernel.core.types import AgentIdentity as _Id, new_id as _nid
        identity = _Id(subject=f"child-of:{inv.agent_id}", display_name=str(objective)[:80])
        child = kernel.create_agent_process(intent, identity=identity, parent_agent_id=inv.agent_id)
        if grant is not None:
            # Prefer the explicitly delegated (subset-enforced) grant
            grant.agent_id = child.agent_id
            child.authority = grant
            child.capabilities = list(grant.capabilities)
        return {"agent_id": child.agent_id, "process_id": child.process_id}

    def _delegate(inv: CapabilityInvocation):
        return _spawn(inv)

    def _mem_read(inv: CapabilityInvocation):
        from kernel.core.memory_manager import MemoryScope as _MS
        scope = _MS.WORKING
        return kernel.memory_manager.read(inv.agent_id, scope, (inv.inputs or {}).get("key", ""))

    def _mem_write(inv: CapabilityInvocation):
        from kernel.core.memory_manager import MemoryScope as _MS
        kernel.memory_manager.write(inv.agent_id, _MS.WORKING,
                                    (inv.inputs or {}).get("key", ""),
                                    (inv.inputs or {}).get("value"))
        return {"ok": True}

    def _checkpoint(inv: CapabilityInvocation):
        cp = kernel.checkpoint_manager.create_full_checkpoint(kernel.get_agent_process(inv.agent_id)) \
            if kernel.get_agent_process(inv.agent_id) else kernel.checkpoint_manager.create_checkpoint(inv.agent_id)
        return {"checkpoint_id": cp.checkpoint_id}

    natives = [
        ("agent.spawn", "Spawn a child agent process (authority subset-enforced)", _spawn,
         [CapabilityRiskLevel.EXTERNAL_SIDE_EFFECT], False, False),
        ("agent.delegate", "Delegate an objective to a child agent", _delegate,
         [CapabilityRiskLevel.EXTERNAL_SIDE_EFFECT], False, False),
        ("memory.read", "Read from the agent's memory scope", _mem_read,
         [CapabilityRiskLevel.READ_ONLY], True, True),
        ("memory.write", "Write to the agent's memory scope", _mem_write,
         [CapabilityRiskLevel.REVERSIBLE], False, False),
        ("checkpoint.create", "Checkpoint the calling agent process", _checkpoint,
         [CapabilityRiskLevel.READ_ONLY], True, True),
    ]
    for cap_id, desc, fn, risks, rev, idem in natives:
        d = CapabilityDescriptor(
            capability_id=cap_id, version="1.0", provider="aetheros.kernel",
            description=desc, side_effects=risks, required_authority=[cap_id],
            required_resources=ResourceBudget(), reversibility=rev, idempotency=idem,
            verification_strategy="observe", tags=["syscall", "kernel"],
        )
        cap_mgr.register(d, _KernelNativeProvider(d, fn))
        counts["native"] += 1

    # 4. Hardware-gated stubs (fail-closed, explicit BLOCKED)
    for cap_id in _HARDWARE_GATED:
        d = CapabilityDescriptor(
            capability_id=cap_id, version="1.0", provider="aetheros.kernel",
            description=f"{cap_id} (REQUIRES_HARDWARE — blocked in this environment)",
            side_effects=[CapabilityRiskLevel.PHYSICAL, CapabilityRiskLevel.SECURITY_CRITICAL],
            required_authority=[cap_id], required_resources=ResourceBudget(),
            device_access=True, data_classification=DataClassification.CONFIDENTIAL,
            verification_strategy="attest", tags=["syscall", "hardware", "blocked"],
        )
        cap_mgr.register(d, _UnavailableProvider(d, "REQUIRES_HARDWARE"))
        counts["unavailable"] += 1

    # 5. Admission-time convenience: grant-aware listing lives on the kernel
    logger.info("syscalls: registered %s", counts)
    return counts
