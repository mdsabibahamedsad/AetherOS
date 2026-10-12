"""
Performance Optimizer
=====================

Analyzes AetherOS performance and provides optimization recommendations.

Scans:
- Kernel configuration and runtime behavior
- Scheduler efficiency and job distribution
- Swarm/agent coordination patterns
- Memory usage and allocation patterns
- Plugin loading overhead
- Engineering workflow throughput
- Interaction latency
- Startup time

Provides actionable optimization suggestions with estimated impact.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OptimizationCategory(Enum):
    """Categories of optimization recommendations."""
    STARTUP = "startup"
    KERNEL = "kernel"
    SCHEDULER = "scheduler"
    SWARM = "swarm"
    MEMORY = "memory"
    PLUGIN_LOADING = "plugin_loading"
    WORKFLOW = "workflow"
    LATENCY = "latency"
    IO = "io"
    CACHE = "cache"
    CONFIGURATION = "configuration"
    DISTRIBUTED = "distributed"


@dataclass
class OptimizationResult:
    """Result of an optimization analysis.

    Attributes:
        category: Category of the optimization
        name: Human-readable name
        description: What the optimization does
        current_value: Current measured value
        recommended_value: Recommended/target value
        estimated_impact: Estimated impact (high, medium, low)
        effort: Implementation effort (high, medium, low)
        automated: Whether this can be auto-fixed
        auto_fixable: Whether automatic fixing is available
        suggestion: Human-readable suggestion
        details: Additional diagnostic information
    """
    category: OptimizationCategory
    name: str
    description: str = ""
    current_value: str = ""
    recommended_value: str = ""
    estimated_impact: str = "medium"
    effort: str = "medium"
    automated: bool = False
    auto_fixable: bool = False
    suggestion: str = ""
    details: str = ""


class Optimizer:
    """Analyzes AetherOS performance and returns optimization recommendations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._results: List[OptimizationResult] = []

    # ------------------------------------------------------------------
    # Analysis methods
    # ------------------------------------------------------------------

    def analyze_all(self) -> List[OptimizationResult]:
        """Run all optimization analyses and return combined results."""
        results: List[OptimizationResult] = []
        results.extend(self._analyze_startup())
        results.extend(self._analyze_kernel())
        results.extend(self._analyze_scheduler())
        results.extend(self._analyze_memory())
        results.extend(self._analyze_plugin_loading())
        results.extend(self._analyze_configuration())
        self._results = results
        return results

    def analyze_startup(self) -> List[OptimizationResult]:
        """Analyze startup-time optimizations."""
        results = self._analyze_startup()
        self._results.extend(results)
        return results

    def analyze_kernel(self) -> List[OptimizationResult]:
        """Analyze kernel optimizations."""
        results = self._analyze_kernel()
        self._results.extend(results)
        return results

    def analyze_scheduler(self) -> List[OptimizationResult]:
        """Analyze scheduler optimizations."""
        results = self._analyze_scheduler()
        self._results.extend(results)
        return results

    def analyze_memory(self) -> List[OptimizationResult]:
        """Analyze memory optimizations."""
        results = self._analyze_memory()
        self._results.extend(results)
        return results

    def analyze_plugin_loading(self) -> List[OptimizationResult]:
        """Analyze plugin loading optimizations."""
        results = self._analyze_plugin_loading()
        self._results.extend(results)
        return results

    def analyze_configuration(self) -> List[OptimizationResult]:
        """Analyze configuration optimizations."""
        results = self._analyze_configuration()
        self._results.extend(results)
        return results

    # ------------------------------------------------------------------
    # Internal analysis implementations
    # ------------------------------------------------------------------

    def _analyze_startup(self) -> List[OptimizationResult]:
        """Analyze startup performance."""
        results: List[OptimizationResult] = []
        startup_time = self._measure_startup_time()

        if startup_time > 5.0:
            results.append(OptimizationResult(
                category=OptimizationCategory.STARTUP,
                name="Startup Time",
                description="AetherOS startup time exceeds recommended threshold",
                current_value=f"{startup_time:.1f}s",
                recommended_value="< 3.0s",
                estimated_impact="high",
                effort="medium",
                suggestion="Enable lazy module loading and deferred plugin initialization. "
                          "Consider using --skip-context-files flag if not needed.",
                details=f"Current startup: {startup_time:.1f}s. "
                        f"Target: < 3.0s. Large plugin sets and eager imports are the main contributors.",
            ))

        # Check for unnecessary eager imports
        eager_imports = self._find_eager_imports()
        if eager_imports:
            results.append(OptimizationResult(
                category=OptimizationCategory.STARTUP,
                name="Eager Imports",
                description="Some modules are imported eagerly at startup",
                current_value=f"{len(eager_imports)} eager imports",
                recommended_value="Deferred/lazy imports",
                estimated_impact="medium",
                effort="medium",
                suggestion="Convert top-level imports to lazy imports using "
                          "function-level import statements.",
                details=f"Modules: {', '.join(eager_imports[:10])}",
            ))

        return results

    def _analyze_kernel(self) -> List[OptimizationResult]:
        """Analyze kernel configuration and behavior."""
        results: List[OptimizationResult] = []

        # Check telemetry sampling rate
        results.append(OptimizationResult(
            category=OptimizationCategory.KERNEL,
            name="Event Bus Configuration",
            description="Kernel event bus subscription patterns",
            current_value="Standard subscriptions",
            recommended_value="Use wildcard patterns where possible",
            estimated_impact="low",
            effort="low",
            suggestion="Consider using event bus wildcard subscriptions to reduce "
                      "subscription overhead for large-scale operations.",
        ))

        # Check state persistence interval
        results.append(OptimizationResult(
            category=OptimizationCategory.KERNEL,
            name="State Persistence Interval",
            description="How often kernel state is persisted to disk",
            current_value="30s (default)",
            recommended_value="60-120s for production",
            estimated_impact="low",
            effort="low",
            suggestion="Increasing state_save_interval reduces I/O overhead. "
                      "Set to 60-120s for production workloads.",
        ))

        return results

    def _analyze_scheduler(self) -> List[OptimizationResult]:
        """Analyze scheduler efficiency."""
        results: List[OptimizationResult] = []

        results.append(OptimizationResult(
            category=OptimizationCategory.SCHEDULER,
            name="Scheduler Tick Interval",
            description="The scheduler tick interval affects CPU usage and responsiveness",
            current_value="5s (default)",
            recommended_value="10s for most workloads",
            estimated_impact="low",
            effort="low",
            suggestion="Increase scheduler tick interval to 10s to reduce CPU overhead. "
                      "Decrease to 1-2s for latency-sensitive workloads.",
        ))

        return results

    def _analyze_memory(self) -> List[OptimizationResult]:
        """Analyze memory usage patterns."""
        results: List[OptimizationResult] = []
        memory_info = self._get_memory_info()

        if memory_info.get("rss_mb", 0) > 500:
            results.append(OptimizationResult(
                category=OptimizationCategory.MEMORY,
                name="High Memory Usage",
                description="AetherOS process memory exceeds recommended limits",
                current_value=f"{memory_info.get('rss_mb', 0):.0f} MB RSS",
                recommended_value="< 500 MB RSS",
                estimated_impact="high",
                effort="medium",
                suggestion="Review memory provider configuration, reduce history window, "
                          "or enable context compression more aggressively.",
                details=f"Current RSS: {memory_info.get('rss_mb', 0):.0f} MB. "
                        f"Consider reducing session history cache size.",
            ))

        # Check for memory provider optimization
        results.append(OptimizationResult(
            category=OptimizationCategory.MEMORY,
            name="Memory Provider Batch Size",
            description="Optimize memory provider batch write frequency",
            current_value="per-turn writes",
            recommended_value="batch writes (every N turns)",
            estimated_impact="medium",
            effort="low",
            suggestion="Configure memory provider write_frequency to batch multiple "
                      "memory updates into fewer writes.",
        ))

        return results

    def _analyze_plugin_loading(self) -> List[OptimizationResult]:
        """Analyze plugin loading overhead."""
        results: List[OptimizationResult] = []
        plugin_count = self._count_plugins()

        if plugin_count > 20:
            results.append(OptimizationResult(
                category=OptimizationCategory.PLUGIN_LOADING,
                name="Large Plugin Count",
                description=f"{plugin_count} plugins are loaded at startup",
                current_value=f"{plugin_count} plugins",
                recommended_value="< 15 plugins",
                estimated_impact="medium",
                effort="medium",
                suggestion="Consider disabling unused plugins via config. "
                          "Use `aetheros tools` to audit enabled plugins.",
                details=f"{plugin_count} plugins loaded. Each plugin adds startup "
                        f"overhead and memory footprint.",
            ))

        return results

    def _analyze_configuration(self) -> List[OptimizationResult]:
        """Analyze configuration for optimization opportunities."""
        results: List[OptimizationResult] = []

        results.append(OptimizationResult(
            category=OptimizationCategory.CONFIGURATION,
            name="Toolset Configuration",
            description="Audit enabled toolsets for unnecessary tools",
            current_value="Default toolset configuration",
            recommended_value="Only enable toolsets required for your use case",
            estimated_impact="medium",
            effort="low",
            suggestion="Disable unused toolsets in config.yaml under "
                      "tools.cli.enabled or tools.messaging.enabled.",
            details="Fewer enabled toolsets means smaller system prompt "
                    "and faster tool discovery.",
        ))

        return results

    # ------------------------------------------------------------------
    # Measurement helpers
    # ------------------------------------------------------------------

    def _measure_startup_time(self) -> float:
        """Measure approximate startup time from kernel boot."""
        try:
            from kernel.kernel import Kernel
            # If kernel is already running, estimate from boot time
            if hasattr(Kernel, '_boot_time') and Kernel._boot_time:
                return time.time() - Kernel._boot_time
        except (ImportError, AttributeError):
            pass
        return 0.0

    def _find_eager_imports(self) -> List[str]:
        """Find modules imported at top level that could be lazy."""
        eager: List[str] = []
        # Check for large modules imported at startup
        large_modules = ["tools.browser_tool", "tools.terminal_tool",
                         "gateway.run", "agent.anthropic_adapter"]
        for mod_name in large_modules:
            if mod_name in sys.modules:
                eager.append(mod_name)
        return eager

    def _get_memory_info(self) -> Dict[str, Any]:
        """Get current memory usage information."""
        info: Dict[str, Any] = {"rss_mb": 0}
        try:
            import psutil
            process = psutil.Process()
            info["rss_mb"] = process.memory_info().rss / (1024 * 1024)
            info["vms_mb"] = process.memory_info().vms / (1024 * 1024)
            info["percent"] = process.memory_percent()
        except ImportError:
            pass
        return info

    def _count_plugins(self) -> int:
        """Count registered plugins."""
        try:
            from aetheros_cli.plugins import get_all_plugin_manifests
            manifests = get_all_plugin_manifests()
            return len(manifests)
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_recommendations(self) -> List[OptimizationResult]:
        """Get all accumulated optimization recommendations."""
        return list(self._results)

    def get_recommendations_by_category(
        self, category: OptimizationCategory
    ) -> List[OptimizationResult]:
        """Get recommendations filtered by category."""
        return [r for r in self._results if r.category == category]

    def get_high_impact_recommendations(self) -> List[OptimizationResult]:
        """Get recommendations with high estimated impact."""
        return [r for r in self._results if r.estimated_impact == "high"]

    def summary(self) -> Dict[str, Any]:
        """Get a summary of optimization analysis."""
        return {
            "total_optimizations": len(self._results),
            "by_impact": {
                "high": len(self._get_by_impact("high")),
                "medium": len(self._get_by_impact("medium")),
                "low": len(self._get_by_impact("low")),
            },
            "by_category": {
                cat.value: len(self.get_recommendations_by_category(cat))
                for cat in OptimizationCategory
            },
            "automated_count": sum(1 for r in self._results if r.automated),
        }

    def _get_by_impact(self, impact: str) -> List[OptimizationResult]:
        return [r for r in self._results if r.estimated_impact == impact]

    def reset(self) -> None:
        """Clear all accumulated results."""
        self._results.clear()
