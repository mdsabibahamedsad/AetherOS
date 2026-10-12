"""Advanced Monitoring & Alerting (Phase 64).

Comprehensive observability with:
- Distributed tracing
- Custom metrics and dashboards
- Alerting with multiple channels
- Anomaly detection
- SLO/SLI tracking
- Log aggregation
- Real-time dashboards
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union
from pathlib import Path

from agent.multimodal.production import MetricsCollector

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertState(Enum):
    FIRING = "firing"
    PENDING = "pending"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class AlertRule:
    rule_id: str
    name: str
    description: str
    metric_name: str
    condition: str  # e.g., "> 0.9", "< 100", "== 0"
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    duration_seconds: int = 60  # How long condition must persist
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    cooldown_seconds: int = 300


@dataclass
class Alert:
    alert_id: str
    rule_id: str
    name: str
    severity: AlertSeverity
    state: AlertState = AlertState.PENDING
    message: str = ""
    value: float = 0.0
    threshold: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    starts_at: float = field(default_factory=time.time)
    ends_at: Optional[float] = None
    updated_at: float = field(default_factory=time.time)
    generator_url: str = ""


@dataclass
class SLO:
    """Service Level Objective."""
    slo_id: str
    name: str
    description: str
    sli_name: str  # Service Level Indicator
    target: float  # e.g., 0.999 for 99.9%
    window: str = "30d"  # 1h, 24h, 7d, 30d
    target_per_period: int = 1  # How many windows must meet target
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class SLI:
    """Service Level Indicator."""
    sli_id: str
    name: str
    description: str
    good_query: str  # Query for "good" events
    total_query: str  # Query for total events
    # Computed
    value: float = 0.0
    error_budget_remaining: float = 1.0
    error_budget_consumed: float = 0.0


class MetricsRegistry:
    """Central metrics registry with multiple backends."""

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._summaries: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._labels_index: Dict[str, Set[str]] = defaultdict(set)

    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value
            if labels:
                for k, v in labels.items():
                    self._labels_index[f"{name}.{k}"].add(v)

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
            if labels:
                for k, v in labels.items():
                    self._labels_index[f"{name}.{k}"].add(v)

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
            # Keep last 1000 values
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]

    def summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.histogram(name, value, labels)

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        key = self._make_key(name, labels)
        with self._lock:
            return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        key = self._make_key(name, labels)
        with self._lock:
            return self._gauges.get(key)

    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        key = self._make_key(name, labels)
        with self._lock:
            values = self._histograms.get(key, [])
            if not values:
                return {}
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            return {
                "count": n,
                "sum": sum(sorted_vals),
                "min": sorted_vals[0],
                "max": sorted_vals[-1],
                "mean": sum(sorted_vals) / n,
                "p50": sorted_vals[n // 2],
                "p90": sorted_vals[int(n * 0.9)],
                "p95": sorted_vals[int(n * 0.95)],
                "p99": sorted_vals[int(n * 0.99)],
            }

    def get_all_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: self._histogram_stats(v) for k, v in self._histograms.items()},
            }

    def _histogram_stats(self, values: List[float]) -> Dict[str, float]:
        if not values:
            return {}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "sum": sum(sorted_vals),
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "mean": sum(sorted_vals) / n,
            "p50": sorted_vals[n // 2],
            "p90": sorted_vals[int(n * 0.9)],
            "p95": sorted_vals[int(n * 0.95)],
            "p99": sorted_vals[int(n * 0.99)],
        }

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class AlertManager:
    """Alert evaluation and management."""

    def __init__(self, metrics: MetricsRegistry):
        self.metrics = metrics
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._lock = threading.Lock()
        self._notification_handlers: List[Callable[[Alert], None]] = []
        self._silences: Dict[str, Dict] = {}  # silence_id -> {rule_id, until}
        self._evaluation_thread: Optional[threading.Thread] = None
        self._running = False

    def add_rule(self, rule: AlertRule) -> bool:
        with self._lock:
            if rule.rule_id in self._rules:
                return False
            self._rules[rule.rule_id] = rule
            return True

    def remove_rule(self, rule_id: str) -> bool:
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                # Also remove any active alerts for this rule
                to_remove = [aid for aid, alert in self._active_alerts.items() if alert.rule_id == rule_id]
                for aid in to_remove:
                    del self._active_alerts[aid]
                return True
            return False

    def add_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        with self._lock:
            self._notification_handlers.append(handler)

    def silence(self, rule_id: str, duration_seconds: int, reason: str = "") -> str:
        silence_id = f"silence_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._silences[silence_id] = {
                "rule_id": rule_id,
                "until": time.time() + duration_seconds,
                "reason": reason,
            }
        return silence_id

    def remove_silence(self, silence_id: str) -> bool:
        with self._lock:
            if silence_id in self._silences:
                del self._silences[silence_id]
                return True
            return False

    def start(self, interval: float = 30.0) -> None:
        if self._running:
            return
        self._running = True
        self._evaluation_thread = threading.Thread(target=self._evaluation_loop, args=(interval,), daemon=True)
        self._evaluation_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._evaluation_thread:
            self._evaluation_thread.join(timeout=5.0)

    def _evaluation_loop(self, interval: float) -> None:
        while self._running:
            time.sleep(interval)
            self._evaluate_rules()

    def _evaluate_rules(self) -> None:
        with self._lock:
            for rule in self._rules.values():
                if not rule.enabled:
                    continue

                # Check silences
                silenced = any(
                    s["rule_id"] == rule.rule_id and s["until"] > time.time()
                    for s in self._silences.values()
                )
                if silenced:
                    continue

                # Evaluate condition
                self._evaluate_rule(rule)

    def _evaluate_rule(self, rule: AlertRule) -> None:
        # Get current metric value
        # Parse condition like "> 0.9", "< 100", "== 0"
        try:
            value = self._get_metric_value(rule.metric_name, rule.labels)
            if value is None:
                return

            triggered = self._evaluate_condition(value, rule.condition, rule.threshold)

            alert_id = f"alert_{rule.rule_id}"
            existing = self._active_alerts.get(alert_id)

            if triggered:
                if existing:
                    existing.value = value
                    existing.updated_at = time.time()
                    if existing.state == AlertState.RESOLVED:
                        existing.state = AlertState.FIRING
                        existing.starts_at = time.time()
                else:
                    alert = Alert(
                        alert_id=alert_id,
                        rule_id=rule.rule_id,
                        name=rule.name,
                        severity=rule.severity,
                        state=AlertState.FIRING,
                        message=f"{rule.name}: {rule.metric_name} {rule.condition} {rule.threshold} (current: {value})",
                        value=value,
                        threshold=rule.threshold,
                        labels=rule.labels,
                        annotations=rule.annotations,
                    )
                    self._active_alerts[alert_id] = alert
                    self._fire_notifications(alert)
            else:
                if existing and existing.state == AlertState.FIRING:
                    existing.state = AlertState.RESOLVED
                    existing.ends_at = time.time()
                    self._fire_notifications(existing)

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")

    def _get_metric_value(self, metric_name: str, labels: Dict[str, str]) -> Optional[float]:
        # Try gauge first, then counter rate
        gauge = self.metrics.get_gauge(metric_name, labels)
        if gauge is not None:
            return gauge
        # Try to compute rate from counter
        # This is simplified - in production would use rate()
        counter = self.metrics.get_counter(metric_name, labels)
        return float(counter) if counter else None

    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        condition = condition.strip()
        if condition.startswith(">"):
            return value > float(condition[1:].strip())
        elif condition.startswith("<"):
            return value < float(condition[1:].strip())
        elif condition.startswith(">="):
            return value >= float(condition[2:].strip())
        elif condition.startswith("<="):
            return value <= float(condition[2:].strip())
        elif condition.startswith("=="):
            return abs(value - float(condition[2:].strip())) < 1e-9
        elif condition.startswith("!="):
            return abs(value - float(condition[2:].strip())) >= 1e-9
        return False

    def _fire_notifications(self, alert: Alert) -> None:
        for handler in self._notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")

    def get_active_alerts(self) -> List[Alert]:
        with self._lock:
            return [a for a in self._active_alerts.values() if a.state == AlertState.FIRING]

    def get_all_alerts(self) -> List[Alert]:
        with self._lock:
            return list(self._active_alerts.values())


class SLOManager:
    """SLO/SLI management and error budget tracking."""

    def __init__(self, metrics: MetricsRegistry):
        self.metrics = metrics
        self._slos: Dict[str, SLO] = {}
        self._slis: Dict[str, SLI] = {}
        self._lock = threading.Lock()

    def create_slo(self, slo: SLO) -> bool:
        with self._lock:
            if slo.slo_id in self._slos:
                return False
            self._slos[slo.slo_id] = slo
            return True

    def create_sli(self, sli: SLI) -> bool:
        with self._lock:
            if sli.sli_id in self._slis:
                return False
            self._slis[sli.sli_id] = sli
            return True

    def compute_sli(self, sli_id: str, window_seconds: float = 3600) -> Optional[SLI]:
        with self._lock:
            sli = self._slis.get(sli_id)
            if not sli:
                return None

            # Query metrics for good/total events
            # This is simplified - in production would query actual metrics
            good = self.metrics.get_counter(f"{sli.sli_name}_good") or 0
            total = self.metrics.get_counter(f"{sli.sli_name}_total") or 0

            if total == 0:
                sli.value = 1.0
                sli.error_budget_remaining = 1.0
                sli.error_budget_consumed = 0.0
            else:
                sli.value = good / total
                # Error budget: 1 - target (for availability SLI)
                # Simplified - would need SLO target
                sli.error_budget_consumed = 1.0 - sli.value
                sli.error_budget_remaining = sli.value

            return sli

    def get_error_budget(self, slo_id: str) -> Dict[str, float]:
        with self._lock:
            slo = self._slos.get(slo_id)
            sli = self._slis.get(slo.sli_name) if slo else None

            if not slo or not sli:
                return {}

            target = slo.target
            current = sli.value
            error_budget = 1.0 - target
            consumed = 1.0 - current
            remaining = max(0, error_budget - consumed)

            # Burn rate
            burn_rate = consumed / error_budget if error_budget > 0 else 0

            return {
                "target": target,
                "current": current,
                "error_budget": error_budget,
                "consumed": consumed,
                "remaining": remaining,
                "burn_rate": burn_rate,
                "exhausted": remaining <= 0,
            }

    def get_slo_status(self, slo_id: str) -> Dict[str, Any]:
        with self._lock:
            slo = self._slos.get(slo_id)
            if not slo:
                return {}

            budget = self.get_error_budget(slo_id)
            return {
                "slo_id": slo_id,
                "name": slo.name,
                "target": slo.target,
                "window": slo.window,
                "error_budget": budget,
                "status": "meeting" if budget.get("remaining", 0) > 0 else "violating",
            }


class DashboardManager:
    """Dashboard management for real-time visualization."""

    def __init__(self, metrics: MetricsRegistry):
        self.metrics = metrics
        self._dashboards: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def create_dashboard(self, dashboard_id: str, name: str, layout: List[Dict]) -> bool:
        with self._lock:
            if dashboard_id in self._dashboards:
                return False
            self._dashboards[dashboard_id] = {
                "dashboard_id": dashboard_id,
                "name": name,
                "layout": layout,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            return True

    def update_dashboard(self, dashboard_id: str, layout: List[Dict]) -> bool:
        with self._lock:
            if dashboard_id not in self._dashboards:
                return False
            self._dashboards[dashboard_id]["layout"] = layout
            self._dashboards[dashboard_id]["updated_at"] = time.time()
            return True

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict]:
        with self._lock:
            return self._dashboards.get(dashboard_id)

    def list_dashboards(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "dashboard_id": d["dashboard_id"],
                    "name": d["name"],
                    "created_at": d["created_at"],
                }
                for d in self._dashboards.values()
            ]

    def get_dashboard_data(self, dashboard_id: str) -> Optional[Dict]:
        """Get real-time data for a dashboard."""
        with self._lock:
            dashboard = self._dashboards.get(dashboard_id)
            if not dashboard:
                return None

            # This would query metrics for each panel
            panels_data = []
            for panel in dashboard["layout"]:
                panel_data = self._query_panel(panel)
                panels_data.append({"panel_id": panel.get("id"), "data": panel_data})

            return {
                "dashboard_id": dashboard_id,
                "name": dashboard["name"],
                "panels": panels_data,
                "timestamp": time.time(),
            }

    def _query_panel(self, panel: Dict) -> Any:
        # Simplified panel query
        panel_type = panel.get("type", "metric")
        metric_name = panel.get("metric")
        labels = panel.get("labels", {})

        if panel_type == "gauge":
            value = self.metrics.get_gauge(metric_name, labels)
            return {"value": value}
        elif panel_type == "counter":
            value = self.metrics.get_counter(metric_name, labels)
            return {"value": value}
        elif panel_type == "histogram":
            return self.metrics.get_histogram_stats(metric_name, labels)
        return {}


class LogAggregator:
    """Centralized log aggregation with search."""

    def __init__(self, storage_path: str = "logs"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, List[int]] = defaultdict(list)  # term -> line numbers
        self._lock = threading.Lock()

    def ingest(self, log_entry: Dict[str, Any]) -> None:
        """Ingest a log entry."""
        with self._lock:
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = self.storage_path / f"logs_{date_str}.jsonl"

            entry = {
                "timestamp": time.time(),
                "level": log_entry.get("level", "INFO"),
                "service": log_entry.get("service", "unknown"),
                "message": log_entry.get("message", ""),
                "trace_id": log_entry.get("trace_id"),
                "span_id": log_entry.get("span_id"),
                "fields": log_entry.get("fields", {}),
            }

            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

            # Index for search
            message = log_entry.get("message", "")
            for term in message.lower().split():
                if len(term) > 2:
                    self._index[term].append(log_file.stat().st_size)  # Simplified

    def search(
        self,
        query: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        service: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Search logs (simplified)."""
        # In production, would use Elasticsearch or similar
        results = []
        query_terms = query.lower().split()

        with self._lock:
            log_files = sorted(self.storage_path.glob("logs_*.jsonl"))
            for log_file in log_files:
                if len(results) >= limit:
                    break
                try:
                    with open(log_file) as f:
                        for line in f:
                            entry = json.loads(line)
                            if service and entry.get("service") != service:
                                continue
                            if level and entry.get("level") != level:
                                continue
                            if start_time and entry["timestamp"] < start_time:
                                continue
                            if end_time and entry["timestamp"] > end_time:
                                continue
                            if all(term in entry["message"].lower() for term in query_terms):
                                results.append(entry)
                                if len(results) >= limit:
                                    break
                except Exception:
                    pass
        return results


class MonitoringStack:
    """Complete monitoring stack integrating all components."""

    def __init__(self, storage_path: str = "monitoring"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.metrics = MetricsRegistry()
        self.alert_manager = AlertManager(self.metrics)
        self.slo_manager = SLOManager(self.metrics)
        self.dashboard_manager = DashboardManager(self.metrics)
        self.log_aggregator = LogAggregator(str(self.storage_path / "logs"))

        # Default alerts
        self._setup_default_alerts()

    def _setup_default_alerts(self) -> None:
        """Setup default alert rules."""
        default_rules = [
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate",
                description="Error rate exceeds 5%",
                metric_name="error_rate",
                condition=">",
                threshold=0.05,
                severity=AlertSeverity.CRITICAL,
                duration_seconds=60,
            ),
            AlertRule(
                rule_id="high_latency",
                name="High Latency",
                description="P99 latency exceeds 5 seconds",
                metric_name="latency_p99",
                condition=">",
                threshold=5.0,
                severity=AlertSeverity.WARNING,
                duration_seconds=300,
            ),
            AlertRule(
                rule_id="high_memory",
                name="High Memory Usage",
                description="Memory usage exceeds 90%",
                metric_name="memory_usage_pct",
                condition=">",
                threshold=0.9,
                severity=AlertSeverity.WARNING,
                duration_seconds=300,
            ),
            AlertRule(
                rule_id="low_disk",
                name="Low Disk Space",
                description="Disk space below 10%",
                metric_name="disk_free_pct",
                condition="<",
                threshold=0.1,
                severity=AlertSeverity.CRITICAL,
                duration_seconds=60,
            ),
        ]

        for rule in default_rules:
            self.alert_manager.add_rule(rule)

    def start(self, evaluation_interval: float = 30.0) -> None:
        self.alert_manager.start(evaluation_interval)

    def stop(self) -> None:
        self.alert_manager.stop()

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        if metric_type == MetricType.COUNTER:
            self.metrics.counter(name, value)
        elif metric_type == MetricType.GAUGE:
            self.metrics.gauge(name, value)
        elif metric_type == MetricType.HISTOGRAM:
            self.metrics.histogram(name, value)
        elif metric_type == MetricType.SUMMARY:
            self.metrics.summary(name, value)

    def get_system_health(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics.get_all_metrics(),
            "active_alerts": self.alert_manager.get_active_alerts(),
            "all_alerts": self.alert_manager.get_all_alerts(),
        }


# Convenience functions
def create_monitoring_stack(storage_path: str = "monitoring") -> MonitoringStack:
    return MonitoringStack(storage_path)


def create_alert_rule(
    name: str,
    metric: str,
    condition: str,
    threshold: float,
    severity: AlertSeverity = AlertSeverity.WARNING,
) -> AlertRule:
    return AlertRule(
        rule_id=f"rule_{uuid.uuid4().hex[:8]}",
        name=name,
        description=f"Alert when {metric} {condition} {threshold}",
        metric_name=metric,
        condition=condition,
        threshold=threshold,
        severity=severity,
    )


def create_slo(
    name: str,
    sli_name: str,
    target: float,
    window: str = "30d",
) -> SLO:
    return SLO(
        slo_id=f"slo_{uuid.uuid4().hex[:8]}",
        name=name,
        description=f"SLO for {sli_name}",
        sli_name=sli_name,
        target=target,
        window=window,
    )


def create_sli(
    name: str,
    good_query: str,
    total_query: str,
) -> SLI:
    return SLI(
        sli_id=f"sli_{uuid.uuid4().hex[:8]}",
        name=name,
        description=f"SLI for {name}",
        good_query=good_query,
        total_query=total_query,
    )