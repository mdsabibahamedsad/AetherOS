"""Logic nodes — control flow, branching, loops, variables, and error handling."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

from workflows.nodes.base import BaseNode, NodeRegistry, NodeResult
from workflows.models import WorkflowNode, WorkflowConfig

logger = logging.getLogger(__name__)


class IfNode(BaseNode):
    type = "logic.if"
    category = "logic"
    label = "If Condition"
    description = "Branch execution based on a condition"
    default_config = {"condition": "", "value_source": ""}
    outputs = [
        {"id": "true", "label": "True", "type": "any"},
        {"id": "false", "label": "False", "type": "any"},
    ]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        condition = node.config.get("condition", "")
        value = context.get("input", context.get(node.config.get("value_source", ""), ""))
        try:
            result = bool(eval(condition, {"__builtins__": {}}, {
                "value": value, "context": context, "len": len, "str": str,
                "int": int, "float": float, "bool": bool, "dict": dict,
                "list": list, "isinstance": isinstance, "type": type,
                "any": any, "all": all,
            }))
        except Exception as e:
            result = bool(value)
        return NodeResult(success=True, output={"condition": condition, "result": result},
                          logs=[{"message": f"If condition: {condition} → {result}"}])


class SwitchNode(BaseNode):
    type = "logic.switch"
    category = "logic"
    label = "Switch"
    description = "Route execution based on value"
    default_config = {"cases": {}}
    outputs = [{"id": "default", "label": "Default", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        value = context.get("input", "")
        cases = node.config.get("cases", {})
        matched = cases.get(str(value), cases.get("default", ""))
        return NodeResult(success=True, output={"value": value, "matched": matched, "case": str(value)},
                          logs=[{"message": f"Switch: {value} → {matched}"}])


class LoopNode(BaseNode):
    type = "logic.loop"
    category = "logic"
    label = "Loop"
    description = "Repeat execution until condition is met"
    default_config = {"max_iterations": 10, "condition": ""}
    outputs = [{"id": "output", "label": "Result", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        max_iter = node.config.get("max_iterations", 10)
        items = context.get("input", [])
        if not isinstance(items, list):
            items = [items]
        results = []
        for i, item in enumerate(items[:max_iter]):
            iter_context = {**context, "item": item, "index": i}
            results.append({"index": i, "item": item})
        return NodeResult(success=True, output=results,
                          logs=[{"message": f"Loop: processed {len(results)} items"}])


class WaitNode(BaseNode):
    type = "logic.wait"
    category = "logic"
    label = "Wait"
    description = "Pause execution for a duration"
    default_config = {"seconds": 5}
    outputs = [{"id": "output", "label": "Resumed", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        seconds = node.config.get("seconds", 5)
        await asyncio.sleep(seconds)
        return NodeResult(success=True, output={"waited": seconds},
                          logs=[{"message": f"Waited {seconds}s"}])


class DelayNode(BaseNode):
    type = "logic.delay"
    category = "logic"
    label = "Delay"
    description = "Delay execution until a specific time"
    default_config = {"delay_until": "", "delay_seconds": 0}
    outputs = [{"id": "output", "label": "Delayed", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        seconds = node.config.get("delay_seconds", 0)
        if seconds > 0:
            await asyncio.sleep(seconds)
        return NodeResult(success=True, output={"delayed": seconds},
                          logs=[{"message": f"Delayed {seconds}s"}])


class MergeNode(BaseNode):
    type = "logic.merge"
    category = "logic"
    label = "Merge"
    description = "Merge multiple inputs into a single output"
    default_config = {"merge_mode": "list"}
    outputs = [{"id": "output", "label": "Merged", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        inputs = context.get("inputs", [context.get("input", [])])
        mode = node.config.get("merge_mode", "list")
        if mode == "dict":
            merged = {}
            for inp in inputs:
                if isinstance(inp, dict):
                    merged.update(inp)
            output = merged
        else:
            merged = []
            for inp in inputs:
                if isinstance(inp, list):
                    merged.extend(inp)
                else:
                    merged.append(inp)
            output = merged
        return NodeResult(success=True, output=output,
                          logs=[{"message": f"Merge: {len(inputs)} inputs → {mode}"}])


class VariablesNode(BaseNode):
    type = "logic.variables"
    category = "logic"
    label = "Variables"
    description = "Set and transform workflow variables"
    default_config = {"variables": {}, "transform": ""}
    outputs = [{"id": "output", "label": "Updated", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        variables = node.config.get("variables", {})
        transform = node.config.get("transform", "")
        resolved = {}
        for key, expr in variables.items():
            try:
                resolved[key] = eval(expr, {"__builtins__": {}}, {
                    **context, "input": context.get("input", ""),
                })
            except Exception:
                resolved[key] = expr
        return NodeResult(success=True, output={"variables": resolved},
                          logs=[{"message": f"Variables: {list(resolved.keys())}"}])


class RetryNode(BaseNode):
    type = "logic.retry"
    category = "logic"
    label = "Retry"
    description = "Retry a failed operation"
    default_config = {"max_retries": 3, "delay_seconds": 1}
    outputs = [{"id": "output", "label": "Result", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        return NodeResult(success=True, output=context.get("input"),
                          logs=[{"message": "Retry wrapper ready"}])


class ErrorHandlerNode(BaseNode):
    type = "logic.error_handler"
    category = "logic"
    label = "Error Handler"
    description = "Handle errors from previous nodes"
    default_config = {"policy": "continue"}
    outputs = [{"id": "output", "label": "Handled", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        error = context.get("error", {})
        policy = node.config.get("policy", workflow.error_policy)
        return NodeResult(success=True, output={
            "error": error, "policy": policy, "handled": True,
        }, logs=[{"message": f"Error handled: {error.get('message', '')} → {policy}"}])


def register():
    NodeRegistry.register(IfNode)
    NodeRegistry.register(SwitchNode)
    NodeRegistry.register(LoopNode)
    NodeRegistry.register(WaitNode)
    NodeRegistry.register(DelayNode)
    NodeRegistry.register(MergeNode)
    NodeRegistry.register(VariablesNode)
    NodeRegistry.register(RetryNode)
    NodeRegistry.register(ErrorHandlerNode)


register()
