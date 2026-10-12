"""
High Availability
=================

Optional support for redundant services, automatic failover,
health monitoring, and cluster-aware recovery.
Graceful degradation is required.
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class NodeStatus(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class FailoverStrategy(enum.Enum):
    ACTIVE_PASSIVE = "active_passive"
    ACTIVE_ACTIVE = "active_active"
    MANUAL = "manual"


@dataclass
class HealthCheck:
    """A health check for a service or node."""
    name: str
    endpoint: str = ""
    interval_seconds: int = 30
    timeout_seconds: int = 5
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3
    last_check: Optional[datetime] = None
    last_status: NodeStatus = NodeStatus.HEALTHY
    consecutive_failures: int = 0

    def record_success(self) -> None:
        self.last_check = datetime.utcnow()
        self.last_status = NodeStatus.HEALTHY
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.last_check = datetime.utcnow()
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.unhealthy_threshold:
            self.last_status = NodeStatus.UNHEALTHY
        else:
            self.last_status = NodeStatus.DEGRADED


@dataclass
class HANode:
    """A node in a high-availability cluster."""
    id: str
    name: str
    host: str = "localhost"
    port: int = 0
    role: str = "active"  # active, passive, standby
    status: NodeStatus = NodeStatus.HEALTHY
    health_checks: Dict[str, HealthCheck] = field(default_factory=dict)
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_healthy(self) -> bool:
        return self.status == NodeStatus.HEALTHY

    def mark_offline(self) -> None:
        self.status = NodeStatus.OFFLINE

    def mark_maintenance(self) -> None:
        self.status = NodeStatus.MAINTENANCE


@dataclass
class HACluster:
    """A high-availability cluster with automatic failover."""
    name: str
    id: str = ""
    nodes: Dict[str, HANode] = field(default_factory=dict)
    failover_strategy: FailoverStrategy = FailoverStrategy.ACTIVE_PASSIVE
    quorum_size: int = 1
    failover_hooks: List[Callable] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_node(self, node: HANode) -> None:
        self.nodes[node.id] = node

    def remove_node(self, node_id: str) -> bool:
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False

    @property
    def active_node(self) -> Optional[HANode]:
        """Get the current active node."""
        for node in self.nodes.values():
            if node.role == "active" and node.is_healthy():
                return node
        return None

    @property
    def healthy_node_count(self) -> int:
        return sum(1 for n in self.nodes.values() if n.is_healthy())

    @property
    def has_quorum(self) -> bool:
        return self.healthy_node_count >= self.quorum_size

    def perform_failover(self) -> Optional[HANode]:
        """Attempt automatic failover to a healthy passive node."""
        if self.failover_strategy == FailoverStrategy.MANUAL:
            return None

        for node in self.nodes.values():
            if node.role == "passive" and node.is_healthy():
                # Promote to active
                for n in self.nodes.values():
                    if n.role == "active":
                        n.role = "standby"
                node.role = "active"
                logger.info("Failover: %s promoted to active", node.name)

                for hook in self.failover_hooks:
                    try:
                        hook(node)
                    except Exception as e:
                        logger.warning("Failover hook failed: %s", e)
                return node
        return None

    def health_summary(self) -> Dict[str, Any]:
        """Get a summary of cluster health."""
        return {
            "cluster": self.name,
            "total_nodes": len(self.nodes),
            "healthy": self.healthy_node_count,
            "degraded": sum(1 for n in self.nodes.values() if n.status == NodeStatus.DEGRADED),
            "unhealthy": sum(1 for n in self.nodes.values() if n.status == NodeStatus.UNHEALTHY),
            "offline": sum(1 for n in self.nodes.values() if n.status == NodeStatus.OFFLINE),
            "has_quorum": self.has_quorum,
            "active_node": self.active_node.name if self.active_node else None,
        }
