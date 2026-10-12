"""Budget Management for AetherOS Orchestration Layer.

Implements Phases 44-48 of Master Prompt 11: resource budgets, cost control,
rate limiting, concurrency control, recursion control, and loop detection.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

from agent.orchestration.types import TaskBudget, BudgetSnapshot, TaskSpec

logger = logging.getLogger(__name__)


# =============================================================================
# Budget Types
# =============================================================================


class BudgetType(Enum):
    """Types of budgets."""

    TIME = "time"              # Wall-clock time (seconds)
    TOKENS = "tokens"          # Model tokens
    COST = "cost"              # Monetary cost (USD)
    TOOL_CALLS = "tool_calls"  # Number of tool invocations
    ITERATIONS = "iterations"  # Agent iterations
    PARALLEL_TASKS = "parallel_tasks"  # Concurrent subtasks
    SUBAGENTS = "subagents"    # Number of subagents spawned


class BudgetAction(Enum):
    """Actions when budget is exceeded."""

    WARN = "warn"              # Log warning, continue
    BLOCK = "block"            # Block further operations
    PAUSE = "pause"            # Pause task
    FAIL = "fail"              # Fail task
    FALLBACK = "fallback"      # Switch to fallback (cheaper model/agent)


@dataclass
class BudgetLimit:
    """A single budget limit."""

    budget_type: BudgetType
    limit: float
    action: BudgetAction = BudgetAction.BLOCK
    warning_threshold: float = 0.8  # Warn at 80%
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetUsage:
    """Current budget usage for a task."""

    task_id: str
    time_seconds: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    iterations: int = 0
    parallel_tasks: int = 0
    subagents: int = 0
    updated_at: float = field(default_factory=time.time)

    def to_snapshot(self) -> BudgetSnapshot:
        """Convert to budget snapshot."""
        return BudgetSnapshot(
            time_seconds=self.time_seconds,
            tokens_used=self.tokens_used,
            cost_usd=self.cost_usd,
            tool_calls=self.tool_calls,
            iterations=self.iterations,
            parallel_subtasks=self.parallel_tasks,
            subagents=self.subagents,
        )

    def get_usage(self, budget_type: BudgetType) -> float:
        """Get usage for a budget type."""
        mapping = {
            BudgetType.TIME: self.time_seconds,
            BudgetType.TOKENS: float(self.tokens_used),
            BudgetType.COST: self.cost_usd,
            BudgetType.TOOL_CALLS: float(self.tool_calls),
            BudgetType.ITERATIONS: float(self.iterations),
            BudgetType.PARALLEL_TASKS: float(self.parallel_tasks),
            BudgetType.SUBAGENTS: float(self.subagents),
        }
        return mapping.get(budget_type, 0.0)


# =============================================================================
# Budget Manager
# =============================================================================


class BudgetManager:
    """Manages resource budgets for tasks with enforcement."""

    def __init__(
        self,
        default_limits: Optional[List[BudgetLimit]] = None,
        global_limits: Optional[Dict[BudgetType, float]] = None,
    ):
        self._default_limits = default_limits or self._get_default_limits()
        self._global_limits = global_limits or {}
        self._task_budgets: Dict[str, BudgetUsage] = {}
        self._task_limits: Dict[str, List[BudgetLimit]] = {}
        self._global_usage: Dict[BudgetType, float] = defaultdict(float)
        self._lock = asyncio.Lock()
        self._callbacks: Dict[str, List[Callable[[str, BudgetType, float, float], None]]] = {}
        self._enforcement_enabled = True

    def _get_default_limits(self) -> List[BudgetLimit]:
        """Get default budget limits."""
        return [
            BudgetLimit(BudgetType.TIME, 3600.0, BudgetAction.FAIL),  # 1 hour
            BudgetLimit(BudgetType.TOKENS, 100000, BudgetAction.FAIL),
            BudgetLimit(BudgetType.COST, 10.0, BudgetAction.FAIL),
            BudgetLimit(BudgetType.TOOL_CALLS, 100, BudgetAction.FAIL),
            BudgetLimit(BudgetType.ITERATIONS, 50, BudgetAction.FAIL),
            BudgetLimit(BudgetType.PARALLEL_TASKS, 5, BudgetAction.BLOCK),
            BudgetLimit(BudgetType.SUBAGENTS, 3, BudgetAction.BLOCK),
        ]

    def set_task_budget(self, task_id: str, budget: TaskBudget, custom_limits: Optional[List[BudgetLimit]] = None) -> None:
        """Set budget for a task."""
        usage = BudgetUsage(task_id=task_id)
        self._task_budgets[task_id] = usage

        # Convert TaskBudget to BudgetLimits
        limits = custom_limits or []
        limits.append(BudgetLimit(BudgetType.TIME, budget.max_time_seconds, BudgetAction.FAIL))
        limits.append(BudgetLimit(BudgetType.TOKENS, budget.max_tokens, BudgetAction.FAIL))
        limits.append(BudgetLimit(BudgetType.COST, budget.max_cost_usd, BudgetAction.FAIL))
        limits.append(BudgetLimit(BudgetType.TOOL_CALLS, budget.max_tool_calls, BudgetAction.FAIL))
        limits.append(BudgetLimit(BudgetType.ITERATIONS, budget.max_iterations, BudgetAction.FAIL))
        limits.append(BudgetLimit(BudgetType.PARALLEL_TASKS, budget.max_parallel_subtasks, BudgetAction.BLOCK))
        limits.append(BudgetLimit(BudgetType.SUBAGENTS, budget.max_subagents, BudgetAction.BLOCK))

        # Add defaults for any missing
        for default in self._default_limits:
            if not any(l.budget_type == default.budget_type for l in limits):
                limits.append(default)

        self._task_limits[task_id] = limits

    def get_task_usage(self, task_id: str) -> Optional[BudgetUsage]:
        """Get current budget usage for a task."""
        return self._task_budgets.get(task_id)

    def get_task_limits(self, task_id: str) -> List[BudgetLimit]:
        """Get budget limits for a task."""
        return self._task_limits.get(task_id, self._default_limits)

    def record_usage(
        self,
        task_id: str,
        budget_type: BudgetType,
        amount: float,
    ) -> bool:
        """Record budget usage. Returns True if within limits."""
        usage = self._task_budgets.get(task_id)
        if not usage:
            logger.warning(f"Recording usage for unknown task: {task_id}")
            return True

        # Update task usage
        if budget_type == BudgetType.TIME:
            usage.time_seconds += amount
        elif budget_type == BudgetType.TOKENS:
            usage.tokens_used += int(amount)
        elif budget_type == BudgetType.COST:
            usage.cost_usd += amount
        elif budget_type == BudgetType.TOOL_CALLS:
            usage.tool_calls += int(amount)
        elif budget_type == BudgetType.ITERATIONS:
            usage.iterations += int(amount)
        elif budget_type == BudgetType.PARALLEL_TASKS:
            usage.parallel_tasks = max(usage.parallel_tasks, int(amount))
        elif budget_type == BudgetType.SUBAGENTS:
            usage.subagents = max(usage.subagents, int(amount))

        usage.updated_at = time.time()

        # Update global usage
        self._global_usage[budget_type] += amount

        # Check limits
        return self._check_limits(task_id, budget_type, usage)

    def _check_limits(self, task_id: str, budget_type: BudgetType, usage: BudgetUsage) -> bool:
        """Check if usage exceeds limits."""
        limits = self._task_limits.get(task_id, self._default_limits)

        for limit in limits:
            if limit.budget_type != budget_type:
                continue

            current = usage.get_usage(budget_type)
            percentage = current / limit.limit if limit.limit > 0 else 0

            # Warning
            if percentage >= limit.warning_threshold and percentage < 1.0:
                self._notify_warning(task_id, budget_type, current, limit.limit)

            # Exceeded
            if current >= limit.limit:
                self._notify_exceeded(task_id, budget_type, current, limit.limit, limit.action)
                if limit.action == BudgetAction.BLOCK or limit.action == BudgetAction.FAIL:
                    return False

        # Check global limits
        global_limit = self._global_limits.get(budget_type)
        if global_limit:
            global_current = self._global_usage[budget_type]
            if global_current >= global_limit:
                logger.warning(f"Global budget exceeded for {budget_type.value}: {global_current}/{global_limit}")
                return False

        return True

    def _notify_warning(self, task_id: str, budget_type: BudgetType, current: float, limit: float) -> None:
        """Notify about budget warning."""
        for cb in self._callbacks.get("warning", []):
            try:
                cb(task_id, budget_type, current, limit)
            except Exception as e:
                logger.warning(f"Budget warning callback failed: {e}")

    def _notify_exceeded(self, task_id: str, budget_type: BudgetType, current: float, limit: float, action: BudgetAction) -> None:
        """Notify about budget exceeded."""
        for cb in self._callbacks.get("exceeded", []):
            try:
                cb(task_id, budget_type, current, limit, action)
            except Exception as e:
                logger.warning(f"Budget exceeded callback failed: {e}")

    def register_callback(
        self,
        event: str,
        callback: Callable[[str, BudgetType, float, float, Optional[BudgetAction]], None],
    ) -> None:
        """Register callback for budget events."""
        self._callbacks.setdefault(event, []).append(callback)

    def check_budget(self, task_id: str, budget_type: BudgetType, projected_amount: float = 0) -> bool:
        """Check if an operation would exceed budget."""
        usage = self._task_budgets.get(task_id)
        if not usage:
            return True

        current = usage.get_usage(budget_type) + projected_amount
        limits = self._task_limits.get(task_id, self._default_limits)

        for limit in limits:
            if limit.budget_type == budget_type:
                if current >= limit.limit:
                    return False

        # Check global
        global_limit = self._global_limits.get(budget_type)
        if global_limit:
            if self._global_usage[budget_type] + projected_amount >= global_limit:
                return False

        return True

    def get_remaining(self, task_id: str, budget_type: BudgetType) -> float:
        """Get remaining budget for a type."""
        usage = self._task_budgets.get(task_id)
        if not usage:
            return float('inf')

        limits = self._task_limits.get(task_id, self._default_limits)
        for limit in limits:
            if limit.budget_type == budget_type:
                return max(0, limit.limit - usage.get_usage(budget_type))

        return float('inf')

    def get_budget_status(self, task_id: str) -> Dict[str, Any]:
        """Get comprehensive budget status for a task."""
        usage = self._task_budgets.get(task_id)
        if not usage:
            return {"error": "Task not found"}

        limits = self._task_limits.get(task_id, self._default_limits)
        status = {}

        for limit in limits:
            current = usage.get_usage(limit.budget_type)
            status[limit.budget_type.value] = {
                "used": current,
                "limit": limit.limit,
                "remaining": max(0, limit.limit - current),
                "percentage": current / limit.limit if limit.limit > 0 else 0,
                "action": limit.action.value,
                "warning_at": limit.warning_threshold,
            }

        return status

    def release_task_budget(self, task_id: str) -> None:
        """Release budget tracking for a completed task."""
        self._task_budgets.pop(task_id, None)
        self._task_limits.pop(task_id, None)

    def set_global_limit(self, budget_type: BudgetType, limit: float) -> None:
        """Set a global budget limit."""
        self._global_limits[budget_type] = limit

    def get_global_usage(self) -> Dict[str, float]:
        """Get global budget usage."""
        return {bt.value: usage for bt, usage in self._global_usage.items()}


# =============================================================================
# Cost Control
# =============================================================================


class CostController:
    """Controls costs across tasks with optimization strategies."""

    def __init__(self, budget_manager: BudgetManager):
        self._budget = budget_manager
        self._model_costs: Dict[str, Dict[str, float]] = {}  # model -> {input, output} per 1k tokens
        self._tool_costs: Dict[str, float] = {}
        self._cost_history: List[Dict[str, Any]] = []

    def register_model_cost(self, model: str, input_cost_per_1k: float, output_cost_per_1k: float) -> None:
        """Register model pricing."""
        self._model_costs[model] = {
            "input": input_cost_per_1k,
            "output": output_cost_per_1k,
        }

    def register_tool_cost(self, tool: str, cost_per_call: float) -> None:
        """Register tool cost."""
        self._tool_costs[tool] = cost_per_call

    def estimate_task_cost(
        self,
        task: TaskSpec,
        model: str = "",
        estimated_input_tokens: int = 1000,
        estimated_output_tokens: int = 2000,
        estimated_tool_calls: int = 10,
    ) -> float:
        """Estimate cost for a task."""
        cost = 0.0

        # Model cost
        if model and model in self._model_costs:
            mc = self._model_costs[model]
            cost += (estimated_input_tokens / 1000) * mc["input"]
            cost += (estimated_output_tokens / 1000) * mc["output"]
        else:
            # Default estimate
            cost += 0.01

        # Tool costs
        cost += estimated_tool_calls * 0.001

        # Add buffer
        return cost * 1.2

    def record_actual_cost(self, task_id: str, model: str, input_tokens: int, output_tokens: int, tool_calls: int) -> float:
        """Record actual cost from execution."""
        cost = 0.0

        if model in self._model_costs:
            mc = self._model_costs[model]
            cost += (input_tokens / 1000) * mc["input"]
            cost += (output_tokens / 1000) * mc["output"]

        for _ in range(tool_calls):
            cost += 0.001  # Default tool cost

        # Record in budget manager
        self._budget.record_usage(task_id, BudgetType.COST, cost)
        self._budget.record_usage(task_id, BudgetType.TOKENS, input_tokens + output_tokens)
        self._budget.record_usage(task_id, BudgetType.TOOL_CALLS, tool_calls)

        # Record history
        self._cost_history.append({
            "task_id": task_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tool_calls": tool_calls,
            "cost": cost,
            "timestamp": time.time(),
        })

        return cost

    def get_cost_report(self, task_id: str = None) -> Dict[str, Any]:
        """Get cost report."""
        if task_id:
            history = [h for h in self._cost_history if h["task_id"] == task_id]
        else:
            history = self._cost_history

        total_cost = sum(h["cost"] for h in history)
        total_tokens = sum(h["input_tokens"] + h["output_tokens"] for h in history)

        by_model = defaultdict(float)
        for h in history:
            by_model[h["model"]] += h["cost"]

        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "by_model": dict(by_model),
            "task_count": len(set(h["task_id"] for h in history)),
        }

    def suggest_optimizations(self, task: TaskSpec) -> List[Dict[str, Any]]:
        """Suggest cost optimizations for a task."""
        suggestions = []

        # Check if cheaper model available
        if task.preferred_model and task.preferred_model in self._model_costs:
            current_cost = self._model_costs[task.preferred_model]
            for model, costs in self._model_costs.items():
                if model == task.preferred_model:
                    continue
                if costs["input"] < current_cost["input"] and costs["output"] < current_cost["output"]:
                    savings = (current_cost["input"] + current_cost["output"]) - (costs["input"] + costs["output"])
                    suggestions.append({
                        "type": "model_switch",
                        "current": task.preferred_model,
                        "suggested": model,
                        "estimated_savings_per_1k": savings,
                    })

        # Check for local alternatives
        suggestions.append({
            "type": "local_model",
            "suggestion": "Consider local models for privacy-sensitive tasks",
            "estimated_savings": "100% (no API cost)",
        })

        # Batch operations
        if task.metadata.get("tool_calls", 0) > 20:
            suggestions.append({
                "type": "batch_tools",
                "suggestion": "Batch multiple tool calls where possible",
                "estimated_savings": "20-30%",
            })

        return suggestions


# =============================================================================
# Rate Limiter
# =============================================================================


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self):
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def create_bucket(
        self,
        key: str,
        rate: float,  # requests per second
        burst: int = 10,
    ) -> None:
        """Create a rate limit bucket."""
        self._buckets[key] = {
            "rate": rate,
            "burst": burst,
            "tokens": float(burst),
            "last_update": time.time(),
        }

    async def acquire(self, key: str, tokens: int = 1, timeout: float = 30.0) -> bool:
        """Acquire tokens from bucket."""
        if key not in self._buckets:
            return True  # No limit

        async with self._lock:
            bucket = self._buckets[key]
            now = time.time()

            # Refill tokens
            elapsed = now - bucket["last_update"]
            bucket["tokens"] = min(bucket["burst"], bucket["tokens"] + elapsed * bucket["rate"])
            bucket["last_update"] = now

            if bucket["tokens"] >= tokens:
                bucket["tokens"] -= tokens
                return True

        # Wait for tokens
        wait_time = (tokens - bucket["tokens"]) / bucket["rate"]
        if wait_time > timeout:
            return False

        await asyncio.sleep(wait_time)
        return await self.acquire(key, tokens, timeout - wait_time)

    def get_available(self, key: str) -> float:
        """Get available tokens in bucket."""
        if key not in self._buckets:
            return float('inf')

        bucket = self._buckets[key]
        elapsed = time.time() - bucket["last_update"]
        return min(bucket["burst"], bucket["tokens"] + elapsed * bucket["rate"])


# =============================================================================
# Concurrency Controller
# =============================================================================


class ConcurrencyController:
    """Controls concurrency across tasks and agents."""

    def __init__(self):
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._active_counts: Dict[str, int] = defaultdict(int)
        self._limits: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    def set_limit(self, scope: str, limit: int) -> None:
        """Set concurrency limit for a scope."""
        self._limits[scope] = limit
        self._semaphores[scope] = asyncio.Semaphore(limit)

    def get_limit(self, scope: str) -> int:
        """Get concurrency limit for a scope."""
        return self._limits.get(scope, float('inf'))

    async def acquire(self, scope: str, timeout: float = None) -> bool:
        """Acquire a concurrency slot."""
        if scope not in self._semaphores:
            return True

        semaphore = self._semaphores[scope]
        try:
            if timeout:
                await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
            else:
                await semaphore.acquire()
            self._active_counts[scope] += 1
            return True
        except asyncio.TimeoutError:
            return False

    def release(self, scope: str) -> None:
        """Release a concurrency slot."""
        if scope in self._semaphores:
            self._semaphores[scope].release()
            self._active_counts[scope] = max(0, self._active_counts[scope] - 1)

    def get_active(self, scope: str) -> int:
        """Get active count for a scope."""
        return self._active_counts.get(scope, 0)

    def get_available(self, scope: str) -> int:
        """Get available slots for a scope."""
        limit = self._limits.get(scope, float('inf'))
        return max(0, limit - self._active_counts.get(scope, 0))

    @contextlib.asynccontextmanager
    async def slot(self, scope: str):
        """Context manager for acquiring a slot."""
        acquired = await self.acquire(scope)
        if not acquired:
            raise RuntimeError(f"Could not acquire concurrency slot for {scope}")
        try:
            yield
        finally:
            self.release(scope)


# =============================================================================
# Recursion Controller
# =============================================================================


class RecursionController:
    """Prevents infinite recursion in agent delegation."""

    def __init__(
        self,
        max_depth: int = 5,
        max_total_tasks: int = 50,
        max_recursive_budget: float = 100.0,
    ):
        self._max_depth = max_depth
        self._max_total_tasks = max_total_tasks
        self._max_recursive_budget = max_recursive_budget
        self._depth_tracker: Dict[str, int] = {}  # root_task_id -> current_depth
        self._task_counts: Dict[str, int] = defaultdict(int)  # root_task_id -> task_count
        self._budget_tracker: Dict[str, float] = defaultdict(float)  # root_task_id -> budget_used
        self._lock = asyncio.Lock()

    def start_task(self, root_task_id: str, parent_task_id: str = "", budget: float = 0.0) -> bool:
        """Register a new task in the recursion tree."""
        depth = self._depth_tracker.get(root_task_id, 0)

        if parent_task_id:
            # Calculate depth from parent
            parent_depth = self._depth_tracker.get(parent_task_id, 0)
            depth = parent_depth + 1

        # Check depth limit
        if depth > self._max_depth:
            logger.warning(f"Recursion depth limit exceeded for {root_task_id}: {depth} > {self._max_depth}")
            return False

        # Check total task limit
        if self._task_counts[root_task_id] >= self._max_total_tasks:
            logger.warning(f"Total task limit exceeded for {root_task_id}")
            return False

        # Check budget
        if self._budget_tracker[root_task_id] + budget > self._max_recursive_budget:
            logger.warning(f"Recursive budget limit exceeded for {root_task_id}")
            return False

        self._depth_tracker[root_task_id] = depth
        self._task_counts[root_task_id] += 1
        self._budget_tracker[root_task_id] += budget

        return True

    def end_task(self, root_task_id: str, budget_used: float = 0.0) -> None:
        """Mark a task as completed."""
        self._budget_tracker[root_task_id] = max(0, self._budget_tracker[root_task_id] - budget_used)

    def get_depth(self, root_task_id: str) -> int:
        """Get current recursion depth."""
        return self._depth_tracker.get(root_task_id, 0)

    def get_task_count(self, root_task_id: str) -> int:
        """Get total tasks in recursion tree."""
        return self._task_counts.get(root_task_id, 0)

    def get_budget_used(self, root_task_id: str) -> float:
        """Get budget used in recursion tree."""
        return self._budget_tracker.get(root_task_id, 0.0)

    def can_spawn(self, root_task_id: str, additional_budget: float = 0.0) -> bool:
        """Check if a new subagent can be spawned."""
        return (
            self._depth_tracker.get(root_task_id, 0) < self._max_depth and
            self._task_counts.get(root_task_id, 0) < self._max_total_tasks and
            self._budget_tracker.get(root_task_id, 0.0) + additional_budget <= self._max_recursive_budget
        )


# =============================================================================
# Loop Detector
# =============================================================================


class LoopDetector:
    """Detects repeated patterns indicating loops."""

    def __init__(
        self,
        max_repetitions: int = 3,
        window_size: int = 10,
    ):
        self._max_repetitions = max_repetitions
        self._window_size = window_size
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def record_step(
        self,
        task_id: str,
        agent_id: str,
        tool: str = "",
        action: str = "",
        result_summary: str = "",
    ) -> bool:
        """Record an execution step. Returns True if loop detected."""
        step = {
            "agent_id": agent_id,
            "tool": tool,
            "action": action,
            "result_summary": result_summary[:100],
            "timestamp": time.time(),
        }

        self._history[task_id].append(step)

        # Trim window
        if len(self._history[task_id]) > self._window_size:
            self._history[task_id] = self._history[task_id][-self._window_size:]

        return self._detect_loop(task_id)

    def _detect_loop(self, task_id: str) -> bool:
        """Detect if recent steps form a loop."""
        history = self._history[task_id]
        if len(history) < 4:
            return False

        # Check for repeated agent+tool+action sequences
        recent = history[-self._window_size:]

        # Build sequence signatures
        signatures = [
            (s["agent_id"], s["tool"], s["action"])
            for s in recent
        ]

        # Check for repeated subsequences
        for length in range(2, len(signatures) // 2 + 1):
            for i in range(len(signatures) - 2 * length + 1):
                subseq = tuple(signatures[i:i+length])
                count = sum(
                    1 for j in range(i + length, len(signatures) - length + 1)
                    if tuple(signatures[j:j+length]) == subseq
                )
                if count >= self._max_repetitions - 1:
                    logger.warning(f"Loop detected in task {task_id}: {subseq} repeated {count+1} times")
                    return True

        return False

    def clear_history(self, task_id: str) -> None:
        """Clear history for a task."""
        self._history.pop(task_id, None)

    def get_recent_steps(self, task_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent steps for a task."""
        return self._history.get(task_id, [])[-limit:]


# =============================================================================
# Unified Budget Controller
# =============================================================================


class BudgetController:
    """Unified controller for all budget and resource management."""

    def __init__(
        self,
        default_task_budget: Optional[TaskBudget] = None,
        global_limits: Optional[Dict[BudgetType, float]] = None,
    ):
        self.budget = BudgetManager(global_limits=global_limits)
        self.cost = CostController(self.budget)
        self.rate_limiter = RateLimiter()
        self.concurrency = ConcurrencyController()
        self.recursion = RecursionController()
        self.loop_detector = LoopDetector()

        # Default concurrency limits
        self.concurrency.set_limit("global_agents", 10)
        self.concurrency.set_limit("per_user", 5)
        self.concurrency.set_limit("per_project", 5)

    def setup_task(self, task: TaskSpec) -> None:
        """Set up budget tracking for a task."""
        self.budget.set_task_budget(task.task_id, task.budget)

        # Register with recursion controller
        root_id = task.root_task_id or task.task_id
        self.recursion.start_task(root_id, task.parent_task_id, task.budget.max_cost_usd)

    def check_all(self, task: TaskSpec, projected: Dict[BudgetType, float] = None) -> tuple[bool, List[str]]:
        """Check all budgets for a task."""
        issues = []

        for budget_type in BudgetType:
            projected_amount = projected.get(budget_type, 0) if projected else 0
            if not self.budget.check_budget(task.task_id, budget_type, projected_amount):
                issues.append(f"Budget exceeded: {budget_type.value}")

        # Check recursion
        root_id = task.root_task_id or task.task_id
        if not self.recursion.can_spawn(root_id):
            issues.append("Recursion limit reached")

        return len(issues) == 0, issues

    def record_execution(
        self,
        task: TaskSpec,
        model: str,
        input_tokens: int,
        output_tokens: int,
        tool_calls: int,
        iterations: int = 1,
        time_seconds: float = 0.0,
    ) -> float:
        """Record execution metrics."""
        self.budget.record_usage(task.task_id, BudgetType.TIME, time_seconds)
        self.budget.record_usage(task.task_id, BudgetType.TOKENS, input_tokens + output_tokens)
        self.budget.record_usage(task.task_id, BudgetType.TOOL_CALLS, tool_calls)
        self.budget.record_usage(task.task_id, BudgetType.ITERATIONS, iterations)

        cost = self.cost.record_actual_cost(task.task_id, model, input_tokens, output_tokens, tool_calls)

        # Record loop detection
        self.loop_detector.record_step(task.task_id, task.assigned_agent, "", "execution", f"tokens:{input_tokens+output_tokens}")

        return cost

    def get_task_status(self, task: TaskSpec) -> Dict[str, Any]:
        """Get comprehensive status for a task."""
        return {
            "budget": self.budget.get_budget_status(task.task_id),
            "cost_report": self.cost.get_cost_report(task.task_id),
            "recursion": {
                "depth": self.recursion.get_depth(task.root_task_id or task.task_id),
                "task_count": self.recursion.get_task_count(task.root_task_id or task.task_id),
                "budget_used": self.recursion.get_budget_used(task.root_task_id or task.task_id),
            },
            "loop_detection": {
                "recent_steps": self.loop_detector.get_recent_steps(task.task_id),
            },
        }

    def cleanup_task(self, task: TaskSpec) -> None:
        """Clean up resources for a completed task."""
        self.budget.release_task_budget(task.task_id)
        self.loop_detector.clear_history(task.task_id)
        root_id = task.root_task_id or task.task_id
        self.recursion.end_task(root_id, task.budget.max_cost_usd)


# =============================================================================
# Factory
# =============================================================================


def create_budget_controller(
    default_task_budget: Optional[TaskBudget] = None,
    global_limits: Optional[Dict[BudgetType, float]] = None,
) -> BudgetController:
    """Create a budget controller with all components."""
    return BudgetController(default_task_budget, global_limits)


__all__ = [
    "BudgetType",
    "BudgetAction",
    "BudgetLimit",
    "BudgetUsage",
    "BudgetManager",
    "CostController",
    "RateLimiter",
    "ConcurrencyController",
    "RecursionController",
    "LoopDetector",
    "BudgetController",
    "create_budget_controller",
]