"""
Load Balancer — distributes tasks across cluster nodes based on
load, resource availability, capabilities, and estimated latency.

Supports multiple balancing strategies including round-robin,
least-loaded, resource-based, capability-based, and latency-based.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cluster.node_registry import NodeInfo, NodeStatus

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(enum.Enum):
    """Strategies for distributing tasks across nodes."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RESOURCE_BASED = "resource_based"
    CAPABILITY_BASED = "capability_based"
    LOWEST_LATENCY = "lowest_latency"
    RANDOM = "random"
    WEIGHTED = "weighted"


@dataclass
class BalancerDecision:
    """Decision from the load balancer about which node to use.

    Attributes:
        node_id: Selected node ID
        confidence: Confidence in this decision (0.0 - 1.0)
        reasoning: Why this node was selected
        estimated_latency_ms: Estimated network latency
        score: Internal score used for ranking
    """
    node_id: str = ""
    confidence: float = 1.0
    reasoning: str = ""
    estimated_latency_ms: float = 0.0
    score: float = 0.0


class LoadBalancer:
    """Distributes tasks across cluster nodes.

    Maintains load counters for each node and selects the optimal
    node based on the configured strategy.

    Usage:
        balancer = LoadBalancer()
        balancer.set_strategy(LoadBalancingStrategy.LEAST_LOADED)

        decision = balancer.select_node(
            candidates=list_of_nodes,
            required_tools=["terminal"],
            priority=10,
        )
    """

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self._strategy = strategy
        self._lock = threading.RLock()

        # Load tracking: node_id -> current task count
        self._load: Dict[str, int] = {}
        # Resource tracking: node_id -> resource usage (0.0 - 1.0)
        self._resource_usage: Dict[str, float] = {}
        # Latency tracking: node_id -> estimated latency ms
        self._latency: Dict[str, float] = {}
        # Round robin index
        self._rr_index = 0

        # Weight configuration: node_id -> weight (for weighted strategy)
        self._weights: Dict[str, float] = {}

        # Available node IDs (maintained separately for speed)
        self._available_nodes: List[str] = []

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_strategy(self, strategy: LoadBalancingStrategy) -> None:
        """Set the load balancing strategy."""
        with self._lock:
            self._strategy = strategy

    def get_strategy(self) -> LoadBalancingStrategy:
        """Get the current load balancing strategy."""
        with self._lock:
            return self._strategy

    def set_weight(self, node_id: str, weight: float) -> None:
        """Set a weight for a node (used by WEIGHTED strategy)."""
        with self._lock:
            self._weights[node_id] = max(0.1, weight)

    def set_latency(self, node_id: str, latency_ms: float) -> None:
        """Set the estimated latency to a node in milliseconds."""
        with self._lock:
            self._latency[node_id] = latency_ms

    def update_load(self, node_id: str, delta: int = 1) -> None:
        """Update the load counter for a node."""
        with self._lock:
            current = self._load.get(node_id, 0)
            self._load[node_id] = max(0, current + delta)

    def update_resource_usage(self, node_id: str, usage: float) -> None:
        """Update resource usage for a node (0.0 - 1.0)."""
        with self._lock:
            self._resource_usage[node_id] = max(0.0, min(1.0, usage))

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select_node(
        self,
        candidates: List[NodeInfo],
        required_tools: Optional[List[str]] = None,
        priority: int = 50,
        strategy: Optional[LoadBalancingStrategy] = None,
    ) -> Optional[BalancerDecision]:
        """Select the best node from candidates for a task.

        Args:
            candidates: Available nodes to choose from
            required_tools: Tools the node must support
            priority: Task priority (lower = more important)
            strategy: Override the default strategy

        Returns:
            BalancerDecision or None if no suitable node found
        """
        if not candidates:
            return None

        effective_strategy = strategy or self._strategy

        # Filter out nodes that don't support required tools
        if required_tools:
            filtered = []
            for node in candidates:
                if node.capabilities:
                    node_tools = set(node.capabilities.supported_tools)
                    if all(tool in node_tools for tool in required_tools):
                        filtered.append(node)
            if filtered:
                candidates = filtered

        if not candidates:
            return None

        with self._lock:
            strategy_fn = self._get_strategy_fn(effective_strategy)
            decision = strategy_fn(candidates, priority)

        return decision

    def _get_strategy_fn(self, strategy: LoadBalancingStrategy):
        """Get the function implementing the given strategy."""
        return {
            LoadBalancingStrategy.ROUND_ROBIN: self._round_robin,
            LoadBalancingStrategy.LEAST_LOADED: self._least_loaded,
            LoadBalancingStrategy.RESOURCE_BASED: self._resource_based,
            LoadBalancingStrategy.CAPABILITY_BASED: self._capability_based,
            LoadBalancingStrategy.LOWEST_LATENCY: self._lowest_latency,
            LoadBalancingStrategy.RANDOM: self._random,
            LoadBalancingStrategy.WEIGHTED: self._weighted,
        }.get(strategy, self._round_robin)

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _round_robin(self, candidates: List[NodeInfo],
                     priority: int) -> BalancerDecision:
        """Round-robin selection."""
        with self._lock:
            self._rr_index = (self._rr_index + 1) % len(candidates)
            node = candidates[self._rr_index]

        return BalancerDecision(
            node_id=node.node_id,
            confidence=0.7,
            reasoning=f"Round-robin selected {node.node_id[:8]}",
        )

    def _least_loaded(self, candidates: List[NodeInfo],
                      priority: int) -> BalancerDecision:
        """Select the node with the fewest active tasks."""
        with self._lock:
            best = min(
                candidates,
                key=lambda n: self._load.get(n.node_id, 0),
            )
            load = self._load.get(best.node_id, 0)

        return BalancerDecision(
            node_id=best.node_id,
            confidence=0.8 if load == 0 else 0.6,
            reasoning=f"Least loaded: {best.node_id[:8]} ({load} active tasks)",
        )

    def _resource_based(self, candidates: List[NodeInfo],
                        priority: int) -> BalancerDecision:
        """Select the node with the most available resources."""
        with self._lock:
            scored = []
            for node in candidates:
                usage = self._resource_usage.get(node.node_id, 0.0)
                # Lower usage = higher score
                score = 1.0 - usage
                scored.append((score, node))

            scored.sort(key=lambda x: -x[0])
            best_score, best = scored[0]

        return BalancerDecision(
            node_id=best.node_id,
            confidence=best_score,
            reasoning=f"Resource-based: {best.node_id[:8]} (usage={1-best_score:.0%} free)",
            score=best_score,
        )

    def _capability_based(self, candidates: List[NodeInfo],
                          priority: int) -> BalancerDecision:
        """Select the node with the best capability match.

        Prefers nodes with more tools, more CPUs, and more memory.
        """
        scored = []
        for node in candidates:
            score = 0.0
            if node.capabilities:
                cap = node.capabilities
                score += len(cap.supported_tools) * 0.1
                score += min(cap.cpu_count / 32, 1.0) * 0.3
                score += min(cap.memory_mb / 65536, 1.0) * 0.3
                score += min(cap.gpu_count / 8, 1.0) * 0.3
            scored.append((score, node))

        scored.sort(key=lambda x: -x[0])
        best_score, best = scored[0]

        return BalancerDecision(
            node_id=best.node_id,
            confidence=best_score,
            reasoning=f"Capability-based: {best.node_id[:8]} (score={best_score:.2f})",
            score=best_score,
        )

    def _lowest_latency(self, candidates: List[NodeInfo],
                        priority: int) -> BalancerDecision:
        """Select the node with the lowest estimated latency."""
        with self._lock:
            best = min(
                candidates,
                key=lambda n: self._latency.get(n.node_id, 100.0),
            )
            latency = self._latency.get(best.node_id, 0.0)

        return BalancerDecision(
            node_id=best.node_id,
            confidence=0.8 if latency < 50 else 0.5,
            reasoning=f"Lowest latency: {best.node_id[:8]} ({latency:.0f}ms)",
            estimated_latency_ms=latency,
        )

    def _random(self, candidates: List[NodeInfo],
                priority: int) -> BalancerDecision:
        """Random selection."""
        import random
        node = random.choice(candidates)
        return BalancerDecision(
            node_id=node.node_id,
            confidence=0.3,
            reasoning=f"Random selection from {len(candidates)} candidates",
        )

    def _weighted(self, candidates: List[NodeInfo],
                  priority: int) -> BalancerDecision:
        """Weighted random selection."""
        with self._lock:
            import random
            weighted = []
            for node in candidates:
                weight = self._weights.get(node.node_id, 1.0)
                weighted.append((node, weight))

            total_weight = sum(w for _, w in weighted)
            if total_weight <= 0:
                return self._round_robin(candidates, priority)

            r = random.uniform(0, total_weight)
            cumulative = 0
            for node, weight in weighted:
                cumulative += weight
                if r <= cumulative:
                    return BalancerDecision(
                        node_id=node.node_id,
                        confidence=weight / total_weight,
                        reasoning=f"Weighted selection: {node.node_id[:8]} (weight={weight:.1f})",
                    )

        return BalancerDecision(
            node_id=candidates[0].node_id,
            confidence=0.3,
            reasoning="Weighted selection by fallback",
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_load_map(self) -> Dict[str, int]:
        """Get the current load distribution across nodes."""
        with self._lock:
            return dict(self._load)

    def get_stats(self) -> Dict[str, Any]:
        """Return load balancer statistics."""
        with self._lock:
            return {
                "strategy": self._strategy.value,
                "tracked_nodes": len(self._load),
                "total_load": sum(self._load.values()),
                "load_map": dict(self._load),
            }

    def reset(self) -> None:
        """Reset all load balancer state."""
        with self._lock:
            self._load.clear()
            self._resource_usage.clear()
            self._latency.clear()
            self._rr_index = 0
