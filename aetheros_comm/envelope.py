"""
Agent Communication Fabric — message envelope and validation
(master spec steps 3, 6, 17, 26).

Every agent-to-agent message is carried in an :class:`AgentMessageEnvelope`
with the required identity / routing / correlation / security fields. Every
inbound message passes through :class:`EnvelopeValidator` before business
logic executes — malformed messages are rejected with a specific reason, never
silently interpreted.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .protocol import PROTOCOL_VERSION
from .types import ContentOrigin, MessagePriority, MessageType, TrustZone

# ---------------------------------------------------------------------------
# Size limits (step 26) — configurable defaults.
# ---------------------------------------------------------------------------


@dataclass
class EnvelopeLimits:
    """Configurable message size limits.

    Any message exceeding a limit is rejected *before* parsing payloads, so
    an oversized or deeply-nested message cannot cause unbounded work.
    """

    max_message_bytes: int = 256 * 1024       # 256 KiB serialized envelope
    max_payload_bytes: int = 192 * 1024       # 192 KiB payload
    max_metadata_bytes: int = 32 * 1024       # 32 KiB metadata
    max_field_length: int = 512               # individual string field length
    max_depth: int = 32                       # nested object/list depth
    max_capabilities: int = 256               # entries in capabilities list
    max_security_context_bytes: int = 16 * 1024

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_message_bytes": self.max_message_bytes,
            "max_payload_bytes": self.max_payload_bytes,
            "max_metadata_bytes": self.max_metadata_bytes,
            "max_field_length": self.max_field_length,
            "max_depth": self.max_depth,
            "max_capabilities": self.max_capabilities,
            "max_security_context_bytes": self.max_security_context_bytes,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "EnvelopeLimits":
        data = data or {}
        return cls(**{k: v for k, v in data.items() if k in {
            "max_message_bytes", "max_payload_bytes", "max_metadata_bytes",
            "max_field_length", "max_depth", "max_capabilities",
            "max_security_context_bytes",
        }})


# ---------------------------------------------------------------------------
# The envelope (step 3)
# ---------------------------------------------------------------------------


@dataclass
class AgentMessageEnvelope:
    """Structured envelope for every agent-to-agent message.

    Fields mirror the master spec step 3 list:

        messageId, messageType, protocolVersion, senderAgentId,
        receiverAgentId, senderInstanceId, missionId, taskId, correlationId,
        causationId, timestamp, expiresAt, priority, securityContext,
        capabilities, payload, signature, metadata
    """

    messageId: str = ""
    messageType: str = MessageType.HELLO.value
    protocolVersion: str = PROTOCOL_VERSION
    senderAgentId: str = ""
    receiverAgentId: str = ""          # "" for broadcast
    senderInstanceId: str = ""
    missionId: str = ""
    taskId: str = ""
    correlationId: str = ""            # links a response to its request
    causationId: str = ""              # parent message that caused this one
    timestamp: float = 0.0
    expiresAt: float = 0.0             # 0.0 = never expires (step 17)
    priority: int = int(MessagePriority.NORMAL)
    securityContext: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    signature: str = ""                # base64 HMAC over canonical bytes
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messageId:
            self.messageId = uuid.uuid4().hex
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.senderInstanceId:
            self.senderInstanceId = f"inst-{uuid.uuid4().hex[:12]}"

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messageId": self.messageId,
            "messageType": self.messageType,
            "protocolVersion": self.protocolVersion,
            "senderAgentId": self.senderAgentId,
            "receiverAgentId": self.receiverAgentId,
            "senderInstanceId": self.senderInstanceId,
            "missionId": self.missionId,
            "taskId": self.taskId,
            "correlationId": self.correlationId,
            "causationId": self.causationId,
            "timestamp": self.timestamp,
            "expiresAt": self.expiresAt,
            "priority": self.priority,
            "securityContext": dict(self.securityContext),
            "capabilities": list(self.capabilities),
            "payload": self.payload,
            "signature": self.signature,
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessageEnvelope":
        caps = data.get("capabilities")
        capabilities = list(caps) if isinstance(caps, (list, tuple)) else caps
        return cls(
            messageId=data.get("messageId", ""),
            messageType=data.get("messageType", MessageType.HELLO.value),
            protocolVersion=data.get("protocolVersion", PROTOCOL_VERSION),
            senderAgentId=data.get("senderAgentId", ""),
            receiverAgentId=data.get("receiverAgentId", ""),
            senderInstanceId=data.get("senderInstanceId", ""),
            missionId=data.get("missionId", ""),
            taskId=data.get("taskId", ""),
            correlationId=data.get("correlationId", ""),
            causationId=data.get("causationId", ""),
            timestamp=data.get("timestamp", 0.0),
            expiresAt=data.get("expiresAt", 0.0),
            priority=data.get("priority", int(MessagePriority.NORMAL)),
            securityContext=data.get("securityContext", {}) or {},
            capabilities=capabilities,
            payload=data.get("payload", {}) or {},
            signature=data.get("signature", ""),
            metadata=data.get("metadata", {}) or {},
        )

    @classmethod
    def from_json(cls, text: str) -> "AgentMessageEnvelope":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise EnvelopeError("envelope must be a JSON object", "NOT_OBJECT")
        return cls.from_dict(data)

    # -- signing support (step 15) ------------------------------------------

    def canonical_bytes(self) -> bytes:
        """Deterministic bytes covering every field except ``signature``.

        This is what the HMAC signature is computed over, so signature
        verification detects any change to the message.
        """
        parts = [
            self.messageId,
            self.messageType,
            self.protocolVersion,
            self.senderAgentId,
            self.receiverAgentId,
            self.senderInstanceId,
            self.missionId,
            self.taskId,
            self.correlationId,
            self.causationId,
            repr(self.timestamp),
            repr(self.expiresAt),
            repr(int(self.priority)),
        ]
        canonical = "\x1f".join(parts)
        canonical += "\x1e" + _canonical_json(self.securityContext)
        canonical += "\x1e" + _canonical_json(sorted(self.capabilities))
        canonical += "\x1e" + _canonical_json(self.payload)
        canonical += "\x1e" + _canonical_json(_sorted_dict(self.metadata))
        return canonical.encode("utf-8")

    # -- convenience --------------------------------------------------------

    @property
    def message_type(self) -> MessageType:
        try:
            return MessageType(self.messageType)
        except ValueError:
            raise EnvelopeError(
                f"unknown messageType {self.messageType!r}", "BAD_MESSAGE_TYPE"
            ) from None

    @property
    def is_expired(self) -> bool:
        return self.expiresAt > 0 and time.time() >= self.expiresAt

    @property
    def is_sensitive(self) -> bool:
        return self.message_type in _SENSITIVE_MESSAGE_TYPES


# Message types that must be authenticated / authorized / (optionally) signed.
_SENSITIVE_MESSAGE_TYPES = frozenset({
    MessageType.AUTHENTICATE.value,
    MessageType.TASK_REQUEST.value,
    MessageType.TASK_CANCEL.value,
    MessageType.DELEGATION_REQUEST.value,
    MessageType.DELEGATION_RESPONSE.value,
    MessageType.REVIEW_REQUEST.value,
    MessageType.REVIEW_RESULT.value,
    MessageType.APPROVAL_REQUEST.value,
    MessageType.APPROVAL_RESULT.value,
    MessageType.HEARTBEAT.value,
})

# Message types that may be broadcast (empty receiverAgentId). Directed
# types (requests, results, delegation, ...) must always name a receiver.
_BROADCAST_CAPABLE_TYPES = frozenset({
    MessageType.HELLO.value,
    MessageType.WARNING.value,
    MessageType.ERROR.value,
    MessageType.RECOVERY.value,
    MessageType.SHUTDOWN.value,
    MessageType.GOODBYE.value,
    MessageType.HEARTBEAT.value,
    MessageType.HEALTH.value,
    MessageType.CAPABILITY_RESPONSE.value,
})


def _sorted_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: data[k] for k in sorted(data.keys())}


def _canonical_json(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True,
                      ensure_ascii=False)


# ---------------------------------------------------------------------------
# Validation (step 6)
# ---------------------------------------------------------------------------


class EnvelopeError(Exception):
    """Raised when an envelope fails validation.

    ``code`` is a stable machine-readable rejection reason (used by the
    fuzz / security tests), ``reason`` is human-readable.
    """

    def __init__(self, reason: str, code: str = "INVALID") -> None:
        super().__init__(reason)
        self.reason = reason
        self.code = code


class EnvelopeValidator:
    """Schema, type, length, enum, timestamp, and limit validation.

    The validator is transport-agnostic: it validates an envelope or raw
    dict *before* any delivery or business logic runs.
    """

    def __init__(self, limits: Optional[EnvelopeLimits] = None) -> None:
        self.limits = limits or EnvelopeLimits()

    # -- top level ----------------------------------------------------------

    def validate_dict(self, data: Any) -> AgentMessageEnvelope:
        """Validate a raw dict and return a parsed envelope.

        Raises :class:`EnvelopeError` on the first violated rule.
        """
        if not isinstance(data, dict):
            raise EnvelopeError("envelope must be a JSON object", "NOT_OBJECT")
        self._check_depth(data, 1)
        envelope = AgentMessageEnvelope.from_dict(data)
        self.validate(envelope)
        return envelope

    def validate(self, env: AgentMessageEnvelope) -> None:
        """Validate an already-parsed envelope (idempotent, ordered checks)."""
        self._check_required(env)
        self._check_protocol(env)
        self._check_ids(env)
        self._check_message_type(env)
        self._check_timestamps(env)
        self._check_limits(env)
        self._check_capabilities(env)
        self._check_origin(env)
        self._check_priority(env)

    # -- individual checks --------------------------------------------------

    def _check_required(self, env: AgentMessageEnvelope) -> None:
        for field_name in ("messageId", "senderAgentId", "senderInstanceId"):
            value = getattr(env, field_name)
            if not isinstance(value, str) or not value:
                raise EnvelopeError(
                    f"missing required field {field_name}", "MISSING_FIELD")
        # receiverAgentId required except for broadcast-capable types
        if not isinstance(env.messageType, str):
            return
        if env.messageType not in _BROADCAST_CAPABLE_TYPES and not env.receiverAgentId:
            raise EnvelopeError(
                "receiverAgentId required for non-broadcast message",
                "MISSING_FIELD")

    def _check_protocol(self, env: AgentMessageEnvelope) -> None:
        from .protocol import is_supported
        if not is_supported(env.protocolVersion):
            raise EnvelopeError(
                f"unsupported protocol version {env.protocolVersion!r}",
                "BAD_PROTOCOL")

    def _check_ids(self, env: AgentMessageEnvelope) -> None:
        for field_name in ("messageId", "senderAgentId", "receiverAgentId",
                           "senderInstanceId", "missionId", "taskId",
                           "correlationId", "causationId"):
            value = getattr(env, field_name)
            if not isinstance(value, str):
                raise EnvelopeError(
                    f"{field_name} must be a string", "BAD_TYPE")
            if len(value) > self.limits.max_field_length:
                raise EnvelopeError(
                    f"{field_name} exceeds max length",
                    "FIELD_TOO_LONG")

    def _check_message_type(self, env: AgentMessageEnvelope) -> None:
        if not isinstance(env.messageType, str):
            raise EnvelopeError("messageType must be a string", "BAD_TYPE")
        try:
            MessageType(env.messageType)
        except ValueError:
            raise EnvelopeError(
                f"unknown messageType {env.messageType!r}",
                "BAD_MESSAGE_TYPE") from None

    def _check_timestamps(self, env: AgentMessageEnvelope) -> None:
        if not isinstance(env.timestamp, (int, float)) or env.timestamp <= 0:
            raise EnvelopeError("timestamp must be a positive number", "BAD_TIMESTAMP")
        if not isinstance(env.expiresAt, (int, float)):
            raise EnvelopeError("expiresAt must be a number", "BAD_TIMESTAMP")
        if env.expiresAt and env.expiresAt <= env.timestamp:
            raise EnvelopeError(
                "expiresAt must be after timestamp", "BAD_EXPIRATION")
        if env.is_expired:
            raise EnvelopeError(
                "message has expired", "EXPIRED")

    def _check_limits(self, env: AgentMessageEnvelope) -> None:
        L = self.limits
        # Bound nesting *before* any serialization so a deeply-nested payload
        # cannot cause unbounded work or a RecursionError.
        self._check_depth(env.payload, 1)
        self._check_depth(env.securityContext, 1)
        self._check_depth(env.metadata, 1)
        try:
            raw = env.to_json()
        except (TypeError, ValueError, RecursionError):
            raise EnvelopeError(
                "envelope is not JSON-serializable", "BAD_PAYLOAD") from None
        if len(raw.encode("utf-8")) > L.max_message_bytes:
            raise EnvelopeError("message exceeds max size", "MESSAGE_TOO_LARGE")
        payload_len = len(json.dumps(env.payload).encode("utf-8"))
        if payload_len > L.max_payload_bytes:
            raise EnvelopeError("payload exceeds max size", "PAYLOAD_TOO_LARGE")
        meta_len = len(json.dumps(env.metadata).encode("utf-8"))
        if meta_len > L.max_metadata_bytes:
            raise EnvelopeError("metadata exceeds max size", "METADATA_TOO_LARGE")
        sc_len = len(json.dumps(env.securityContext).encode("utf-8"))
        if sc_len > L.max_security_context_bytes:
            raise EnvelopeError(
                "securityContext exceeds max size", "SECURITY_CONTEXT_TOO_LARGE")
        if len(env.capabilities) > L.max_capabilities:
            raise EnvelopeError(
                "too many capabilities", "CAPABILITIES_TOO_MANY")

    def _check_priority(self, env: AgentMessageEnvelope) -> None:
        if not isinstance(env.priority, int) or env.priority < 0:
            raise EnvelopeError(
                "priority must be a non-negative integer", "BAD_PRIORITY")

    def _check_capabilities(self, env: AgentMessageEnvelope) -> None:
        if not isinstance(env.capabilities, list) or not all(
                isinstance(c, str) for c in env.capabilities):
            raise EnvelopeError(
                "capabilities must be a list of strings", "BAD_TYPE")

    def _check_depth(self, value: Any, depth: int) -> None:
        if depth > self.limits.max_depth:
            raise EnvelopeError(
                "nested structure too deep", "TOO_DEEP")
        if isinstance(value, dict):
            for item in value.values():
                self._check_depth(item, depth + 1)
        elif isinstance(value, (list, tuple)):
            for item in value:
                self._check_depth(item, depth + 1)

    def _check_origin(self, env: AgentMessageEnvelope) -> None:
        origin = env.metadata.get("origin")
        if origin is None:
            return
        try:
            ContentOrigin(origin)
        except ValueError:
            raise EnvelopeError(
                f"invalid content origin {origin!r}", "BAD_ORIGIN") from None


def now() -> float:
    return time.time()