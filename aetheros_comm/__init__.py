"""
AetherOS Agent Communication Fabric
====================================

A thin, security-hardened communication layer that unifies the existing
AetherOS agent transports (local bus, kernel inter-agent bus, swarm bus,
orchestrator event bus, cluster transport) behind one logical interface with a
structured message envelope, protocol versioning, agent identity and
registration, capability-based routing, trust zones, zero-trust
authorization, message signing / replay protection / expiration, delegation
chains, credential isolation, reliability (retry, circuit breaker,
backpressure, fallback), observability, audit, and quarantine.

Design principles (per the master spec):

    - **No competing transport.** Adapters wrap the existing buses; the
      fabric never replaces them.
    - **Every agent boundary is a trust boundary.** Each message is
      independently validated and authorized.
    - **Least privilege.** Scoped permissions propagate down delegation
      chains; children can never widen them.
    - **Security always wins.** Conflicts are never resolved by majority
      vote; policy is deterministic and fail-closed.
"""

from __future__ import annotations

__version__ = "1.0.0"

from .audit import CommAudit  # noqa: E402
from .authz import (AuthorizationContext, MessageAuthorizer,  # noqa: E402
                    ScopedPermission)
from .capability import CapabilityRouter, CapabilitySet  # noqa: E402
from .config import (DEFAULT_COMMUNICATION_CONFIG,  # noqa: E402
                     get_communication_config, load_communication_config)
from .envelope import (AgentMessageEnvelope, EnvelopeError,  # noqa: E402
                       EnvelopeLimits, EnvelopeValidator)
from .fabric import (AgentCommunicationFabric, InboundResult,  # noqa: E402
                     SendResult)
from .identity import (AgentCard, AgentIdentity, AgentRegistry,  # noqa: E402
                       AgentStatus, IdentityError)
from .idempotency import IdempotencyStore  # noqa: E402
from .lifecycle import (ConnectionStateMachine, GracefulShutdown,  # noqa: E402
                        HeartbeatMonitor)
from .observability import CommunicationGraph, FabricMetrics  # noqa: E402
from .protocol import (PROTOCOL_VERSION, ProtocolError,  # noqa: E402
                       negotiate_protocol, supported_versions)
from .quarantine import QuarantineController  # noqa: E402
from .reliability import (Backpressure, CircuitBreaker,  # noqa: E402
                          FailureClass, FallbackChain, RetryPolicy)
from .security import (scan_for_credentials, to_log_safe)  # noqa: E402
from .signing import MessageSigner, ReplayStore  # noqa: E402
from .transport import (AgentTransport, ClusterTransport,  # noqa: E402
                        KernelBusTransport, LocalAgentBus,
                        OrchestratorBusTransport, SendReceipt,
                        SwarmBusTransport, TransportHealth,
                        TransportState)
from .trust import TrustZonePolicy  # noqa: E402
from .types import (ContentOrigin, DeliveryGuarantee, FailureClass,  # noqa: E402
                    MessagePriority, MessageType, TrustZone)

__all__ = [
    "__version__",
    "AgentCommunicationFabric",
    "SendResult",
    "InboundResult",
    "AgentMessageEnvelope",
    "EnvelopeError",
    "EnvelopeLimits",
    "EnvelopeValidator",
    "AgentCard",
    "AgentIdentity",
    "AgentRegistry",
    "AgentStatus",
    "IdentityError",
    "CapabilityRouter",
    "CapabilitySet",
    "TrustZonePolicy",
    "MessageAuthorizer",
    "AuthorizationContext",
    "ScopedPermission",
    "MessageSigner",
    "ReplayStore",
    "AgentTransport",
    "LocalAgentBus",
    "KernelBusTransport",
    "SwarmBusTransport",
    "OrchestratorBusTransport",
    "ClusterTransport",
    "TransportState",
    "TransportHealth",
    "SendReceipt",
    "RetryPolicy",
    "CircuitBreaker",
    "Backpressure",
    "FallbackChain",
    "IdempotencyStore",
    "ConnectionStateMachine",
    "HeartbeatMonitor",
    "GracefulShutdown",
    "FabricMetrics",
    "CommunicationGraph",
    "CommAudit",
    "QuarantineController",
    "PROTOCOL_VERSION",
    "ProtocolError",
    "negotiate_protocol",
    "supported_versions",
    "MessageType",
    "TrustZone",
    "MessagePriority",
    "ContentOrigin",
    "DeliveryGuarantee",
    "DEFAULT_COMMUNICATION_CONFIG",
    "get_communication_config",
    "load_communication_config",
    "scan_for_credentials",
    "to_log_safe",
]