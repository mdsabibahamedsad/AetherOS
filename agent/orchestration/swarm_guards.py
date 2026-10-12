"""Runtime swarm security guards (P73-79).

Enforcement — not description:
- capabilities are intersected at assignment and checked at every tool call;
- agent messages are DATA: injection-shaped content is flagged, never obeyed;
- handoffs cannot carry secrets or unauthorized sensitivity across agents
  (exfiltration guard);
- execution identity chains are validated (no impersonation).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

from agent.orchestration.types import RiskLevel


class CapabilityViolation(Exception):
    """P20/P21/P73 — agent used a capability it was never granted."""


class ExfiltrationBlocked(Exception):
    """P78 — transfer would move sensitive payload to an unauthorized target."""


class SecretBoundaryViolation(Exception):
    """P79 — secret material detected in a cross-agent payload."""


class ImpersonationBlocked(Exception):
    """P95 — identity chain does not match the claimed parent/execution."""


# --- capability model (P4) ------------------------------------------------------

class Capability:
    WEB_SEARCH = "WEB_SEARCH"
    BROWSER_READ = "BROWSER_READ"
    BROWSER_INTERACT = "BROWSER_INTERACT"
    FILE_READ = "FILE_READ"
    FILE_WRITE = "FILE_WRITE"
    SHELL_EXECUTE = "SHELL_EXECUTE"
    CODE_EDIT = "CODE_EDIT"
    TEST_EXECUTE = "TEST_EXECUTE"
    COMPUTER_CONTROL = "COMPUTER_CONTROL"
    MCP_USE = "MCP_USE"
    MEMORY_READ = "MEMORY_READ"
    MEMORY_WRITE = "MEMORY_WRITE"
    RESEARCH = "RESEARCH"
    NETWORK_ACCESS = "NETWORK_ACCESS"

ALL_CAPABILITIES = frozenset({
    v for k, v in vars(Capability).items() if k.isupper()
})

# P6 — risk floor per capability; agent risk = max over granted caps.
_RISK = {
    Capability.WEB_SEARCH: RiskLevel.LOW,
    Capability.BROWSER_READ: RiskLevel.LOW,
    Capability.MEMORY_READ: RiskLevel.LOW,
    Capability.FILE_READ: RiskLevel.LOW,
    Capability.RESEARCH: RiskLevel.LOW,
    Capability.BROWSER_INTERACT: RiskLevel.MEDIUM,
    Capability.MCP_USE: RiskLevel.MEDIUM,
    Capability.NETWORK_ACCESS: RiskLevel.MEDIUM,
    Capability.CODE_EDIT: RiskLevel.MEDIUM,
    Capability.TEST_EXECUTE: RiskLevel.MEDIUM,
    Capability.MEMORY_WRITE: RiskLevel.MEDIUM,
    Capability.FILE_WRITE: RiskLevel.HIGH,
    Capability.SHELL_EXECUTE: RiskLevel.HIGH,
    Capability.COMPUTER_CONTROL: RiskLevel.CRITICAL,
}

_RISK_ORDER = {
    RiskLevel.READ_ONLY: 0, RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4,
}


def risk_from_capabilities(capabilities: Iterable[str]) -> RiskLevel:
    """P6 — risk comes from actual granted capabilities, never the name."""
    level = RiskLevel.READ_ONLY
    for cap in capabilities:
        cap_risk = _RISK.get(cap)
        if cap_risk is not None and _RISK_ORDER[cap_risk] > _RISK_ORDER[level]:
            level = cap_risk
    return level


@dataclass
class GrantedCapabilities:
    """The immutable intersection an agent actually receives (P5)."""

    agent_id: str
    task_id: str
    caps: frozenset
    risk: RiskLevel = RiskLevel.READ_ONLY

    @classmethod
    def grant(cls, *, agent_id: str, task_id: str,
              requested: Iterable[str], manifest_caps: Iterable[str]) -> "GrantedCapabilities":
        allowed = set(manifest_caps)
        effective = frozenset(c for c in requested if c in allowed)
        return cls(agent_id=agent_id, task_id=task_id, caps=effective,
                   risk=risk_from_capabilities(effective))

    def check(self, capability: str) -> None:
        if capability not in self.caps:
            raise CapabilityViolation(
                f"agent {self.agent_id} attempted {capability} without grant "
                f"(has: {sorted(self.caps)})"
            )


# --- message / handoff guards (P18, P77-79) -------------------------------------

_INJECTION_MARKERS = (
    ("ignore", "previous"), ("ignore", "instructions"),
    ("ignore all previous instructions",),
    ("disregard", "policy"), ("disregard", "instructions"),
    ("you are now",), ("new policy:",), ("policy override",),
    ("reveal your", "system prompt"), ("override", "security"),
    ("grant", "computer_control"), ("disable security"),
)


def scan_message_for_injection(text: str) -> List[str]:
    """Return matched marker descriptions; message stays DATA either way."""
    low = " ".join(str(text).lower().split())
    hits = []
    for markers in _INJECTION_MARKERS:
        if all(m in low for m in markers):
            hits.append("+".join(markers))
    return hits


@dataclass
class SensitivityLabel:
    level: str = "internal"          # public|internal|sensitive|secret
    topics: Set[str] = field(default_factory=set)


def check_handoff_payload(
    *,
    source_agent: str,
    target_agent: str,
    payload: Dict[str, Any],
    target_authorized_topics: Optional[Set[str]] = None,
) -> List[str]:
    """P76/P78/P79 — screen a handoff/blackboard payload before transfer.

    - secret-shaped strings anywhere in the payload are refused outright;
    - 'sensitive'-labeled entries pass only when every topic is in the
      target's authorization set (else ExfiltrationBlocked);
    - injection-shaped free text is returned as warnings (content remains
      DATA and is delivered flagged, never executed as instruction).
    """
    from agent.memory_os.security import scan_secrets

    warnings: List[str] = []
    authorized = target_authorized_topics or set()

    def walk(obj: Any, path: str) -> None:
        if isinstance(obj, str):
            if scan_secrets(obj):
                raise SecretBoundaryViolation(
                    f"secret material at '{path}' in {source_agent}->{target_agent} "
                    "handoff; use the credential architecture instead"
                )
            for hit in scan_message_for_injection(obj):
                warnings.append(f"injection-marker:{hit}@{path}")
        elif isinstance(obj, dict):
            label = obj.get("sensitivity")
            for k, v in obj.items():
                if k == "sensitivity" and isinstance(v, str) and v == "sensitive":
                    topics = set(obj.get("topics") or ())
                    if not topics or not topics.issubset(authorized):
                        raise ExfiltrationBlocked(
                            f"sensitive payload '{path}' not authorized for "
                            f"{target_agent} (topics={sorted(topics)})"
                        )
                walk(v, f"{path}.{k}")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")

    walk(payload, "payload")
    return warnings


# --- identity chain (P7, impersonation guard) ------------------------------------

@dataclass
class ExecutionIdentity:
    agent_id: str
    execution_id: str
    parent_execution_id: str
    task_id: str
    user_context: str
    created_at: float = field(default_factory=time.time)

    def validate_child(self, child: "ExecutionIdentity",
                       *, max_depth: int = 3, parent_depth: int = 1) -> None:
        """Impersonation + recursion guard (P60-61, P95).

        The orchestrator passes its own identity as `self` and its current
        chain depth; a spawn is valid only when the child points back at THIS
        execution, stays inside the same task, and the resulting chain keeps
        within max_depth.
        """
        if not child.agent_id or not child.execution_id or not child.task_id:
            raise ImpersonationBlocked("child identity incomplete")
        if child.parent_execution_id != self.execution_id:
            raise ImpersonationBlocked(
                f"child {child.execution_id} claims parent "
                f"{child.parent_execution_id}, actual {self.execution_id}"
            )
        if self.task_id and child.task_id != self.task_id:
            raise ImpersonationBlocked(
                "child task_id must stay within parent's task"
            )
        if parent_depth + 1 > max_depth:
            raise ImpersonationBlocked(
                f"delegation depth {parent_depth + 1} exceeds cap {max_depth}"
            )
        return child


def derive_tool_risk(capability: str) -> RiskLevel:
    """P74 — per-call risk floor used by tool-policy checks."""
    return _RISK.get(capability, RiskLevel.LOW)
