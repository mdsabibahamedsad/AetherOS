"""Tool Chaining Engine — cross-runtime workflow execution.

Allows chaining multiple tools across different runtimes into a single workflow.
Data flows from one step to the next via context propagation.

Example::
    Filesystem (read file)
    -> Python (process data)
    -> Browser (fetch web data)
    -> Git (commit results)
    -> Email (send notification)
    -> Desktop (show notification)
    -> Memory (store result)
    -> Chat (report to user)
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from tool_runtime.interface import ToolInterface, ToolMetadata, ToolResult, ToolStatus, ToolRiskLevel, ToolCategory
from tool_runtime.manager import ToolRuntimeManager, get_runtime_manager

logger = logging.getLogger(__name__)


@dataclass
class ChainStep:
    """A single step in a tool chain."""
    id: str
    runtime: str
    params: Dict[str, Any]
    description: str = ""
    depends_on: List[str] = field(default_factory=list)
    transform: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    timeout_seconds: float = 60.0
    result: Optional[ToolResult] = None
    error: Optional[str] = None


@dataclass
class ChainResult:
    """Result of executing a tool chain."""
    success: bool
    steps: List[ChainStep]
    duration_ms: float
    error: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)


class ChainingEngine(ToolInterface):
    """Cross-runtime tool chaining engine.

    Orchestrates sequential/parallel execution of tools across
    different runtimes with data flow between steps.
    """

    def __init__(self):
        meta = ToolMetadata(
            id="chaining",
            name="Tool Chaining Engine",
            description="Cross-runtime workflow: chain filesystem, python, browser, git, desktop, and more",
            category=ToolCategory.CHAINING,
            risk_level=ToolRiskLevel.EXECUTE,
            version="2.0.0",
            tags=["chain", "workflow", "orchestration"],
            requires_approval=False,
            timeout_seconds=120.0,
        )
        super().__init__(meta)
        self._manager: Optional[ToolRuntimeManager] = None

    @property
    def manager(self) -> ToolRuntimeManager:
        if self._manager is None:
            self._manager = get_runtime_manager()
        return self._manager

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "chaining",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "runtime": {"type": "string"},
                                "operation": {"type": "string"},
                                "params": {"type": "object"},
                                "depends_on": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "description": {"type": "string"},
                            },
                            "required": ["runtime", "operation"],
                        },
                    },
                    "context": {"type": "object", "description": "Initial context"},
                    "parallel": {"type": "boolean", "description": "Run steps in parallel where possible"},
                },
                "required": ["steps"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        steps = params.get("steps", [])
        if not steps:
            errors.append("Missing required parameter: steps")
        elif not isinstance(steps, list):
            errors.append("steps must be an array")
        else:
            for i, step in enumerate(steps):
                if "runtime" not in step:
                    errors.append(f"Step {i}: missing 'runtime'")
                if "operation" not in step:
                    errors.append(f"Step {i}: missing 'operation'")
        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        steps_data = params.get("steps", [])
        initial_context = params.get("context", {})
        parallel = params.get("parallel", False)

        runtime_context = dict(initial_context)
        runtime_context.update(context)

        steps = []
        for i, sd in enumerate(steps_data):
            step = ChainStep(
                id=sd.get("id", f"step_{i}"),
                runtime=sd["runtime"],
                params=sd.get("params", {}),
                description=sd.get("description", f"Step {i}: {sd['runtime']}.{sd['operation']}"),
                depends_on=sd.get("depends_on", []),
                timeout_seconds=sd.get("timeout", 60.0),
            )
            steps.append(step)

        chain_result = self._execute_chain(steps, runtime_context, parallel)

        if chain_result.success:
            return ToolResult.ok(chain_result.outputs)
        else:
            return ToolResult.fail(
                chain_result.error or "Chain execution failed",
                output=chain_result.outputs,
            )

    def _execute_chain(
        self,
        steps: List[ChainStep],
        context: Dict[str, Any],
        parallel: bool,
    ) -> ChainResult:
        start = time.time()

        completed: Dict[str, ChainStep] = {}
        outputs: Dict[str, Any] = {}

        ready = [s for s in steps if not s.depends_on]
        blocked = [s for s in steps if s.depends_on]
        errors: List[str] = []
        max_iter = len(steps) * 3
        iteration = 0

        while (ready or blocked) and iteration < max_iter:
            iteration += 1

            for step in ready[:]:
                ready.remove(step)
                step.params["chain_context"] = {
                    k: v for k, v in outputs.items()
                    if not k.startswith("_")
                }

                runtime = self._get_runtime_for_step(step)
                if not runtime:
                    step.error = f"Runtime not found for step '{step.runtime}'"
                    errors.append(step.error)
                    continue

                try:
                    result = self.manager.execute(
                        tool_name=step.runtime,
                        params=step.params,
                        context=context,
                        timeout_seconds=step.timeout_seconds,
                    )
                    step.result = result
                    if result.success:
                        step_out = result.output or {}
                        if isinstance(step_out, dict):
                            outputs[f"step:{step.id}"] = step_out
                            outputs[f"step:{step.id}.output"] = step_out.get("output", step_out)
                        else:
                            outputs[f"step:{step.id}"] = {"output": step_out}
                    else:
                        step.error = result.error
                        errors.append(f"Step '{step.id}' ({step.description}): {result.error}")
                except Exception as e:
                    step.error = str(e)
                    errors.append(f"Step '{step.id}' error: {e}")

                completed[step.id] = step

            new_ready = []
            for step in blocked[:]:
                deps_met = all(dep in completed for dep in step.depends_on)
                if deps_met:
                    blocked.remove(step)
                    new_ready.append(step)
            ready.extend(new_ready)

            if errors and not parallel:
                break

        elapsed = (time.time() - start) * 1000

        success = len(errors) == 0
        return ChainResult(
            success=success,
            steps=steps,
            duration_ms=elapsed,
            error="; ".join(errors) if errors else None,
            outputs=outputs,
        )

    def _get_runtime_for_step(self, step: ChainStep) -> Optional[str]:
        runtime_map = {
            "filesystem": "filesystem",
            "terminal": "terminal",
            "python": "python",
            "browser": "browser",
            "desktop": "desktop",
            "git": "git",
            "rest": "rest_api",
            "database": "database",
            "plugin": "plugin_manager",
            "read": "filesystem",
            "write": "filesystem",
            "search": "filesystem",
        }
        runtime_name = runtime_map.get(step.runtime, step.runtime)
        if self.manager.get_runtime(runtime_name):
            return runtime_name

        tool_map = {
            "read_file": "filesystem", "write_file": "filesystem",
            "terminal": "terminal", "python": "python",
            "browser": "browser", "desktop": "desktop",
            "git": "git", "github": "git",
        }
        for prefix, rt in tool_map.items():
            if step.runtime.startswith(prefix):
                if self.manager.get_runtime(rt):
                    return rt

        return None

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["available_runtimes"] = [
            r["name"] for r in self.manager.list_runtimes()
        ]
        return base
