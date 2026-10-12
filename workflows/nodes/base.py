"""Base node definitions — abstract node class and result types."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from workflows.models import WorkflowNode, WorkflowConfig

logger = logging.getLogger(__name__)


@dataclass
class NodeResult:
    success: bool = True
    output: Any = None
    error: str = ""
    logs: list[dict] = field(default_factory=list)
    retry_allowed: bool = True

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output,
                "error": self.error, "logs": self.logs,
                "retry_allowed": self.retry_allowed}


class BaseNode(ABC):
    type: str = ""
    category: str = ""
    label: str = ""
    description: str = ""
    default_config: dict = field(default_factory=dict)
    inputs: list[dict] = field(default_factory=lambda: [{"id": "input", "label": "Input", "type": "any"}])
    outputs: list[dict] = field(default_factory=lambda: [{"id": "output", "label": "Output", "type": "any"}])

    @abstractmethod
    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        ...

    def validate(self, node: WorkflowNode) -> list[str]:
        errors = []
        return errors

    def get_config_schema(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}


class NodeRegistry:
    _nodes: dict[str, type[BaseNode]] = {}

    @classmethod
    def register(cls, node_class: type[BaseNode]) -> None:
        cls._nodes[node_class.type] = node_class
        logger.debug("Registered node type: %s", node_class.type)

    @classmethod
    def get(cls, node_type: str) -> Optional[type[BaseNode]]:
        return cls._nodes.get(node_type)

    @classmethod
    def get_all(cls) -> dict[str, type[BaseNode]]:
        return dict(cls._nodes)

    @classmethod
    def get_by_category(cls, category: str) -> list[type[BaseNode]]:
        return [n for n in cls._nodes.values() if n.category == category]

    @classmethod
    def discover(cls) -> None:
        import workflows.nodes.triggers
        import workflows.nodes.ai
        import workflows.nodes.logic
        import workflows.nodes.actions
        import workflows.nodes.agent_nodes
        import workflows.nodes.mcp_nodes
