"""Safety controller (§42-44): independent of planner/LLM. Can stop,
slow, limit, reject. LLM can NEVER override e-stop, hardware limits,
collision boundaries, restricted zones, or human-safety policy."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional

from .models import PhysicalAction
from .spatial import SpatialWorldModel


class SafetyVeto(Exception):
    pass


class SafetyController:
    def __init__(self, world: Optional[SpatialWorldModel] = None,
                 plane: Any = None) -> None:
        self.world = world or SpatialWorldModel()
        self.plane = plane
        self.e_stop_active = False
        self.safe_mode = False
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []
        self.safety_log: List[Dict[str, Any]] = []
        self._prev_hash = "GENESIS"

    # -- emergency stop (§44): overrides everything ---------------------
    def emergency_stop(self, reason: str = "operator",
                       actor: str = "unknown") -> Dict[str, Any]:
        self.e_stop_active = True
        ev = self._log("EMERGENCY_STOP",
                       {"reason": reason, "actor": actor})
        for fn in self.listeners:
            try:
                fn(ev)
            except Exception:
                pass
        try:
            if self.plane is not None:
                from aetheros_control_plane.emergency import StopScope
                self.plane.emergency.stop(StopScope.GLOBAL, "",
                                          f"embodied: {reason}", actor)
        except Exception:
            pass
        return ev

    def clear_estop(self, actor: str = "operator") -> Dict[str, Any]:
        self.e_stop_active = False
        return self._log("ESTOP_CLEARED", {"actor": actor})

    def on_estop(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        self.listeners.append(fn)

    # -- gating ----------------------------------------------------------
    def check_action(self, action: PhysicalAction,
                     ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Returns {allowed, reasons}. Vetoes are absolute."""
        ctx = ctx or {}
        reasons = []
        if self.e_stop_active:
            return {"allowed": False, "reasons": ["E-STOP ACTIVE"]}
        if action.risk == "HIGH" and action.approval != "approved":
            reasons.append("HIGH risk requires approval")
        x, y = (action.parameters.get("x"),
                action.parameters.get("y"))
        if x is not None and y is not None:
            zone = self.world.zone_at(x, y)
            if zone and zone.kind == "KEEP_OUT":
                return {"allowed": False,
                        "reasons": [f"KEEP_OUT zone {zone.name}"]}
            if zone and zone.kind in ("SLOW_ZONE", "COLLABORATIVE_ZONE"):
                speed = float(action.parameters.get("speed", 1.0))
                if speed > zone.speed_limit:
                    reasons.append(
                        f"speed {speed} exceeds {zone.name} limit "
                        f"{zone.speed_limit}")
        if ctx.get("human_nearby") and action.risk in ("HIGH", "MEDIUM"):
            reasons.append("human nearby: slow/stop per policy")
        force = float(action.parameters.get("force_n", 0.0))
        if force > float(ctx.get("force_limit_n", 50.0)):
            reasons.append(f"force {force}N exceeds limit")
        if reasons:
            self._log("VETO", {"action": action.id, "reasons": reasons})
            return {"allowed": False, "reasons": reasons}
        return {"allowed": True, "reasons": ["safety checks passed"]}

    # -- tamper-evident safety log (§99) ----------------------------------
    def _log(self, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps({"kind": kind, "at": time.time(),
                           "prev": self._prev_hash, **payload},
                          sort_keys=True)
        h = hashlib.sha256(body.encode()).hexdigest()
        ev = json.loads(body)
        ev["hash"] = h
        self._prev_hash = h
        self.safety_log.append(ev)
        return ev

    def verify_log(self) -> Dict[str, Any]:
        prev = "GENESIS"
        for ev in self.safety_log:
            if ev.get("prev") != prev:
                return {"ok": False, "at": ev}
            body = {k: v for k, v in ev.items() if k != "hash"}
            h = hashlib.sha256(json.dumps(
                body, sort_keys=True).encode()).hexdigest()
            if h != ev["hash"]:
                return {"ok": False, "at": ev}
            prev = ev["hash"]
        return {"ok": True, "events": len(self.safety_log)}
