"""
Workflow SDK for AetherOS
=========================

SDK for creating and executing workflows with nodes, conditions, triggers, actions, and outputs.

Usage::

    from aetheros_developer_platform.workflow_sdk import WorkflowBuilder

    workflow = WorkflowBuilder("my-workflow")
    workflow.add_trigger("webhook", {"url": "/api/my-workflow"})
    workflow.add_condition("validate_input", {"field": "data"})
    workflow.add_action("process_data", {"transform": "uppercase"})
    workflow.add_output("send_notification", {"channel": "slack"})
    wf = workflow.build()
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Workflow node types."""
    TRIGGER = "trigger"
    CONDITION = "condition"
    ACTION = "action"
    OUTPUT = "output"
    PARALLEL = "parallel"
    LOOP = "loop"
    ERROR_HANDLER = "error_handler"


class TriggerType(Enum):
    """Trigger types."""
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"
    FILE_CHANGE = "file_change"
    API_CALL = "api_call"


@dataclass
class WorkflowNode:
    """A node in a workflow."""
    id: str
    node_type: NodeType
    config: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None
    next_nodes: List[str] = field(default_factory=list)
    error_handler: Optional[str] = None


@dataclass
class WorkflowEdge:
    """An edge connecting two nodes."""
    source: str
    target: str
    condition: Optional[str] = None


@dataclass
class WorkflowState:
    """Current state of a workflow execution."""
    workflow_id: str
    execution_id: str
    status: str
    current_node: Optional[str] = None
    started_at: float = 0.0
    completed_at: float = 0.0
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, Any] = field(default_factory=dict)


class BaseWorkflow(ABC):
    """Base class for all workflows."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._nodes: Dict[str, WorkflowNode] = {}
        self._edges: List[WorkflowEdge] = []
        self._start_node: Optional[str] = None

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute the workflow."""
        ...

    def add_node(self, node: WorkflowNode) -> None:
        """Add a node to the workflow."""
        self._nodes[node.id] = node

    def add_edge(self, edge: WorkflowEdge) -> None:
        """Add an edge to the workflow."""
        self._edges.append(edge)

    def set_start_node(self, node_id: str) -> None:
        """Set the start node."""
        self._start_node = node_id

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_next_nodes(self, node_id: str) -> List[str]:
        """Get the next nodes after a given node."""
        node = self._nodes.get(node_id)
        if node:
            return node.next_nodes
        return []

    def to_dict(self) -> Dict[str, Any]:
        """Export workflow as dictionary."""
        return {
            "name": self._name,
            "nodes": [
                {
                    "id": node.id,
                    "type": node.node_type.value,
                    "config": node.config,
                    "next_nodes": node.next_nodes,
                }
                for node in self._nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "condition": edge.condition,
                }
                for edge in self._edges
            ],
            "start_node": self._start_node,
        }


class Workflow(BaseWorkflow):
    """Standard workflow implementation."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._state: Optional[WorkflowState] = None

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute the workflow."""
        import uuid

        execution_id = str(uuid.uuid4())
        self._state = WorkflowState(
            workflow_id=self._name,
            execution_id=execution_id,
            status="running",
            started_at=time.time(),
            context=context or {},
        )

        logger.info("Executing workflow: %s (execution: %s)", self._name, execution_id)

        try:
            current_node_id = self._start_node
            if not current_node_id:
                raise ValueError("No start node defined")

            while current_node_id:
                node = self._nodes.get(current_node_id)
                if not node:
                    raise ValueError(f"Node '{current_node_id}' not found")

                self._state.current_node = current_node_id
                logger.debug("Executing node: %s", current_node_id)

                # Execute node
                result = await self._execute_node(node, input_data)
                self._state.node_results[current_node_id] = result

                # Find next node
                next_nodes = self.get_next_nodes(current_node_id)
                if next_nodes:
                    current_node_id = next_nodes[0]
                else:
                    current_node_id = None

            self._state.status = "completed"
            self._state.completed_at = time.time()

            return {
                "status": "completed",
                "execution_id": execution_id,
                "results": self._state.node_results,
            }

        except Exception as exc:
            self._state.status = "failed"
            self._state.error = str(exc)
            self._state.completed_at = time.time()

            logger.error("Workflow execution failed: %s", exc)
            return {
                "status": "failed",
                "execution_id": execution_id,
                "error": str(exc),
            }

    async def _execute_node(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
    ) -> Any:
        """Execute a single workflow node."""
        if node.handler:
            return await node.handler(input_data)

        # Default handlers based on node type
        if node.node_type == NodeType.TRIGGER:
            return {"triggered": True, "config": node.config}
        elif node.node_type == NodeType.CONDITION:
            return {"condition_met": True, "config": node.config}
        elif node.node_type == NodeType.ACTION:
            return {"action_completed": True, "config": node.config}
        elif node.node_type == NodeType.OUTPUT:
            return {"output_sent": True, "config": node.config}

        return {"processed": True}


class WorkflowBuilder:
    """Builder for creating workflows.

    Usage::

        builder = WorkflowBuilder("my-workflow")
        builder.add_trigger("webhook", {"url": "/api/my-workflow"})
        builder.add_condition("validate_input", {"field": "data"})
        builder.add_action("process_data", {"transform": "uppercase"})
        builder.add_output("send_notification", {"channel": "slack"})
        workflow = builder.build()
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._nodes: List[WorkflowNode] = []
        self._edges: List[WorkflowEdge] = []
        self._node_counter = 0

    def _next_node_id(self, prefix: str) -> str:
        """Generate the next node ID."""
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"

    def add_trigger(
        self,
        trigger_type: str,
        config: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable] = None,
    ) -> "WorkflowBuilder":
        """Add a trigger node."""
        node_id = self._next_node_id("trigger")
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.TRIGGER,
            config={"trigger_type": trigger_type, **(config or {})},
            handler=handler,
        )
        self._nodes.append(node)
        return self

    def add_condition(
        self,
        condition_type: str,
        config: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable] = None,
    ) -> "WorkflowBuilder":
        """Add a condition node."""
        node_id = self._next_node_id("condition")
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.CONDITION,
            config={"condition_type": condition_type, **(config or {})},
            handler=handler,
        )
        self._nodes.append(node)
        return self

    def add_action(
        self,
        action_type: str,
        config: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable] = None,
    ) -> "WorkflowBuilder":
        """Add an action node."""
        node_id = self._next_node_id("action")
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.ACTION,
            config={"action_type": action_type, **(config or {})},
            handler=handler,
        )
        self._nodes.append(node)
        return self

    def add_output(
        self,
        output_type: str,
        config: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable] = None,
    ) -> "WorkflowBuilder":
        """Add an output node."""
        node_id = self._next_node_id("output")
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.OUTPUT,
            config={"output_type": output_type, **(config or {})},
            handler=handler,
        )
        self._nodes.append(node)
        return self

    def add_parallel(
        self,
        parallel_config: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowBuilder":
        """Add a parallel node."""
        node_id = self._next_node_id("parallel")
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.PARALLEL,
            config=parallel_config or {},
        )
        self._nodes.append(node)
        return self

    def add_loop(
        self,
        loop_config: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowBuilder":
        """Add a loop node."""
        node_id = self._next_node_id("loop")
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.LOOP,
            config=loop_config or {},
        )
        self._nodes.append(node)
        return self

    def add_error_handler(
        self,
        handler_config: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowBuilder":
        """Add an error handler node."""
        node_id = self._next_node_id("error_handler")
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.ERROR_HANDLER,
            config=handler_config or {},
        )
        self._nodes.append(node)
        return self

    def connect(
        self,
        source_index: int,
        target_index: int,
        condition: Optional[str] = None,
    ) -> "WorkflowBuilder":
        """Connect two nodes by index."""
        if 0 <= source_index < len(self._nodes) and 0 <= target_index < len(self._nodes):
            source_node = self._nodes[source_index]
            target_node = self._nodes[target_index]

            source_node.next_nodes.append(target_node.id)

            edge = WorkflowEdge(
                source=source_node.id,
                target=target_node.id,
                condition=condition,
            )
            self._edges.append(edge)

        return self

    def build(self) -> Workflow:
        """Build the workflow."""
        workflow = Workflow(self._name)

        for node in self._nodes:
            workflow.add_node(node)

        for edge in self._edges:
            workflow.add_edge(edge)

        if self._nodes:
            workflow.set_start_node(self._nodes[0].id)

        return workflow


def create_workflow(
    name: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Workflow:
    """Create a workflow from node and edge definitions.

    Args:
        name: Workflow name.
        nodes: List of node definitions.
        edges: List of edge definitions.

    Returns:
        Configured workflow instance.
    """
    builder = WorkflowBuilder(name)

    for node_def in nodes:
        node_type = node_def.get("type", "action")
        config = node_def.get("config", {})

        if node_type == "trigger":
            builder.add_trigger(config.get("trigger_type", "manual"), config)
        elif node_type == "condition":
            builder.add_condition(config.get("condition_type", "default"), config)
        elif node_type == "action":
            builder.add_action(config.get("action_type", "default"), config)
        elif node_type == "output":
            builder.add_output(config.get("output_type", "default"), config)

    workflow = builder.build()

    # Note: edges need to be connected by index after building
    # This is a simplified implementation
    return workflow
