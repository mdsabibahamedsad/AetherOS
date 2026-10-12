"""Emergency control (§38-39, §164-165): RUNNING/PAUSING/STOPPING/
EMERGENCY_STOPPED/RECOVERY machine plus layered kill switches
(GLOBAL/AGENT/TASK/SWARM/AUTOMATION/REMOTE_AGENT/ROBOT/NETWORK/TOOL)
built on M50 EmergencyStop listeners. Kill never needs model
cooperation; external non-cancellable ops surface CANCEL_REQUESTED."""
from __future__ import annotations

import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from aetheros_control_plane.emergency import EmergencyStop, StopScope


class RunState(str, Enum):
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    STOPPING = "STOPPING"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"
    RECOVERY = "RECOVERY"


_KILL_TO_SCOPE = {
    "GLOBAL_KILL": StopScope.GLOBAL,
    "AGENT_KILL": StopScope.AGENT,
    "TASK_KILL": StopScope.TASK,
    "SWARM_KILL": StopScope.SWARM,
    "AUTOMATION_KILL": StopScope.ALL_AUTONOMOUS,
    "REMOTE_AGENT_KILL": StopScope.ALL_REMOTE,
    "ROBOT_KILL": StopScope.ALL_AUTONOMOUS,
    "NETWORK_KILL": StopScope.ALL_REMOTE,
    "TOOL_KILL": StopScope.ACTION,
}


class EmergencyController:
    def __init__(self, emergency: Optional[EmergencyStop] = None):
        self.emergency = emergency or EmergencyStop()
        self.state: RunState = RunState.RUNNING
        self._cancel_requested: List[str] = []
        self.emergency.on_stop(lambda _s: self._enter_stopped())

    def _enter_stopped(self) -> None:
        self.state = RunState.EMERGENCY_STOPPED

    def kill(self, layer: str, target: str = "",
             reason: str = "", actor: str = "") -> Dict[str, Any]:
        if layer not in _KILL_TO_SCOPE:
            raise ValueError(f"unknown kill layer {layer}")
        self.state = RunState.STOPPING
        st = self.emergency.stop(_KILL_TO_SCOPE[layer], target, reason,
                                 actor)
        self.state = RunState.EMERGENCY_STOPPED
        return {"layer": layer, "target": target,
                "at": st.at, "state": self.state.value}

    def request_cancel_external(self, action_id: str) -> Dict[str, str]:
        """External systems that cannot guarantee immediate cancellation
        are marked CANCEL_REQUESTED — never faked as cancelled (§38)."""
        self._cancel_requested.append(action_id)
        return {"action": action_id, "state": "CANCEL_REQUESTED"}

    def begin_recovery(self) -> List[str]:
        """STOPPED->DIAGNOSTICS->REVIEW->RESTORE MINIMAL->REAUTHORIZE->
        RESUME (§165). Never auto-resumes to unrestricted autonomy."""
        self.state = RunState.RECOVERY
        return ["DIAGNOSTICS", "REVIEW", "RESTORE_MINIMAL", "REAUTHORIZE",
                "RESUME"]

    def resume(self, scope: StopScope, target: str = "",
               minimal: bool = True) -> Dict[str, Any]:
        n = self.emergency.resume(scope, target)
        if not self.emergency.active():
            self.state = RunState.RUNNING
        return {"resumed": n, "minimal": minimal,
                "state": self.state.value}
