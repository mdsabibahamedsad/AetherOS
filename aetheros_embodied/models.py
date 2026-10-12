"""Master 54 core models: tasks, world state, devices, robots,
sensors, actions, telemetry, incidents, skills. Every physical-world
datum carries value/timestamp/source/confidence/freshness/mode."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _now() -> float:
    return time.time()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ExecMode:
    HARDWARE_UNAVAILABLE = "HARDWARE_UNAVAILABLE"
    SIMULATION = "SIMULATION"
    REPLAY = "REPLAY"
    LIVE_HARDWARE = "LIVE_HARDWARE"


class TaskStatus:
    CREATED = "CREATED"
    OBSERVING = "OBSERVING"
    MODELING = "MODELING"
    SIMULATING = "SIMULATING"
    PLANNING = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class Permission:
    READ_ONLY = "READ_ONLY"
    OBSERVE = "OBSERVE"
    SIMULATE = "SIMULATE"
    LOW_RISK_ACTION = "LOW_RISK_ACTION"
    CONTROLLED_ACTION = "CONTROLLED_ACTION"
    HIGH_RISK_ACTION = "HIGH_RISK_ACTION"
    PHYSICAL_EXPERIMENT = "PHYSICAL_EXPERIMENT"


@dataclass
class StateVar:
    """One physical-world variable. Never a bare float."""
    value: Any = None
    timestamp: float = field(default_factory=_now)
    source: str = "unknown"  # sensor | camera | manual | human | simulation | memory
    confidence: float = 0.0
    freshness_s: float = 0.0  # max acceptable age; 0 = no constraint
    mode: str = ExecMode.SIMULATION  # OBSERVED | INFERRED | PREDICTED | SIMULATED | REPLAYED | UNKNOWN
    unit: str = ""

    def age(self, at: Optional[float] = None) -> float:
        return (at or _now()) - self.timestamp

    def is_fresh(self, at: Optional[float] = None) -> bool:
        if not self.freshness_s:
            return True
        return self.age(at) <= self.freshness_s


@dataclass
class PhysicalWorldState:
    id: str = field(default_factory=lambda: new_id("pws"))
    environment: str = ""
    rooms: Dict[str, Any] = field(default_factory=dict)
    surfaces: Dict[str, Any] = field(default_factory=dict)
    objects: Dict[str, Dict[str, StateVar]] = field(default_factory=dict)
    robots: Dict[str, Dict[str, StateVar]] = field(default_factory=dict)
    devices: Dict[str, Dict[str, StateVar]] = field(default_factory=dict)
    people: Dict[str, Dict[str, StateVar]] = field(default_factory=dict)
    hazards: List[str] = field(default_factory=list)
    connectivity: Dict[str, str] = field(default_factory=dict)
    power: Dict[str, Any] = field(default_factory=dict)
    environmental: Dict[str, StateVar] = field(default_factory=dict)
    uncertainties: Dict[str, float] = field(default_factory=dict)
    version: int = 1
    updated_at: float = field(default_factory=_now)


@dataclass
class EmbodiedTask:
    id: str = field(default_factory=lambda: new_id("emb"))
    objective: str = ""
    environment: str = ""
    entities: List[str] = field(default_factory=list)
    devices: List[str] = field(default_factory=list)
    robots: List[str] = field(default_factory=list)
    sensors: List[str] = field(default_factory=list)
    actuators: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=lambda: [Permission.OBSERVE])
    risk_level: str = "LOW"
    autonomy_level: int = 1
    simulation_required: bool = True
    approval_required: bool = False
    execution_mode: str = ExecMode.SIMULATION
    deadline: Optional[float] = None
    budget: Dict[str, float] = field(default_factory=dict)
    energy_budget_j: float = 0.0
    status: str = TaskStatus.CREATED
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)


@dataclass
class DeviceCapability:
    name: str = ""
    risk: str = "LOW"
    required_permission: str = Permission.OBSERVE
    input_schema: Dict[str, str] = field(default_factory=dict)
    output_schema: Dict[str, str] = field(default_factory=dict)
    limits: Dict[str, float] = field(default_factory=dict)
    verification_method: str = "telemetry"  # sensor|camera|telemetry|state_change|ack


@dataclass
class PhysicalDevice:
    id: str = field(default_factory=lambda: new_id("dev"))
    kind: str = ""  # camera | lidar | imu | robotic_arm | ...
    manufacturer: str = ""
    model: str = ""
    firmware: str = ""
    protocol: str = ""
    network: str = ""
    location: str = ""
    capabilities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=lambda: [Permission.OBSERVE])
    safety_limits: Dict[str, float] = field(default_factory=dict)
    calibration_id: str = ""
    health: str = "unknown"  # online | offline | degraded | fault | maintenance | unknown
    trust: str = "UNTRUSTED_DEVICE"
    locked_by_human: bool = False
    maintenance: bool = False


@dataclass
class Robot:
    id: str = field(default_factory=lambda: new_id("rob"))
    type: str = ""  # arm | mobile | humanoid | drone | lab | ...
    manufacturer: str = ""
    model: str = ""
    firmware: str = ""
    capabilities: List[str] = field(default_factory=list)
    joints: int = 0
    end_effectors: List[str] = field(default_factory=list)
    sensors: List[str] = field(default_factory=list)
    workspace: Dict[str, float] = field(default_factory=dict)
    safety_limits: Dict[str, float] = field(default_factory=dict)
    pose: Dict[str, float] = field(default_factory=dict)
    state: str = "idle"
    battery_pct: float = 100.0
    health: str = "unknown"
    trust: str = "UNTRUSTED_DEVICE"
    e_stop: bool = False


@dataclass
class PhysicalAction:
    id: str = field(default_factory=lambda: new_id("pact"))
    actor: str = ""
    device: str = ""
    capability: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    expected_outcome: Dict[str, Any] = field(default_factory=dict)
    risk: str = "LOW"
    reversibility: str = "reversible"
    simulation_result: Optional[str] = None
    approval: str = "none"  # none | pending | approved | rejected
    execution_mode: str = ExecMode.SIMULATION
    verification: str = "UNVERIFIED"
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    created_at: float = field(default_factory=_now)


@dataclass
class TelemetryEvent:
    at: float = field(default_factory=_now)
    kind: str = ""
    device: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    mode: str = ExecMode.SIMULATION
    seq: int = 0


@dataclass
class PhysicalIncident:
    id: str = field(default_factory=lambda: new_id("inc"))
    type: str = ""  # collision|nearMiss|unexpectedMotion|sensorFailure|...
    severity: str = "LOW"
    device: str = ""
    location: str = ""
    cause: str = ""
    response: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    at: float = field(default_factory=_now)
