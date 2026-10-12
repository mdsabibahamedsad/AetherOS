"""
Agent Communication Fabric — the unified facade (master spec).

:class:`AgentCommunicationFabric` wires the envelope, validation, identity,
capability routing, trust zones, signing/replay/expiration, zero-trust
authorization, rate limiting, backpressure, circuit breakers, retry,
idempotency, observability, audit, and quarantine layers into one send /
inbound pipeline. It drives any existing transport through the
:class:`aetheros_comm.transport.AgentTransport` interface.

Pipeline (every sensitive request is independently validated, step 13):

    send:
      validate schema -> rate limit -> broadcast gate -> credential scan
      -> authorize -> sign -> idempotency -> circuit breaker
      -> backpressure -> retry-send -> metrics/graph

    inbound:
      validate schema/expiry -> replay -> signature -> authorize
      -> credential scan -> rate limit -> deliver -> metrics/audit
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .audit import CommAudit
from .authz import (AuthorizationContext, MessageAuthorizer,
                    has_capability)
from .capability import CapabilityRouter
from .config import get_communication_config
from .envelope import (AgentMessageEnvelope, EnvelopeError, EnvelopeLimits,
                       EnvelopeValidator)
from .identity import AgentIdentity, AgentRegistry
from .idempotency import IdempotencyStore
from .lifecycle import HeartbeatMonitor
from .observability import CommunicationGraph, FabricMetrics
from .protocol import PROTOCOL_VERSION, is_supported, negotiate_protocol
from .quarantine import QuarantineController
from .reliability import (Backpressure, CircuitBreaker, FailureClass,
                          RetryPolicy, classify_error)
from .security import scan_for_credentials
from .signing import MessageSigner, ReplayStore
from .transport import (AgentTransport, InboundHandler, LocalAgentBus,
                        TransportState)
from .trust import TrustZonePolicy
from .types import MessageType, TrustZone

logger = logging.getLogger(__name__)

#: Message types that honor idempotency keys (step 32).
_IDEMPOTENT_TYPES = frozenset({
    MessageType.TASK_REQUEST.value,
    MessageType.DELEGATION_REQUEST.value,
    MessageType.REVIEW_REQUEST.value,
    MessageType.APPROVAL_REQUEST.value,
    MessageType.TASK_RESULT.value,
    MessageType.DELEGATION_RESPONSE.value,
    MessageType.APPROVAL_RESULT.value,
})


@dataclass
class SendResult:
    """Result of an outbound send/request."""

    envelope: AgentMessageEnvelope
    accepted: bool
    reason: str = ""
    code: str = ""
    delivered: bool = False
    response: Optional[AgentMessageEnvelope] = None

    @property
    def ok(self) -> bool:
        return self.accepted and self.delivered


@dataclass
class InboundResult:
    """Result of inbound message processing."""

    envelope: AgentMessageEnvelope
    accepted: bool
    reason: str = ""
    code: str = ""
    responses: List[AgentMessageEnvelope] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.accepted


class AgentCommunicationFabric:
    """The Agent Communication Fabric facade.

    Construct with sensible defaults; override components (registry,
    transport, policy, signer, ...) to match the deployment.
    """

    def __init__(self, *, registry: Optional[AgentRegistry] = None,
                 transport: Optional[AgentTransport] = None,
                 trust_policy: Optional[TrustZonePolicy] = None,
                 signer: Optional[MessageSigner] = None,
                 replay_store: Optional[ReplayStore] = None,
                 idempotency: Optional[IdempotencyStore] = None,
                 metrics: Optional[FabricMetrics] = None,
                 graph: Optional[CommunicationGraph] = None,
                 audit: Optional[CommAudit] = None,
                 quarantine: Optional[QuarantineController] = None,
                 backpressure: Optional[Backpressure] = None,
                 validator: Optional[EnvelopeValidator] = None,
                 config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or get_communication_config()
        limits = EnvelopeLimits.from_dict(self._config.get("message_limits", {}))
        self.validator = validator or EnvelopeValidator(limits)

        self.registry = registry or AgentRegistry()
        self.transport = transport or LocalAgentBus()
        self.trust_policy = trust_policy or TrustZonePolicy()
        self._apply_trust_zone_config()

        sign_cfg = self._config.get("authentication", {})
        self._require_signature = bool(sign_cfg.get("require_signature", True))
        self.signer = signer
        if self.signer is None and self._require_signature:
            key_path = sign_cfg.get("signing_key_path") or None
            self.signer = MessageSigner(
                key_path=Path(key_path) if key_path else None)
        self._replay_store = replay_store or ReplayStore(
            self._config.get("replay", {}).get("retention_seconds", 3600.0))
        self.idempotency = idempotency or IdempotencyStore(
            self._config.get("idempotency", {}).get("ttl_seconds", 86400.0))
        self.metrics = metrics or FabricMetrics()
        self.graph = graph or CommunicationGraph()
        self.audit = audit or CommAudit()
        self.quarantine = quarantine or QuarantineController(self.audit)
        bp_cfg = self._config.get("backpressure", {})
        self.backpressure = backpressure or Backpressure(
            max_in_flight=bp_cfg.get("max_in_flight", 32),
            queue_limit=bp_cfg.get("queue_limit", 512))
        self.authorizer = MessageAuthorizer(
            self.registry, self.trust_policy,
            require_signed_sensitive=self._require_signature)
        self.router = CapabilityRouter(self.registry, self.trust_policy)
        self.heartbeats = HeartbeatMonitor(
            self._config.get("timeouts", {}).get(
                "heartbeat_stale_seconds", 60.0))

        retry_cfg = self._config.get("retry", {})
        self._retry_policy = RetryPolicy(
            max_attempts=retry_cfg.get("max_attempts", 3),
            base_delay=retry_cfg.get("base_delay_seconds", 0.2),
            max_delay=retry_cfg.get("max_delay_seconds", 5.0))
        cb_cfg = self._config.get("circuit_breaker", {})
        self._cb_cfg = (cb_cfg.get("failure_threshold", 5),
                        cb_cfg.get("open_timeout_seconds", 10.0))
        self._breakers: Dict[str, CircuitBreaker] = {}

        self._handlers: Dict[str, List[InboundHandler]] = {}
        self._lock = threading.RLock()
        self._rate_limiter = None
        self._connected = False
        self._attached: set = set()
        self._attached_local_wildcard = False

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _apply_trust_zone_config(self) -> None:
        zones = self._config.get("trust_zones", {})
        for allowance, caps in (zones.get("cross_zone_allowances") or {}).items():
            try:
                source_s, target_s = str(allowance).split("->", 1)
                source = TrustZone.from_str(source_s.strip())
                target = TrustZone.from_str(target_s.strip())
                self.trust_policy.allow_cross_zone(
                    source, target, capabilities=tuple(caps or ()))
            except Exception:  # noqa: BLE001
                logger.warning("Ignoring invalid cross-zone allowance %r",
                               allowance)

    def _get_rate_limiter(self):
        if self._rate_limiter is None:
            from aetheros_security.rate_limit import RateLimiter
            limiter = RateLimiter()
            rl = self._config.get("rate_limits", {})
            limiter.set_config("agent_comm",
                               max_requests=rl.get("messages_per_second", 100),
                               window_seconds=60,
                               burst_limit=rl.get("burst_limit", 100))
            limiter.set_config("agent_comm_delegation",
                               max_requests=rl.get(
                                   "delegation_requests_per_agent", 50),
                               window_seconds=60, burst_limit=5)
            self._rate_limiter = limiter
        return self._rate_limiter

    def _get_breaker(self, agent_id: str) -> CircuitBreaker:
        with self._lock:
            breaker = self._breakers.get(agent_id)
            if breaker is None:
                breaker = CircuitBreaker(
                    name=f"agent:{agent_id}",
                    failure_threshold=self._cb_cfg[0],
                    open_timeout=self._cb_cfg[1])
                self._breakers[agent_id] = breaker
            return breaker

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        if isinstance(self.transport, LocalAgentBus) and not self._connected:
            for identity in self.registry.list_agents():
                self.transport.register_agent(identity["agentId"])
                self._attach_inbound(identity["agentId"])
        if not self._connected:
            self.transport.connect()
            self._connected = True

    def close(self) -> None:
        if isinstance(self.transport, LocalAgentBus):
            for identity in self.registry.list_agents():
                self.transport.unregister_agent(identity["agentId"])
        self.transport.disconnect()
        self._connected = False

    # ------------------------------------------------------------------
    # Agent registration / subscription
    # ------------------------------------------------------------------

    def register_agent(self, identity: AgentIdentity,
                       *, transport_registration: bool = True) -> AgentIdentity:
        """Register an agent in the fabric and (if local) on the bus."""
        registered = self.registry.register(identity)
        if transport_registration:
            if isinstance(self.transport, LocalAgentBus):
                self.transport.register_agent(identity.agentId)
                self._attach_inbound(identity.agentId)
            else:
                self._attach_inbound(identity.agentId)
        return registered

    def _attach_inbound(self, agent_id: str) -> None:
        if agent_id in self._attached:
            return
        self._attached.add(agent_id)
        try:
            if isinstance(self.transport, LocalAgentBus):
                # The local bus already routes directed messages to the
                # recipient and fans broadcasts out; one wildcard handler is
                # enough and avoids double-processing broadcasts.
                if not self._attached_local_wildcard:
                    self.transport.subscribe_all(self._inbound)
                    self._attached_local_wildcard = True
            else:
                self.transport.subscribe(agent_id, self._inbound)
        except Exception as exc:  # noqa: BLE001
            logger.debug("transport subscribe for %s failed: %s", agent_id, exc)

    def subscribe(self, agent_id: str, handler: InboundHandler) -> Callable[[], None]:
        """Subscribe ``handler`` to inbound messages addressed to ``agent_id``."""
        with self._lock:
            self._handlers.setdefault(agent_id, []).append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._handlers.get(agent_id, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def _dispatch(self, envelope: AgentMessageEnvelope) -> List[AgentMessageEnvelope]:
        responses: List[AgentMessageEnvelope] = []
        with self._lock:
            if envelope.receiverAgentId:
                handlers = list(self._handlers.get(envelope.receiverAgentId, []))
            else:
                # Broadcast: deliver to every subscribed handler except the
                # sender's own (a broadcast carries no receiver).
                handlers = [
                    handler for agent_id, subs in self._handlers.items()
                    if agent_id != envelope.senderAgentId
                    for handler in subs
                ]
        for handler in handlers:
            try:
                result = handler(envelope)
                if result is not None:
                    responses.append(result)
            except Exception as exc:  # noqa: BLE001 - isolate handlers
                logger.warning("Handler for %s failed: %s",
                               envelope.receiverAgentId, exc)
        return responses

    # ------------------------------------------------------------------
    # Outbound pipeline
    # ------------------------------------------------------------------

    def send(self, envelope: AgentMessageEnvelope, *,
             context: Optional[AuthorizationContext] = None,
             idempotency_key: str = "",
             timeout: float = 30.0) -> SendResult:
        """Run the full outbound pipeline and deliver the message."""
        start = time.time()
        prepared = self._prepare_outbound(envelope, context, idempotency_key)
        if not prepared.accepted:
            return prepared
        if prepared.code == "IDEMPOTENT":
            # An idempotent replay was already executed; do not deliver again.
            return prepared

        receiver = envelope.receiverAgentId
        breaker = self._get_breaker(receiver or "*")

        # Circuit breaker (step 35).
        if not breaker.allow_request():
            self.audit.circuit_breaker(receiver or "*", "open")
            self.metrics.increment("circuit_breaker_open")
            return SendResult(envelope, False,
                              f"circuit open for {receiver}", "UNAVAILABLE")

        # Backpressure (step 36).
        if not self.backpressure.acquire(receiver or "*"):
            self.metrics.increment("backpressure_rejected")
            return SendResult(envelope, False,
                              "dependency overloaded", "UNAVAILABLE")

        try:
            return self._send_with_retry(envelope, receiver or "*",
                                         breaker, timeout)
        finally:
            self.backpressure.release(receiver or "*")
            self.metrics.record_latency("send", time.time() - start)

    def _prepare_outbound(self, envelope: AgentMessageEnvelope,
                          context: Optional[AuthorizationContext],
                          idempotency_key: str) -> SendResult:
        """Shared outbound validation + authorization + signing.

        Used by :meth:`send` (then delivers via ``transport.send``) and
        :meth:`request` (then delivers via ``transport.request``), so a
        request is never sent twice and never trips replay protection.
        """
        try:
            self.validator.validate(envelope)
        except EnvelopeError as exc:
            return SendResult(envelope, False, exc.reason, exc.code)

        # Broadcast control (step 28).
        if not envelope.receiverAgentId:
            allowed = self._config.get("broadcast", {}).get(
                "allowed_agents", [])
            may_broadcast = envelope.senderAgentId in allowed
            if not may_broadcast:
                sender_ident = self.registry.get(envelope.senderAgentId)
                declared = (sender_ident.capabilities
                            if sender_ident else [])
                may_broadcast = has_capability(
                    declared, "comm:broadcast")
            if not may_broadcast:
                self.audit.authorization_decision(
                    envelope.senderAgentId, False, "broadcast not permitted")
                return SendResult(envelope, False,
                                  "sender may not broadcast", "BROADCAST_DENIED")

        # Rate limit (step 27).
        if not self._rate_check(envelope):
            return SendResult(envelope, False, "rate limited", "RATE_LIMIT")

        # Credential isolation (step 24) — raw credentials never travel on
        # sensitive channels.
        if envelope.is_sensitive:
            scan = scan_for_credentials(envelope.payload)
            if scan.found:
                self.audit.authorization_decision(
                    envelope.senderAgentId, False,
                    "payload contains raw credentials")
                return SendResult(envelope, False,
                                  "payload contains raw credentials",
                                  "CREDENTIALS_REJECTED")

        # Authorize (step 20).
        ctx = self._outbound_context(envelope, context)
        decision = self.authorizer.authorize(envelope, context=ctx,
                                             signature_ok=True, replay_ok=True)
        if not decision.allowed:
            self.audit.authorization_decision(
                envelope.senderAgentId, False, decision.reason,
                {"code": decision.code, "receiver": envelope.receiverAgentId})
            self.metrics.increment("authz_denials")
            return SendResult(envelope, False, decision.reason, decision.code)

        # Embed the authorization context so the receiver can independently
        # validate the delegation chain / mission / task ownership (steps 22,
        # 23). It is part of the signed canonical bytes, so it cannot be
        # tampered with after signing.
        if ctx is not None:
            envelope.securityContext["authorization"] = ctx.to_dict()

        # Idempotency (step 32).
        if idempotency_key and envelope.messageType in _IDEMPOTENT_TYPES:
            was_cached, cached = self.idempotency.get_or_record(
                envelope.senderAgentId, idempotency_key,
                lambda: {"status": "executed"})
            if was_cached:
                return SendResult(envelope, True, "idempotent replay",
                                  "IDEMPOTENT", response=None)

        # Sign (step 15).
        if self.signer is not None and (
                envelope.is_sensitive or envelope.messageType ==
                MessageType.AUTHENTICATE.value):
            try:
                self.signer.sign(envelope)
            except Exception as exc:  # noqa: BLE001
                return SendResult(envelope, False, str(exc), "SIGN_FAILED")

        return SendResult(envelope, True)

    def _send_with_retry(self, envelope: AgentMessageEnvelope, receiver: str,
                         breaker: CircuitBreaker, timeout: float) -> SendResult:
        attempt = 0
        while True:
            receipt = self.transport.send(envelope)
            if receipt.delivered:
                breaker.record_success()
                self.metrics.increment("messages_sent")
                self.graph.record(envelope.senderAgentId, receiver, 0.0)
                return SendResult(envelope, True, delivered=True)
            self.metrics.increment("delivery_failures")
            failure_class = classify_error(Exception(receipt.error))
            breaker.record_failure()
            if not self._retry_policy.should_retry(failure_class, attempt):
                return SendResult(envelope, False, receipt.error,
                                  f"DELIVERY_{failure_class.value}")
            delay = self._retry_policy.delay_for(attempt)
            self.metrics.increment("retries")
            attempt += 1
            time.sleep(delay)

    def request(self, envelope: AgentMessageEnvelope, *,
                context: Optional[AuthorizationContext] = None,
                timeout: float = 30.0,
                idempotency_key: str = "") -> SendResult:
        """Send a request and await the correlated response (steps 29, 33).

        Uses the transport's native request/response when available,
        otherwise correlation via the local bus.

        The correlation id is assigned before signing so it is covered by the
        message signature (it becomes part of the canonical bytes).
        """
        if not envelope.correlationId:
            envelope.correlationId = uuid.uuid4().hex
        result = self._prepare_outbound(envelope, context, idempotency_key)
        if not result.accepted:
            return result
        if result.code == "IDEMPOTENT":
            return result

        start = time.time()
        receiver = envelope.receiverAgentId
        breaker = self._get_breaker(receiver or "*")

        # Circuit breaker (step 35).
        if not breaker.allow_request():
            self.audit.circuit_breaker(receiver or "*", "open")
            self.metrics.increment("circuit_breaker_open")
            return SendResult(envelope, False,
                              f"circuit open for {receiver}", "UNAVAILABLE")

        # Backpressure (step 36).
        if not self.backpressure.acquire(receiver or "*"):
            self.metrics.increment("backpressure_rejected")
            return SendResult(envelope, False,
                              "dependency overloaded", "UNAVAILABLE")

        try:
            try:
                response = self.transport.request(envelope, timeout=timeout)
            except NotImplementedError:
                return SendResult(envelope, True, reason="transport has no "
                                 "request/response", code="NO_RESPONSE",
                                 delivered=True)
        finally:
            self.backpressure.release(receiver or "*")
            self.metrics.record_latency("request", time.time() - start)

        latency = time.time() - start
        self.metrics.record_latency("request", latency)
        if response is None:
            self.metrics.increment("timeouts")
            return SendResult(envelope, True, reason="request timed out",
                              code="TIMEOUT", delivered=True)
        self.metrics.increment("messages_sent")
        self.graph.record(envelope.senderAgentId, receiver, latency)
        return SendResult(envelope, True, delivered=True, response=response)

    def broadcast(self, envelope: AgentMessageEnvelope,
                  context: Optional[AuthorizationContext] = None) -> SendResult:
        envelope.receiverAgentId = ""
        return self.send(envelope, context=context)

    def send_heartbeat(self, sender: str = "",
                       receiver: str = "",
                       seq: int = 0) -> SendResult:
        """Send a HEARTBEAT carrying only necessary metadata (step 50).

        ``sender`` is the local agent's registered identity; the receiver
        marks ``sender`` as alive on the inbound side.
        """
        envelope = AgentMessageEnvelope(
            messageType=MessageType.HEARTBEAT.value,
            senderAgentId=sender,
            receiverAgentId=receiver,
            metadata={"origin": "SYSTEM", "seq": seq},
        )
        return self.send(envelope)

    # ------------------------------------------------------------------
    # Inbound pipeline
    # ------------------------------------------------------------------

    def _inbound(self, envelope: AgentMessageEnvelope) -> Optional[AgentMessageEnvelope]:
        result = self.handle_inbound(envelope)
        responses = result.responses
        return responses[0] if responses else None

    def handle_inbound(self, envelope: AgentMessageEnvelope,
                       *, deliver: bool = True) -> InboundResult:
        """Validate, authenticate, authorize, and deliver an inbound message."""
        start = time.time()
        sender = envelope.senderAgentId
        receiver = envelope.receiverAgentId

        # 1. Schema + expiry (steps 6, 17).
        try:
            self.validator.validate(envelope)
        except EnvelopeError as exc:
            self.metrics.increment("schema_failures")
            self.audit.authorization_decision(sender, False, exc.reason,
                                              {"code": exc.code})
            self.quarantine.record_violation(sender, "malformed",
                                             f"{exc.code}: {exc.reason}")
            return InboundResult(envelope, False, exc.reason, exc.code)

        # 2. Replay protection (step 16).
        if not self._replay_store.check_and_record(sender, envelope.messageId):
            self.metrics.increment("replay_rejections")
            self.audit.replay_rejected(sender, envelope.messageId)
            self.quarantine.record_violation(sender, "security", "replay")
            return InboundResult(envelope, False, "replayed message",
                                 "REPLAY_REJECTED")

        # 3. Signature verification (step 15).
        signature_ok = True
        if (self.signer is not None and self._require_signature
                and envelope.is_sensitive):
            signature_ok = self.signer.verify(envelope)
            if not signature_ok:
                self.metrics.increment("signature_failures")
                self.audit.signature_failure(sender, envelope.messageId)
                self.quarantine.record_violation(sender, "security",
                                                 "bad signature")
                return InboundResult(envelope, False,
                                     "bad signature", "BAD_SIGNATURE")

        # 4. Credential scan on sensitive inbound (step 24).
        if envelope.is_sensitive:
            scan = scan_for_credentials(envelope.payload)
            if scan.found:
                self.metrics.increment("credential_rejections")
                return InboundResult(envelope, False,
                                     "payload contains raw credentials",
                                     "CREDENTIALS_REJECTED")

        # 5. Rate limit (step 27).
        if not self._rate_check(envelope):
            return InboundResult(envelope, False, "rate limited", "RATE_LIMIT")

        # 6. Authorize (step 20) — zero-trust, independently validated.
        ctx = self._inbound_context(envelope)
        decision = self.authorizer.authorize(
            envelope, signature_ok=signature_ok, replay_ok=True, context=ctx)
        if not decision.allowed:
            self.metrics.increment("authz_denials")
            self.audit.authorization_decision(
                sender, False, decision.reason,
                {"code": decision.code, "receiver": receiver})
            self.quarantine.record_violation(sender, "authorization",
                                             decision.code)
            return InboundResult(envelope, False, decision.reason,
                                 decision.code)

        # 7. Heartbeat liveness (step 50).
        if envelope.messageType == MessageType.HEARTBEAT.value:
            seq = envelope.metadata.get("seq", 0)
            self.heartbeats.mark_seen(
                sender, seq=int(seq or 0),
                overloaded=bool(envelope.metadata.get("overloaded", False)))

        # 8. Deliver (step 29/30).
        responses: List[AgentMessageEnvelope] = []
        if deliver:
            responses = self._dispatch(envelope)

        self.metrics.increment("messages_received")
        self.graph.record(sender, receiver, 0.0)
        self.audit.auth_attempt(sender, receiver or "", True)
        return InboundResult(envelope, True, responses=responses)

    # ------------------------------------------------------------------
    # Authorization context resolution
    # ------------------------------------------------------------------

    def _outbound_context(self, envelope: AgentMessageEnvelope,
                          context: Optional[AuthorizationContext]
                          ) -> Optional[AuthorizationContext]:
        if context is not None:
            return context
        auth = envelope.securityContext.get("authorization")
        if isinstance(auth, dict):
            return AuthorizationContext.from_dict(auth)
        return AuthorizationContext(
            principal_chain=[envelope.senderAgentId],
            mission_id=envelope.missionId,
            task_id=envelope.taskId)

    def _inbound_context(self, envelope: AgentMessageEnvelope
                         ) -> Optional[AuthorizationContext]:
        auth = envelope.securityContext.get("authorization")
        if isinstance(auth, dict):
            return AuthorizationContext.from_dict(auth)
        return None

    # ------------------------------------------------------------------
    # Rate limiting (step 27)
    # ------------------------------------------------------------------

    def _rate_check(self, envelope: AgentMessageEnvelope) -> bool:
        try:
            limiter = self._get_rate_limiter()
        except Exception:
            return True  # no limiter configured -> fail open on absence only
        sender = envelope.senderAgentId
        if envelope.messageType == MessageType.DELEGATION_REQUEST.value:
            if not limiter.check(f"comm:delegation:{sender}",
                                 scope="agent_comm_delegation"):
                self.audit.rate_limited(sender, "delegation")
                self.metrics.increment("rate_limited")
                return False
        if not limiter.check(f"comm:agent:{sender}", scope="agent_comm"):
            self.audit.rate_limited(sender, "agent")
            self.metrics.increment("rate_limited")
            return False
        return True

    # ------------------------------------------------------------------
    # Quarantine / recovery (steps 60, 61)
    # ------------------------------------------------------------------

    def quarantine_agent(self, agent_id: str, reason: str,
                         evidence: Optional[List[str]] = None) -> bool:
        return self.quarantine.quarantine(agent_id, reason, evidence,
                                          registry=self.registry)

    def reactivate_agent(self, agent_id: str, *, health_ok: bool,
                         identity_ok: bool, config_ok: bool,
                         security_review: bool) -> bool:
        return self.quarantine.reactivate(
            agent_id, health_ok=health_ok, identity_ok=identity_ok,
            config_ok=config_ok, security_review=security_review,
            registry=self.registry)

    def is_quarantined(self, agent_id: str) -> bool:
        return self.quarantine.is_quarantined(agent_id)

    # ------------------------------------------------------------------
    # Capability routing (step 11)
    # ------------------------------------------------------------------

    def route(self, required: list, *, requester_agent_id: str = "",
              requester_zone: Optional[TrustZone] = None,
              preferred: list = (), exclude: Optional[list] = None) -> Optional[str]:
        return self.router.route(required,
                                 requester_agent_id=requester_agent_id,
                                 requester_zone=requester_zone,
                                 preferred=preferred, exclude=exclude)

    def fallback_chain(self, required: list, *, requester_agent_id: str = "",
                       requester_zone: Optional[TrustZone] = None,
                       exclude: Optional[list] = None) -> list:
        return self.router.fallback_chain(
            required, requester_agent_id=requester_agent_id,
            requester_zone=requester_zone, exclude=exclude)

    # ------------------------------------------------------------------
    # Protocol versioning (step 5)
    # ------------------------------------------------------------------

    def negotiate(self, theirs: list) -> str:
        """Negotiate the highest common protocol version with a peer."""
        return negotiate_protocol(self._config.get("protocol_versions",
                                                   [PROTOCOL_VERSION]),
                                  theirs)

    # ------------------------------------------------------------------
    # Observability / status
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "transport": self.transport.name,
            "transport_state": (self.transport.state.value
                                if isinstance(self.transport.state,
                                               TransportState)
                                else str(self.transport.state)),
            "registry": self.registry.get_stats(),
            "metrics": self.metrics.snapshot(),
            "graph": self.graph.to_dict(),
            "quarantine": self.quarantine.get_stats(),
            "replay_seen": len(self._replay_store),
            "idempotency_entries": len(self.idempotency),
            "circuit_breakers": [b.to_dict()
                                 for b in self._breakers.values()],
            "backpressure": self.backpressure.snapshot(),
        }