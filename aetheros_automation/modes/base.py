from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BaseExecutionMode(ABC):
    engine: Optional[Any] = None

    def bind_engine(self, engine: Any):
        self.engine = engine

    @abstractmethod
    async def execute(self, task: Any, context: dict[str, Any]) -> str:
        ...

    @abstractmethod
    async def approve_step(self, step: Any, context: dict[str, Any]) -> bool:
        ...
