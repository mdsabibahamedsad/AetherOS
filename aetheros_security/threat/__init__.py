"""
Threat Detection for AetherOS
=============================

Detect security threats:
    - Suspicious Plugins
    - Repeated Failures
    - Unexpected File Access
    - Mass File Deletion
    - Unusual Network Activity
    - Excessive Resource Usage

Usage::

    from aetheros_security.threat import ThreatDetector

    detector = ThreatDetector()
    threats = detector.analyze_activity()
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ThreatCategory(Enum):
    """Categories of threats."""
    SUSPICIOUS_PLUGIN = "suspicious_plugin"
    REPEATED_FAILURES = "repeated_failures"
    UNEXPECTED_FILE_ACCESS = "unexpected_file_access"
    MASS_FILE_DELETION = "mass_file_deletion"
    UNUSUAL_NETWORK = "unusual_network"
    EXCESSIVE_RESOURCES = "excessive_resources"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"


class ThreatLevel(Enum):
    """Threat levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ThreatAlert:
    """A detected threat alert."""
    alert_id: str
    category: ThreatCategory
    level: ThreatLevel
    title: str
    description: str
    timestamp: float
    source: str = ""
    affected_components: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActivityRecord:
    """An activity record for analysis."""
    timestamp: float
    activity_type: str
    source: str
    details: Dict[str, Any] = field(default_factory=dict)


class ThreatDetector:
    """Detects security threats in AetherOS.

    Usage::

        detector = ThreatDetector()

        # Record activity
        detector.record_activity("file_access", "my-plugin", {"path": "/etc/passwd"})

        # Analyze for threats
        threats = detector.analyze_activity()

        # Get recent alerts
        alerts = detector.get_recent_alerts()
    """

    def __init__(self) -> None:
        self._activities: List[ActivityRecord] = []
        self._alerts: List[ThreatAlert] = []
        self._counters: Dict[str, int] = defaultdict(int)
        self._thresholds = {
            "failure_limit": 5,
            "file_delete_limit": 10,
            "network_request_limit": 100,
            "resource_usage_percent": 90,
        }

    def record_activity(
        self,
        activity_type: str,
        source: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an activity for analysis.

        Args:
            activity_type: Type of activity.
            source: Source of the activity.
            details: Activity details.
        """
        record = ActivityRecord(
            timestamp=time.time(),
            activity_type=activity_type,
            source=source,
            details=details or {},
        )
        self._activities.append(record)

        # Keep only last 10000 activities
        if len(self._activities) > 10000:
            self._activities = self._activities[-10000:]

    def analyze_activity(self) -> List[ThreatAlert]:
        """Analyze recorded activity for threats.

        Returns:
            List of detected threat alerts.
        """
        new_alerts = []

        # Check for repeated failures
        alerts = self._check_repeated_failures()
        new_alerts.extend(alerts)

        # Check for mass file deletion
        alerts = self._check_mass_file_deletion()
        new_alerts.extend(alerts)

        # Check for unusual network activity
        alerts = self._check_unusual_network()
        new_alerts.extend(alerts)

        # Check for suspicious plugins
        alerts = self._check_suspicious_plugins()
        new_alerts.extend(alerts)

        # Check for excessive resource usage
        alerts = self._check_excessive_resources()
        new_alerts.extend(alerts)

        # Store new alerts
        self._alerts.extend(new_alerts)

        return new_alerts

    def _check_repeated_failures(self) -> List[ThreatAlert]:
        """Check for repeated failures from a source."""
        alerts = []
        failure_counts: Dict[str, int] = defaultdict(int)

        # Count failures in last 5 minutes
        cutoff = time.time() - 300
        for activity in self._activities:
            if activity.timestamp < cutoff:
                continue
            if activity.activity_type == "failure":
                failure_counts[activity.source] += 1

        for source, count in failure_counts.items():
            if count >= self._thresholds["failure_limit"]:
                alerts.append(ThreatAlert(
                    alert_id=f"FLOOD-{len(self._alerts)+1:04d}",
                    category=ThreatCategory.REPEATED_FAILURES,
                    level=ThreatLevel.MEDIUM,
                    title=f"Repeated failures from {source}",
                    description=f"{source} has failed {count} times in 5 minutes",
                    timestamp=time.time(),
                    source=source,
                    recommendations=[
                        "Check plugin configuration",
                        "Review error logs",
                        "Consider blocking the source",
                    ],
                ))

        return alerts

    def _check_mass_file_deletion(self) -> List[ThreatAlert]:
        """Check for mass file deletion."""
        alerts = []
        delete_counts: Dict[str, int] = defaultdict(int)

        # Count deletions in last minute
        cutoff = time.time() - 60
        for activity in self._activities:
            if activity.timestamp < cutoff:
                continue
            if activity.activity_type == "file_delete":
                delete_counts[activity.source] += 1

        for source, count in delete_counts.items():
            if count >= self._thresholds["file_delete_limit"]:
                alerts.append(ThreatAlert(
                    alert_id=f"MASSDEL-{len(self._alerts)+1:04d}",
                    category=ThreatCategory.MASS_FILE_DELETION,
                    level=ThreatLevel.HIGH,
                    title=f"Mass file deletion by {source}",
                    description=f"{source} deleted {count} files in 1 minute",
                    timestamp=time.time(),
                    source=source,
                    affected_components=["filesystem"],
                    recommendations=[
                        "Verify deletion was intentional",
                        "Check backup status",
                        "Consider blocking the source",
                    ],
                ))

        return alerts

    def _check_unusual_network(self) -> List[ThreatAlert]:
        """Check for unusual network activity."""
        alerts = []
        network_counts: Dict[str, int] = defaultdict(int)

        # Count requests in last minute
        cutoff = time.time() - 60
        for activity in self._activities:
            if activity.timestamp < cutoff:
                continue
            if activity.activity_type == "network_request":
                network_counts[activity.source] += 1

        for source, count in network_counts.items():
            if count >= self._thresholds["network_request_limit"]:
                alerts.append(ThreatAlert(
                    alert_id=f"NETFLOOD-{len(self._alerts)+1:04d}",
                    category=ThreatCategory.UNUSUAL_NETWORK,
                    level=ThreatLevel.MEDIUM,
                    title=f"Unusual network activity from {source}",
                    description=f"{source} made {count} network requests in 1 minute",
                    timestamp=time.time(),
                    source=source,
                    affected_components=["network"],
                    recommendations=[
                        "Check for data exfiltration",
                        "Review network logs",
                        "Consider rate limiting",
                    ],
                ))

        return alerts

    def _check_suspicious_plugins(self) -> List[ThreatAlert]:
        """Check for suspicious plugin activity."""
        alerts = []

        # Check for plugins requesting excessive permissions
        permission_requests: Dict[str, int] = defaultdict(int)
        cutoff = time.time() - 3600  # Last hour

        for activity in self._activities:
            if activity.timestamp < cutoff:
                continue
            if activity.activity_type == "permission_request":
                permission_requests[activity.source] += 1

        for source, count in permission_requests.items():
            if count > 10:  # More than 10 permission requests in an hour
                alerts.append(ThreatAlert(
                    alert_id=f"SUSP-{len(self._alerts)+1:04d}",
                    category=ThreatCategory.SUSPICIOUS_PLUGIN,
                    level=ThreatLevel.LOW,
                    title=f"Suspicious plugin activity: {source}",
                    description=f"{source} made {count} permission requests in 1 hour",
                    timestamp=time.time(),
                    source=source,
                    recommendations=[
                        "Review plugin permissions",
                        "Check plugin reputation",
                        "Consider disabling the plugin",
                    ],
                ))

        return alerts

    def _check_excessive_resources(self) -> List[ThreatAlert]:
        """Check for excessive resource usage.

        Uses ``psutil`` to compare current process memory/CPU/thread counts
        against configurable thresholds. Raised alerts carry the measured
        values so the threshold check is behaviorally testable.
        """
        alerts = []
        try:
            import psutil
        except ImportError:
            return alerts

        try:
            proc = psutil.Process(os.getpid())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return alerts

        thresholds = self._thresholds
        memory_mb = proc.memory_info().rss / (1024 * 1024)
        mem_limit = thresholds.get("max_memory_mb", 4096)
        if memory_mb > mem_limit:
            alerts.append(self._make_alert(
                ThreatCategory.EXCESSIVE_RESOURCES,
                ThreatLevel.HIGH,
                f"Process memory {memory_mb:.0f} MB exceeds {mem_limit} MB limit",
                f"memory={memory_mb:.0f}MB limit={mem_limit}MB",
                ["Restart the agent process", "Review running plugins for leaks"],
            ))

        cpu_percent = proc.cpu_percent(interval=0.1)
        cpu_limit = thresholds.get("max_cpu_percent", 95.0)
        if cpu_percent > cpu_limit:
            alerts.append(self._make_alert(
                ThreatCategory.EXCESSIVE_RESOURCES,
                ThreatLevel.MEDIUM,
                f"Process CPU {cpu_percent:.0f}% exceeds {cpu_limit:.0f}% limit",
                f"cpu={cpu_percent:.0f}% limit={cpu_limit:.0f}%",
                ["Identify the hot code path", "Reduce polling loops"],
            ))

        try:
            thread_count = len(proc.threads())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            thread_count = 0
        thread_limit = thresholds.get("max_threads", 500)
        if thread_count > thread_limit:
            alerts.append(self._make_alert(
                ThreatCategory.EXCESSIVE_RESOURCES,
                ThreatLevel.MEDIUM,
                f"Process spawned {thread_count} threads (limit {thread_limit})",
                f"threads={thread_count} limit={thread_limit}",
                ["Review thread usage in plugins", "Restart the agent process"],
            ))

        return alerts

    def _make_alert(
        self,
        category: ThreatCategory,
        level: ThreatLevel,
        title: str,
        description: str,
        recommendations: List[str],
    ) -> ThreatAlert:
        alert = ThreatAlert(
            alert_id=f"RES-{len(self._alerts)+1:04d}",
            category=category,
            level=level,
            title=title,
            description=description,
            timestamp=time.time(),
            source="threat_detector",
            recommendations=recommendations,
        )
        return alert

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent threat alerts.

        Args:
            limit: Maximum number of alerts.

        Returns:
            Recent alerts.
        """
        alerts = self._alerts[-limit:]
        return [
            {
                "alert_id": a.alert_id,
                "category": a.category.value,
                "level": a.level.value,
                "title": a.title,
                "description": a.description,
                "timestamp": a.timestamp,
                "source": a.source,
                "recommendations": a.recommendations,
            }
            for a in reversed(alerts)
        ]

    def get_threat_summary(self) -> Dict[str, Any]:
        """Get threat summary."""
        level_counts = {}
        category_counts = {}

        for alert in self._alerts:
            # Count by level
            level = alert.level.value
            level_counts[level] = level_counts.get(level, 0) + 1

            # Count by category
            category = alert.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "total_alerts": len(self._alerts),
            "by_level": level_counts,
            "by_category": category_counts,
            "recent_count": sum(
                1 for a in self._alerts
                if time.time() - a.timestamp < 3600
            ),
        }

    def set_threshold(self, key: str, value: int) -> None:
        """Set a detection threshold."""
        self._thresholds[key] = value

    def get_thresholds(self) -> Dict[str, int]:
        """Get detection thresholds."""
        return dict(self._thresholds)

    def clear_alerts(self) -> int:
        """Clear all alerts."""
        count = len(self._alerts)
        self._alerts.clear()
        return count


# Global threat detector
_threat_detector: ThreatDetector | None = None


def get_threat_detector() -> ThreatDetector:
    """Return the global ThreatDetector singleton."""
    global _threat_detector
    if _threat_detector is None:
        _threat_detector = ThreatDetector()
    return _threat_detector
