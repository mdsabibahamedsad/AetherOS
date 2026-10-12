from __future__ import annotations

import logging
from typing import Any, Optional

from aetheros_automation.models.models import ExecutionMode
from aetheros_automation.modes.base import BaseExecutionMode
from aetheros_automation.modes.manual import ManualMode
from aetheros_automation.modes.assisted import AssistedMode
from aetheros_automation.modes.semi import SemiAutonomousMode
from aetheros_automation.modes.full import FullyAutonomousMode

logger = logging.getLogger(__name__)


class ModeController:
    def __init__(self, engine: Optional[Any] = None) -> None:
        self._manual = ManualMode()
        self._assisted = AssistedMode()
        self._semi = SemiAutonomousMode()
        self._full = FullyAutonomousMode()
        self._current: ExecutionMode = ExecutionMode.ASSISTED
        if engine:
            self.bind_engine(engine)

    def bind_engine(self, engine: Any):
        for mode in (self._manual, self._assisted, self._semi, self._full):
            mode.bind_engine(engine)

    def get_mode(self, mode: ExecutionMode) -> BaseExecutionMode:
        mapping: dict[ExecutionMode, BaseExecutionMode] = {
            ExecutionMode.MANUAL: self._manual,
            ExecutionMode.ASSISTED: self._assisted,
            ExecutionMode.SEMI_AUTONOMOUS: self._semi,
            ExecutionMode.FULLY_AUTONOMOUS: self._full,
        }
        return mapping[mode]

    def set_mode(self, mode: ExecutionMode) -> None:
        self._current = mode
        logger.info("ModeController: active mode set to %s", mode.value)

    @property
    def current_mode(self) -> ExecutionMode:
        return self._current

    async def switch_to(self, mode: ExecutionMode) -> bool:
        try:
            self.set_mode(mode)
            return True
        except Exception as e:
            logger.error("Failed to switch mode: %s", e)
            return False

    async def execute_in_mode(
        self,
        mode: ExecutionMode,
        task: Any,
        context: dict[str, Any],
    ) -> str:
        executor = self.get_mode(mode)
        logger.info(
            "ModeController: executing task %s in mode %s",
            getattr(task, "id", "?"),
            mode.value,
        )
        return await executor.execute(task, context)
