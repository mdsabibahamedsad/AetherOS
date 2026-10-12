"""Digital Twins (§54-63): RobotTwin, RoomTwin, RepositoryTwin, etc."""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_cognitive.twins import DigitalTwin as _BaseDigitalTwin


class TwinDriftEvent(Exception):
    pass


class PhysicalDigitalTwin(_BaseDigitalTwin):
    kind = "physical"

    def __init__(self, twin_id: str, mode: str = "SIMULATION") -> None:
        super().__init__(mode)
        self.twin_id = twin_id
        self.state: Dict[str, Any] = {}
        self.last_sync: float = 0.0
        self.sync_latency_s: float = 0.0
        self.drift_events: List[Dict[str, Any]] = []

    def sync(self, real: Dict[str, Any], confidence: float = 1.0) -> Dict[str, Any]:
        t0 = time.time()
        self.state = copy.deepcopy(real)
        self.last_sync = time.time()
        self.sync_latency_s = self.last_sync - t0
        return {"twin": self.twin_id, "synced_at": self.last_sync,
                "latency_s": self.sync_latency_s, "confidence": confidence}

    def predict(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return {"twin": self.twin_id, "action": action.get("type", "?"),
                "predicted": "see subclass", "note": "PREDICTION, not observation"}

    def check_drift(self, real: Dict[str, Any], tolerance: float = 0.05) -> Dict[str, Any]:
        diffs = {}
        for k, v in real.items():
            old = self.state.get(k)
            if isinstance(v, (int, float)) and isinstance(old, (int, float)):
                if abs(v - old) > tolerance:
                    diffs[k] = {"twin": old, "real": v}
            elif v != old:
                diffs[k] = {"twin": old, "real": v}
        if diffs:
            ev = {"twin": self.twin_id, "diffs": diffs, "at": time.time()}
            self.drift_events.append(ev)
            return {"drift": True, "event": ev, "action": "REALITY_GAP — replan from real state"}
        return {"drift": False}


class RobotTwin(PhysicalDigitalTwin):
    kind = "robot"

    def __init__(self, twin_id: str, dof: int = 6) -> None:
        super().__init__(twin_id)
        self.dof = dof
        self.joints = [0.0] * dof
        self.pose = {"x": 0.0, "y": 0.0, "theta": 0.0}

    def predict(self, action: Dict[str, Any]) -> Dict[str, Any]:
        p = action.get("parameters", {})
        if action.get("type") == "move_joints":
            target = p.get("joints", self.joints)
            return {"twin": self.twin_id, "predicted_joints": target,
                    "note": "kinematic target, dynamics not modeled"}
        if action.get("type") == "move_base":
            return {"twin": self.twin_id,
                    "predicted_pose": {"x": p.get("x", self.pose["x"]),
                                       "y": p.get("y", self.pose["y"]),
                                       "theta": p.get("theta", self.pose["theta"])},
                    "note": "ideal kinematics; slip not modeled"}
        return super().predict(action)


class RoomTwin(PhysicalDigitalTwin):
    kind = "room"

    def __init__(self, twin_id: str, mode: str = "SIMULATION") -> None:
        super().__init__(twin_id, mode)
        self.objects: Dict[str, Dict[str, Any]] = {}

    def place(self, obj_id: str, x: float, y: float, mode: str = "SIMULATED") -> None:
        self.objects[obj_id] = {"x": x, "y": y, "mode": mode, "at": time.time()}

    def move(self, obj_id: str, x: float, y: float) -> bool:
        if obj_id in self.objects:
            self.objects[obj_id] = {"x": x, "y": y, "mode": self.objects[obj_id].get("mode", "SIMULATED"), "at": time.time()}
            return True
        return False

    def remove(self, obj_id: str) -> bool:
        if obj_id in self.objects:
            del self.objects[obj_id]
            return True
        return False


# Re-export for convenience
__all__ = ["PhysicalDigitalTwin", "RobotTwin", "RoomTwin", "TwinDriftEvent"]

import copy
import time
from typing import Any, Dict, List, Optional

from aetheros_cognitive.twins import DigitalTwin as _BaseDigitalTwin