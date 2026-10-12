"""Emergency stop (§36) + quarantine (§27) + budgets (§53).

Emergency stop is plain authoritative state + listener callbacks — it
never depends on model cooperation. Scopes: action / task / agent /
swarm / all-autonomous / all-remote / global.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


class StopScope(str, Enum):
    ACTION = "action"
    TASK = "task"
    AGENT = "agent"
    SWARM = "swarm"
    ALL_AUTONOMOUS = "all_autonomous"
    ALL_REMOTE = "all_remote"
    GLOBAL = "global"


@dataclass
class StopState:
    scope: StopScope
    target: str = ""
    reason: str = ""
    at: float = field(default_factory=time.time)
    actor: str = ""


class EmergencyStop:
    def __init__(self) -> None:
        self._stops: List[StopState] = []
        self._listeners: List[Callable[[StopState], None]] = []

    def on_stop(self, fn: Callable[[StopState], None]) -> None:
        self._listeners.append(fn)

    def stop(self, scope: StopScope, target: str = "", reason: str = "",
             actor: str = "") -> StopState:
        st = StopState(scope=scope, target=target, reason=reason, actor=actor)
        self._stops.append(st)
        for fn in self._listeners:
            try:
                fn(st)
            except Exception:
                pass
        return st

    def resume(self, scope: StopScope, target: str = "") -> int:
        before = len(self._stops)
        self._stops = [s for s in self._stops
                       if not (s.scope == scope and s.target == target)]
        return before - len(self._stops)

    def blocked(self, scope: StopScope, target: str = "") -> Optional[StopState]:
        for s in self._stops:
            if s.scope == StopScope.GLOBAL:
                return s
            if s.scope == scope and (not s.target or s.target == target):
                return s
            # broader stops cover narrower targets
            if s.scope in (StopScope.ALL_AUTONOMOUS, StopScope.ALL_REMOTE,
                           StopScope.SWARM) and scope in (
                               StopScope.ACTION, StopScope.TASK,
                               StopScope.AGENT, StopScope.SWARM):
                return s
        return None

    def active(self) -> List[StopState]:
        return list(self._stops)


# ---------------------------------------------------------------------------
# Quarantine (§27)
# ---------------------------------------------------------------------------

class Quarantine:
    def __init__(self) -> None:
        self._held: Dict[str, dict] = {}

    def hold(self, identity_id: str, reason: str) -> None:
        self._held[identity_id] = {"reason": reason, "at": time.time()}

    def release(self, identity_id: str) -> bool:
        return self._held.pop(identity_id, None) is not None

    def is_held(self, identity_id: str) -> bool:
        return identity_id in self._held

    def list(self) -> Dict[str, dict]:
        return dict(self._held)


# ---------------------------------------------------------------------------
# Autonomy budgets (§53)
# ---------------------------------------------------------------------------

@dataclass
class Budget:
    name: str = "default"
    max_tool_calls: int = 100
    max_network_requests: int = 50
    max_delegations: int = 5
    max_tokens: int = 200_000
    used_tool_calls: int = 0
    used_network_requests: int = 0
    used_delegations: int = 0
    used_tokens: int = 0

    def check(self, kind: str, amount: int = 1) -> tuple[bool, str]:
        table = {"tool": ("used_tool_calls", "max_tool_calls"),
                 "network": ("used_network_requests",
                             "max_network_requests"),
                 "delegation": ("used_delegations", "max_delegations"),
                 "tokens": ("used_tokens", "max_tokens")}
        if kind not in table:
            return True, "unknown budget kind"
        used_f, max_f = table[kind]
        if getattr(self, used_f) + amount > getattr(self, max_f):
            return False, f"budget exhausted: {kind}"
        return True, "ok"

    def spend(self, kind: str, amount: int = 1) -> None:
        mapping = {"tool": "used_tool_calls", "network": "used_network_requests",
                   "delegation": "used_delegations", "tokens": "used_tokens"}
        if kind in mapping:
            setattr(self, mapping[kind], getattr(self, mapping[kind]) + amount)
