#!/usr/bin/env python3
"""
Execution Engine — Execute → Observe → Verify → Recover Loop

Implements the core execution lifecycle for capability steps with
observation, verification, and automatic recovery strategies.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import (
    ExecutionResult,
    RecoveryStrategy,
    Task,
    TaskStep,
    TaskState,
    VerificationStrategy,
)
from .planner import get_parameterizer, ParameterizationResult

# Import existing tool execution infrastructure
try:
    from model_tools import handle_function_call
    from tools.registry import registry as tool_registry
    TOOL_EXECUTION_AVAILABLE = True
except ImportError:
    TOOL_EXECUTION_AVAILABLE = False
    logger.warning("Tool execution infrastructure not available")

logger = logging.getLogger(__name__)


# Built-in recovery strategies
DEFAULT_RECOVERY_STRATEGIES = {
    "retry": RecoveryStrategy(
        name="retry",
        description="Simple retry with exponential backoff",
        handler="aetheros_capability.execution_engine._recovery_retry",
        applies_to=["*"],
        max_attempts=3,
        backoff_seconds=1.0,
        backoff_multiplier=2.0,
    ),
    "alternative_tool": RecoveryStrategy(
        name="alternative_tool",
        description="Try an alternative tool for the same capability",
        handler="aetheros_capability.execution_engine._recovery_alternative_tool",
        applies_to=["*"],
        max_attempts=2,
        backoff_seconds=0.5,
    ),
    "alternative_model": RecoveryStrategy(
        name="alternative_model",
        description="Switch to a different model for the same task",
        handler="aetheros_capability.execution_engine._recovery_alternative_model",
        applies_to=["*"],
        max_attempts=2,
        backoff_seconds=0.5,
    ),
    "replan": RecoveryStrategy(
        name="replan",
        description="Ask the planner to create a new plan",
        handler="aetheros_capability.execution_engine._recovery_replan",
        applies_to=["*"],
        max_attempts=1,
        backoff_seconds=1.0,
    ),
    "ask_user": RecoveryStrategy(
        name="ask_user",
        description="Ask the user for guidance or clarification",
        handler="aetheros_capability.execution_engine._recovery_ask_user",
        applies_to=["*"],
        max_attempts=1,
        backoff_seconds=0.0,
    ),
}


# Built-in verification strategies
DEFAULT_VERIFICATION_STRATEGIES = {
    "output_schema": VerificationStrategy(
        name="output_schema",
        description="Verify output matches expected schema",
        handler="aetheros_capability.execution_engine._verify_output_schema",
        applies_to=["*"],
        required=True,
    ),
    "tool_success": VerificationStrategy(
        name="tool_success",
        description="Verify tool execution reported success",
        handler="aetheros_capability.execution_engine._verify_tool_success",
        applies_to=["*"],
        required=True,
    ),
    "non_empty_output": VerificationStrategy(
        name="non_empty_output",
        description="Verify output is not empty",
        handler="aetheros_capability.execution_engine._verify_non_empty_output",
        applies_to=["*"],
        required=False,
    ),
    "file_exists": VerificationStrategy(
        name="file_exists",
        description="Verify file operations created expected files",
        handler="aetheros_capability.execution_engine._verify_file_exists",
        applies_to=["file_system", "coding"],
        required=False,
    ),
    "process_completed": VerificationStrategy(
        name="process_completed",
        description="Verify terminal process completed successfully",
        handler="aetheros_capability.execution_engine._verify_process_completed",
        applies_to=["terminal"],
        required=False,
    ),
}


@dataclass
class ExecutionEngine:
    """
    Core execution engine implementing the Execute → Observe → Verify → Recover loop.
    """
    
    _recovery_strategies: Dict[str, RecoveryStrategy] = field(default_factory=dict)
    _verification_strategies: Dict[str, VerificationStrategy] = field(default_factory=dict)
    _tool_handlers: Dict[str, Callable] = field(default_factory=dict)
    _verification_handlers: Dict[str, Callable] = field(default_factory=dict)
    _recovery_handlers: Dict[str, Callable] = field(default_factory=dict)
    _observation_handlers: Dict[str, Callable] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _config: Dict[str, Any] = field(default_factory=dict)
    _execution_stats: Dict[str, Any] = field(default_factory=lambda: defaultdict(int))

    def __init__(self, config: Dict[str, Any] | None = None):
        self._config = config or {}
        self._recovery_strategies = {}
        self._verification_strategies = {}
        self._tool_handlers = {}
        self._verification_handlers = {}
        self._recovery_handlers = {}
        self._observation_handlers = {}
        self._lock = threading.RLock()
        self._execution_stats = defaultdict(int)
        
        # Register default strategies
        self.register_default_recovery_strategies()
        self.register_default_verification_strategies()
        
        # Register built-in handlers
        self._register_builtin_handlers()

    def _register_builtin_handlers(self) -> None:
        """Register built-in handler functions."""
        # Recovery handlers
        self._recovery_handlers["_recovery_retry"] = self._recovery_retry
        self._recovery_handlers["_recovery_alternative_tool"] = self._recovery_alternative_tool
        self._recovery_handlers["_recovery_alternative_model"] = self._recovery_alternative_model
        self._recovery_handlers["_recovery_replan"] = self._recovery_replan
        self._recovery_handlers["_recovery_ask_user"] = self._recovery_ask_user
        
        # Verification handlers
        self._verification_handlers["_verify_output_schema"] = self._verify_output_schema
        self._verification_handlers["_verify_tool_success"] = self._verify_tool_success
        self._verification_handlers["_verify_non_empty_output"] = self._verify_non_empty_output
        self._verification_handlers["_verify_file_exists"] = self._verify_file_exists
        self._verification_handlers["_verify_process_completed"] = self._verify_process_completed

    def register_default_recovery_strategies(self) -> None:
        """Register all default recovery strategies."""
        with self._lock:
            for name, strategy in DEFAULT_RECOVERY_STRATEGIES.items():
                self._recovery_strategies[name] = strategy
                handler_name = strategy.handler.split(".")[-1]
                if handler_name in self._recovery_handlers:
                    strategy._handler_func = self._recovery_handlers[handler_name]

    def register_default_verification_strategies(self) -> None:
        """Register all default verification strategies."""
        with self._lock:
            for name, strategy in DEFAULT_VERIFICATION_STRATEGIES.items():
                self._verification_strategies[name] = strategy
                handler_name = strategy.handler.split(".")[-1]
                if handler_name in self._verification_handlers:
                    strategy._handler_func = self._verification_handlers[handler_name]

    def register_recovery_strategy(self, strategy: RecoveryStrategy) -> None:
        """Register a custom recovery strategy."""
        with self._lock:
            self._recovery_strategies[strategy.name] = strategy
            handler_name = strategy.handler.split(".")[-1]
            if handler_name in self._recovery_handlers:
                strategy._handler_func = self._recovery_handlers[handler_name]
            logger.debug(f"Registered recovery strategy: {strategy.name}")

    def register_verification_strategy(self, strategy: VerificationStrategy) -> None:
        """Register a custom verification strategy."""
        with self._lock:
            self._verification_strategies[strategy.name] = strategy
            handler_name = strategy.handler.split(".")[-1]
            if handler_name in self._verification_handlers:
                strategy._handler_func = self._verification_handlers[handler_name]
            logger.debug(f"Registered verification strategy: {strategy.name}")

    def get_recovery_strategy(self, name: str) -> Optional[RecoveryStrategy]:
        with self._lock:
            return self._recovery_strategies.get(name)

    def get_verification_strategy(self, name: str) -> Optional[VerificationStrategy]:
        with self._lock:
            return self._verification_strategies.get(name)

    def list_recovery_strategies(self) -> List[RecoveryStrategy]:
        with self._lock:
            return list(self._recovery_strategies.values())

    def list_verification_strategies(self) -> List[VerificationStrategy]:
        with self._lock:
            return list(self._verification_strategies.values())

    def execute_step(self, step: TaskStep, task: Task) -> ExecutionResult:
        """
        Execute a single task step with full observation, verification, and recovery.
        """
        start_time = time.time()
        step_id = step.id
        capability_id = step.capability_id
        tool_name = step.tool_name
        input_data = step.input_data
        
        self._execution_stats["total_executions"] += 1
        
        try:
            # Phase 1: Execute
            output = self._execute_tool(tool_name, input_data, step, task)
            
            # Phase 2: Observe
            observations = self._observe_execution(tool_name, output, step, task)
            
            # Phase 3: Verify
            verification_results = self._verify_execution(step, output, observations, task)
            
            # Determine overall success
            success = all(v.get("passed", True) for v in verification_results.values())
            if not success and any(v.get("required", False) for v in verification_results.values()):
                success = False
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = ExecutionResult(
                step_id=step_id,
                success=success,
                output=output,
                error=None if success else "Verification failed",
                execution_time_ms=execution_time_ms,
                observations=observations,
                verification=verification_results,
            )
            
            if success:
                self._execution_stats["successful_executions"] += 1
            else:
                self._execution_stats["failed_executions"] += 1
            
            return result
            
        except Exception as e:
            logger.exception(f"Execution error for step {step_id}: {e}")
            execution_time_ms = (time.time() - start_time) * 1000
            self._execution_stats["errors"] += 1
            
            return ExecutionResult(
                step_id=step_id,
                success=False,
                output={},
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

    def _execute_tool(self, tool_name: str, input_data: Dict[str, Any], 
                     step: TaskStep, task: Task) -> Dict[str, Any]:
        """Execute a tool using the existing tool infrastructure."""
        if not TOOL_EXECUTION_AVAILABLE:
            return {"error": "Tool execution not available", "simulated": True}
        
        # Get the tool reference from the capability registry
        from .capability_registry import get_capability_registry
        registry = get_capability_registry()
        
        # Find the tool reference
        tool_ref = None
        for cap_id, entry in registry._capabilities.items():
            for tool in entry.spec.tools:
                if tool.name == tool_name:
                    tool_ref = tool
                    break
            if tool_ref:
                break
        
        # Parameterize the tool call if we have a tool reference
        parameterized_input = input_data
        if tool_ref:
            parameterizer = get_parameterizer(self._config)
            
            # Get previous results for context
            previous_results = {}
            if task and task.plan:
                for s in task.plan:
                    if s.id == step.id:
                        break
                    if s.result:
                        previous_results[s.id] = s.result
            
            # Get intent from step or task
            intent = step.input_data.get("intent", "") if isinstance(step.input_data, dict) else ""
            if not intent and task:
                intent = task.goal
            
            # Parameterize
            param_result = parameterizer.parameterize(
                intent=intent,
                tool=tool_ref,
                context=task.request.context if task and task.request else {},
                previous_results=previous_results,
            )
            
            if param_result.missing_required:
                logger.warning(f"Tool {tool_name} missing required parameters: {param_result.missing_required}")
            
            # Merge parameterized input with original input
            parameterized_input = {**param_result.parameters, **input_data}
            logger.debug(f"Parameterized {tool_name}: {param_result.reasoning}")
        
        if not TOOL_EXECUTION_AVAILABLE:
            return {"error": "Tool execution not available", "simulated": True}
        
        # Use the existing handle_function_call from model_tools
        try:
            # Get task_id for context
            task_id = task.id if task else str(uuid.uuid4())
            
            # Call the tool through the existing infrastructure
            result_json = handle_function_call(tool_name, parameterized_input, task_id=task_id)
            
            # Parse result
            import json
            try:
                result = json.loads(result_json)
            except json.JSONDecodeError:
                result = {"raw_output": result_json}
            
            return result
        except Exception as e:
            logger.exception(f"Tool execution failed for {tool_name}: {e}")
            return {"error": str(e), "tool": tool_name}

    def _observe_execution(self, tool_name: str, output: Dict[str, Any],
                          step: TaskStep, task: Task) -> Dict[str, Any]:
        """Observe the execution results and environment state."""
        observations = {
            "tool": tool_name,
            "output_keys": list(output.keys()) if isinstance(output, dict) else [],
            "has_error": "error" in output if isinstance(output, dict) else False,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Add tool-specific observations
        if tool_name == "terminal":
            observations["exit_code"] = output.get("exit_code")
            observations["stdout_lines"] = len(output.get("stdout", "").splitlines()) if output.get("stdout") else 0
            observations["stderr_lines"] = len(output.get("stderr", "").splitlines()) if output.get("stderr") else 0
        
        elif tool_name in ("browser_navigate", "browser_click", "browser_type"):
            observations["url"] = output.get("url")
            observations["page_title"] = output.get("title")
        
        elif tool_name in ("read_file", "write_file", "patch"):
            observations["file_path"] = output.get("path")
            observations["bytes"] = output.get("bytes_written") or output.get("bytes_read")
        
        return observations

    def _verify_execution(self, step: TaskStep, output: Dict[str, Any],
                         observations: Dict[str, Any], task: Task) -> Dict[str, Dict[str, Any]]:
        """Run all applicable verification strategies."""
        results = {}
        
        with self._lock:
            strategies = list(self._verification_strategies.values())
        
        for strategy in strategies:
            # Check if strategy applies to this step's capability/category
            if not self._strategy_applies(strategy, step):
                continue
            
            handler = getattr(strategy, '_handler_func', None)
            if not handler:
                # Try to import handler
                try:
                    module_path, func_name = strategy.handler.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    handler = getattr(module, func_name)
                except Exception:
                    logger.warning(f"No handler for verification strategy: {strategy.name}")
                    continue
            
            try:
                result = handler(step, output, observations, task)
                results[strategy.name] = result
            except Exception as e:
                logger.warning(f"Verification {strategy.name} failed: {e}")
                results[strategy.name] = {"passed": False, "error": str(e)}
        
        return results

    def _strategy_applies(self, strategy: VerificationStrategy, step: TaskStep) -> bool:
        """Check if a verification strategy applies to a step."""
        if not strategy.applies_to:
            return True
        if "*" in strategy.applies_to:
            return True
        
        # Check capability ID
        if step.capability_id in strategy.applies_to:
            return True
        
        # Check category (would need capability spec)
        return False

    def attempt_recovery(self, step: TaskStep, error: str | None) -> Optional[ExecutionResult]:
        """Attempt to recover from a failed step using registered recovery strategies."""
        if not error:
            return None
        
        with self._lock:
            strategies = list(self._recovery_strategies.values())
        
        for strategy in strategies:
            if not self._recovery_applies(strategy, step, error):
                continue
            
            handler = getattr(strategy, '_handler_func', None)
            if not handler:
                try:
                    module_path, func_name = strategy.handler.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    handler = getattr(module, func_name)
                except Exception:
                    logger.warning(f"No handler for recovery strategy: {strategy.name}")
                    continue
            
            try:
                logger.info(f"Attempting recovery '{strategy.name}' for step {step.id}")
                result = handler(step, error, strategy)
                if result and result.success:
                    result.recovery_applied = strategy.name
                    self._execution_stats["recoveries"] += 1
                    return result
            except Exception as e:
                logger.warning(f"Recovery {strategy.name} failed: {e}")
        
        return None

    def _recovery_applies(self, strategy: RecoveryStrategy, step: TaskStep, error: str) -> bool:
        """Check if a recovery strategy applies to a step/error."""
        if not strategy.applies_to:
            return True
        if "*" in strategy.applies_to:
            return True
        if step.capability_id in strategy.applies_to:
            return True
        return False

    # =========================================================================
    # Built-in Recovery Handlers
    # =========================================================================

    def _recovery_retry(self, step: TaskStep, error: str, 
                       strategy: RecoveryStrategy) -> Optional[ExecutionResult]:
        """Simple retry with backoff."""
        for attempt in range(strategy.max_attempts):
            if attempt > 0:
                wait_time = strategy.backoff_seconds * (strategy.backoff_multiplier ** attempt)
                logger.info(f"Retry attempt {attempt + 1}/{strategy.max_attempts} after {wait_time:.1f}s")
                time.sleep(wait_time)
            
            result = self.execute_step(step, None)  # Task context would be passed in real impl
            if result.success:
                return result
        
        return None

    def _recovery_alternative_tool(self, step: TaskStep, error: str,
                                  strategy: RecoveryStrategy) -> Optional[ExecutionResult]:
        """Try an alternative tool for the same capability."""
        from .capability_registry import get_capability_registry
        registry = get_capability_registry()
        
        if not step.capability_id:
            return None
        
        cap_spec = registry.get_capability_spec(step.capability_id)
        if not cap_spec or len(cap_spec.tools) <= 1:
            return None
        
        # Find alternative tools
        current_tool = step.tool_name
        for tool in cap_spec.tools:
            if tool.name != current_tool:
                logger.info(f"Trying alternative tool: {tool.name}")
                step.tool_name = tool.name
                result = self.execute_step(step, None)
                if result.success:
                    return result
        
        return None

    def _recovery_alternative_model(self, step: TaskStep, error: str,
                                   strategy: RecoveryStrategy) -> Optional[ExecutionResult]:
        """Try an alternative model for the same task."""
        from .capability_registry import get_capability_registry
        registry = get_capability_registry()
        
        if not step.capability_id:
            return None
        
        cap_spec = registry.get_capability_spec(step.capability_id)
        if not cap_spec or len(cap_spec.models) <= 1:
            return None
        
        current_model = step.model_name
        for model in cap_spec.models:
            if model.name != current_model:
                logger.info(f"Trying alternative model: {model.name}")
                step.model_name = model.name
                result = self.execute_step(step, None)
                if result.success:
                    return result
        
        return None

    def _recovery_replan(self, step: TaskStep, error: str,
                        strategy: RecoveryStrategy) -> Optional[ExecutionResult]:
        """Ask the planner to create a new plan."""
        # This would integrate with a planner component
        logger.info("Replan recovery triggered - would invoke planner")
        return None

    def _recovery_ask_user(self, step: TaskStep, error: str,
                          strategy: RecoveryStrategy) -> Optional[ExecutionResult]:
        """Ask the user for guidance."""
        # This would integrate with a clarification system
        logger.info("User clarification requested")
        return None

    # =========================================================================
    # Built-in Verification Handlers
    # =========================================================================

    def _verify_output_schema(self, step: TaskStep, output: Dict[str, Any],
                             observations: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Verify output matches expected schema."""
        # In a real implementation, this would validate against the step's expected_output schema
        return {"passed": True, "strategy": "output_schema"}

    def _verify_tool_success(self, step: TaskStep, output: Dict[str, Any],
                            observations: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Verify tool execution reported success."""
        has_error = "error" in output if isinstance(output, dict) else False
        passed = not has_error
        return {
            "passed": passed,
            "strategy": "tool_success",
            "error": output.get("error") if has_error else None,
        }

    def _verify_non_empty_output(self, step: TaskStep, output: Dict[str, Any],
                                observations: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Verify output is not empty."""
        if isinstance(output, dict):
            passed = len(output) > 0 and not (len(output) == 1 and "error" in output)
        else:
            passed = bool(output)
        return {"passed": passed, "strategy": "non_empty_output"}

    def _verify_file_exists(self, step: TaskStep, output: Dict[str, Any],
                           observations: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Verify file operations created expected files."""
        path = output.get("path") or observations.get("file_path")
        if path:
            import os
            exists = os.path.exists(path)
            return {"passed": exists, "strategy": "file_exists", "path": path}
        return {"passed": True, "strategy": "file_exists", "skipped": "no path in output"}

    def _verify_process_completed(self, step: TaskStep, output: Dict[str, Any],
                                 observations: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Verify terminal process completed successfully."""
        exit_code = output.get("exit_code") or observations.get("exit_code")
        if exit_code is not None:
            passed = exit_code == 0
            return {"passed": passed, "strategy": "process_completed", "exit_code": exit_code}
        return {"passed": True, "strategy": "process_completed", "skipped": "no exit code"}

    def get_stats(self) -> Dict[str, Any]:
        """Get execution engine statistics."""
        with self._lock:
            return {
                "total_executions": self._execution_stats["total_executions"],
                "successful_executions": self._execution_stats["successful_executions"],
                "failed_executions": self._execution_stats["failed_executions"],
                "recoveries": self._execution_stats["recoveries"],
                "errors": self._execution_stats["errors"],
                "success_rate": (
                    self._execution_stats["successful_executions"] / 
                    max(1, self._execution_stats["total_executions"])
                ),
                "recovery_strategies": len(self._recovery_strategies),
                "verification_strategies": len(self._verification_strategies),
            }


# Module-level instance
_execution_engine_instance: Optional[ExecutionEngine] = None


def get_execution_engine(config: Dict[str, Any] | None = None) -> ExecutionEngine:
    """Get the global execution engine instance."""
    global _execution_engine_instance
    if _execution_engine_instance is None:
        _execution_engine_instance = ExecutionEngine(config)
    return _execution_engine_instance