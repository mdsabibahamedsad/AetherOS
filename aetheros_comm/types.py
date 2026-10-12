"""
Agent Communication Fabric — core vocabulary.

Shared enums for the agent-to-agent message protocol:

    - :class:`MessageType` — the full catalog of supported message kinds
      (master spec step 4).
    - :class:`TrustZone` — logical security zones (step 12).
    - :class:`MessagePriority` — priority for ordering / preemption.
    - :class:`ContentOrigin` — provenance labelling for content (step 43).
    - :class:`DeliveryGuarantee` — documented transport guarantees (step 31).
    - :class:`FailureClass` — retry classification (step 34).

These are deliberately the *only* vocabulary module; every other fabric
module imports from here, so there is a single source of truth.
"""

from __future__ import annotations

import enum


class MessageType(str, enum.Enum):
    """The message-type catalog supported by the fabric (master spec step 4).

    Every envelope's ``messageType`` must be one of these values.
    """

    HELLO = "HELLO"
    AUTHENTICATE = "AUTHENTICATE"
    CAPABILITY_QUERY = "CAPABILITY_QUERY"
    CAPABILITY_RESPONSE = "CAPABILITY_RESPONSE"
    TASK_REQUEST = "TASK_REQUEST"
    TASK_ACCEPTED = "TASK_ACCEPTED"
    TASK_REJECTED = "TASK_REJECTED"
    TASK_PROGRESS = "TASK_PROGRESS"
    TASK_RESULT = "TASK_RESULT"
    TASK_FAILED = "TASK_FAILED"
    TASK_CANCEL = "TASK_CANCEL"
    TASK_CANCELLED = "TASK_CANCELLED"
    TASK_PAUSE = "TASK_PAUSE"
    TASK_RESUME = "TASK_RESUME"
    DELEGATION_REQUEST = "DELEGATION_REQUEST"
    DELEGATION_RESPONSE = "DELEGATION_RESPONSE"
    REVIEW_REQUEST = "REVIEW_REQUEST"
    REVIEW_RESULT = "REVIEW_RESULT"
    APPROVAL_REQUEST = "APPROVAL_REQUEST"
    APPROVAL_RESULT = "APPROVAL_RESULT"
    HEARTBEAT = "HEARTBEAT"
    HEALTH = "HEALTH"
    WARNING = "WARNING"
    ERROR = "ERROR"
    RECOVERY = "RECOVERY"
    SHUTDOWN = "SHUTDOWN"
    GOODBYE = "GOODBYE"


class TrustZone(str, enum.Enum):
    """Logical trust zones (master spec step 12).

    Agents must not automatically communicate across zones; cross-zone
    communication requires an explicit policy allowance (see ``trust.py``).
    """

    ZONE_0 = "ZONE_0"   # Untrusted external content (web, email, documents)
    ZONE_1 = "ZONE_1"   # Normal agents
    ZONE_2 = "ZONE_2"   # Privileged agents
    ZONE_3 = "ZONE_3"   # System agents
    ZONE_4 = "ZONE_4"   # Security / control plane

    @classmethod
    def from_str(cls, value: str) -> "TrustZone":
        try:
            return cls(value)
        except ValueError:
            raise ValueError(
                f"invalid trust zone {value!r}; expected one of "
                + ", ".join(z.value for z in cls)
            ) from None

    @property
    def numeric(self) -> int:
        return int(self.value.rsplit("_", 1)[1])


class MessagePriority(enum.IntEnum):
    """Priority of an agent message (0-100, higher = more urgent)."""

    LOW = 0
    NORMAL = 50
    HIGH = 75
    CRITICAL = 100


class ContentOrigin(str, enum.Enum):
    """Provenance label for message content (master spec step 43).

    Downstream agents must treat ``WEB``/``FILE``/``EXTERNAL_API`` content as
    untrusted, and the runtime must keep these origins distinct from system
    policy and user instruction (prompt-injection boundary, step 42).
    """

    USER = "USER"
    AGENT = "AGENT"
    TOOL = "TOOL"
    WEB = "WEB"
    FILE = "FILE"
    SYSTEM = "SYSTEM"
    EXTERNAL_API = "EXTERNAL_API"


class DeliveryGuarantee(str, enum.Enum):
    """Documented delivery guarantees (master spec step 31).

    The fabric never claims exactly-once. ``EFFECTIVELY_ONCE`` is achieved
    via idempotency keys on the consumer side, not by the transport.
    """

    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EFFECTIVELY_ONCE = "effectively_once"


class FailureClass(str, enum.Enum):
    """Failure classification for retry policy (master spec step 34)."""

    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    AUTHORIZATION = "AUTHORIZATION"
    SECURITY = "SECURITY"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID_REQUEST = "INVALID_REQUEST"