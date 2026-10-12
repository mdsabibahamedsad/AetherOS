"""Memory security: secret refusal, injection firewall, access control.

P32-40 + P83-84 semantics:
- Secrets are never persisted (refused with SecretDetectedError).
- Untrusted sources (WEB/TOOL/MODEL_INFERENCE) can never create authoritative
  or procedural memory; injection-shaped content is quarantined.
- Every retrieval is evaluated against an AccessContext (owner/scope/project/
  agent/tool/sensitivity).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from agent.memory_os.models import (
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    Sensitivity,
    SourceType,
    UNTRUSTED_SOURCES,
)


class SecretDetected(Exception):
    """P33/34 — content looks like a credential; refuse to persist."""


class FirewallViolation(Exception):
    """P39 — external content attempted to create authoritative memory."""


class AccessDenied(Exception):
    """P36 — retrieval/store not permitted for this actor."""


SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{30,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\."),  # JWT
    re.compile(r"(?i)\b(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*\S{8,}"),
    re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+\S{8,}"),
    re.compile(r"(?i)\brecovery\s+codes?\b\s*[:=]"),
    re.compile(r"(?i)\bsession[-_]?(token|id|cookie)\s*[:=]\s*\S{8,}"),
    re.compile(r"(?i)\bcookie\s*:\s*\S{10,}"),
]

# P39/P40/P84 — durable-instruction planting attempts from external content.
INJECTION_PATTERNS = [
    re.compile(r"(ignore|disregard)\s+(all\s+)?(previous|prior|above|your)\s+"
               r"(instructions|rules|prompts|policies)", re.I),
    re.compile(r"you\s+(are\s+now|must\s+now|will\s+now)\s+(a|an|the)\s+", re.I),
    re.compile(r"reveal\s+(your|the)\s+(system\s+)?(prompt|instructions)", re.I),
    re.compile(r"new\s+(permanent\s+)?policy\s*:", re.I),
    re.compile(r"always\s+(send|forward|upload|post)\s+(files?|data|credentials?)\s+to\b", re.I),
    re.compile(r"remember\s+(this|the)\s+(password|api[- ]?key|token|secret|credential)", re.I),
    re.compile(r"exfiltrat(e|ion)|upload\s+secrets?\s+to", re.I),
]


def scan_secrets(content: str) -> Optional[str]:
    """Return the matching secret pattern description, or None if clean."""
    for pat in SECRET_PATTERNS:
        m = pat.search(content)
        if m:
            return pat.pattern
    return None


def scan_injection(content: str) -> Optional[str]:
    """Return the matching injection pattern description, or None."""
    for pat in INJECTION_PATTERNS:
        m = pat.search(content)
        if m:
            return pat.pattern
    return None


class ActorKind(str, Enum):
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    SYSTEM = "system"


@dataclass
class AccessContext:
    """Who is asking. Evaluated on every store/retrieve/delete (P36)."""

    kind: ActorKind = ActorKind.USER
    actor_id: str = "default"          # user name, agent id, or tool id
    project_id: str = ""               # project currently "entered" (P56/57)
    task_id: str = ""
    tool_id: str = ""                  # for kind=TOOL
    roles: frozenset = field(default_factory=lambda: frozenset({"user"}))

    @classmethod
    def user(cls, actor_id: str = "default", project_id: str = "") -> "AccessContext":
        return cls(kind=ActorKind.USER, actor_id=actor_id, project_id=project_id,
                   roles=frozenset({"user"}))

    @classmethod
    def agent(cls, agent_id: str, project_id: str = "", task_id: str = "") -> "AccessContext":
        return cls(kind=ActorKind.AGENT, actor_id=agent_id, project_id=project_id,
                   task_id=task_id, roles=frozenset({"agent"}))

    @classmethod
    def tool(cls, tool_id: str, project_id: str = "") -> "AccessContext":
        return cls(kind=ActorKind.TOOL, actor_id=tool_id, tool_id=tool_id,
                   project_id=project_id, roles=frozenset({"tool"}))


def check_read_access(item: MemoryItem, ctx: AccessContext) -> bool:
    """P36/P37/P90 authorization predicate for a retrieval candidate."""
    if item.status == MemoryStatus.FORGOTTEN:
        return False
    if item.sensitivity == Sensitivity.SENSITIVE and ctx.kind is not ActorKind.USER:
        return False
    if ctx.kind is ActorKind.AGENT:
        # Agents only see what was explicitly shared, their own task/project,
        # or non-sensitive project/research context of the current project.
        if item.scope in (MemoryScope.USER, MemoryScope.ORGANIZATION, MemoryScope.SYSTEM):
            if not item.allow_agents:
                return False
        if item.project_id and ctx.project_id and item.project_id != ctx.project_id:
            return False  # cross-project isolation (P57/P58)
        if item.task_id and ctx.task_id and item.task_id != ctx.task_id:
            if item.scope == MemoryScope.TASK:
                return False  # another agent's task memory
    if ctx.kind is ActorKind.TOOL:
        # Tools are the least privileged: no sensitive data, no org/system scope.
        if item.sensitivity == Sensitivity.SENSITIVE:
            return False
        if item.scope in (MemoryScope.ORGANIZATION, MemoryScope.SYSTEM):
            return False
    if ctx.kind is ActorKind.USER:
        # Users may read everything they own; other owners' USER-scope items
        # are private across owners (cross-user leakage guard, SC26).
        if item.owner != ctx.actor_id and item.scope in (
            MemoryScope.USER, MemoryScope.TASK, MemoryScope.SESSION
        ):
            return False
    return True


def enforce_write_firewall(
    *,
    type_: MemoryType,
    source_type: SourceType,
    status: MemoryStatus,
) -> MemoryStatus:
    """P39/P40/P84 — external content never becomes authoritative memory.

    Returns the (possibly downgraded) status that may be persisted.
    Raises FirewallViolation for hard violations (procedural/workflow/system
    types originating from untrusted sources).
    """
    authoritative_types = {MemoryType.PROCEDURAL, MemoryType.WORKFLOW, MemoryType.SYSTEM}
    if source_type in UNTRUSTED_SOURCES:
        if type_ in authoritative_types:
            raise FirewallViolation(
                f"{source_type.value} content cannot create {type_.value} memory"
            )
        if status == MemoryStatus.ACTIVE:
            status = MemoryStatus.CANDIDATE
    return status


# Sources whose raw content is external data even when the channel is
# user-mediated (P39: "a document saying 'ignore your policies' must remain
# untrusted content").
EXTERNAL_CONTENT_SOURCES = frozenset(
    set(UNTRUSTED_SOURCES) | {SourceType.USER_PROVIDED_FILE}
)


def pre_persist_check(item: MemoryItem, *, allow_quarantine: bool = True) -> MemoryStatus:
    """Full gate before persistence. Order matters: hard firewall violations
    (untrusted source creating authoritative memory) fail first; injection-
    shaped external content is then quarantined; secrets are refused
    unconditionally."""
    hit = scan_secrets(item.content)
    if hit:
        raise SecretDetected(f"refusing to persist credential-like content ({hit}); "
                             "use the approved credential store")
    enforce_write_firewall(
        type_=item.type, source_type=item.source_type, status=item.status
    )
    if item.source_type in EXTERNAL_CONTENT_SOURCES:
        inj = scan_injection(item.content)
        if inj:
            if not allow_quarantine:
                raise FirewallViolation(f"injection pattern in external content ({inj})")
            return MemoryStatus.QUARANTINED
    return item.status if item.status is MemoryStatus.ACTIVE else MemoryStatus.CANDIDATE
