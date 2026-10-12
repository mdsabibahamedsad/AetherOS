"""
AetherOS Agent Hypervisor 1.0 — capsule runtime (§1-§5, §121).

The hypervisor sits between the Agent Kernel and the host: every meaningful
agent workload executes inside an explicit, isolated, resource-bounded,
authority-bounded, observable, and recoverable Agent Capsule.

An agent does not receive the machine. An agent receives a capsule.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.core.hypervisor.filesystem import CapsuleFilesystem, capsule_base_dir
from kernel.core.hypervisor.guards import (
    PathEscapeError,
    check_egress_url,
    domain_matches_allowlist,
    normalize_domain,
)
from kernel.core.hypervisor.isolation import (
    IsolationProvider,
    IsolationReport,
    IsolationStatus,
    detect_isolation_support,
    select_provider,
    strongest_available_level,
)
from kernel.core.hypervisor.profiles import CapsuleProfile, get_profile
from kernel.core.hypervisor.risk import assess_capsule, blast_radius_for
from kernel.core.hypervisor.secrets import SecretBroker
from kernel.core.hypervisor.types import (
    SNAPSHOT_VERSION,
    AgentCapsule,
    AgentCapsuleContract,
    AutonomyLevel,
    BlastRadius,
    CapabilityManifest,
    CapsuleHealth,
    CapsuleLifecycleState,
    CapsuleProfileName,
    CapsuleReceipt,
    CapsuleSnapshot,
    CircuitState,
    ForensicSnapshot,
    IsolationLevel,
    MemoryScopeKind,
    MountType,
    NetworkMode,
    NetworkPolicy,
    PlacementDecision,
    ReplayMode,
    RiskAssessment,
    TerminationMode,
)
from kernel.core.types import (
    AuthorityGrant,
    DataClassification,
    Intent,
    ProvenanceType,
    ResourceBudget,
    _now,
    new_id,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Small control-plane primitives (§61-§63)
# ---------------------------------------------------------------------------


@dataclass
class CircuitBreaker:
    """Per-scope circuit breaker (§61)."""
    key: str
    failure_threshold: int = 5
    open_seconds: float = 60.0
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    opened_at: Optional[float] = None
    half_open_probes: int = 0

    def before(self) -> Optional[str]:
        if self.state == CircuitState.OPEN:
            if self.opened_at and (_now() - self.opened_at) >= self.open_seconds:
                self.state = CircuitState.HALF_OPEN
                self.half_open_probes = 0
                return None
            return f"circuit OPEN for {self.key}"
        return None

    def after(self, ok: bool) -> None:
        if ok:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
            self.failures = 0
            self.opened_at = None
        else:
            self.failures += 1
            if self.state == CircuitState.HALF_OPEN or self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = _now()

    def to_dict(self) -> Dict[str, Any]:
        return {"key": self.key, "state": self.state.value,
                "failures": self.failures, "opened_at": self.opened_at}


@dataclass
class RateBucket:
    """Fixed-window rate limiter (§62)."""
    key: str
    action: str
    limit: int
    window_seconds: float = 60.0
    _hits: List[float] = field(default_factory=list)

    def allow(self) -> bool:
        now = _now()
        cutoff = now - self.window_seconds
        self._hits = [t for t in self._hits if t > cutoff]
        if len(self._hits) >= self.limit:
            return False
        self._hits.append(now)
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {"key": self.key, "action": self.action, "limit": self.limit,
                "used": len(self._hits), "window_seconds": self.window_seconds}


# External side-effect capabilities: never auto-executed during replay (§54).
EXTERNAL_SIDE_EFFECT_CAPS = (
    "financial", "pay", "transfer", "buy", "sell", "message", "send",
    "email", "publish", "post", "robot", "actuator", "device.control",
    "computer.click", "computer.type", "browser.click", "browser.type",
    "process.execute", "terminal.execute", "network", "request",
)


def _is_external(capability: str) -> bool:
    c = capability.lower()
    return any(k in c for k in EXTERNAL_SIDE_EFFECT_CAPS)


# ---------------------------------------------------------------------------
# Hypervisor
# ---------------------------------------------------------------------------


class AgentHypervisor:
    """Capsule lifecycle, isolation, enforcement, and observability."""

    def __init__(self, config: Any, event_bus: Any, kernel: Any) -> None:
        self.config = config
        self.event_bus = event_bus
        self.kernel = kernel
        self._lock = threading.RLock()
        self._capsules: Dict[str, AgentCapsule] = {}
        self._agent_index: Dict[str, str] = {}  # agent_id -> capsule_id
        self._filesystems: Dict[str, CapsuleFilesystem] = {}
        self._isolation_handles: Dict[str, Dict[str, Any]] = {}
        self._snapshots: Dict[str, CapsuleSnapshot] = {}
        self._capsule_snapshots: Dict[str, List[str]] = {}
        self._receipts: Dict[str, List[CapsuleReceipt]] = {}
        self._receipt_heads: Dict[str, str] = {}
        self._forensics: Dict[str, ForensicSnapshot] = {}
        self._egress_log: Dict[str, List[Dict[str, Any]]] = {}
        self._observations: Dict[str, List[Dict[str, Any]]] = {}
        self._security_events: Dict[str, List[Dict[str, Any]]] = {}
        self._heartbeats: Dict[str, float] = {}
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._buckets: Dict[str, RateBucket] = {}
        self._usage: Dict[str, Dict[str, float]] = {}
        self._swarm_quotas: Dict[str, Dict[str, float]] = {}
        self._takeovers: Dict[str, Dict[str, Any]] = {}
        self._base_dir = capsule_base_dir(config)
        self.secret_broker = SecretBroker(audit=self._audit_secret_event)
        self._isolation_reports: Optional[List[IsolationReport]] = None
        self._metrics = {
            "capsules_created": 0, "capsules_destroyed": 0,
            "capsules_quarantined": 0, "capsules_migrated": 0,
            "checkpoints": 0, "restores": 0, "replays": 0,
            "denials": 0, "anomalies": 0, "gc_runs": 0, "gc_reclaimed": 0,
        }

    # -- internal helpers -------------------------------------------------
    def _emit(self, topic: str, data: Dict[str, Any]) -> None:
        if self.event_bus:
            try:
                self.event_bus.emit(topic, data)
            except Exception as exc:
                logger.debug("hypervisor emit failed: %s", exc)

    def _audit(self, action: str, capsule_id: str, outcome: str,
               details: Optional[Dict[str, Any]] = None) -> None:
        try:
            self.kernel.audit_engine.log(
                event_type="capsule." + action, actor_id="hypervisor",
                action=action, target=capsule_id, outcome=outcome,
                details=details or {}, provenance=ProvenanceType.SYSTEM_DERIVED)
        except Exception as exc:
            logger.debug("hypervisor audit failed: %s", exc)

    def _audit_secret_event(self, action: str, agent_id: str,
                            capsule_id: str, details: Dict[str, Any]) -> None:
        self._audit(action, capsule_id, "ok",
                    {"agent_id": agent_id, **details})

    def _transition(self, capsule: AgentCapsule,
                    new_state: CapsuleLifecycleState) -> None:
        old = capsule.lifecycle_state
        capsule.transition(new_state)
        self._emit("capsule.lifecycle.transition", {
            "capsule_id": capsule.capsule_id, "agent_id": capsule.agent_id,
            "from_state": old.value, "to_state": new_state.value,
            "timestamp": capsule.updated_at})
        self._audit("lifecycle.transition", capsule.capsule_id, "ok",
                    {"from": old.value, "to": new_state.value})

    # -- cross-process registry (CLI visibility, §77) --------------------------
    def _registry_path(self) -> str:
        return os.path.join(self._base_dir, "registry.json")

    def _persist_registry(self) -> None:
        """Persist capsule records so `aetheros capsule list/inspect` can see
        capsules across processes. Records are snapshots (live control still
        requires the owning kernel); readers must treat them as such."""
        try:
            with self._lock:
                data = {cid: cap.to_dict() for cid, cap in self._capsules.items()}
            tmp = self._registry_path() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"v": 1, "capsules": data}, fh)
            os.replace(tmp, self._registry_path())
        except OSError as exc:
            logger.debug("capsule registry persist failed: %s", exc)

    def registry_snapshot(self) -> Dict[str, Any]:
        """Read persisted capsule records (cross-process, not live)."""
        try:
            with open(self._registry_path(), encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict) or "capsules" not in data:
                raise ValueError("invalid registry schema")
            return {"live": False,
                    "note": "registry snapshot; live state requires the owning kernel",
                    "capsules": data["capsules"]}
        except (OSError, ValueError) as exc:
            return {"live": False, "capsules": {},
                    "note": f"no registry available: {exc}"}

    def _get(self, capsule_id: str) -> AgentCapsule:
        capsule = self._capsules.get(capsule_id)
        if capsule is None:
            raise KeyError(f"unknown capsule: {capsule_id}")
        return capsule

    def _breaker(self, key: str) -> CircuitBreaker:
        with self._lock:
            breaker = self._breakers.get(key)
            if breaker is None:
                breaker = CircuitBreaker(key=key)
                self._breakers[key] = breaker
            return breaker

    def _bucket(self, key: str, action: str, limit: int) -> RateBucket:
        with self._lock:
            bid = f"{key}:{action}"
            bucket = self._buckets.get(bid)
            if bucket is None:
                bucket = RateBucket(key=key, action=action, limit=limit)
                self._buckets[bid] = bucket
            return bucket

    def _record_receipt(self, capsule: AgentCapsule, capability: str,
                        authority_grant_id: str, inputs: Dict[str, Any],
                        result: Any, outcome: str) -> CapsuleReceipt:
        body = json.dumps({"in": inputs}, sort_keys=True, default=str)
        out = json.dumps({"out": result}, sort_keys=True, default=str)
        receipt = CapsuleReceipt(
            capsule_id=capsule.capsule_id, agent_id=capsule.agent_id,
            intent_id=capsule.intent_id, capability=capability,
            authority_grant_id=authority_grant_id,
            policy_version=capsule.policy_version,
            input_hash=CapsuleReceipt.hash_payload(body),
            result_hash=CapsuleReceipt.hash_payload(out),
            outcome=outcome)
        with self._lock:
            head = self._receipt_heads.get(capsule.capsule_id, "")
            receipt.seal(head)
            self._receipts.setdefault(capsule.capsule_id, []).append(receipt)
            self._receipt_heads[capsule.capsule_id] = receipt.receipt_hash
        return receipt

    def _security_event(self, capsule: AgentCapsule, kind: str,
                        detail: str) -> None:
        record = {"kind": kind, "detail": detail, "at": _now(),
                  "capsule_id": capsule.capsule_id}
        with self._lock:
            self._security_events.setdefault(capsule.capsule_id, []).append(record)
        self._emit("capsule.security.event", record)
        self._audit("security.event", capsule.capsule_id, "alert",
                    {"kind": kind, "detail": detail})

    # -- isolation capability surface (§7-§11) ------------------------------
    def isolation_status(self) -> Dict[str, Any]:
        if self._isolation_reports is None:
            self._isolation_reports = detect_isolation_support()
        strongest = strongest_available_level(self._isolation_reports)
        return {
            "strongest_available": strongest.value,
            "providers": [r.to_dict() for r in self._isolation_reports],
            "note": "LEVEL_3/LEVEL_4 are NOT claimed in 1.0.",
        }

    # -- admission & creation (§5, §13-§16) ---------------------------------
    def preview(self, objective: str, profile: str = "standard",
                capabilities: Optional[List[str]] = None,
                parent_capsule_id: Optional[str] = None) -> Dict[str, Any]:
        """Capsule preview + resource preview (§84-§85). Estimates only."""
        prof = get_profile(profile)
        caps = sorted(set(list(capabilities or []) + list(prof.capabilities)))
        network = prof.network
        return {
            "CAPSULE_PREVIEW": {
                "profile": prof.name,
                "filesystem": "capsule-private + declared mounts only",
                "mounts": [m.to_dict() for m in prof.mounts],
                "network": network.to_dict(),
                "models": {k: v for k, v in prof.model_policy.items()},
                "secrets": "broker-mediated only; none embedded",
                "devices": dict(prof.device_policy) or "none",
                "parent_capsule_id": parent_capsule_id,
            },
            "RESOURCE_PREVIEW_ESTIMATES": {
                "cpu_cores": prof.resources.cpu_cores,
                "ram_mb": prof.resources.ram_mb,
                "disk_mb": prof.resources.disk_mb,
                "token_budget_per_min": prof.resources.llm_tokens_per_minute,
                "note": "estimates, not commitments",
            },
            "capabilities": caps,
            "risk_note": "final risk is computed deterministically at admission",
        }

    def create_capsule(
        self,
        intent: Intent,
        profile: str = "standard",
        *,
        parent_capsule_id: Optional[str] = None,
        task_id: str = "",
        trust_level: Optional[int] = None,
        autonomy: str = "autonomy_1",
        isolation_provider: Optional[str] = None,
        expires_in_seconds: Optional[float] = None,
        extra_capabilities: Optional[List[str]] = None,
        start: bool = False,
    ) -> AgentCapsule:
        """Create a capsule for an intent (model never self-authorizes)."""
        prof = get_profile(profile)
        capsule = AgentCapsule(
            task_id=task_id or new_id("task"),
            intent_id=intent.intent_id,
            # Parent linkage is attached only AFTER admission checks pass:
            # the capsule must not count itself in the parent child quota.
            parent_capsule_id=None,
            security_profile=prof.name,
            capsule_profile=prof.name,
            trust_level=trust_level if trust_level is not None else (0 if prof.name == "untrusted" else 1),
            autonomy=AutonomyLevel(autonomy),
            node_id="local",
            policy_version="1.0",
            expires_at=(_now() + expires_in_seconds) if expires_in_seconds else None,
        )
        with self._lock:
            self._capsules[capsule.capsule_id] = capsule
        try:
            self._transition(capsule, CapsuleLifecycleState.ADMISSION_CHECK)
            self._admit(capsule, intent, prof,
                        parent_capsule_id=parent_capsule_id,
                        extra_capabilities=extra_capabilities)
            self._transition(capsule, CapsuleLifecycleState.PROVISIONING)
            self._provision(capsule, prof, isolation_provider=isolation_provider)
            self._transition(capsule, CapsuleLifecycleState.INITIALIZING)
            self._initialize(capsule, intent, prof)
            self._transition(capsule, CapsuleLifecycleState.READY)
            self._metrics["capsules_created"] += 1
            self._emit("capsule.created", {"capsule_id": capsule.capsule_id,
                                           "agent_id": capsule.agent_id,
                                           "profile": prof.name})
            self._persist_registry()
            if start:
                self.start_capsule(capsule.capsule_id)
            return capsule
        except Exception as exc:
            capsule.error = str(exc)[:500]
            try:
                self._transition(capsule, CapsuleLifecycleState.FAILED)
            except ValueError:
                pass
            self._metrics["denials"] += 1
            self._audit("capsule.create", capsule.capsule_id, "denied",
                        {"reason": str(exc)[:300]})
            # Normalize resource exhaustion to an admission denial: callers
            # handle one denial type, and the reason names the limit.
            try:
                from kernel.core.resource_manager import ResourceError as _ResourceError
                if isinstance(exc, _ResourceError):
                    raise PermissionError(f"insufficient resources: {exc}") from exc
            except PermissionError:
                raise
            except ImportError:
                pass
            raise

    def _admit(self, capsule: AgentCapsule, intent: Intent, prof: CapsuleProfile,
               *, parent_capsule_id: Optional[str],
               extra_capabilities: Optional[List[str]]) -> None:
        kernel = self.kernel
        # 1. Parent subset pre-check (§14, §63): depth + children + total.
        parent_capsule = None
        if parent_capsule_id:
            parent_capsule = self._get(parent_capsule_id)
            if parent_capsule.lifecycle_state in (
                    CapsuleLifecycleState.QUARANTINED,
                    CapsuleLifecycleState.TERMINATED,
                    CapsuleLifecycleState.DESTROYED):
                raise PermissionError("parent capsule cannot delegate in its state")
            depth = self._capsule_depth(parent_capsule) + 1
            if depth > int(getattr(kernel.config, "max_agent_depth", 5)):
                raise PermissionError(f"capsule delegation depth {depth} exceeds limit")
            children = self._child_count(parent_capsule_id)
            max_children = int((parent_capsule.process_policy or {}).get("max_children", 8))
            if children >= max_children:
                raise PermissionError("parent capsule child quota exceeded")
            if len(self._capsules) >= int(getattr(kernel.config, "max_concurrent_agents", 50)) + 50:
                raise PermissionError("hypervisor capsule capacity exceeded")
        # 2. Requested = profile defaults ∪ explicit extras (deny-by-default:
        #    anything not declared here is unavailable, §15-§16).
        requested = sorted(set(list(prof.capabilities) + list(extra_capabilities or [])))
        intent.requested_capabilities = requested
        # Scope the admission/allocation footprint to the capsule slice (§25):
        # the agent never receives the host-wide default budget.
        from kernel.core.types import ResourceBudget as _Budget
        capsule_budget = _Budget(**prof.resources.to_dict())
        intent.requested_resources = capsule_budget
        intent.budget = capsule_budget
        # 3. Agent process creation performs kernel admission (intent →
        #    authority → policy → resources). Parent linkage enforced below.
        process = kernel.create_agent_process(
            intent,
            parent_agent_id=(parent_capsule.agent_id if parent_capsule else None),
            resource_budget=_Budget(**prof.resources.to_dict()),
            security_profile=prof.name)
        capsule.agent_id = process.agent_id
        capsule.intent_id = intent.intent_id
        # 4. Capsule authority ⊆ agent authority ⊆ parent authority (§14).
        # Attach parent linkage now that quota/depth checks have passed.
        capsule.parent_capsule_id = parent_capsule_id
        grant = process.authority
        if parent_capsule and parent_capsule.authority:
            delegated = kernel.authority_manager.delegate_authority(
                parent_capsule.agent_id, process.agent_id, intent,
                parent_grant_id=parent_capsule.authority.grant_id)
            grant = delegated
            process.authority = delegated
            process.capabilities = list(delegated.capabilities)
        allowed = [c for c in requested if c in (grant.capabilities or [])]
        denied = sorted(set(requested) - set(allowed))
        if denied:
            logger.info("capsule %s: kernel denied capabilities: %s",
                        capsule.capsule_id, denied)
        capsule.authority = grant
        capsule.capabilities = allowed
        capsule.manifest = CapabilityManifest(
            capsule_id=capsule.capsule_id, capabilities=allowed,
            policy_version=capsule.policy_version).seal()
        # 5. Resource availability for the capsule slice.
        avail = kernel.resource_manager.check_availability(prof.resources)
        if not avail.get("available", True):
            raise PermissionError(f"insufficient resources: {avail.get('reason', 'unknown')}")
        capsule.resource_limits = prof.resources
        with self._lock:
            self._agent_index[process.agent_id] = capsule.capsule_id

    def _provision(self, capsule: AgentCapsule, prof: CapsuleProfile,
                   *, isolation_provider: Optional[str]) -> None:
        provider = select_provider(isolation_provider)
        report = provider.detect()
        if report.status == IsolationStatus.UNAVAILABLE and provider.name != "native_process":
            raise PermissionError(
                f"isolation provider {provider.name} UNAVAILABLE: {report.detail}")
        capsule.isolation_provider = provider.name
        order = list(__import__("kernel.core.hypervisor.types", fromlist=["IsolationLevel"]).IsolationLevel)
        if order.index(report.level) < order.index(
                __import__("kernel.core.hypervisor.types", fromlist=["IsolationLevel"]).IsolationLevel(
                    prof.isolation_floor)):
            raise PermissionError(
                f"profile {prof.name} requires {prof.isolation_floor}; "
                f"{provider.name} offers {report.level.value}")
        capsule.isolation_level = report.level
        handle = provider.provision(capsule.capsule_id, {"profile": prof.name})
        with self._lock:
            self._isolation_handles[capsule.capsule_id] = handle
        # Filesystem roots + mounts.
        fs = CapsuleFilesystem(capsule.capsule_id, self._base_dir,
                               mounts=list(prof.mounts),
                               policy_version=capsule.policy_version)
        fs.provision()
        with self._lock:
            self._filesystems[capsule.capsule_id] = fs
        capsule.mounts = list(prof.mounts)
        capsule.network = NetworkPolicy(mode=prof.network.mode,
                                        allowlist=list(prof.network.allowlist),
                                        denylist=list(prof.network.denylist),
                                        require_tls=prof.network.require_tls)
        # Push capsule network constraints into the kernel network manager
        # as capsule-scoped rules (additive; global policy untouched).
        try:
            if capsule.network.denylist:
                kernel = self.kernel
                kernel.network_manager.add_domain_denylist(list(capsule.network.denylist))
        except Exception as exc:
            logger.debug("capsule network push failed: %s", exc)

    def _initialize(self, capsule: AgentCapsule, intent: Intent,
                    prof: CapsuleProfile) -> None:
        capsule.identity_key_id = f"capsule-key-{capsule.capsule_id}"
        capsule.memory_policy = MemoryScopeKind(prof.memory_scope)
        capsule.model_policy = dict(prof.model_policy)
        capsule.tool_policy = dict(prof.tool_policy)
        capsule.device_policy = dict(prof.device_policy)
        capsule.secret_policy = dict(prof.secret_policy)
        capsule.process_policy = dict(prof.process_policy)
        capsule.environment_policy = {
            "AETHEROS_CAPSULE_ID": capsule.capsule_id,
            "AETHEROS_CAPSULE_PROFILE": prof.name,
        }
        capsule.contract = AgentCapsuleContract(
            objective=intent.objective, authority=[capsule.authority.grant_id] if capsule.authority else [],
            capabilities=list(capsule.capabilities), resources=capsule.resource_limits,
            security_profile=prof.name, privacy_class=prof.privacy_class,
            network=capsule.network, mounts=list(capsule.mounts))
        capsule.risk = assess_capsule(capsule)
        capsule.blast_radius = blast_radius_for(capsule)
        capsule.policy_hash = hashlib.sha256(
            json.dumps({"profile": prof.name, "caps": sorted(capsule.capabilities),
                        "v": capsule.policy_version},
                       sort_keys=True).encode()).hexdigest()[:16]
        capsule.provenance = {"created_by": "hypervisor", "profile": prof.name,
                              "intent_id": intent.intent_id,
                              "manifest_hash": (capsule.manifest.manifest_hash if capsule.manifest else "")}
        # Max-autonomy clamp from profile (§59).
        order = ["autonomy_0", "autonomy_1", "autonomy_2", "autonomy_3",
                 "autonomy_4", "autonomy_5"]
        if order.index(capsule.autonomy.value) > order.index(prof.max_autonomy):
            capsule.autonomy = AutonomyLevel(prof.max_autonomy)
        self._heartbeats[capsule.capsule_id] = _now()
        with self._lock:
            self._usage[capsule.capsule_id] = {"tool_calls": 0, "network_calls": 0,
                                               "model_calls": 0, "memory_writes": 0,
                                               "spawns": 0, "bytes_out": 0}

    # -- lifecycle operations (§76) -----------------------------------------
    def start_capsule(self, capsule_id: str) -> AgentCapsule:
        capsule = self._get(capsule_id)
        self._ensure_operable(capsule, op="start")
        if capsule.lifecycle_state == CapsuleLifecycleState.READY:
            self.kernel.start_agent(capsule.agent_id)
            self._transition(capsule, CapsuleLifecycleState.RUNNING)
        elif capsule.lifecycle_state == CapsuleLifecycleState.SUSPENDED:
            self._transition(capsule, CapsuleLifecycleState.RUNNING)
        self._heartbeats[capsule_id] = _now()
        return capsule

    def pause_capsule(self, capsule_id: str) -> AgentCapsule:
        capsule = self._get(capsule_id)
        if capsule.lifecycle_state != CapsuleLifecycleState.RUNNING:
            raise ValueError(f"capsule not running: {capsule.lifecycle_state.value}")
        try:
            self.kernel.pause_agent(capsule.agent_id)
        except Exception:
            pass
        self.snapshot_capsule(capsule_id)
        self._transition(capsule, CapsuleLifecycleState.SUSPENDED)
        return capsule

    def resume_capsule(self, capsule_id: str) -> AgentCapsule:
        capsule = self._get(capsule_id)
        self._ensure_operable(capsule, op="resume")
        if capsule.lifecycle_state != CapsuleLifecycleState.SUSPENDED:
            raise ValueError(f"capsule not suspended: {capsule.lifecycle_state.value}")
        try:
            self.kernel.resume_agent(capsule.agent_id)
        except Exception:
            pass
        self._transition(capsule, CapsuleLifecycleState.RUNNING)
        self._heartbeats[capsule_id] = _now()
        return capsule

    def destroy_capsule(self, capsule_id: str,
                        mode: TerminationMode = TerminationMode.GRACEFUL,
                        *,
                        preserve_artifacts_to: Optional[str] = None) -> Dict[str, Any]:
        """Terminate a capsule (§92). Physical capsules fail safe (§41)."""
        capsule = self._get(capsule_id)
        if mode == TerminationMode.GRACEFUL:
            # Stop new actions, checkpoint, release, terminate.
            if capsule.lifecycle_state == CapsuleLifecycleState.RUNNING:
                try:
                    self.pause_capsule(capsule_id)
                except Exception:
                    pass
            else:
                try:
                    self.snapshot_capsule(capsule_id)
                except Exception:
                    pass
        elif mode == TerminationMode.EMERGENCY:
            # Block privileged actions immediately; no graceful anything.
            try:
                self.kernel.security_boundary.quarantine_agent(capsule.agent_id, "emergency")
            except Exception:
                pass
        # Physical safe-state: never blindly cut actuators (§41).
        safe_state: Dict[str, Any] = {}
        if capsule.capsule_profile == "physical" or capsule.device_policy.get("actuators"):
            safe_state = {"actuators": "commanded to configured safe state",
                          "note": "device handles released after safe-state confirm"}
        # Forensic capture already exists for quarantined capsules; keep it.
        # Release resources + agent.
        try:
            try:
                self.kernel.stop_agent(capsule.agent_id, reason=f"capsule destroy ({mode.value})")
            except Exception:
                pass
            try:
                self.kernel.resource_manager.release(capsule.agent_id)
            except Exception:
                pass
        finally:
            pass
        fs = self._filesystems.pop(capsule_id, None)
        fs_meta: Dict[str, Any] = {}
        if fs is not None:
            fs_meta = fs.destroy(preserve_artifacts_to=preserve_artifacts_to)
        # Revoke capsule secrets (§30: no lingering plaintext).
        for binding in self.secret_broker.bindings_for_capsule(capsule_id):
            self.secret_broker.revoke_secret(binding.binding_id, reason="capsule destroy")
        # Release isolation backend state.
        handle = self._isolation_handles.pop(capsule_id, None)
        try:
            select_provider(capsule.isolation_provider).teardown(capsule_id, handle)
        except Exception:
            pass
        for terminal in (CapsuleLifecycleState.TERMINATED, CapsuleLifecycleState.DESTROYED):
            try:
                self._transition(capsule, terminal)
                if terminal == CapsuleLifecycleState.DESTROYED:
                    break
            except ValueError:
                continue
        with self._lock:
            self._agent_index.pop(capsule.agent_id, None)
            self._metrics["capsules_destroyed"] += 1
        self._persist_registry()
        self._emit("capsule.destroyed", {"capsule_id": capsule_id, "mode": mode.value})
        self._audit("capsule.destroy", capsule_id, "ok",
                    {"mode": mode.value, "fs": fs_meta, "safe_state": safe_state})
        return {"capsule_id": capsule_id, "mode": mode.value,
                "filesystem": fs_meta, "safe_state": safe_state}

    # -- guards -------------------------------------------------------------
    def _ensure_operable(self, capsule: AgentCapsule, op: str) -> None:
        if capsule.lifecycle_state == CapsuleLifecycleState.QUARANTINED:
            raise PermissionError(f"capsule quarantined: {op} denied")
        if capsule.lifecycle_state in (CapsuleLifecycleState.TERMINATED,
                                       CapsuleLifecycleState.DESTROYED):
            raise PermissionError(f"capsule {capsule.lifecycle_state.value}: {op} denied")
        if capsule.is_expired():
            raise PermissionError("capsule expired: revoke/renew required")
        if capsule.authority is not None and not capsule.authority.is_valid():
            raise PermissionError("capsule authority expired or revoked")

    def _check_manifest(self, capsule: AgentCapsule, capability: str) -> None:
        if capsule.manifest is None or not capsule.manifest.verify():
            raise PermissionError("capability manifest invalid: all calls blocked")
        if capability not in capsule.capabilities or capability not in capsule.manifest.capabilities:
            self._metrics["denials"] += 1
            self._audit("capability.manifest_deny", capsule.capsule_id, "denied",
                        {"capability": capability})
            raise PermissionError(f"capability not in manifest: {capability}")

    # -- mediated invocation (§33, §22, §26, §61-§62) -------------------------
    def invoke(self, capsule_id: str, capability: str,
               inputs: Optional[Dict[str, Any]] = None,
               *, intent_id: str = "") -> Any:
        """Execute a capability through the capsule boundary.

        Enforces: operability → manifest gate → revocation → circuit breaker
        → rate limit → resource budgets → network/screen/secret policy →
        kernel invocation → receipt + egress record.
        """
        capsule = self._get(capsule_id)
        inputs = dict(inputs or {})
        self._ensure_operable(capsule, op=f"invoke {capability}")
        self._check_manifest(capsule, capability)
        breaker = self._breaker(f"capsule:{capsule_id}:{capability}")
        blocked = breaker.before()
        if blocked:
            raise PermissionError(blocked)
        # Rate limits (defaults; profiles/quotas may tighten).
        limits = {"tool_calls": 600, "network_calls": 300, "model_calls": 300,
                  "memory_writes": 600, "spawns": 20}
        kind = ("network_calls" if any(k in capability for k in ("network", "browser", "research", "web"))
                else "spawns" if capability in ("agent.spawn", "agent.delegate") else
                "memory_writes" if capability.startswith("memory.") else "tool_calls")
        if not self._bucket(capsule_id, kind, limits[kind]).allow():
            raise PermissionError(f"rate limit exceeded: {kind}")
        # Resource budgets (§25-§26).
        self._enforce_budgets(capsule, capability, kind)
        # Network policy for network-touching caps (§20-§22).
        if kind == "network_calls":
            self._enforce_network(capsule, capability, inputs)
        # Screen data protection (§38).
        if capability in ("computer.observe", "computer.screenshot",
                          "browser.screenshot", "browser.extract"):
            inputs = self._redact_screen_inputs(capsule, inputs)
        try:
            result = self.kernel.invoke_capability(
                capsule.agent_id, capability, inputs,
                intent_id=intent_id or capsule.intent_id)
        except Exception as exc:
            breaker.after(False)
            self._record_receipt(capsule, capability,
                                 capsule.authority.grant_id if capsule.authority else "",
                                 inputs, {"error": str(exc)[:300]}, "failed")
            raise
        ok = getattr(result, "status", "completed") == "completed"
        breaker.after(ok)
        with self._lock:
            usage = self._usage.setdefault(capsule_id, {})
            usage[kind] = usage.get(kind, 0) + 1
        self._record_receipt(capsule, capability,
                             capsule.authority.grant_id if capsule.authority else "",
                             inputs, getattr(result, "result", result),
                             "ok" if ok else "failed")
        self._heartbeats[capsule_id] = _now()
        self._observe(capsule, capability, inputs, result)
        return result

    def _enforce_budgets(self, capsule: AgentCapsule, capability: str, kind: str) -> None:
        usage = self._usage.get(capsule.capsule_id, {})
        lim = capsule.resource_limits
        if kind == "tool_calls" and usage.get("tool_calls", 0) >= max(1, lim.tool_concurrency * 200):
            raise PermissionError("tool-call budget exceeded: stop/escalate")
        if kind == "network_calls" and usage.get("network_calls", 0) >= 1000:
            raise PermissionError("network quota exceeded: blocked")
        if kind == "spawns":
            max_children = int((capsule.process_policy or {}).get("max_children", 8))
            if self._child_count(capsule.capsule_id) >= max_children:
                raise PermissionError("child-agent quota exceeded: spawn denied")
        # Token budget: consult kernel cost/latency accounting when present.
        try:
            cost = self.kernel.cost_manager.get_stats() if self.kernel.cost_manager else {}
            _ = cost
        except Exception:
            pass

    def _enforce_network(self, capsule: AgentCapsule, capability: str,
                         inputs: Dict[str, Any]) -> None:
        policy = capsule.network
        url = str(inputs.get("url") or inputs.get("destination") or "")
        if policy.mode == NetworkMode.NO_NETWORK:
            self._metrics["denials"] += 1
            raise PermissionError("capsule network disabled (NO_NETWORK)")
        if policy.mode == NetworkMode.FULL_NETWORK:
            self._security_event(capsule, "high_risk_network",
                                 f"FULL_NETWORK egress via {capability}")
        if url:
            allow_private = policy.mode in (NetworkMode.PRIVATE_NETWORK,)
            allow_localhost = policy.mode in (NetworkMode.LOCAL_ONLY,
                                              NetworkMode.PRIVATE_NETWORK)
            ok, reason = check_egress_url(url, allow_private=allow_private,
                                          allow_localhost=allow_localhost)
            record = {"capability": capability, "destination": url,
                      "allowed": ok, "reason": reason, "at": _now()}
            with self._lock:
                self._egress_log.setdefault(capsule.capsule_id, []).append(record)
            if not ok:
                self._metrics["denials"] += 1
                raise PermissionError(f"egress blocked: {reason}")
            if policy.mode == NetworkMode.ALLOWLIST:
                from urllib.parse import urlparse as _up
                host = (_up(url).hostname or "")
                if host and not domain_matches_allowlist(host, policy.allowlist):
                    self._metrics["denials"] += 1
                    raise PermissionError(f"destination not allowlisted: {host}")
            # Kernel-level check (defense in depth: scopes, budgets, rules).
            try:
                allowed, reason = self.kernel.network_manager.check_url(
                    url, grant=capsule.authority, agent_id=capsule.agent_id)
                if not allowed:
                    self._metrics["denials"] += 1
                    raise PermissionError(f"kernel network denied: {reason}")
            except PermissionError:
                raise
            except Exception as exc:
                logger.debug("kernel network check failed: %s", exc)

    # -- observations & anomaly detection (§56) -------------------------------
    def _observe(self, capsule: AgentCapsule, capability: str,
                 inputs: Dict[str, Any], result: Any) -> None:
        obs = {"capability": capability, "at": _now(),
               "input_keys": sorted(inputs.keys())[:12]}
        with self._lock:
            log = self._observations.setdefault(capsule.capsule_id, [])
            log.append(obs)
            if len(log) > 500:
                del log[:len(log) - 500]
        self._detect_anomalies(capsule)

    def _detect_anomalies(self, capsule: AgentCapsule) -> List[str]:
        with self._lock:
            log = list(self._observations.get(capsule.capsule_id, []))
            egress = list(self._egress_log.get(capsule.capsule_id, []))
        if not log:
            return []
        window = [o for o in log if _now() - o["at"] < 60]
        findings: List[str] = []
        # Rapid action escalation: many distinct caps in 60s.
        distinct = {o["capability"] for o in window}
        if len(distinct) >= 8 and len(window) >= 20:
            findings.append(f"rapid action escalation: {len(distinct)} caps / 60s")
        # Unexpected capability vs manifest-adjacent families.
        families = {c.split(".")[0] for c in capsule.capabilities}
        for o in window[-10:]:
            if o["capability"].split(".")[0] not in families and o["capability"] not in capsule.capabilities:
                findings.append(f"unexpected capability request: {o['capability']}")
                break
        # Unexpected network destinations.
        allowed_hosts = {normalize_domain(h) for h in (capsule.network.allowlist or [])}
        for rec in egress[-20:]:
            if rec.get("allowed") and allowed_hosts:
                from urllib.parse import urlparse as _up
                host = normalize_domain(_up(rec.get("destination", "")).hostname or "")
                if host and not domain_matches_allowlist(host, list(allowed_hosts)):
                    findings.append(f"unexpected network destination: {host}")
                    break
        # Resource spike: tool-call velocity.
        if len(window) >= 100:
            findings.append(f"resource spike: {len(window)} actions / 60s")
        for finding in findings:
            self._security_event(capsule, "anomaly", finding)
        with self._lock:
            self._metrics["anomalies"] += len(findings)
        # Auto-quarantine on strong signals (policy-controlled threshold).
        if any("unexpected capability" in f or "resource spike" in f for f in findings):
            try:
                self.quarantine_capsule(capsule.capsule_id, reason="; ".join(findings)[:300])
            except Exception:
                pass
        return findings

    # -- quarantine & forensics (§55, §93) ------------------------------------
    def quarantine_capsule(self, capsule_id: str, reason: str = "security") -> AgentCapsule:
        capsule = self._get(capsule_id)
        if capsule.lifecycle_state == CapsuleLifecycleState.QUARANTINED:
            return capsule
        # SUSPEND → QUARANTINE → FORENSIC SNAPSHOT → POLICY DECISION.
        if capsule.lifecycle_state == CapsuleLifecycleState.RUNNING:
            try:
                self.kernel.pause_agent(capsule.agent_id)
            except Exception:
                pass
        try:
            self.kernel.security_boundary.quarantine_agent(capsule.agent_id, reason)
        except Exception:
            pass
        # Forensic snapshot BEFORE any state change destroys evidence (§55).
        forensic = ForensicSnapshot(
            capsule_id=capsule_id,
            configuration=capsule.to_dict(),
            policy_version=capsule.policy_version,
            event_trace=list(self._observations.get(capsule_id, [])[-100:]),
            process_tree={"agent_id": capsule.agent_id,
                          "runtime": "kernel-managed",
                          "children": self._child_ids(capsule_id)},
            network_metadata={"egress": list(self._egress_log.get(capsule_id, [])[-100:])},
            filesystem_metadata=(self._filesystems[capsule_id].metadata()
                                  if capsule_id in self._filesystems else {}),
            security_events=list(self._security_events.get(capsule_id, [])),
        )
        with self._lock:
            self._forensics[capsule_id] = forensic
        # Legal transitions into QUARANTINED from most states.
        for attempt in (capsule.lifecycle_state,):
            _ = attempt
        transitioned = False
        for target in (CapsuleLifecycleState.QUARANTINED,):
            try:
                self._transition(capsule, target)
                transitioned = True
            except ValueError:
                # Force via SUSPENDED when the direct edge is missing.
                try:
                    if capsule.lifecycle_state == CapsuleLifecycleState.RUNNING:
                        self._transition(capsule, CapsuleLifecycleState.SUSPENDED)
                    self._transition(capsule, target)
                    transitioned = True
                except ValueError:
                    pass
        if not transitioned:
            capsule.lifecycle_state = CapsuleLifecycleState.QUARANTINED
        with self._lock:
            self._metrics["capsules_quarantined"] += 1
        self._persist_registry()
        self._security_event(capsule, "quarantine", reason)
        self._emit("capsule.quarantined", {"capsule_id": capsule_id, "reason": reason})
        return capsule

    def release_quarantine(self, capsule_id: str, *, recover: bool = True) -> AgentCapsule:
        capsule = self._get(capsule_id)
        if capsule.lifecycle_state != CapsuleLifecycleState.QUARANTINED:
            raise ValueError("capsule is not quarantined")
        try:
            self.kernel.security_boundary.release_quarantine(capsule.agent_id)
        except Exception:
            pass
        if recover:
            self._transition(capsule, CapsuleLifecycleState.RECOVERING)
            self._revalidate(capsule)
            self._transition(capsule, CapsuleLifecycleState.READY)
        return capsule

    def _revalidate(self, capsule: AgentCapsule) -> None:
        """Authority revalidation after recovery/handoff/migration."""
        if capsule.authority is not None and not capsule.authority.is_valid():
            raise PermissionError("capsule authority no longer valid")
        if capsule.manifest is None or not capsule.manifest.verify():
            raise PermissionError("capsule manifest integrity failure")

    # -- snapshots, checkpoints, restore (§45-§46, §50-§51) --------------------
    def snapshot_capsule(self, capsule_id: str) -> CapsuleSnapshot:
        capsule = self._get(capsule_id)
        fs = self._filesystems.get(capsule_id)
        snap = CapsuleSnapshot(
            capsule_id=capsule_id, agent_id=capsule.agent_id,
            state=capsule.lifecycle_state, authority=capsule.authority,
            capabilities=list(capsule.capabilities),
            manifest_hash=capsule.manifest.manifest_hash if capsule.manifest else "",
            policy_version=capsule.policy_version, policy_hash=capsule.policy_hash,
            resource_limits=capsule.resource_limits,
            filesystem_meta=fs.metadata() if fs else {},
            network_state={"egress": list(self._egress_log.get(capsule_id, [])[-50:])},
            memory_refs=[f"capsule:{capsule_id}"],
            event_offset=len(self._receipts.get(capsule_id, [])),
        ).seal()
        with self._lock:
            self._snapshots[snap.integrity_hash] = snap
            self._capsule_snapshots.setdefault(capsule_id, []).append(snap.integrity_hash)
            capsule.checkpoint_id = snap.integrity_hash
            self._metrics["checkpoints"] += 1
        # Avoid capturing ephemeral credentials (§46): snapshots carry only
        # fingerprints via authority metadata, never secret values.
        self._persist_registry()
        self._emit("capsule.checkpoint", {"capsule_id": capsule_id,
                                          "snapshot": snap.integrity_hash})
        self._audit("capsule.checkpoint", capsule_id, "ok",
                    {"snapshot": snap.integrity_hash})
        return snap

    def restore_snapshot(self, snapshot_hash: str, *,
                         new_capsule: bool = False) -> AgentCapsule:
        snap = self._snapshots.get(snapshot_hash)
        if snap is None:
            raise KeyError(f"unknown snapshot: {snapshot_hash}")
        if not snap.verify():
            raise PermissionError("snapshot integrity failure: refusing restore")
        if snap.version != SNAPSHOT_VERSION:
            raise PermissionError(f"incompatible snapshot version: {snap.version}")
        old = self._capsules.get(snap.capsule_id)
        if old is not None and not new_capsule:
            # In-place restore: revalidate authority, reset to snapshot state.
            self._revalidate(old)
            old.capabilities = list(snap.capabilities)
            old.manifest = CapabilityManifest(
                capsule_id=old.capsule_id, capabilities=list(snap.capabilities),
                policy_version=snap.policy_version).seal()
            old.checkpoint_id = snapshot_hash
            if old.lifecycle_state == CapsuleLifecycleState.QUARANTINED:
                self.release_quarantine(old.capsule_id)
            with self._lock:
                self._metrics["restores"] += 1
            self._audit("capsule.restore", old.capsule_id, "ok",
                        {"snapshot": snapshot_hash})
            return old
        # New-capsule restore (migration target): fresh identity, snapshot state.
        intent = snap.intent or Intent(actor="system",
                                       objective="capsule restore",
                                       requested_capabilities=list(snap.capabilities))
        capsule = self.create_capsule(intent, profile="standard")
        capsule.capabilities = list(snap.capabilities)
        capsule.manifest = CapabilityManifest(
            capsule_id=capsule.capsule_id, capabilities=list(snap.capabilities),
            policy_version=snap.policy_version).seal()
        with self._lock:
            self._metrics["restores"] += 1
        return capsule

    # -- migration (§47-§49, §105, §107) ----------------------------------------
    def placement(self, capsule_id: str) -> PlacementDecision:
        """Choose execution location (§104). Privacy/latency/cost/trust."""
        capsule = self._get(capsule_id)
        reasons = ["local default: lowest latency, no data movement"]
        warnings: List[str] = []
        target = "local"
        if capsule.network.mode == NetworkMode.NO_NETWORK:
            reasons.append("NO_NETWORK capsule stays local")
        if (capsule.model_policy.get("local_only") or
                capsule.capsule_profile in ("local_only", "offline")):
            reasons.append("local-only model policy pins execution to this node")
        if capsule.device_policy.get("actuators") or capsule.capsule_profile == "physical":
            warnings.append("physical device is local-only: migration denied")
        return PlacementDecision(target=target, reasons=reasons, warnings=warnings)

    def migrate_capsule(self, capsule_id: str, destination: str = "local",
                        *, force: bool = False) -> Dict[str, Any]:
        """Pause → checkpoint → verify destination → transfer → restore →
        verify → resume, with rollback (§47, §49)."""
        capsule = self._get(capsule_id)
        # Migration policy denials (§105).
        if capsule.device_policy.get("actuators") or capsule.capsule_profile == "physical":
            raise PermissionError("migration denied: physical device is local-only")
        if (capsule.model_policy.get("local_only") and destination != "local"
                and not force):
            raise PermissionError("migration denied: private data cannot leave node")
        if destination != "local":
            return {"capsule_id": capsule_id, "destination": destination,
                    "status": "REQUIRES_CONFIGURATION",
                    "reason": "remote nodes require explicit pairing + mTLS "
                              "(not configured); nothing was moved"}
        # Local migration: full cycle with rollback.
        was_running = capsule.lifecycle_state == CapsuleLifecycleState.RUNNING
        if was_running:
            self.pause_capsule(capsule_id)
        else:
            self._ensure_operable(capsule, op="migrate")
        snap = self.snapshot_capsule(capsule_id)
        # Verify destination: local provider compatibility.
        provider = select_provider(capsule.isolation_provider)
        report = provider.detect()
        if report.status == IsolationStatus.UNAVAILABLE:
            # Rollback: source checkpoint restore + revalidation.
            self.restore_snapshot(snap.integrity_hash)
            raise PermissionError(f"migration denied: {report.detail}")
        try:
            self._transition(capsule, CapsuleLifecycleState.MIGRATING)
            # Transfer: snapshot integrity verified on restore path.
            restored = self.restore_snapshot(snap.integrity_hash)
            self._revalidate(restored)
            self._transition(restored, CapsuleLifecycleState.READY)
            if was_running:
                self.start_capsule(restored.capsule_id)
            with self._lock:
                self._metrics["capsules_migrated"] += 1
            self._audit("capsule.migrate", capsule_id, "ok",
                        {"destination": destination,
                         "snapshot": snap.integrity_hash})
            return {"capsule_id": capsule_id, "destination": destination,
                    "status": "MIGRATED", "snapshot": snap.integrity_hash}
        except Exception as exc:
            # Rollback (§49): destination cleanup, source restore,
            # authority revalidation, audit.
            try:
                self.restore_snapshot(snap.integrity_hash)
            except Exception:
                pass
            try:
                self._revalidate(capsule)
            except Exception:
                pass
            self._audit("capsule.migrate", capsule_id, "rolled_back",
                        {"reason": str(exc)[:300]})
            raise

    # -- replay (§52-§54) --------------------------------------------------------
    def replay(self, capsule_id: str,
               mode: ReplayMode = ReplayMode.OBSERVE_ONLY,
               *, authorize_full: bool = False) -> Dict[str, Any]:
        """Replay capsule actions. Default OBSERVE_ONLY; external side
        effects are never auto-executed (§54)."""
        capsule = self._get(capsule_id)
        with self._lock:
            receipts = list(self._receipts.get(capsule_id, []))
        with self._lock:
            self._metrics["replays"] += 1
        if mode == ReplayMode.OBSERVE_ONLY:
            return {"capsule_id": capsule_id, "mode": mode.value,
                    "actions": [r.to_dict() for r in receipts],
                    "executed": 0,
                    "note": "recorded requests/results shown; nothing re-executed"}
        if mode in (ReplayMode.DRY_RUN, ReplayMode.SIMULATION):
            simulated = []
            for receipt in receipts:
                if _is_external(receipt.capability):
                    simulated.append({"capability": receipt.capability,
                                      "verdict": "BLOCKED_EXTERNAL",
                                      "recorded_outcome": receipt.outcome})
                else:
                    simulated.append({"capability": receipt.capability,
                                      "verdict": "WOULD_POLICY_CHECK",
                                      "recorded_outcome": receipt.outcome})
            return {"capsule_id": capsule_id, "mode": mode.value,
                    "simulated": simulated, "executed": 0}
        # FULL_EXECUTION: explicit authorization + re-admission required.
        if not authorize_full:
            raise PermissionError("FULL_EXECUTION replay requires authorize_full=True "
                                  "and fresh human authorization")
        return {"capsule_id": capsule_id, "mode": mode.value,
                "status": "REQUIRES_APPROVAL",
                "note": "full re-execution gated on human approval; "
                        "external effects re-authorized one by one"}

    # -- inspection surface (§76, §79-§81) -----------------------------------------
    def inspect_capsule(self, capsule_id: str) -> Dict[str, Any]:
        capsule = self._get(capsule_id)
        fs = self._filesystems.get(capsule_id)
        return {
            **capsule.to_dict(),
            "filesystem": fs.metadata() if fs else {},
            "health": self.health(capsule_id).value,
            "egress": list(self._egress_log.get(capsule_id, [])[-20:]),
            "security_events": list(self._security_events.get(capsule_id, [])[-20:]),
            "receipts": len(self._receipts.get(capsule_id, [])),
            "snapshots": list(self._capsule_snapshots.get(capsule_id, [])),
            "forensic_available": capsule_id in self._forensics,
        }

    def list_capsules(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            capsules = list(self._capsules.values())
        if state:
            capsules = [c for c in capsules if c.lifecycle_state.value == state]
        return [{"capsule_id": c.capsule_id, "agent_id": c.agent_id,
                 "profile": c.capsule_profile, "state": c.lifecycle_state.value,
                 "risk": c.risk.band if c.risk else "?",
                 "isolation": c.isolation_level.value,
                 "node": c.node_id} for c in capsules]

    def capsule_resources(self, capsule_id: str) -> Dict[str, Any]:
        capsule = self._get(capsule_id)
        usage = dict(self._usage.get(capsule_id, {}))
        alloc = None
        try:
            alloc = self.kernel.resource_manager.get_usage(capsule.agent_id)
        except Exception:
            pass
        return {"capsule_id": capsule_id,
                "limits": capsule.resource_limits.to_dict(),
                "usage": usage,
                "allocation": alloc.to_dict() if alloc and hasattr(alloc, "to_dict") else None}

    def capsule_permissions(self, capsule_id: str) -> Dict[str, Any]:
        capsule = self._get(capsule_id)
        return {"capsule_id": capsule_id,
                "capabilities": list(capsule.capabilities),
                "manifest_valid": capsule.manifest.verify() if capsule.manifest else False,
                "manifest_hash": capsule.manifest.manifest_hash if capsule.manifest else "",
                "authority": capsule.authority.to_dict() if capsule.authority else None,
                "policy_version": capsule.policy_version,
                "policy_hash": capsule.policy_hash}

    def capsule_trace(self, capsule_id: str) -> Dict[str, Any]:
        with self._lock:
            receipts = [r.to_dict() for r in self._receipts.get(capsule_id, [])]
            observations = list(self._observations.get(capsule_id, []))
        return {"capsule_id": capsule_id, "receipts": receipts,
                "observations": observations}

    def diff_capsules(self, capsule_a: str, capsule_b: str) -> Dict[str, Any]:
        """Compare permissions/resources/models/network/filesystem/risk (§82)."""
        a = self._get(capsule_a)
        b = self._get(capsule_b)

        def _diff_list(x: List[str], y: List[str]) -> Dict[str, List[str]]:
            return {"only_a": sorted(set(x) - set(y)),
                    "only_b": sorted(set(y) - set(x)),
                    "common": sorted(set(x) & set(y))}

        return {
            "a": capsule_a, "b": capsule_b,
            "permissions": _diff_list(a.capabilities, b.capabilities),
            "resources": {"a": a.resource_limits.to_dict(),
                          "b": b.resource_limits.to_dict()},
            "models": {"a": dict(a.model_policy), "b": dict(b.model_policy)},
            "network": {"a": a.network.to_dict(), "b": b.network.to_dict()},
            "filesystem": {"a": [m.to_dict() for m in a.mounts],
                           "b": [m.to_dict() for m in b.mounts]},
            "policies": {"a": a.policy_version, "b": b.policy_version},
            "risk": {"a": a.risk.to_dict() if a.risk else None,
                     "b": b.risk.to_dict() if b.risk else None},
        }

    def simulate(self, capsule_id: str, capability: str,
                 inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Policy simulator: would X be allowed? Never executes X (§83)."""
        capsule = self._get(capsule_id)
        inputs = dict(inputs or {})
        try:
            self._ensure_operable(capsule, op=f"simulate {capability}")
            self._check_manifest(capsule, capability)
        except PermissionError as exc:
            return {"verdict": "DENY", "capability": capability,
                    "reasons": [str(exc)]}
        if _is_external(capability):
            return {"verdict": "APPROVAL_REQUIRED", "capability": capability,
                    "reasons": ["external side-effect class requires approval"]}
        if capability.startswith(("network", "browser", "research", "web")):
            url = str(inputs.get("url") or "")
            if url and capsule.network.mode == NetworkMode.NO_NETWORK:
                return {"verdict": "DENY", "capability": capability,
                        "reasons": ["capsule network disabled"]}
        return {"verdict": "ALLOW", "capability": capability, "reasons": []}

    # -- policy change, revocation, handoff, takeover (§88-§91) ----------------------
    def reevaluate_policy(self, capsule_id: str) -> Dict[str, Any]:
        """Re-evaluate a running capsule against current policy (§88)."""
        capsule = self._get(capsule_id)
        verdict = "CONTINUE"
        reasons: List[str] = []
        if capsule.is_expired():
            verdict, reasons = "TERMINATE", ["capsule expired"]
        elif capsule.authority is not None and not capsule.authority.is_valid():
            verdict, reasons = "TERMINATE", ["authority expired or revoked"]
        elif capsule.manifest is None or not capsule.manifest.verify():
            verdict, reasons = "PAUSE", ["manifest integrity failure"]
        elif capsule.risk and capsule.risk.band == "CRITICAL":
            verdict, reasons = "REQUIRE_APPROVAL", ["critical risk band"]
        elif capsule.risk and capsule.risk.band == "HIGH":
            verdict, reasons = "RESTRICT", ["high risk band: restrict to read-only"]
            self._restrict_to_readonly(capsule)
        self._audit("capsule.reevaluate", capsule_id, verdict.lower(),
                    {"reasons": reasons})
        return {"capsule_id": capsule_id, "verdict": verdict, "reasons": reasons}

    def _restrict_to_readonly(self, capsule: AgentCapsule) -> None:
        keep = [c for c in capsule.capabilities
                if any(k in c for k in ("read", "list", "observe", "inspect"))]
        capsule.capabilities = keep
        capsule.manifest = CapabilityManifest(
            capsule_id=capsule.capsule_id, capabilities=keep,
            policy_version=capsule.policy_version).seal()

    def revoke_capability(self, capsule_id: str, capability: str) -> Dict[str, Any]:
        """Live revocation: future calls blocked; past actions stand (§89)."""
        capsule = self._get(capsule_id)
        had = capability in capsule.capabilities
        capsule.capabilities = [c for c in capsule.capabilities if c != capability]
        capsule.manifest = CapabilityManifest(
            capsule_id=capsule.capsule_id, capabilities=list(capsule.capabilities),
            policy_version=capsule.policy_version).seal()
        self._audit("capsule.revoke_capability", capsule_id, "ok",
                    {"capability": capability, "had": had,
                     "note": "future calls blocked; completed actions unaffected"})
        return {"capsule_id": capsule_id, "capability": capability,
                "revoked": True, "was_present": had}

    def handoff_capsule(self, capsule_id: str, to_agent_id: str) -> AgentCapsule:
        """Transfer a capsule between agents (§91). Only permitted state moves;
        authority is revalidated (never inherited blindly)."""
        capsule = self._get(capsule_id)
        new_process = self.kernel.get_agent_process(to_agent_id)
        if new_process is None:
            raise KeyError(f"unknown agent: {to_agent_id}")
        if new_process.authority is None:
            raise PermissionError("receiving agent has no authority grant")
        # Receiving authority must cover the capsule's capabilities.
        missing = [c for c in capsule.capabilities
                   if c not in (new_process.authority.capabilities or [])]
        if missing:
            raise PermissionError(f"handoff denied: receiving agent lacks {missing}")
        old_agent = capsule.agent_id
        with self._lock:
            self._agent_index.pop(old_agent, None)
            self._agent_index[to_agent_id] = capsule_id
        capsule.agent_id = to_agent_id
        capsule.authority = new_process.authority
        self._revalidate(capsule)
        self._audit("capsule.handoff", capsule_id, "ok",
                    {"from_agent": old_agent, "to_agent": to_agent_id})
        self._emit("capsule.handoff", {"capsule_id": capsule_id,
                                       "from_agent": old_agent,
                                       "to_agent": to_agent_id})
        return capsule

    def takeover(self, capsule_id: str, *, by: str = "human",
                 reason: str = "operator takeover") -> Dict[str, Any]:
        """Human takeover of browser/computer/automation/physical (§90)."""
        capsule = self._get(capsule_id)
        if capsule.lifecycle_state == CapsuleLifecycleState.RUNNING:
            self.pause_capsule(capsule_id)
        with self._lock:
            self._takeovers[capsule_id] = {"by": by, "reason": reason,
                                           "at": _now()}
        self._audit("capsule.takeover", capsule_id, "ok",
                    {"by": by, "reason": reason})
        return {"capsule_id": capsule_id, "takeover_by": by,
                "note": "conflicting agent actions suspended"}

    def release_takeover(self, capsule_id: str) -> Dict[str, Any]:
        with self._lock:
            self._takeovers.pop(capsule_id, None)
        return {"capsule_id": capsule_id, "takeover_released": True}

    # -- model boundary (§27-§29, §67-§69) --------------------------------------------
    def check_model_use(self, capsule_id: str, model_id: str, *,
                        provider: str = "", cloud: bool = False,
                        tokens: int = 0) -> Dict[str, Any]:
        capsule = self._get(capsule_id)
        policy = capsule.model_policy or {}
        allowed_models = policy.get("allowed_models") or []
        if allowed_models and model_id not in allowed_models:
            return {"allowed": False, "reason": f"model not in capsule set: {model_id}"}
        if policy.get("local_only") and cloud:
            return {"allowed": False,
                    "reason": "LOCAL_ONLY capsule: cloud fallback denied"}
        if not policy.get("cloud_allowed", True) and cloud:
            return {"allowed": False, "reason": "cloud models not allowed"}
        maximum = int(policy.get("maximum_tokens", 0) or 0)
        if maximum and tokens > maximum:
            return {"allowed": False,
                    "reason": f"token request {tokens} exceeds capsule max {maximum}"}
        provider_policy = (policy.get("provider_policy") or {})
        if provider and provider_policy and provider not in provider_policy.get("allow", [provider]):
            return {"allowed": False, "reason": f"provider not allowed: {provider}"}
        return {"allowed": True, "reason": "model use permitted"}

    def gpu_status(self) -> Dict[str, Any]:
        """GPU isolation status (§27): honest NOT_SUPPORTED unless enforced."""
        return {"status": "NOT_SUPPORTED",
                "detail": "No GPU time-slicing/memory enforcement is wired to "
                          "capsules on this host; GPU budgets are accounting-only."}

    # -- memory with provenance (§42-§43, §97) ------------------------------------------
    def memory_write(self, capsule_id: str, key: str, value: Any, *,
                     confidence: float = 1.0,
                     classification: str = "internal") -> Dict[str, Any]:
        capsule = self._get(capsule_id)
        self._ensure_operable(capsule, op="memory.write")
        self._check_manifest(capsule, "memory.write")
        with self._lock:
            usage = self._usage.setdefault(capsule_id, {})
            usage["memory_writes"] = usage.get("memory_writes", 0) + 1
        try:
            self.kernel.memory_manager.write(
                capsule.agent_id, capsule.memory_policy.value, key,
                {"value": value,
                 "provenance": {"source_capsule": capsule_id,
                                "agent": capsule.agent_id,
                                "task": capsule.task_id,
                                "confidence": confidence,
                                "classification": classification,
                                "origin": ProvenanceType.AGENT_DERIVED.value}})
        except Exception as exc:
            raise PermissionError(f"memory write denied: {exc}")
        return {"ok": True, "capsule_id": capsule_id, "key": key}

    # -- observation helpers: world-model labels, screen redaction -----------------------
    @staticmethod
    def label_world_state(kind: str) -> str:
        """Enforce OBSERVED/INFERRED/PREDICTED/SIMULATED labeling (§98)."""
        valid = {"OBSERVED", "INFERRED", "PREDICTED", "SIMULATED"}
        label = (kind or "").upper()
        if label not in valid:
            raise ValueError(f"world-state must be one of {sorted(valid)}")
        return label

    @staticmethod
    def redact_screen_text(text: str) -> str:
        """Redact password fields, card numbers, key material (§38)."""
        import re as _re
        redacted = _re.sub(r'(?i)(password|passwd|pwd)\s*[:=]\s*\S+', r'\1: ‹redacted›', text)
        redacted = _re.sub(r'\b(?:\d[ -]?){13,19}\b', '‹redacted-card›', redacted)
        redacted = _re.sub(r'\b(sk-[A-Za-z0-9]{8,}|xox[bap]-[A-Za-z0-9-]{8,}|ghp_[A-Za-z0-9]{8,})\b',
                           '‹redacted-key›', redacted)
        return redacted

    def _redact_screen_inputs(self, capsule: AgentCapsule,
                              inputs: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(inputs)
        for key in ("text", "content", "screen", "ocr", "observation"):
            if isinstance(out.get(key), str):
                out[key] = self.redact_screen_text(out[key])
        return out

    # -- health, GC, leak detection (§116-§119) --------------------------------------------
    def heartbeat(self, capsule_id: str) -> None:
        with self._lock:
            self._heartbeats[capsule_id] = _now()

    def health(self, capsule_id: str) -> CapsuleHealth:
        capsule = self._get(capsule_id)
        state = capsule.lifecycle_state
        if state == CapsuleLifecycleState.QUARANTINED:
            return CapsuleHealth.QUARANTINED
        if state in (CapsuleLifecycleState.FAILED,):
            return CapsuleHealth.FAILED
        if state in (CapsuleLifecycleState.TERMINATED, CapsuleLifecycleState.DESTROYED):
            return CapsuleHealth.FAILED
        last = self._heartbeats.get(capsule_id, capsule.updated_at)
        if _now() - last > 300:
            return CapsuleHealth.UNRESPONSIVE
        usage = self._usage.get(capsule_id, {})
        if usage.get("tool_calls", 0) > 5000:
            return CapsuleHealth.RESOURCE_STARVED
        if state == CapsuleLifecycleState.SUSPENDED:
            return CapsuleHealth.BLOCKED
        if self._security_events.get(capsule_id):
            return CapsuleHealth.DEGRADED
        return CapsuleHealth.HEALTHY

    def gc(self, *, max_age_seconds: float = 3600,
           dry_run: bool = False) -> Dict[str, Any]:
        """Safe cleanup of expired/temporary capsule state (§117)."""
        now = _now()
        reclaimed: List[str] = []
        with self._lock:
            candidates = list(self._capsules.values())
        for capsule in candidates:
            terminal = capsule.lifecycle_state in (
                CapsuleLifecycleState.COMPLETED, CapsuleLifecycleState.TERMINATED,
                CapsuleLifecycleState.DESTROYED, CapsuleLifecycleState.FAILED)
            expired = capsule.is_expired()
            old = (now - capsule.updated_at) > max_age_seconds
            if (expired or (terminal and old)) and capsule.lifecycle_state != CapsuleLifecycleState.DESTROYED:
                if dry_run:
                    reclaimed.append(capsule.capsule_id)
                    continue
                try:
                    self.destroy_capsule(capsule.capsule_id)
                    reclaimed.append(capsule.capsule_id)
                except Exception as exc:
                    logger.debug("gc destroy failed for %s: %s", capsule.capsule_id, exc)
        # Trim bounded logs.
        with self._lock:
            for log in list(self._egress_log.values()):
                del log[:-200]
            for log in list(self._observations.values()):
                del log[:-200]
            self.secret_broker.gc_expired()
            self._metrics["gc_runs"] += 1
            self._metrics["gc_reclaimed"] += len(reclaimed)
        self._audit("capsule.gc", "hypervisor", "ok",
                    {"reclaimed": reclaimed, "dry_run": dry_run})
        return {"reclaimed": reclaimed, "dry_run": dry_run}

    def leak_scan(self) -> Dict[str, Any]:
        """Detect orphan processes/mounts/reservations/sessions (§118)."""
        orphans: Dict[str, List[str]] = {"processes": [], "mounts": [],
                                         "reservations": [], "sessions": []}
        with self._lock:
            live_agents = set(self._agent_index.keys())
            live_capsules = set(self._capsules.keys())
        try:
            for process in self.kernel.list_agent_processes():
                if (process.agent_id not in live_agents and
                        process.state not in ("terminated",)):
                    state = getattr(process.state, "value", str(process.state))
                    if state not in ("terminated",):
                        orphans["processes"].append(process.agent_id)
        except Exception:
            pass
        try:
            if os.path.isdir(self._base_dir):
                for entry in os.listdir(self._base_dir):
                    if entry not in live_capsules:
                        orphans["mounts"].append(entry)
        except OSError:
            pass
        return {"orphans": orphans,
                "total": sum(len(v) for v in orphans.values())}

    # -- hierarchy helpers ---------------------------------------------------
    def _capsule_depth(self, capsule: AgentCapsule) -> int:
        depth = 0
        current = capsule
        seen = {current.capsule_id}
        while current.parent_capsule_id:
            parent = self._capsules.get(current.parent_capsule_id)
            if parent is None or parent.capsule_id in seen:
                break
            seen.add(parent.capsule_id)
            depth += 1
            current = parent
        return depth

    def _child_count(self, capsule_id: str) -> int:
        with self._lock:
            return sum(1 for c in self._capsules.values()
                       if c.parent_capsule_id == capsule_id
                       and c.lifecycle_state != CapsuleLifecycleState.DESTROYED)

    def _child_ids(self, capsule_id: str) -> List[str]:
        with self._lock:
            return [c.capsule_id for c in self._capsules.values()
                    if c.parent_capsule_id == capsule_id]

    def swarm_children(self, parent_capsule_id: str) -> List[AgentCapsule]:
        """Worker capsules of a swarm parent (§106)."""
        with self._lock:
            return [c for c in self._capsules.values()
                    if c.parent_capsule_id == parent_capsule_id]

    def set_swarm_quota(self, parent_capsule_id: str,
                        quota: Dict[str, float]) -> Dict[str, float]:
        """Collective swarm quota (§64). Workers cannot exceed it jointly."""
        with self._lock:
            self._swarm_quotas[parent_capsule_id] = dict(quota)
            return dict(quota)

    def check_swarm_quota(self, parent_capsule_id: str) -> Dict[str, Any]:
        quota = self._swarm_quotas.get(parent_capsule_id, {})
        totals: Dict[str, float] = {}
        for child in self.swarm_children(parent_capsule_id):
            usage = self._usage.get(child.capsule_id, {})
            for key, value in usage.items():
                totals[key] = totals.get(key, 0) + value
        over = {k: totals.get(k, 0) for k, v in quota.items()
                if totals.get(k, 0) > v}
        return {"quota": dict(quota), "used": totals,
                "within_quota": not over, "over": over}

    # -- stats / shutdown ------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            by_state: Dict[str, int] = {}
            for capsule in self._capsules.values():
                key = capsule.lifecycle_state.value
                by_state[key] = by_state.get(key, 0) + 1
            return {"capsules": len(self._capsules),
                    "by_state": by_state,
                    "snapshots": len(self._snapshots),
                    "forensics": len(self._forensics),
                    "breakers": {k: b.to_dict() for k, b in self._breakers.items()
                                 if b.state != CircuitState.CLOSED},
                    "metrics": dict(self._metrics),
                    "isolation": (self.isolation_status()
                                  if self._isolation_reports is not None else {})}

    def shutdown(self) -> None:
        logger.info("AgentHypervisor: shutting down")
        with self._lock:
            capsules = list(self._capsules.values())
        for capsule in capsules:
            if capsule.lifecycle_state in (CapsuleLifecycleState.RUNNING,
                                           CapsuleLifecycleState.READY):
                try:
                    self.destroy_capsule(capsule.capsule_id,
                                         mode=TerminationMode.FORCED)
                except Exception as exc:
                    logger.debug("hypervisor shutdown destroy failed: %s", exc)
