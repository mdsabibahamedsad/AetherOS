"""
Agent Communication Fabric — authorization, least privilege, and delegation
chains (master spec steps 20-24).

Every message is authorized independently at delivery time. Nothing is trusted
because "the orchestrator already checked it" (step 13). The authorizer
evaluates sender, receiver, mission, task, capability, requested action,
resource, trust zone, scoped permissions, and the delegation chain.

Delegation propagates a *scoped* authorization context (step 23): a child can
never receive permissions its parent did not hold, and can never upgrade a
``read`` grant into a ``write`` grant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .envelope import AgentMessageEnvelope
from .identity import AgentRegistry, AgentStatus
from .types import MessageType
from .trust import TrustZonePolicy

# ---------------------------------------------------------------------------
# Scoped permission + authorization context (step 22-23)
# ---------------------------------------------------------------------------

#: Permission modes, ordered so ``read`` can never upgrade to ``write``.
_MODE_RANK = {"read": 0, "write": 1, "execute": 2, "admin": 3}


@dataclass
class ScopedPermission:
    """A capability grant scoped to a resource and mode (step 23).

    A delegation chain intersects these: a child receives ``min(parent_mode,
    granted_mode)`` and the parent's resource restriction, never more.
    """

    capability: str
    resource_glob: str = "*"
    mode: str = "read"
    granted_by: str = ""      # principal that granted it
    depth: int = 0            # delegation depth at grant time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability,
            "resource_glob": self.resource_glob,
            "mode": self.mode,
            "granted_by": self.granted_by,
            "depth": self.depth,
        }


@dataclass
class AuthorizationContext:
    """The authorization state carried by a delegation chain (step 22).

    ``principal_chain`` traces user -> orchestrator -> agent A -> agent B so
    every delegated request preserves the authorization chain. Only scoped
    permissions are propagated downstream — never unrestricted credentials
    (step 24).
    """

    principal_chain: List[str] = field(default_factory=list)
    scoped_permissions: List[ScopedPermission] = field(default_factory=list)
    mission_id: str = ""
    task_id: str = ""
    user: str = ""
    risk_level: str = "medium"
    delegation_depth: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def propagate(self, new_principal: str,
                  granted_capabilities: Optional[Iterable[str]] = None,
                  *, mission_id: str = "", task_id: str = "") -> "AuthorizationContext":
        """Derive a child context bound to ``new_principal``.

        The child's scoped permissions are the parent's permissions filtered
        to the granted capabilities (if any) — never widened, never resource-
        loosened. The chain grows by one principal.
        """
        child_perms = list(self.scoped_permissions)
        if granted_capabilities is not None:
            granted = set(granted_capabilities)
            child_perms = [
                p for p in child_perms if p.capability in granted
            ]
        child = AuthorizationContext(
            principal_chain=list(self.principal_chain) + [new_principal],
            scoped_permissions=child_perms,
            mission_id=mission_id or self.mission_id,
            task_id=task_id or self.task_id,
            user=self.user,
            risk_level=self.risk_level,
            delegation_depth=self.delegation_depth + 1,
            metadata=dict(self.metadata),
        )
        return child

    def grants(self, capability: str) -> bool:
        return any(p.capability == capability for p in self.scoped_permissions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal_chain": list(self.principal_chain),
            "scoped_permissions": [p.to_dict() for p in self.scoped_permissions],
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "user": self.user,
            "risk_level": self.risk_level,
            "delegation_depth": self.delegation_depth,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthorizationContext":
        perms = [
            ScopedPermission(
                capability=p.get("capability", ""),
                resource_glob=p.get("resource_glob", "*"),
                mode=p.get("mode", "read"),
                granted_by=p.get("granted_by", ""),
                depth=p.get("depth", 0),
            )
            for p in (data.get("scoped_permissions") or [])
        ]
        return cls(
            principal_chain=list(data.get("principal_chain") or []),
            scoped_permissions=perms,
            mission_id=data.get("mission_id", ""),
            task_id=data.get("task_id", ""),
            user=data.get("user", ""),
            risk_level=data.get("risk_level", "medium"),
            delegation_depth=data.get("delegation_depth", 0),
            metadata=dict(data.get("metadata") or {}),
        )

    def max_mode(self, capability: str) -> str:
        modes = [p.mode for p in self.scoped_permissions
                 if p.capability == capability]
        if not modes:
            return ""
        return max(modes, key=lambda m: _MODE_RANK.get(m, 0))


def _mode_at_least(granted: str, required: str) -> bool:
    return _MODE_RANK.get(granted, 0) >= _MODE_RANK.get(required, 0)


def capability_matches(declared: str, required: str) -> bool:
    """Whether a declared capability covers a required one.

    ``comm:*`` (or ``*``) covers ``comm:warn``; ``comm:*`` does not cover
    ``repository_read``. Exact string match otherwise.
    """
    if declared == required:
        return True
    if required and declared.endswith(":*"):
        prefix = declared[:-2]
        return prefix == "" or required.startswith(prefix + ":")
    if declared == "*":
        return bool(required)
    return False


def has_capability(declared: Iterable[str], required: str) -> bool:
    return any(capability_matches(cap, required) for cap in declared)


# ---------------------------------------------------------------------------
# Message-type policy (capability requirements per message type)
# ---------------------------------------------------------------------------


@dataclass
class MessagePolicyEntry:
    """Policy for one message type."""

    message_type: str
    required_capability: str = ""
    sensitive: bool = False
    allows_broadcast: bool = False


# Sensitive types require an authenticated, authorized, (optionally) signed
# message and are governed by the delegation chain / scoped permissions.
_SENSITIVE_POLICY: Dict[str, MessagePolicyEntry] = {
    MessageType.AUTHENTICATE.value: MessagePolicyEntry(
        MessageType.AUTHENTICATE.value, "auth:authenticate", sensitive=True),
    MessageType.TASK_REQUEST.value: MessagePolicyEntry(
        MessageType.TASK_REQUEST.value, "task:request", sensitive=True),
    MessageType.TASK_CANCEL.value: MessagePolicyEntry(
        MessageType.TASK_CANCEL.value, "task:cancel", sensitive=True),
    MessageType.DELEGATION_REQUEST.value: MessagePolicyEntry(
        MessageType.DELEGATION_REQUEST.value, "delegation:request", sensitive=True),
    MessageType.DELEGATION_RESPONSE.value: MessagePolicyEntry(
        MessageType.DELEGATION_RESPONSE.value, "delegation:respond", sensitive=True),
    MessageType.REVIEW_REQUEST.value: MessagePolicyEntry(
        MessageType.REVIEW_REQUEST.value, "review:request", sensitive=True),
    MessageType.REVIEW_RESULT.value: MessagePolicyEntry(
        MessageType.REVIEW_RESULT.value, "review:respond", sensitive=True),
    MessageType.APPROVAL_REQUEST.value: MessagePolicyEntry(
        MessageType.APPROVAL_REQUEST.value, "approval:request", sensitive=True),
    MessageType.APPROVAL_RESULT.value: MessagePolicyEntry(
        MessageType.APPROVAL_RESULT.value, "approval:respond", sensitive=True),
}

# Non-sensitive types still require the sender to be a registered, active
# agent and a zone policy allowance, but do not require a signed delegation
# context. Broadcast-capable types (empty receiverAgentId) are marked
# ``allows_broadcast`` — they may be announced to every agent; everything
# else must always name a receiver.
_NORMAL_POLICY: Dict[str, MessagePolicyEntry] = {
    MessageType.HELLO.value: MessagePolicyEntry(
        MessageType.HELLO.value, "", allows_broadcast=True),
    MessageType.CAPABILITY_QUERY.value: MessagePolicyEntry(
        MessageType.CAPABILITY_QUERY.value, "comm:capability_query"),
    MessageType.CAPABILITY_RESPONSE.value: MessagePolicyEntry(
        MessageType.CAPABILITY_RESPONSE.value, "comm:capability_response",
        allows_broadcast=True),
    MessageType.TASK_ACCEPTED.value: MessagePolicyEntry(
        MessageType.TASK_ACCEPTED.value, "task:respond"),
    MessageType.TASK_REJECTED.value: MessagePolicyEntry(
        MessageType.TASK_REJECTED.value, "task:respond"),
    MessageType.TASK_PROGRESS.value: MessagePolicyEntry(
        MessageType.TASK_PROGRESS.value, "task:report"),
    MessageType.TASK_RESULT.value: MessagePolicyEntry(
        MessageType.TASK_RESULT.value, "task:report"),
    MessageType.TASK_FAILED.value: MessagePolicyEntry(
        MessageType.TASK_FAILED.value, "task:report"),
    MessageType.TASK_CANCELLED.value: MessagePolicyEntry(
        MessageType.TASK_CANCELLED.value, "task:report"),
    MessageType.TASK_PAUSE.value: MessagePolicyEntry(
        MessageType.TASK_PAUSE.value, "task:manage"),
    MessageType.TASK_RESUME.value: MessagePolicyEntry(
        MessageType.TASK_RESUME.value, "task:manage"),
    MessageType.HEARTBEAT.value: MessagePolicyEntry(
        MessageType.HEARTBEAT.value, "comm:heartbeat", allows_broadcast=True),
    MessageType.HEALTH.value: MessagePolicyEntry(
        MessageType.HEALTH.value, "comm:health", allows_broadcast=True),
    MessageType.WARNING.value: MessagePolicyEntry(
        MessageType.WARNING.value, "comm:warn", allows_broadcast=True),
    MessageType.ERROR.value: MessagePolicyEntry(
        MessageType.ERROR.value, "comm:error", allows_broadcast=True),
    MessageType.RECOVERY.value: MessagePolicyEntry(
        MessageType.RECOVERY.value, "comm:recover", allows_broadcast=True),
    MessageType.SHUTDOWN.value: MessagePolicyEntry(
        MessageType.SHUTDOWN.value, "comm:shutdown", allows_broadcast=True),
    MessageType.GOODBYE.value: MessagePolicyEntry(
        MessageType.GOODBYE.value, "comm:goodbye", allows_broadcast=True),
}

_MESSAGE_POLICY = {**_NORMAL_POLICY, **_SENSITIVE_POLICY}


def policy_for(message_type: str) -> MessagePolicyEntry:
    return _MESSAGE_POLICY.get(
        message_type, MessagePolicyEntry(message_type, "comm:unknown"))


# ---------------------------------------------------------------------------
# The authorizer (steps 13, 20, 21)
# ---------------------------------------------------------------------------


@dataclass
class AuthzDecision:
    """Result of authorizing a message."""

    allowed: bool
    reason: str = ""
    code: str = "ALLOW"
    required_capability: str = ""
    sender_status: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "code": self.code,
            "required_capability": self.required_capability,
        }


class MessageAuthorizer:
    """Deterministic, fail-closed authorizer for inter-agent messages.

    Every sensitive request is independently validated (step 13): identity,
    zone, capability, mission/task ownership, and the delegation context.
    """

    def __init__(self, registry: AgentRegistry,
                 trust_policy: TrustZonePolicy,
                 *,
                 require_signed_sensitive: bool = True) -> None:
        self._registry = registry
        self._trust_policy = trust_policy
        self._require_signed = require_signed_sensitive

    # ------------------------------------------------------------------

    def authorize(self, envelope: AgentMessageEnvelope,
                  *, signature_ok: bool = True,
                  replay_ok: bool = True,
                  context: Optional[AuthorizationContext] = None,
                  require_signed: Optional[bool] = None) -> AuthzDecision:
        """Authorize ``envelope`` and return an :class:`AuthzDecision`.

        ``signature_ok`` / ``replay_ok`` are the results of the signing and
        replay checks performed by the inbound pipeline; the authorizer turns
        failures into DENY decisions so the pipeline has a single decision
        point.
        """
        try:
            mtype = envelope.message_type
        except Exception:
            return AuthzDecision(False, "unknown message type", "BAD_TYPE")

        policy = policy_for(envelope.messageType)

        # 1. Sender identity (zero-trust: never trust the name on the wire).
        sender = self._registry.get(envelope.senderAgentId)
        if sender is None:
            return AuthzDecision(False, "unknown sender", "UNKNOWN_SENDER",
                                 policy.required_capability, "unknown")
        if sender.status != AgentStatus.ACTIVE:
            return AuthzDecision(
                False, f"sender status is {sender.status}", "SENDER_NOT_ACTIVE",
                policy.required_capability, sender.status)

        # 2. Receiver identity (directed messages).
        if envelope.receiverAgentId:
            receiver = self._registry.get(envelope.receiverAgentId)
            if receiver is None:
                return AuthzDecision(False, "unknown receiver", "UNKNOWN_RECEIVER",
                                     policy.required_capability, sender.status)
            if receiver.status != AgentStatus.ACTIVE:
                return AuthzDecision(
                    False, f"receiver status is {receiver.status}",
                    "RECEIVER_NOT_ACTIVE", policy.required_capability,
                    sender.status)
        elif mtype is not None and not policy.allows_broadcast:
            return AuthzDecision(False, "broadcast not allowed for this type",
                                 "BROADCAST_DENIED", policy.required_capability,
                                 sender.status)

        # 3. Trust zone boundary (step 12).
        from .types import TrustZone
        sender_zone = TrustZone.from_str(sender.trustZone)
        required_cap = policy.required_capability
        if envelope.receiverAgentId:
            receiver_zone = TrustZone.from_str(
                self._registry.get(envelope.receiverAgentId).trustZone)
            if not self._trust_policy.can_communicate(
                    sender_zone, receiver_zone, capability=required_cap):
                return AuthzDecision(
                    False,
                    f"cross-zone {sender_zone.value}->{receiver_zone.value} "
                    "not permitted by policy",
                    "CROSS_ZONE_DENIED", required_cap, sender.status)

        # 4. Capability (least privilege, step 21).
        if required_cap and not self._capability_granted(
                envelope.senderAgentId, required_cap, context):
            return AuthzDecision(
                False, f"sender lacks capability {required_cap}",
                "CAPABILITY_DENIED", required_cap, sender.status)

        # 5. Mission / task ownership (step 6).
        if envelope.missionId:
            if context is None or (
                    context.mission_id and context.mission_id != envelope.missionId):
                return AuthzDecision(
                    False, "message missionId not owned by authorization context",
                    "MISSION_MISMATCH", required_cap, sender.status)
        if envelope.taskId:
            if context is None or (
                    context.task_id and context.task_id != envelope.taskId):
                return AuthzDecision(
                    False, "message taskId not owned by authorization context",
                    "TASK_MISMATCH", required_cap, sender.status)

        # 6. Sensitive messages require a delegation/authorization context
        #    and (by default) a valid signature.
        if policy.sensitive:
            if context is None or not context.principal_chain:
                return AuthzDecision(
                    False, "sensitive message requires authorization context",
                    "NO_AUTHORIZATION_CONTEXT", required_cap, sender.status)
            # The chain must terminate at the sender: the real principal
            # acting is the last hop. A context whose chain ends anywhere
            # else is a forged delegation chain (impersonation).
            if context.principal_chain[-1] != envelope.senderAgentId:
                return AuthzDecision(
                    False, "authorization context does not chain to sender",
                    "CHAIN_MISMATCH", required_cap, sender.status)
            signed = (require_signed if require_signed is not None
                      else self._require_signed)
            if signed and not signature_ok:
                return AuthzDecision(
                    False, "sensitive message failed signature verification",
                    "BAD_SIGNATURE", required_cap, sender.status)

        # 7. Replay protection (step 16).
        if not replay_ok:
            return AuthzDecision(
                False, "replayed message rejected", "REPLAY_REJECTED",
                required_cap, sender.status)

        return AuthzDecision(True, "allowed", "ALLOW",
                             required_cap, sender.status)

    def _capability_granted(self, sender_id: str, capability: str,
                            context: Optional[AuthorizationContext]) -> bool:
        """Capability grant check under least privilege.

        If a delegation context is present, its scoped permissions are
        authoritative (the child cannot fall back to self-declared base
        capabilities). Otherwise the agent's registered base capabilities
        are used.
        """
        if context is not None and context.scoped_permissions:
            return any(capability_matches(p.capability, capability)
                       for p in context.scoped_permissions)
        identity = self._registry.get(sender_id)
        return identity is not None and has_capability(
            identity.capabilities, capability)