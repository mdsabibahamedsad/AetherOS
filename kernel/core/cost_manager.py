"""
Cost Manager — unified cost accounting for all kernel operations.

Tracks LLM tokens, model costs, GPU time, CPU time, network, storage,
tool calls, external API costs, agent delegation, automation, physical execution.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import defaultdict
from enum import Enum

from kernel.core.types import (
    ResourceBudget,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class CostCategory(Enum):
    LLM_TOKENS = "llm_tokens"
    MODEL_COST = "model_cost"
    GPU_TIME = "gpu_time"
    CPU_TIME = "cpu_time"
    NETWORK = "network"
    STORAGE = "storage"
    TOOL_CALLS = "tool_calls"
    EXTERNAL_API = "external_api"
    AGENT_DELEGATION = "agent_delegation"
    AUTOMATION = "automation"
    PHYSICAL_EXECUTION = "physical_execution"
    RESEARCH = "research"


@dataclass
class CostEntry:
    """A cost entry."""
    entry_id: str
    category: CostCategory
    agent_id: str
    task_id: str = ""
    intent_id: str = ""
    amount_usd: float = 0.0
    units: float = 0.0  # tokens, seconds, bytes, etc.
    unit_type: str = ""  # "tokens", "seconds", "MB", "calls"
    description: str = ""
    timestamp: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostBudget:
    """Cost budget for an agent/task."""
    budget_id: str
    agent_id: str
    task_id: str = ""
    intent_id: str = ""
    max_cost_usd: float = 10.0
    max_tokens: int = 100000
    max_gpu_seconds: float = 3600.0
    max_cpu_seconds: float = 3600.0
    spent_usd: float = 0.0
    spent_tokens: int = 0
    spent_gpu_seconds: float = 0.0
    spent_cpu_seconds: float = 0.0
    alert_threshold: float = 0.8  # Alert at 80%
    hard_limit: bool = True  # Enforce hard limit
    created_at: float = field(default_factory=_now)
    expires_at: Optional[float] = None


class CostManager:
    """
    Unified cost accounting for all kernel operations.
    
    Every task gets estimated cost, actual cost, and remaining budget.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        self._cost_entries: List[CostEntry] = []
        self._budgets: Dict[str, CostBudget] = {}
        self._agent_budgets: Dict[str, List[str]] = defaultdict(list)  # agent_id -> budget_ids
        
        # Cost rates (configurable)
        self._cost_rates = {
            CostCategory.LLM_TOKENS: {"input": 0.00001, "output": 0.00003},  # per 1K tokens
            CostCategory.GPU_TIME: 0.50,  # per hour
            CostCategory.CPU_TIME: 0.05,  # per hour
            CostCategory.NETWORK: 0.01,  # per GB
            CostCategory.STORAGE: 0.02,  # per GB/month
            CostCategory.TOOL_CALLS: 0.0001,  # per call
            CostCategory.EXTERNAL_API: 0.001,  # per call (varies)
            CostCategory.AGENT_DELEGATION: 0.01,  # per delegation
            CostCategory.AUTOMATION: 0.005,  # per automation run
            CostCategory.PHYSICAL_EXECUTION: 1.00,  # per physical action
            CostCategory.RESEARCH: 0.005,  # per research request
        }
        
        # Callbacks
        self._budget_alert_callbacks: List[Callable[[CostBudget, float], None]] = []
        self._budget_exceeded_callbacks: List[Callable[[CostBudget], None]] = []

    def register_budget_alert_callback(self, callback: Callable[[CostBudget, float], None]) -> None:
        """Register a budget alert callback."""
        self._budget_alert_callbacks.append(callback)

    def register_budget_exceeded_callback(self, callback: Callable[[CostBudget], None]) -> None:
        """Register a budget exceeded callback."""
        self._budget_exceeded_callbacks.append(callback)

    def create_budget(
        self,
        agent_id: str,
        max_cost_usd: float = 10.0,
        max_tokens: int = 100000,
        max_gpu_seconds: float = 3600.0,
        max_cpu_seconds: float = 3600.0,
        task_id: str = "",
        intent_id: str = "",
        alert_threshold: float = 0.8,
        hard_limit: bool = True,
    ) -> CostBudget:
        """Create a cost budget."""
        budget = CostBudget(
            budget_id=new_id("budget"),
            agent_id=agent_id,
            task_id=task_id,
            intent_id=intent_id,
            max_cost_usd=max_cost_usd,
            max_tokens=max_tokens,
            max_gpu_seconds=max_gpu_seconds,
            max_cpu_seconds=max_cpu_seconds,
            alert_threshold=alert_threshold,
            hard_limit=hard_limit,
        )

        with self._lock:
            self._budgets[budget.budget_id] = budget
            self._agent_budgets[agent_id].append(budget.budget_id)

        if self.event_bus:
            self.event_bus.emit("cost.budget.created", {
                "budget_id": budget.budget_id,
                "agent_id": agent_id,
                "max_cost_usd": max_cost_usd,
            })

        return budget

    def get_budget(self, budget_id: str) -> Optional[CostBudget]:
        """Get a budget by ID."""
        with self._lock:
            return self._budgets.get(budget_id)

    def get_agent_budgets(self, agent_id: str) -> List[CostBudget]:
        """Get all budgets for an agent."""
        with self._lock:
            budget_ids = self._agent_budgets.get(agent_id, [])
            return [self._budgets[bid] for bid in budget_ids if bid in self._budgets]

    def record_cost(
        self,
        agent_id: str,
        category: CostCategory,
        amount_usd: float = 0.0,
        units: float = 0.0,
        unit_type: str = "",
        task_id: str = "",
        intent_id: str = "",
        description: str = "",
        metadata: Dict[str, Any] = None,
    ) -> CostEntry:
        """Record a cost entry."""
        entry = CostEntry(
            entry_id=new_id("cost"),
            category=category,
            agent_id=agent_id,
            task_id=task_id,
            intent_id=intent_id,
            amount_usd=amount_usd,
            units=units,
            unit_type=unit_type,
            description=description,
            metadata=metadata or {},
        )

        with self._lock:
            self._cost_entries.append(entry)
            
            # Update relevant budgets
            for budget in self.get_agent_budgets(agent_id):
                if budget.task_id and budget.task_id != task_id:
                    continue
                if budget.intent_id and budget.intent_id != intent_id:
                    continue
                
                self._apply_cost_to_budget(budget, entry)
                
                # Check alerts
                self._check_budget_alerts(budget)

        if self.event_bus:
            self.event_bus.emit("cost.recorded", {
                "entry_id": entry.entry_id,
                "agent_id": agent_id,
                "category": category.value,
                "amount_usd": amount_usd,
            })

        return entry

    def _apply_cost_to_budget(self, budget: CostBudget, entry: CostEntry) -> None:
        """Apply cost entry to budget."""
        budget.spent_usd += entry.amount_usd
        
        if entry.category == CostCategory.LLM_TOKENS:
            budget.spent_tokens += int(entry.units)
        elif entry.category == CostCategory.GPU_TIME:
            budget.spent_gpu_seconds += entry.units
        elif entry.category == CostCategory.CPU_TIME:
            budget.spent_cpu_seconds += entry.units

    def _check_budget_alerts(self, budget: CostBudget) -> None:
        """Check budget alerts."""
        if budget.max_cost_usd > 0:
            ratio = budget.spent_usd / budget.max_cost_usd
            
            if ratio >= budget.alert_threshold and ratio < 1.0:
                for callback in self._budget_alert_callbacks:
                    try:
                        callback(budget, ratio)
                    except Exception as exc:
                        logger.error("Budget alert callback error: %s", exc)
                
                if self.event_bus:
                    self.event_bus.emit("cost.budget.alert", {
                        "budget_id": budget.budget_id,
                        "agent_id": budget.agent_id,
                        "ratio": ratio,
                        "spent_usd": budget.spent_usd,
                        "max_usd": budget.max_cost_usd,
                    })

            if ratio >= 1.0 and budget.hard_limit:
                for callback in self._budget_exceeded_callbacks:
                    try:
                        callback(budget)
                    except Exception as exc:
                        logger.error("Budget exceeded callback error: %s", exc)
                
                if self.event_bus:
                    self.event_bus.emit("cost.budget.exceeded", {
                        "budget_id": budget.budget_id,
                        "agent_id": budget.agent_id,
                        "spent_usd": budget.spent_usd,
                        "max_usd": budget.max_cost_usd,
                    })

    def estimate_cost(
        self,
        category: CostCategory,
        units: float,
        unit_type: str = "",
    ) -> float:
        """Estimate cost for an operation."""
        rates = self._cost_rates.get(category, {})
        
        if category == CostCategory.LLM_TOKENS:
            if unit_type == "input":
                return (units / 1000) * rates.get("input", 0.00001)
            elif unit_type == "output":
                return (units / 1000) * rates.get("output", 0.00003)
            else:
                # Assume 50/50 split
                return (units / 1000) * (rates.get("input", 0.00001) + rates.get("output", 0.00003)) / 2
        
        elif category == CostCategory.GPU_TIME:
            return (units / 3600) * rates.get(CostCategory.GPU_TIME, 0.50)
        
        elif category == CostCategory.CPU_TIME:
            return (units / 3600) * rates.get(CostCategory.CPU_TIME, 0.05)
        
        elif category == CostCategory.NETWORK:
            return (units / 1024) * rates.get(CostCategory.NETWORK, 0.01)  # per GB
        
        elif category == CostCategory.STORAGE:
            return (units / 1024) * rates.get(CostCategory.STORAGE, 0.02)  # per GB
        
        elif category == CostCategory.TOOL_CALLS:
            return units * rates.get(CostCategory.TOOL_CALLS, 0.0001)
        
        elif category == CostCategory.EXTERNAL_API:
            return units * rates.get(CostCategory.EXTERNAL_API, 0.001)
        
        elif category == CostCategory.AGENT_DELEGATION:
            return units * rates.get(CostCategory.AGENT_DELEGATION, 0.01)
        
        elif category == CostCategory.AUTOMATION:
            return units * rates.get(CostCategory.AUTOMATION, 0.005)
        
        elif category == CostCategory.PHYSICAL_EXECUTION:
            return units * rates.get(CostCategory.PHYSICAL_EXECUTION, 1.00)
        
        elif category == CostCategory.RESEARCH:
            return units * rates.get(CostCategory.RESEARCH, 0.005)
        
        return 0.0

    def set_cost_rate(self, category: CostCategory, rate: float, unit: str = "") -> None:
        """Set a cost rate."""
        if category == CostCategory.LLM_TOKENS:
            if isinstance(self._cost_rates[category], dict):
                if unit == "input":
                    self._cost_rates[category]["input"] = rate
                elif unit == "output":
                    self._cost_rates[category]["output"] = rate
        else:
            self._cost_rates[category] = rate

    def get_cost_summary(self, agent_id: str = "", task_id: str = "", since: float = 0) -> Dict[str, Any]:
        """Get cost summary."""
        with self._lock:
            entries = list(self._cost_entries)

        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        if task_id:
            entries = [e for e in entries if e.task_id == task_id]
        if since > 0:
            entries = [e for e in entries if e.timestamp >= since]

        total_usd = sum(e.amount_usd for e in entries)
        by_category: Dict[str, float] = defaultdict(float)
        by_agent: Dict[str, float] = defaultdict(float)

        for entry in entries:
            by_category[entry.category.value] += entry.amount_usd
            by_agent[entry.agent_id] += entry.amount_usd

        return {
            "total_usd": total_usd,
            "entry_count": len(entries),
            "by_category": dict(by_category),
            "by_agent": dict(by_agent),
        }

    def get_budget_status(self, budget_id: str) -> Dict[str, Any]:
        """Get budget status."""
        budget = self.get_budget(budget_id)
        if not budget:
            return {"error": "Budget not found"}

        return {
            "budget_id": budget.budget_id,
            "agent_id": budget.agent_id,
            "max_cost_usd": budget.max_cost_usd,
            "spent_usd": budget.spent_usd,
            "remaining_usd": budget.max_cost_usd - budget.spent_usd,
            "ratio": budget.spent_usd / budget.max_cost_usd if budget.max_cost_usd > 0 else 0,
            "max_tokens": budget.max_tokens,
            "spent_tokens": budget.spent_tokens,
            "max_gpu_seconds": budget.max_gpu_seconds,
            "spent_gpu_seconds": budget.spent_gpu_seconds,
            "max_cpu_seconds": budget.max_cpu_seconds,
            "spent_cpu_seconds": budget.spent_cpu_seconds,
            "alert_threshold": budget.alert_threshold,
            "hard_limit": budget.hard_limit,
            "is_exceeded": budget.spent_usd >= budget.max_cost_usd if budget.max_cost_usd > 0 else False,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get cost manager statistics."""
        with self._lock:
            total_entries = len(self._cost_entries)
            total_cost = sum(e.amount_usd for e in self._cost_entries)
            active_budgets = len(self._budgets)
            
            by_category: Dict[str, float] = defaultdict(float)
            for entry in self._cost_entries:
                by_category[entry.category.value] += entry.amount_usd

        return {
            "total_cost_entries": total_entries,
            "total_cost_usd": total_cost,
            "active_budgets": active_budgets,
            "by_category": dict(by_category),
            "cost_rates": {k.value if isinstance(k, CostCategory) else k: v for k, v in self._cost_rates.items()},
        }

    def shutdown(self) -> None:
        """Shutdown the cost manager."""
        logger.info("CostManager: shutting down")
        with self._lock:
            self._cost_entries.clear()
            self._budgets.clear()
            self._agent_budgets.clear()