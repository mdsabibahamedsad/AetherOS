"""AetherOS Agent Gateway (Master 46 sections 71-72).

Single choke point for all remote-agent traffic: authentication,
authorization, routing, rate limiting, policy, observability, tenant
routing, revocation, abuse protection. The gateway never becomes a
privilege-escalation layer: remote principals only ever hold explicitly
granted capabilities, and every denial/approval is audited.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .agent_card import AgentCard, parse_agent_card, validate_agent_card, verification_label
from .artifacts import Artifact, examine_artifact, safe_filename
from .audit import AuditLog, summarize_payload
from .discovery import DiscoveryResult
from .identity import AgentIdentity
from .policy import (
    authorize_action,
    classify_data,
    detect_prompt_injection,
    dlp_scan,
    redact_secrets,
)
from .registry import AgentRegistry
from .router import AgentNetworkRouter, AgentRouteDecision, RouteCandidate
from .tasks import RemoteTask, TaskStore, new_task
from .transport import A2ATransport, TransportConfig, TransportError
from .trust import TrustStore

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover - importable outside checkout
    from pathlib import Path as _P

    def get_aetheros_home():  # type: ignore[misc]
        from os import environ
        return _P(environ.get("AETHEROS_HOME", str(_P.home() / ".aetheros")))


def default_home() -> Path:
    return Path(get_aetheros_home()) / "agent_network"


class RateLimiter:
    """Token-bucket per scope (agent/org/user/task)."""

    def __init__(self, per_minute: int = 60, burst: int = 10) -> None:
        self.per_minute = per_minute
        self.burst = burst
        self._buckets: Dict[str, Dict[str, float]] = {}

    def check(self, scope: str) -> bool:
        now = time.time()
        bucket = self._buckets.get(scope, {"tokens": float(self.burst), "at": now})
        elapsed = now - bucket["at"]
        bucket["tokens"] = min(float(self.burst),
                               bucket["tokens"] + elapsed * self.per_minute / 60.0)
        bucket["at"] = now
        if bucket["tokens"] < 1.0:
            self._buckets[scope] = bucket
            return False
        bucket["tokens"] -= 1.0
        self._buckets[scope] = bucket
        return True


class CircuitBreaker:
    """CLOSED -> OPEN -> HALF_OPEN per agent (section 67)."""

    def __init__(self, failure_threshold: int = 5, open_seconds: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self._state: Dict[str, Dict[str, Any]] = {}

    def state(self, agent_id: str) -> str:
        st = self._state.get(agent_id, {"state": "closed", "failures": 0, "opened_at": 0.0})
        if st["state"] == "open" and time.time() - st["opened_at"] >= self.open_seconds:
            st["state"] = "half_open"
        return st["state"]

    def success(self, agent_id: str) -> None:
        self._state[agent_id] = {"state": "closed", "failures": 0, "opened_at": 0.0}

    def failure(self, agent_id: str) -> str:
        st = self._state.get(agent_id, {"state": "closed", "failures": 0, "opened_at": 0.0})
        st["failures"] += 1
        if st["state"] == "half_open" or st["failures"] >= self.failure_threshold:
            st["state"] = "open"
            st["opened_at"] = time.time()
        self._state[agent_id] = st
        return st["state"]


class AgentGateway:
    """Owns registry, trust, policy, transport, tasks, audit, limits."""

    def __init__(self, home: Optional[Path] = None,
                 transport_config: Optional[TransportConfig] = None) -> None:
        self.home = Path(home) if home else default_home()
        self.home.mkdir(parents=True, exist_ok=True)
        self.registry = AgentRegistry(self.home / "registry.json")
        self.trust = TrustStore(self.home / "trust.json")
        self.tasks = TaskStore(self.home / "tasks.sqlite")
        self.audit = AuditLog(self.home / "audit.jsonl")
        self.router = AgentNetworkRouter()
        self.transport_config = transport_config or TransportConfig()
        self.rate_limiter = RateLimiter()
        self.circuit = CircuitBreaker()
        self._transports: Dict[str, A2ATransport] = {}
        # Relationship memory: reliability per agent per task-class (decayed).
        self._relationships: Dict[str, Dict[str, Any]] = {}

    # -- pairing / trust -------------------------------------------------
    def adopt_discovery(self, result: DiscoveryResult) -> str:
        """Persist a DISCOVERED record. Trust stays discovered/unverified."""
        if result.errors or not result.agent_id:
            raise ValueError(f"cannot adopt discovery: {result.errors}")
        identity = AgentIdentity.from_dict(result.identity)
        card = parse_agent_card(result.card, source_url=result.card.get("source_url", ""))
        self.registry.upsert(identity.agent_id, identity, card,
                             source=result.source,
                             provenance={"verification": result.verification,
                                         "warnings": result.warnings})
        self.trust.get(identity.agent_id)  # ensure discovered record
        self.audit.record("agent.discovered", actor="local",
                          subject=identity.agent_id,
                          details={"source": result.source})
        return identity.agent_id

    def verify_agent(self, agent_id: str, checks: Dict[str, Any]) -> str:
        """Record verification evidence; returns UNVERIFIED/VERIFIED/TRUSTED/REVOKED."""
        label = verification_label(checks)
        if label == "REVOKED":
            self.trust.set_level(agent_id, "revoked", by="verification",
                                 evidence=checks)
        elif label in ("VERIFIED", "TRUSTED"):
            current = self.trust.level(agent_id)
            if current in ("unknown", "discovered", "unverified", "blocked"):
                self.trust.set_level(agent_id, "verified", by="verification",
                                     evidence=checks)
        self.audit.record("agent.verified", actor="local", subject=agent_id,
                          details={"label": label,
                                   "evidence_keys": sorted(checks.keys())})
        return label

    def set_trust(self, agent_id: str, level: str, by: str = "user") -> None:
        self.trust.set_level(agent_id, level, by=by)
        self.audit.record("agent.trust_changed", actor=by, subject=agent_id,
                          details={"level": level})

    def revoke(self, agent_id: str, by: str = "user") -> None:
        self.trust.set_level(agent_id, "revoked", by=by)
        rec = self.registry.get_including_removed(agent_id)
        if rec is not None:
            rec.health = "revoked"
            self.registry.save()
        # Cancel non-terminal tasks for this agent (explicit policy).
        for task in self.tasks.list():
            if task.target_agent == agent_id and task.status not in (
                    "completed", "failed", "cancelled", "expired", "rejected", "timed_out"):
                self.tasks.transition(task.task_id, "cancelled", "agent revoked")
        self.audit.record("agent.revoked", actor=by, subject=agent_id, details={})

    # -- task delegation ---------------------------------------------------
    def grant_permissions(self, agent_id: str, permissions: List[str],
                          by: str = "user") -> List[str]:
        """Grant capabilities to a paired agent. Only REMOTE_GRANTABLE
        permissions may be granted; anything else is rejected."""
        from .policy import PERMISSION_CATALOG, REMOTE_GRANTABLE

        rec = self.registry.get(agent_id)
        if rec is None:
            raise KeyError(f"unknown agent: {agent_id}")
        for perm in permissions:
            if perm not in REMOTE_GRANTABLE or perm not in PERMISSION_CATALOG:
                raise ValueError(f"permission not grantable to remote agents: {perm}")
        granted = sorted(set(rec.permissions) | set(permissions))
        rec.permissions = granted
        self.registry.save()
        self.audit.record("agent.permissions_granted", actor=by, subject=agent_id,
                          details={"permissions": granted})
        return granted

    def _transport_for(self, agent_id: str) -> A2ATransport:
        rec = self.registry.get(agent_id)
        if rec is None:
            raise KeyError(f"unknown agent: {agent_id}")
        url = rec.card.get("url", "")
        t = self._transports.get(agent_id)
        if t is None or t.base_url != url.rstrip("/"):
            t = A2ATransport(url, self.transport_config)
            self._transports[agent_id] = t
        return t

    def delegate(self, target_agent: str, purpose: str, message: Dict[str, Any],
                 permissions: Optional[List[str]] = None,
                 data_scope: str = "internal",
                 origin_agent: str = "local", owner: str = "",
                 require_approval: bool = False) -> RemoteTask:
        """Full delegation pipeline (section 26): capability, trust,
        permission, privacy, budget, destination, approval, submission."""
        if self.trust.is_blocked(target_agent):
            raise PermissionError(f"agent {target_agent} is blocked/revoked")
        if self.circuit.state(target_agent) == "open":
            raise ConnectionError(f"circuit open for {target_agent}")
        if not self.rate_limiter.check(f"agent:{target_agent}"):
            raise ConnectionError(f"rate limited for {target_agent}")
        if self.tasks.queue_depth()["full"]:
            raise ConnectionError("remote task queue full")

        rec = self.registry.get(target_agent)
        if rec is None:
            raise KeyError(f"unknown agent: {target_agent}")

        # Privacy/DLP on the outbound message FIRST — secrets fail fast,
        # before any approval bookkeeping.
        text = str(message)
        findings = dlp_scan(text)
        if findings and data_scope in ("private", "sensitive", "highly_sensitive"):
            self.audit.record("task.dlp_blocked", actor=origin_agent,
                              subject=target_agent,
                              details={"findings": [f["type"] for f in findings]})
            raise PermissionError(
                f"outbound payload contains {len(findings)} secret-like match(es); "
                "blocked — remove credentials or lower data scope with explicit approval")

        skills = {s.get("id") for s in rec.card.get("skills", [])}
        for perm in permissions or []:
            # Capability check: permission must be grantable and skill-backed
            # where a matching skill exists.
            decision = authorize_action(
                self.trust.level(target_agent), perm, data_scope,
                granted_permissions=rec.permissions or None)
            if not decision.allowed:
                self.audit.record("task.delegation_denied", actor=origin_agent,
                                  subject=target_agent,
                                  details={"permission": perm, "reason": decision.reason})
                raise PermissionError(decision.reason)
            if decision.approval_required and require_approval is False and perm not in (rec.permissions or []):
                # Pause for approval instead of auto-sending.
                task = new_task(origin_agent, target_agent, purpose,
                                permissions=permissions or [], data_scope=data_scope,
                                owner=owner)
                task.status = "approval_required"
                task.events.append({"at": time.time(), "to": "approval_required",
                                    "note": decision.reason})
                self.tasks.save(task)
                self.audit.record("task.approval_required", actor=origin_agent,
                                  subject=target_agent,
                                  details={"task_id": task.task_id, "reason": decision.reason})
                return task

        task = new_task(origin_agent, target_agent, purpose,
                        permissions=permissions or [], data_scope=data_scope,
                        owner=owner)
        task.status = "authorized"
        task.events.append({"at": time.time(), "to": "authorized",
                            "note": "policy checks passed"})
        self.tasks.save(task)

        # Submission with idempotency + duplicate defense.
        existing = self.tasks.find_by_idempotency(task.idempotency_key)
        if existing is not None and existing.task_id != task.task_id:
            return existing  # already submitted under this key
        transport = self._transport_for(target_agent)
        try:
            result = transport.send_message(
                {"role": "user", "parts": [{"text": purpose}],
                 "_aetheros_task_id": task.task_id,
                 "_aetheros_message": message},
                idempotency_key=task.idempotency_key)
            task = self.tasks.transition(task.task_id, "submitted", "sent to remote")
            task.provenance["remote"] = summarize_payload(result)
            remote_state = str(result.get("task", {}).get("state", ""))
            if remote_state == "accepted":
                task = self.tasks.transition(task.task_id, "accepted", "remote accepted")
            self.circuit.success(target_agent)
            self.registry.record_task_outcome(target_agent, True)
            self.audit.record("task.delegated", actor=origin_agent, subject=target_agent,
                              details={"task_id": task.task_id})
        except (TransportError, ConnectionError) as e:
            task.events.append({"at": time.time(), "to": task.status, "note": f"submit failed: {e}"})
            self.tasks.save(task)
            self.circuit.failure(target_agent)
            self.registry.record_task_outcome(target_agent, False)
            self.audit.record("task.submit_failed", actor=origin_agent, subject=target_agent,
                              details={"task_id": task.task_id, "error": str(e)})
            raise
        return task

    def poll(self, task_id: str) -> RemoteTask:
        """Query remote state and reconcile (resume-safe)."""
        task = self.tasks.get(task_id)
        if task is None:
            raise KeyError(f"unknown task: {task_id}")
        transport = self._transport_for(task.target_agent)
        result = transport.get_task(task_id)
        remote_state = str(result.get("state", "")).lower()
        mapping = {"accepted": "accepted", "running": "running",
                   "input-required": "input_required",
                   "completed": "completed", "failed": "failed",
                   "canceled": "cancelled", "cancelled": "cancelled"}
        if remote_state in mapping:
            task = self.tasks.reconcile(task_id, mapping[remote_state])
        if result.get("artifacts"):
            task.artifacts = [str(a) for a in result["artifacts"]][:32]
            self.tasks.save(task)
        return task

    def cancel(self, task_id: str) -> RemoteTask:
        task = self.tasks.get(task_id)
        if task is None:
            raise KeyError(f"unknown task: {task_id}")
        try:
            transport = self._transport_for(task.target_agent)
            transport.cancel_task(task_id)
        except Exception as e:  # best-effort remote cancel; local state is authoritative
            task.events.append({"at": time.time(), "to": task.status,
                                "note": f"remote cancel failed: {e}"})
        return self.tasks.transition(task_id, "cancelled", "cancel requested")

    # -- inbound remote content: always untrusted ---------------------------
    def screen_inbound_text(self, agent_id: str, text: str) -> Dict[str, Any]:
        """Prompt-injection screen for anything a remote agent sent."""
        hits = detect_prompt_injection(text)
        if hits:
            self.audit.record("security.injection_blocked", actor=agent_id,
                              subject="local",
                              details={"hits": len(hits)})
        return {"blocked": bool(hits), "hits": hits}

    def record_relationship(self, agent_id: str, task_class: str,
                            success: bool, latency_ms: Optional[float] = None) -> None:
        """Task-class-specific, time-decayed reliability (sections 61, 114)."""
        rel = self._relationships.setdefault(
            agent_id, {"by_class": {}, "updated_at": time.time()})
        cls = rel["by_class"].setdefault(
            task_class, {"success": 0, "total": 0, "latency_ms": []})
        # Decay old evidence.
        cls["success"] *= 0.95
        cls["total"] *= 0.95
        cls["total"] += 1
        if success:
            cls["success"] += 1
        if latency_ms is not None:
            cls["latency_ms"] = (cls["latency_ms"] + [latency_ms])[-20:]
        rel["updated_at"] = time.time()

    def reliability(self, agent_id: str, task_class: str) -> Optional[float]:
        cls = self._relationships.get(agent_id, {}).get("by_class", {}).get(task_class)
        if not cls or cls["total"] < 1:
            return None
        return cls["success"] / cls["total"]
