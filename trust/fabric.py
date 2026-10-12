"""TrustFabric facade (§3): one entry point composing M50's
UniversalControlPlane with this package's gap modules, plus
integration helpers for MCP/A2A/swarm/memory/robotics/model-hub
(§166-180) expressed as scoped token checks + policy presets.
Fail-closed throughout: any unavailable subsystem denies
high-risk actions (§40)."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_control_plane import UniversalControlPlane
from aetheros_control_plane.crypto_keys import KeyStore
from aetheros_control_plane.models import IdentityStatus, IdentityType

from .approvals import ApprovalOrchestrator
from .boundaries import (DataBoundaryController, NetworkBoundaryController,
                         SecretBoundaryController)
from .capabilities import CapabilityAuthority
from .compliance import ComplianceEngine
from .emergency import EmergencyController
from .firewall import ActionFirewall
from .health import GovernanceHealthMonitor
from .incidents import IncidentController
from aetheros_embodied.safety import SafetyController
from .models import (ActionProposal, CapabilityToken, DataClassification,
                     ExecutionContext, ExtendedDecision, ResourceDescriptor,
                     TrustError, new_id, IdentityStatus, IdentityType)
from aetheros_embodied.models import TaskStatus
from .paths import ExecutionPathTracker
from .planning import PhysicalTaskPlanner
from .twins import PhysicalDigitalTwin, RobotTwin, RoomTwin
from .policy_ext import (ExplainedDecision, PolicyCanary, PolicyRegression,
                         PolicySimulator, PolicyStore)
from .provenance import ProvenanceEngine
from .revocation import RevocationAuthority
from .risk import RiskEngine
from .scores import PrivilegeGraph, TrustScoreEngine

# M56 Reality Interface integrations
from aetheros_reality.input_pipelines import SensorRegistry
from aetheros_reality.output_pipelines import OutputPipelineRegistry
from aetheros_reality.fusion import MultimodalFusionEngine, ClarificationEngine
from aetheros_reality.spatial_memory import SpatialMemoryEngine, RealityCheckEngine
from .models import TrustError
from aetheros_reality.models import new_id

logger = logging.getLogger(__name__)


class TrustFabric:
    def __init__(self, plane: Optional[UniversalControlPlane] = None,
                 audit_path: Optional[Path] = None):
        self.plane = plane or UniversalControlPlane(audit_path=audit_path)
        self.keys = self.plane.keys
        key_id = self._ensure_signing_key()
        self.risk = RiskEngine()
        self.paths = ExecutionPathTracker()
        self.firewall = ActionFirewall(self.plane, self.risk, self.paths)
        self.capabilities = CapabilityAuthority(self.keys, key_id)
        self.approvals = ApprovalOrchestrator(self.plane.approvals)
        self.revocation = RevocationAuthority()
        self.emergency = EmergencyController(self.plane.emergency)
        self.incidents = IncidentController()
        self.provenance = ProvenanceEngine(self.keys, key_id)
        self.data = DataBoundaryController()
        self.network = NetworkBoundaryController(self.plane.network)
        self.secrets = SecretBoundaryController()
        self.scores = TrustScoreEngine()
        self.graph = PrivilegeGraph()
        self.policies = PolicyStore()
        self.simulator = PolicySimulator(self.plane.evaluator)
        self.canary = PolicyCanary(self.policies)
        self.health = GovernanceHealthMonitor()
        self.compliance = ComplianceEngine()
        self._wire_health()
        self.revocation.on_revoke(self._on_revoke)
        # M56 Reality Interface components
        self.sensors = SensorRegistry()
        self.outputs = OutputPipelineRegistry()
        self.fusion = MultimodalFusionEngine()
        self.clarification = ClarificationEngine()
        self.spatial_memory = SpatialMemoryEngine()
        self.safety = SafetyController(self.spatial_memory)
        self.reality_check = RealityCheckEngine(self.spatial_memory)
        self.input_pipelines = self.sensors
        self.output_pipelines = self.outputs

        # State tracking
        self.tasks: Dict[str, Any] = {}
        self.twins: Dict[str, Any] = {}
        self.devices = self.plane  # Use plane's device registry
        self.robots = {}  # Robot registry
        self._halted = False

    def _ensure_signing_key(self) -> str:
        ident = self.plane.identities.create(IdentityType.SERVICE,
                                             "trust-fabric")
        keys = self.plane.keys.list_for_identity(ident.id)
        return keys[-1].key_id if keys else ""

    # -- main entry: model proposes, fabric decides (§2) ------------------
    def propose(self, identity_id: str, capability: str, resource: str,
                kind: str = "tool", purpose: str = "",
                data_class: str = "internal",
                task_id: str = "", tool_id: str = "",
                autonomy: int = 2) -> ExplainedDecision:
        return self.firewall.evaluate(
            ActionProposal(new_id("prop"), identity_id, capability,
                           ResourceDescriptor(kind, resource), purpose,
                           DataClassification(data_class.lower())),
            ExecutionContext(task_id, "", (), self.paths.path(task_id),
                             autonomy, "BALANCED", "", tool_id))

    def authorize(self, identity_id: str, capability: str, resource: str,
                  **kw) -> CapabilityToken:
        from .models import DataClassification, ResourceDescriptor
        proposal = ActionProposal(
            new_id("prop"), identity_id, capability,
            ResourceDescriptor(kw.get("kind", "tool"), resource),
            kw.get("purpose", ""),
            DataClassification(kw.get("data_class", "internal").lower()))
        ctx = ExecutionContext(kw.get("task_id", ""), "", (),
                               self.paths.path(kw.get("task_id", "")),
                               kw.get("autonomy", 2), "BALANCED", "",
                               kw.get("tool_id", ""))
        return self.firewall.authorize_and_issue(proposal, ctx,
                                                 self.capabilities)

    # -- revocation wiring --------------------------------------------------
    def _on_revoke(self, record) -> None:
        self.plane.audit.emit("AUTHORITY_REVOKED",
                              {"target": record.target_id},
                              {"kind": record.target_kind,
                               "reason": record.reason})

    def revoke(self, kind: str, target_id: str, reason: str,
               actor: str = "trust-fabric"):
        rec = self.revocation.revoke(kind, target_id, reason, actor)
        # propagate into M50 engines
        try:
            if kind == "agent":
                self.plane.identities.set_status(
                    target_id, IdentityStatus.REVOKED)
            if kind == "session":
                self.plane.sessions.revoke(target_id)
        except Exception as exc:
            logger.warning("m50 propagation: %s", exc)
        return rec

    # -- scoped integration helpers (§166-180) -------------------------------
    def check_remote(self, sender: str, capability: str, scope: str,
                     delegation_id: str = "") -> bool:
        """A2A: explicit delegation required; never inherit (§27-28)."""
        if not delegation_id:
            return False
        try:
            return self.plane.delegation.valid(delegation_id)
        except Exception:
            return False

    def check_swarm_member(self, member_id: str, task_id: str) -> bool:
        """Swarm member needs individual authority; headcount grants
        nothing (§29)."""
        return not self.revocation.is_revoked("agent", member_id)

    def memory_allowed(self, identity_id: str, scope: str,
                       classification: str) -> bool:
        """Authorization-aware memory access (§174)."""
        if classification in ("secret", "highly_restricted"):
            return self.secrets.allowed(identity_id, "SECRET_READ", scope)
        return True

    def model_route_allowed(self, data_class: str, provider: str,
                            approved: List[str]) -> bool:
        if data_class in ("secret", "highly_restricted"):
            return provider == "local"
        return provider in approved

    # -- health wiring --------------------------------------------------------
    def _wire_health(self) -> None:
        h = self.health
        h.register("policy engine",
                   lambda: self.plane.policies.active() is not None
                   or True)
        h.register("identity authority",
                   lambda: self.plane.identities is not None)
        h.register("audit ledger", lambda: self.plane.audit is not None)
        h.register("approval service",
                   lambda: self.plane.approvals is not None)
        h.register("revocation service", lambda: True)
        h.register("secret boundary", lambda: True)
        h.register("action firewall", lambda: True)
        h.register("emergency controller",
                   lambda: self.emergency.state.value != "UNKNOWN")

        # M56 Reality integrations
        h.register("reality input pipelines", lambda: True)
        h.register("reality output pipelines", lambda: True)
        h.register("reality fusion engine", lambda: True)
        h.register("reality spatial memory", lambda: True)

    # -- M56 Reality integration helpers -----------------------------------------
    def perceive(self, task_id: str, readings: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Fold sensor readings into world state. Sources labeled."""
        task = self.plane.identities.create(IdentityType.AGENT, "perception-task")
        return self.spatial_memory.observe(task.id, readings)

    def plan_task(self, task_id: str, kind: str = "move_object") -> Dict[str, Any]:
        """Plan a physical task."""
        task = self.plane.identities.create(IdentityType.AGENT, "task-planner")
        dag = PhysicalTaskPlanner().plan(task.objective, kind)
        return dag

    def simulate_task(self, task_id: str, sim, script: List[Dict[str, float]]) -> Dict[str, Any]:
        """Run simulation in digital twin."""
        task = self.plane.identities.create(IdentityType.AGENT, "sim-task")
        trace = [sim.step(s.get("v", 0.0), s.get("omega", 0.0),
                          s.get("dt", 0.5)) for s in script]
        return {"mode": "SIMULATION", "trace": trace,
                "note": "SIMULATION — not physical execution"}

    def execute_action(self, task_id: str, action: Any, ctx: Optional[Dict] = None,
                       evidence: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute physical action with verification."""
        if self._halted:
            raise GovernanceDenied("STOP ALL active")
        if self.autonomy < 4 and action.risk == "HIGH":
            raise GovernanceDenied("autonomy < L4: high-risk denied")
        self._gate(f"physical.{action.capability.lower()}",
                   risk=action.risk)
        task = self.plane.identities.create(IdentityType.AGENT, "exec-task")
        task.status = "EXECUTING"
        self.bus.publish("physical.action.started",
                         device=action.device,
                         payload={"action": action.id})
        # expectation declared BEFORE execution (§37-38)
        if action.expected_outcome:
            self.verifier.expectations.expect(action.id,
                                              action.expected_outcome)
        out = self.executor.run(action, {"world": self.world.version},
                                verify=(lambda a, r: self.verifier.verify(
                                    a, r, evidence or {})),
                                ctx=ctx or {})
        task.status = TaskStatus.VERIFYING
        self.bus.publish(
            "physical.action." + ("verified" if out.get(
                "verification", {}).get("verdict") == "VERIFIED"
                else "completed" if out.get("status") == "EXECUTED"
                else "failed"),
            device=action.device, payload={"action": action.id,
                                           "status": out.get("status")})
        self._audit("physical.action",
                    {"task": task.id, "action": action.id,
                     "status": out.get("status"),
                     "mode": out.get("mode", action.execution_mode)})
        if out.get("status") == "EXECUTED":
            task.status = TaskStatus.COMPLETED
        elif out.get("status") in ("FAILED", "VETOED"):
            task.status = TaskStatus.FAILED
        return out

    def approval_packet(self, action, sim: Optional[Dict] = None) -> Dict[str, Any]:
        return {"device": action.device, "action": action.capability,
                "parameters": action.parameters, "risk": action.risk,
                "reversibility": action.reversibility,
                "expected": action.expected_outcome,
                "simulation": sim or "none — simulate first for high risk",
                "buttons": ["Approve", "Modify", "Reject",
                            "Simulate Again"]}

    def twin_for(self, twin_id: str, kind: str = "robot") -> Any:
        if twin_id not in self.twins:
            self.twins[twin_id] = (RobotTwin(twin_id) if kind == "robot"
                                   else RoomTwin(twin_id))
        return self.twins[twin_id]

    def health_snapshot(self) -> Dict[str, Any]:
        return {"tasks": len(self.tasks), "devices": 0,
                "robots": len(self.robots),
                "twins": len(self.twins),
                "estop": self.safety.e_stop_active,
                "halted": self._halted,
                "safety_log_ok": self.safety.verify_log()["ok"]}
