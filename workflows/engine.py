"""DAG execution engine — topological sort, node runner, context propagation, retry logic."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Optional

from workflows.models import (WorkflowConfig, WorkflowNode, Connection,
                               ExecutionStatus, ExecutionRecord)
from workflows.nodes.base import BaseNode, NodeRegistry, NodeResult
from workflows.store import WorkflowStore

logger = logging.getLogger(__name__)


class WorkflowEngine:
    def __init__(self, store: Optional[WorkflowStore] = None):
        self.store = store or WorkflowStore()
        self._running: dict[str, asyncio.Task] = {}
        self._hooks: dict[str, list[Callable]] = defaultdict(list)
        self._node_cache: dict[str, type[BaseNode]] = {}

    def on(self, event: str, handler: Callable) -> None:
        self._hooks[event].append(handler)

    def _emit(self, event: str, **data) -> None:
        for handler in self._hooks.get(event, []):
            try:
                handler(**data)
            except Exception as e:
                logger.error("Hook error on %s: %s", event, e)

    def _get_nodes(self, workflow: WorkflowConfig) -> list[WorkflowNode]:
        return workflow.nodes

    def _get_connections(self, workflow: WorkflowConfig) -> list[Connection]:
        return workflow.connections

    def _topological_sort(self, workflow: WorkflowConfig) -> list[str]:
        """Return node IDs in topological order using Kahn's algorithm."""
        nodes = {n.id: n for n in workflow.nodes}
        connections = workflow.connections
        in_degree: dict[str, int] = {n.id: 0 for n in workflow.nodes}
        adjacency: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
        for conn in connections:
            if conn.source_id in adjacency and conn.target_id in nodes:
                adjacency[conn.source_id].append(conn.target_id)
                in_degree[conn.target_id] = in_degree.get(conn.target_id, 0) + 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_nodes = []
        while queue:
            nid = queue.pop(0)
            sorted_nodes.append(nid)
            for neighbor in adjacency.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if len(sorted_nodes) != len(nodes):
            logger.error("Circular dependency detected in workflow %s", workflow.id)
            return [n.id for n in workflow.nodes]
        return sorted_nodes

    def _get_upstream_nodes(self, node_id: str, workflow: WorkflowConfig) -> list[WorkflowNode]:
        nodes_map = {n.id: n for n in workflow.nodes}
        upstream = []
        for conn in workflow.connections:
            if conn.target_id == node_id and conn.source_id in nodes_map:
                upstream.append(nodes_map[conn.source_id])
        return upstream

    def _get_node_class(self, node: WorkflowNode) -> Optional[type[BaseNode]]:
        return NodeRegistry.get(node.type)

    def _get_edge_output_key(self, node_id: str, target_id: str,
                             workflow: WorkflowConfig) -> str:
        for conn in workflow.connections:
            if conn.source_id == node_id and conn.target_id == target_id:
                return conn.source_output or "output"
        return "output"

    def _build_context(self, node_id: str, context: dict,
                       workflow: WorkflowConfig) -> dict:
        """Build execution context for a node based on upstream results."""
        upstream = self._get_upstream_nodes(node_id, workflow)
        ctx = dict(context)
        if not upstream:
            return ctx
        inputs = []
        for up in upstream:
            result = context.get(f"node:{up.id}", {})
            edge_key = self._get_edge_output_key(up.id, node_id, workflow)
            output = result.get("output", None) if isinstance(result, dict) else result
            if edge_key != "output" and isinstance(output, dict):
                val = output.get(edge_key, output)
            else:
                val = output
            inputs.append(val)
            # Also inject named outputs into context
            if isinstance(output, dict):
                for k, v in output.items():
                    ctx[f"{up.id}.{k}"] = v
        if inputs:
            ctx["input"] = inputs[0] if len(inputs) == 1 else inputs
            ctx["inputs"] = inputs
        return ctx

    async def execute_node(self, node: WorkflowNode, context: dict,
                           workflow: WorkflowConfig) -> NodeResult:
        node_class = self._get_node_class(node)
        if not node_class:
            return NodeResult(success=False, error=f"Unknown node type: {node.type}",
                              retry_allowed=False)
        instance = node_class()
        errors = instance.validate(node)
        if errors:
            return NodeResult(success=False, error="; ".join(errors), retry_allowed=False)
        try:
            result = await instance.execute(node, context, workflow, engine=self)
            return result
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Node %s (%s) failed: %s", node.id, node.type, e)
            return NodeResult(success=False, output={"error": str(e)},
                              error=f"{type(e).__name__}: {e}",
                              retry_allowed=True)

    async def execute_workflow(self, workflow: WorkflowConfig,
                               initial_context: dict = None) -> ExecutionRecord:
        start_time = time.time()
        context = dict(initial_context or {})
        sorted_ids = self._topological_sort(workflow)
        nodes_map = {n.id: n for n in workflow.nodes}
        record = ExecutionRecord(
            workflow_id=workflow.id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            triggered_by=context.get("trigger", "manual"),
        )
        if self.store:
            self.store.save_execution(record)
        self._emit("workflow.started", workflow=workflow, record=record)
        for node_id in sorted_ids:
            if node_id not in nodes_map:
                continue
            node = nodes_map[node_id]
            node_ctx = self._build_context(node_id, context, workflow)
            max_retries = node.config.get("max_retries",
                                          workflow.error_policy.get("max_retries", 0))
            retry_delay = node.config.get("retry_delay",
                                          workflow.error_policy.get("retry_delay", 1))
            for attempt in range(max_retries + 1):
                self._emit("node.started", node=node, context=node_ctx,
                           workflow=workflow, attempt=attempt)
                result = await self.execute_node(node, node_ctx, workflow)
                result_dict = result.to_dict()
                context[f"node:{node.id}"] = result_dict
                context[f"node:{node.id}.output"] = result.output
                record.steps.append({
                    "node_id": node.id,
                    "node_type": node.type,
                    "node_label": node.label,
                    "success": result.success,
                    "output": str(result.output)[:500] if result.output else "",
                    "error": result.error,
                    "attempt": attempt,
                    "logs": result.logs,
                })
                self._emit("node.completed", node=node, result=result,
                           workflow=workflow, attempt=attempt)
                if result.success:
                    break
                if not result.retry_allowed or attempt >= max_retries:
                    break
                await asyncio.sleep(retry_delay)
            # Stop on failure if policy says so
            if not result.success and workflow.error_policy.get("action", "continue") == "stop":
                record.status = ExecutionStatus.FAILED
                record.error = f"Node {node.label} failed: {result.error}"
                break
        elapsed = time.time() - start_time
        if record.status != ExecutionStatus.FAILED:
            record.status = ExecutionStatus.COMPLETED if all(
                s.get("success", True) for s in (record.steps or [])
            ) else ExecutionStatus.PARTIAL
        record.completed_at = datetime.utcnow()
        record.duration = elapsed
        record.final_output = context.get("output", context)
        if self.store:
            self.store.update_execution(record)
        self._emit("workflow.completed", workflow=workflow, record=record)
        return record

    async def run_async(self, workflow_id: str,
                        initial_context: dict = None) -> ExecutionRecord:
        workflow = self.store.get_workflow(workflow_id) if self.store else None
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        return await self.execute_workflow(workflow, initial_context)

    def run(self, workflow_id: str, initial_context: dict = None) -> ExecutionRecord:
        """Synchronous wrapper for run_async."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.run_async(workflow_id, initial_context))

    def start_background(self, workflow_id: str,
                         initial_context: dict = None) -> str:
        task = asyncio.create_task(self.run_async(workflow_id, initial_context))
        self._running[workflow_id] = task
        return workflow_id

    async def cancel(self, workflow_id: str) -> bool:
        task = self._running.get(workflow_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def discover_nodes(self) -> dict:
        NodeRegistry.discover()
        return NodeRegistry.get_all()
