"""Hardware abstraction (§236-242) + action execution (§34-39):
adapter interfaces, simulated robot adapter (kinematics-backed),
command authentication + replay protection + idempotency (§52-54),
rate limits (§150), loop detection (§151), closed-loop execute with
recovery (§58-60). No real hardware here: LIVE execution requires a
registered third-party adapter; otherwise HARDWARE_UNAVAILABLE."""
from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from .models import ExecMode, PhysicalAction
from .safety import SafetyController, SafetyVeto


class PhysicalAdapter:
    kind = "base"

    def discover(self) -> List[str]:
        return []

    def connect(self, device_id: str) -> Dict[str, Any]:
        raise ValueError("HARDWARE_UNAVAILABLE: no driver for "
                         f"{device_id}")

    def capabilities(self, device_id: str) -> List[str]:
        return []

    def state(self, device_id: str) -> Dict[str, Any]:
        raise ValueError("HARDWARE_UNAVAILABLE")

    def observe(self, device_id: str) -> Dict[str, Any]:
        raise ValueError("HARDWARE_UNAVAILABLE")

    def plan(self, *a: Any, **k: Any) -> Dict[str, Any]:
        return {"ok": False, "reason": "HARDWARE_UNAVAILABLE"}

    def execute(self, action: PhysicalAction) -> Dict[str, Any]:
        raise ValueError("HARDWARE_UNAVAILABLE: cannot execute "
                         f"{action.capability} — no hardware adapter")

    def stop(self, device_id: str) -> Dict[str, Any]:
        return {"stopped": device_id, "mode": ExecMode.SIMULATION}

    def health(self, device_id: str) -> Dict[str, Any]:
        return {"device": device_id, "health": "unknown",
                "mode": ExecMode.HARDWARE_UNAVAILABLE}

    def disconnect(self, device_id: str) -> None:
        pass


class SimulatedRobotAdapter(PhysicalAdapter):
    """Kinematics-backed simulated robot. Mode is ALWAYS SIMULATION;
    outputs are predictions, never hardware claims."""
    kind = "simulated_robot"

    def __init__(self) -> None:
        from .simulation import KinematicSimulator
        self.sim = KinematicSimulator(seed=7)
        self.connected: Dict[str, bool] = {}

    def discover(self) -> List[str]:
        return ["sim-arm-01", "sim-base-01"]

    def connect(self, device_id: str) -> Dict[str, Any]:
        if device_id not in self.discover():
            raise ValueError(f"HARDWARE_UNAVAILABLE: {device_id}")
        self.connected[device_id] = True
        return {"device": device_id, "mode": ExecMode.SIMULATION,
                "note": "simulated — not hardware"}

    def capabilities(self, device_id: str) -> List[str]:
        return ["MOVE", "ROTATE", "READ_POSITION"]

    def state(self, device_id: str) -> Dict[str, Any]:
        if not self.connected.get(device_id):
            raise ValueError(f"not connected: {device_id}")
        s = self.sim.observe()
        s["device"] = device_id
        return s

    def execute(self, action: PhysicalAction) -> Dict[str, Any]:
        if not self.connected.get(action.device):
            raise ValueError(f"not connected: {action.device}")
        p = action.parameters
        if action.capability == "MOVE":
            s = self.sim.step(float(p.get("v", 0.1)),
                              float(p.get("omega", 0.0)),
                              float(p.get("dt", 1.0)))
            return {"ack": True, "state": s, "mode": ExecMode.SIMULATION}
        if action.capability == "ROTATE":
            self.sim.theta += float(p.get("dtheta", 0.0))
            return {"ack": True, "state": self.sim.observe(),
                    "mode": ExecMode.SIMULATION}
        return {"ack": False, "reason": f"unsupported {action.capability}",
                "mode": ExecMode.SIMULATION}


class CommandAuthenticator:
    """HMAC command auth: identity + timestamp + nonce + scope.
    Replay cache rejects reuse (§53)."""

    def __init__(self, skew_s: float = 60.0) -> None:
        self.keys: Dict[str, bytes] = {}
        self.seen_nonces: Dict[str, float] = {}
        self.skew_s = skew_s

    def enroll(self, identity: str) -> bytes:
        import secrets
        key = secrets.token_bytes(32)
        self.keys[identity] = key
        return key

    def sign(self, identity: str, action: PhysicalAction) -> str:
        key = self.keys.get(identity)
        if key is None:
            raise ValueError(f"unknown identity {identity}")
        msg = (f"{identity}|{action.id}|{action.device}|"
               f"{action.capability}|{action.nonce}|"
               f"{int(action.created_at)}").encode()
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    def verify(self, identity: str, action: PhysicalAction,
               sig: str) -> Dict[str, Any]:
        if action.nonce in self.seen_nonces:
            return {"ok": False, "reason": "REPLAY_REJECTED"}
        if abs(time.time() - action.created_at) > self.skew_s:
            return {"ok": False, "reason": "STALE_COMMAND"}
        try:
            expect = self.sign(identity, action)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc)}
        if not hmac.compare_digest(expect, sig):
            return {"ok": False, "reason": "BAD_SIGNATURE"}
        self.seen_nonces[action.nonce] = time.time()
        return {"ok": True}


class RateLimiter:
    def __init__(self, per_minute: int = 30,
                 max_motion_s: float = 300.0) -> None:
        self.per_minute = per_minute
        self.max_motion_s = max_motion_s
        self._times: List[float] = []

    def allow(self, motion_s: float = 0.0) -> Dict[str, Any]:
        now = time.time()
        self._times = [t for t in self._times if now - t < 60]
        if len(self._times) >= self.per_minute:
            return {"ok": False, "reason": "RATE_LIMITED"}
        if motion_s > self.max_motion_s:
            return {"ok": False, "reason": "MOTION_TOO_LONG"}
        self._times.append(now)
        return {"ok": True}


class LoopDetector:
    """Detects move->back and repeated identical commands (§151)."""

    def __init__(self, window: int = 6) -> None:
        self.window = window
        self.recent: List[str] = []

    def observe(self, signature: str) -> Dict[str, Any]:
        self.recent.append(signature)
        self.recent = self.recent[-self.window:]
        if len(self.recent) >= 4 and self.recent[-1] == self.recent[-3] \
                and self.recent[-2] == self.recent[-4] \
                and self.recent[-1] != self.recent[-2]:
            return {"loop": True,
                    "reason": "oscillation detected — stopping"}
        if len(set(self.recent[-4:])) == 1 and len(self.recent) >= 4:
            return {"loop": True,
                    "reason": "repeated identical command — stopping"}
        return {"loop": False}


class ActionExecutor:
    """Closed-loop: preconditions -> simulate -> safety -> approval ->
    execute -> verify. Recovery via strategies, never blind retry."""

    RECOVERY = ["retry", "relocalize", "regrasp", "change_trajectory",
                "change_tool", "return_safe", "request_human", "abort"]

    def __init__(self, safety: SafetyController,
                 adapter: Optional[PhysicalAdapter] = None) -> None:
        self.safety = safety
        self.adapter = adapter or PhysicalAdapter()
        self.executed: Dict[str, Dict[str, Any]] = {}  # idempotency
        self.loops = LoopDetector()
        self.limiter = RateLimiter()

    def check_preconditions(self, action: PhysicalAction,
                            world: Dict[str, Any]) -> List[str]:
        missing = [p for p in action.preconditions if p not in world]
        return missing

    def run(self, action: PhysicalAction, world: Dict[str, Any],
            verify: Optional[Callable[[PhysicalAction, Dict[str, Any]],
                                      Dict[str, Any]]] = None,
            ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = ctx or {}
        if action.id in self.executed:
            return {"status": "DUPLICATE",
                    "prior": self.executed[action.id]}
        missing = self.check_preconditions(action, world)
        if missing:
            return {"status": "BLOCKED", "missing": missing}
        gate = self.safety.check_action(action, ctx)
        if not gate["allowed"]:
            return {"status": "VETOED", "reasons": gate["reasons"]}
        if action.risk == "HIGH" and action.approval != "approved":
            return {"status": "AWAITING_APPROVAL"}
        lim = self.limiter.allow(
            float(action.parameters.get("duration_s", 1.0)))
        if not lim["ok"]:
            return {"status": "RATE_LIMITED", "reason": lim["reason"]}
        loop = self.loops.observe(
            f"{action.device}:{action.capability}:"
            f"{sorted(action.parameters.items())}")
        if loop["loop"]:
            return {"status": "LOOP_STOPPED", "reason": loop["reason"]}
        try:
            result = self.adapter.execute(action)
        except ValueError as exc:
            return {"status": "FAILED", "reason": str(exc),
                    "mode": ExecMode.HARDWARE_UNAVAILABLE
                    if "HARDWARE_UNAVAILABLE" in str(exc)
                    else action.execution_mode}
        outcome = {"status": "EXECUTED", "result": result,
                   "mode": result.get("mode", action.execution_mode)}
        if verify is not None:
            outcome["verification"] = verify(action, result)
            action.verification = outcome["verification"].get(
                "verdict", "UNVERIFIED")
        self.executed[action.id] = outcome
        return outcome

    def recover(self, action: PhysicalAction, diagnosis: str) -> Dict[str, Any]:
        strategy = ("request_human" if "human" in diagnosis
                    else "relocalize" if "pose" in diagnosis
                    else "change_trajectory" if "collision" in diagnosis
                    else "return_safe")
        return {"strategy": strategy,
                "note": "recovery chosen, not blind retry"}
