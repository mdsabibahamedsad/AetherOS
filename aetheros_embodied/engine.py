"""EmbodiedIntelligenceEngine facade: the full loop
PERCEIVE->...->LEARN with safety gates, budgets, checkpoints,
recovery, approvals, and Master 50/52/53 integration. Defaults to
SIMULATION; LIVE_HARDWARE only via authorized adapters."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import memory as _mem  # noqa: F401  (package anchor for tooling)
from .execution import ActionExecutor, PhysicalAdapter, SimulatedRobotAdapter
from .lab import LabAutomationEngine
from .memory import PhysicalMemory
from .models import (EmbodiedTask, ExecMode, Permission, PhysicalAction,
                     PhysicalWorldState, StateVar, TaskStatus, new_id)
from .planning import MotionPlanner, PhysicalTaskPlanner
from .registries import (ActuatorRegistry, CapabilityRegistry,
                         CredentialBroker, PhysicalDeviceRegistry,
                         RobotRegistry)
from .safety import SafetyController
from .security import DeviceSecurityController
from .sensors import SensorFusionEngine
from .simulation import KinematicSimulator, SimToRealTracker
from .spatial import CollisionChecker, MappingEngine, SpatialWorldModel
from .telemetry import ClockModel, EventBus, HealthMonitor
from .twins import PhysicalDigitalTwin, RobotTwin, RoomTwin
from .verification import ActionVerifier

logger = logging.getLogger(__name__)


class EmbodiedDenied(Exception):
    pass


class EmbodiedIntelligenceEngine:
    def __init__(self, home: Path, plane: Any = None,
                 autonomy: int = 1, tenant: str = "default") -> None:
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.plane = plane
        self.autonomy = autonomy
        self.tenant = tenant
        self.broker = CredentialBroker()
        self.devices = PhysicalDeviceRegistry(self.broker)
        self.robots = RobotRegistry(self.broker)
        self.actuators = ActuatorRegistry()
        self.capabilities = CapabilityRegistry()
        self.fusion = SensorFusionEngine()
        self.spatial = SpatialWorldModel()
        self.mapping = MappingEngine()
        self.safety = SafetyController(self.spatial, plane)
        self.executor = ActionExecutor(self.safety, SimulatedRobotAdapter())
        self.verifier = ActionVerifier()
        self.bus = EventBus()
        self.clock = ClockModel()
        self.health = HealthMonitor()
        self.security = DeviceSecurityController()
        self.memory = PhysicalMemory()
        self.lab = LabAutomationEngine()
        self.twins: Dict[str, PhysicalDigitalTwin] = {}
        self.sim2real = SimToRealTracker()
        self.tasks: Dict[str, EmbodiedTask] = {}
        self.world = PhysicalWorldState()
        self._halted = False
        self._identity_id: Optional[str] = None
        self._ensure_identity()
        if plane is not None:
            try:
                plane.emergency.on_stop(lambda _s: self.stop_all())
            except Exception:
                pass

    # -- governance ------------------------------------------------------
    def _audit(self, typ: str, data: Dict[str, Any]) -> None:
        if self.plane is not None:
            try:
                self.plane.audit.emit(typ, {"tenant": self.tenant}, data)
                return
            except Exception as exc:
                logger.warning("audit emit failed: %s", exc)
        logger.info("embodied audit %s %s", typ, data)

    def _gate(self, capability: str, risk: str = "LOW") -> None:
        if self.plane is None:
            if risk == "HIGH":
                raise EmbodiedDenied(
                    "no control plane: high-risk physical action denied")
            return
        try:
            from aetheros_control_plane.models import ActionManifest
            manifest = ActionManifest(
                task_id="embodied", agent_id="embodied-engine",
                identity_id=self._identity_id or "embodied-engine",
                capabilities=[capability],
                scopes=[capability], resources=["physical"])
            gate = self.plane.check(manifest)
            if not gate.allowed:
                raise EmbodiedDenied("; ".join(gate.reasons))
        except EmbodiedDenied:
            raise
        except Exception as exc:
            raise EmbodiedDenied(f"control-plane error: {exc}")

    def _ensure_identity(self) -> None:
        """Provision the engine's service identity + declared scopes.
        Install-time provisioning, audited. Trust/policy decisions stay
        with the plane administrator."""
        if self.plane is None or self._identity_id:
            return
        try:
            from aetheros_control_plane.models import IdentityType
            existing = [i for i in self.plane.identities.list()
                        if i.display_name == "embodied-engine"]
            if existing:
                self._identity_id = existing[0].id
                return
            ident = self.plane.identities.create(
                IdentityType.SERVICE, "embodied-engine",
                capabilities=["physical.move", "physical.rotate",
                              "physical.read", "physical.measure",
                              "physical.simulate"],
                scopes=["physical.move", "physical.rotate",
                        "physical.read", "physical.measure",
                        "physical.simulate"])
            self._identity_id = ident.id
            self.plane.audit.emit(
                "embodied.identity.provisioned", {"tenant": self.tenant},
                {"identity": ident.id,
                 "note": "service identity; trust not self-granted"})
        except Exception as exc:
            logger.warning("identity provisioning failed: %s", exc)

    def stop_all(self, reason: str = "STOP ALL") -> None:
        self._halted = True
        self.safety.emergency_stop(reason, actor="embodied-engine")
        for t in self.tasks.values():
            if t.status in (TaskStatus.EXECUTING, TaskStatus.PLANNING,
                            TaskStatus.SIMULATING):
                t.status = TaskStatus.CANCELLED
        self._audit("physical.stopped_all", {"reason": reason})

    # -- task loop ---------------------------------------------------------
    def create_task(self, objective: str, **kw: Any) -> EmbodiedTask:
        t = EmbodiedTask(objective=objective, **kw)
        self.tasks[t.id] = t
        self.bus.publish("physical.task.started", payload={"task": t.id})
        return t

    def observe(self, task: EmbodiedTask,
                readings: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Fold sensor readings into world state. Sources labeled."""
        task.status = TaskStatus.OBSERVING
        for name, r in readings.items():
            self.world.devices.setdefault(name, {})["last"] = StateVar(
                value=r.get("value"), source=r.get("source", "sensor"),
                confidence=r.get("confidence", 0.0),
                mode=r.get("mode", "OBSERVED"), unit=r.get("unit", ""))
        task.status = TaskStatus.MODELING
        self.world.version += 1
        return {"entities": len(self.world.devices),
                "version": self.world.version}

    def plan_task(self, task: EmbodiedTask,
                  kind: str = "move_object") -> Dict[str, Any]:
        task.status = TaskStatus.PLANNING
        dag = PhysicalTaskPlanner().plan(task.objective, kind)
        self.bus.publish("physical.task.planned",
                         payload={"task": task.id})
        return dag

    def simulate_task(self, task: EmbodiedTask,
                      sim: KinematicSimulator,
                      script: List[Dict[str, float]]) -> Dict[str, Any]:
        task.status = TaskStatus.SIMULATING
        trace = [sim.step(s.get("v", 0.0), s.get("omega", 0.0),
                          s.get("dt", 1.0)) for s in script]
        return {"mode": ExecMode.SIMULATION, "trace": trace,
                "note": "SIMULATION — not physical execution"}

    def execute_action(self, task: EmbodiedTask, action: PhysicalAction,
                       ctx: Optional[Dict[str, Any]] = None,
                       evidence: Optional[Dict[str, Any]] = None
                       ) -> Dict[str, Any]:
        if self._halted:
            raise EmbodiedDenied("STOP ALL active")
        if self.autonomy < 4 and action.risk == "HIGH":
            raise EmbodiedDenied("autonomy < L4: high-risk denied")
        self._gate(f"physical.{action.capability.lower()}",
                   risk=action.risk)
        task.status = TaskStatus.EXECUTING
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

    def approval_packet(self, action: PhysicalAction,
                        sim: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"device": action.device, "action": action.capability,
                "parameters": action.parameters, "risk": action.risk,
                "reversibility": action.reversibility,
                "expected": action.expected_outcome,
                "simulation": sim or "none — simulate first for high risk",
                "buttons": ["Approve", "Modify", "Reject",
                            "Simulate Again"]}

    def twin_for(self, twin_id: str, kind: str = "robot") -> PhysicalDigitalTwin:
        if twin_id not in self.twins:
            self.twins[twin_id] = (RobotTwin(twin_id) if kind == "robot"
                                   else RoomTwin(twin_id))
        return self.twins[twin_id]

    def health_snapshot(self) -> Dict[str, Any]:
        return {"tasks": len(self.tasks), "devices": len(self.devices.devices),
                "robots": len(self.robots.robots),
                "twins": len(self.twins),
                "estop": self.safety.e_stop_active,
                "halted": self._halted,
                "safety_log_ok": self.safety.verify_log()["ok"]}
