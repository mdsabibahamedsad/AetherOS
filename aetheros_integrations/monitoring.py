"""AetherOS Integrations — Monitoring.

Tracks integration status, failures, retries, latency, quota usage, and API
errors. Stores samples in a JSON history with retention pruning, and derives
aggregate health summaries.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from aetheros_integrations.config import get_aetheros_dir, load_integrations_settings
from aetheros_integrations.models import MonitorSample

logger = logging.getLogger(__name__)


class Monitor:
    """Time-series sample store with retention and aggregation."""

    def __init__(self, dirpath=None, settings=None):
        self._settings = settings or load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(self._settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "monitoring.json"
        self._lock = threading.RLock()
        self._samples: List[MonitorSample] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._samples = [MonitorSample(**item) for item in data]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load monitoring samples: %s", exc)

    def _save(self) -> None:
        payload = [s.to_dict() for s in self._samples]
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def record(self, integration_id: str, metric: str, value: float = 0.0, extra: Optional[Dict[str, Any]] = None) -> MonitorSample:
        sample = MonitorSample(integration_id=integration_id, metric=metric, value=value, extra=extra or {})
        with self._lock:
            self._samples.append(sample)
            self._prune()
            self._save()
        return sample

    def record_api_error(self, integration_id: str, status: int, detail: str = "") -> None:
        self.record(integration_id, "api_error", extra={"status": status, "detail": detail[:200]})

    def record_failure(self, integration_id: str, error: str = "") -> None:
        self.record(integration_id, "failure", extra={"error": error[:200]})

    def record_retry(self, integration_id: str, attempt: int) -> None:
        self.record(integration_id, "retry", value=attempt)

    def record_quota(self, integration_id: str, used: float, limit: float = 0.0) -> None:
        self.record(integration_id, "quota_used", value=used, extra={"limit": limit})

    def _prune(self) -> None:
        cutoff = time.time() - self._settings.monitoring.retention_s
        self._samples = [s for s in self._samples if s.timestamp >= cutoff]
        if len(self._samples) > self._settings.monitoring.sample_limit:
            self._samples = self._samples[-self._settings.monitoring.sample_limit :]

    # -- queries ----------------------------------------------------------

    def query(self, integration_id: str = "", metric: str = "", limit: int = 100) -> List[MonitorSample]:
        with self._lock:
            items = list(self._samples)
        if integration_id:
            items = [s for s in items if s.integration_id == integration_id]
        if metric:
            items = [s for s in items if s.metric == metric]
        items.sort(key=lambda s: s.timestamp, reverse=True)
        return items[:limit]

    def summary(self, integration_id: str = "") -> Dict[str, Any]:
        samples = self.query(integration_id=integration_id, limit=10000)
        failures = [s for s in samples if s.metric == "failure"]
        retries = [s for s in samples if s.metric == "retry"]
        api_errors = [s for s in samples if s.metric == "api_error"]
        latencies = [s.value for s in samples if s.metric == "latency_ms"]
        latencies += [s.value for s in samples if s.metric == "workflow_latency_ms"]
        quotas = [s for s in samples if s.metric == "quota_used"]
        return {
            "integration_id": integration_id,
            "samples": len(samples),
            "failures": len(failures),
            "retries": sum(s.value for s in retries),
            "api_errors": len(api_errors),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "max_latency_ms": round(max(latencies), 2) if latencies else 0.0,
            "quota_samples": len(quotas),
            "latest_quota": quotas[-1].value if quotas else 0.0,
        }
