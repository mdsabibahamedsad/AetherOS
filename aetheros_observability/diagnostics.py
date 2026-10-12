"""Diagnostics service — collect, analyze, summarize, export, validate.

Generates safe diagnostic bundles containing system version, AetherOS
version, platform, runtime versions, component health, recent errors,
metrics summary, trace IDs and a configuration summary.

NEVER includes secrets: every payload passes through automatic redaction.
"""

from __future__ import annotations

import csv
import io
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_observability.redaction import redact_payload, redact_text
from aetheros_observability.metrics import get_unified_metrics
from aetheros_observability.health import get_health_service
from aetheros_observability.errors import ErrorType

#: Keys that are always stripped from config summaries (defense in depth —
#: even if redaction misses a shape, these are dropped entirely).
_CONFIG_BLOCKLIST = frozenset(
    {"api_key", "secret", "token", "password", "auth", "credential"}
)


def _is_blocklisted_key(key: str) -> bool:
    k = key.lower()
    return any(b in k for b in _CONFIG_BLOCKLIST)


def _safe_config_summary(config: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
    """Return a redacted, size-capped config summary."""
    if depth > 2:
        return {"...": True}
    out: Dict[str, Any] = {}
    for key, value in (config or {}).items():
        if _is_blocklisted_key(key):
            continue
        if isinstance(value, dict):
            out[key] = _safe_config_summary(value, depth + 1)
        elif isinstance(value, (list, tuple)):
            out[key] = [redact_payload({"v": v})["v"] if isinstance(v, (dict, list)) else v
                        for v in value[:20]]
        elif isinstance(value, str) and len(value) > 500:
            out[key] = value[:500] + "..."
        else:
            out[key] = value
    return out


class DiagnosticsService:
    """Composes safe diagnostic bundles from existing infrastructure.

    Usage::

        ds = get_diagnostics_service()
        bundle = ds.bundle()
        ds.export(bundle, "diagnostics.json")
    """

    def __init__(self, diagnostics_manager=None, health_service=None,
                 metrics=None) -> None:
        self._diagnostics_manager = diagnostics_manager
        self._health_service = health_service
        self._metrics = metrics

    # ------------------------------------------------------------------
    # Lazy wiring to existing singletons
    # ------------------------------------------------------------------

    @property
    def manager(self):
        if self._diagnostics_manager is None:
            from aetheros_production.observability import get_diagnostics_manager
            self._diagnostics_manager = get_diagnostics_manager()
        return self._diagnostics_manager

    @property
    def health_service(self):
        if self._health_service is None:
            return get_health_service()
        return self._health_service

    @property
    def metrics(self):
        if self._metrics is None:
            return get_unified_metrics()
        return self._metrics

    # ------------------------------------------------------------------
    # Collection
    # ------------------------------------------------------------------

    def collect(self) -> Dict[str, Any]:
        """Collect environment + system information (no secrets)."""
        report = {
            "timestamp": time.time(),
            "platform": {
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
            },
            "runtime": {
                "python": sys.version.split()[0],
                "python_full": sys.version.replace("\n", " "),
                "implementation": sys.implementation.name,
            },
            "aetheros": self._aetheros_info(),
        }
        try:
            base = self.manager.run_diagnostics()
            for section in ("disk", "network", "environment"):
                if section in base:
                    report[section] = base[section]
        except Exception:
            pass
        return report

    def _aetheros_info(self) -> Dict[str, Any]:
        try:
            from aetheros_constants import get_aetheros_home
            home = get_aetheros_home()
            return {
                "home": str(home),
                "config_exists": (home / "config.yaml").exists(),
            }
        except Exception:
            return {"error": "could not resolve aetheros home"}

    # ------------------------------------------------------------------
    # Bundle
    # ------------------------------------------------------------------

    def bundle(self, *, config: Optional[Dict[str, Any]] = None,
               recent_errors: Optional[List[Dict[str, Any]]] = None,
               extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build a full, safe diagnostic bundle (Step 32).

        Fields: system version, AetherOS version, platform, runtime
        versions, component health, recent errors, metrics summary, trace
        IDs, configuration summary, dependency versions.  All redacted.
        """
        health = self.health_service.summary()
        metrics_snapshot = self.metrics.snapshot()
        bundle = {
            "generated_at": time.time(),
            "diagnostic_id": _new_id(),
            "aetheros_version": self._aetheros_version(),
            "collect": self.collect(),
            "health": health,
            "metrics": metrics_snapshot,
            "recent_errors": redact_payload(recent_errors or []),
            "trace_ids": self._recent_trace_ids(),
            "config_summary": _safe_config_summary(config or {}),
            "dependencies": self._dependency_versions(),
        }
        if extra:
            bundle["extra"] = redact_payload(extra)
        return self.redact(bundle)

    def _aetheros_version(self) -> str:
        try:
            from aetheros_production import get_version
            return get_version()
        except Exception:
            return "unknown"

    def _recent_trace_ids(self) -> List[str]:
        try:
            from aetheros_observability.tracing import get_unified_tracer
            spans = get_unified_tracer().get_recent_spans(limit=20)
            return [s.get("trace_id") for s in spans if s.get("trace_id")]
        except Exception:
            return []

    def _dependency_versions(self) -> Dict[str, str]:
        """Best-effort versions of key runtime dependencies."""
        versions: Dict[str, str] = {}
        for name in ("aetheros", "yaml", "requests", "httpx", "psutil"):
            try:
                from importlib.metadata import version as _ver
                versions[name] = _ver(name)
            except Exception:
                try:
                    mod = __import__(name)
                    versions[name] = getattr(mod, "__version__", "unknown")
                except Exception:
                    versions[name] = "unknown"
        return versions

    # ------------------------------------------------------------------
    # Redact / validate / summarize
    # ------------------------------------------------------------------

    def redact(self, payload: Any) -> Any:
        """Redact a bundle (or any payload) before export."""
        return redact_payload(payload)

    def validate(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a bundle for export safety.

        Checks required sections exist and no raw secrets leak.  Returns
        ``{valid, issues}``.
        """
        issues: List[str] = []
        for key in ("generated_at", "collect", "health", "metrics",
                    "config_summary"):
            if key not in bundle:
                issues.append(f"missing section: {key}")
        blob = json.dumps(bundle, default=str)
        for probe in ("sk-", "ghp_", "-----BEGIN"):
            if probe in blob:
                issues.append(f"possible secret leak: {probe}")
        return {"valid": not issues, "issues": issues}

    def summarize(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Return a concise summary for humans."""
        health = bundle.get("health", {})
        metrics = bundle.get("metrics", {})
        return {
            "aetheros_version": bundle.get("aetheros_version"),
            "os": bundle.get("collect", {}).get("platform", {}).get("os"),
            "health_status": health.get("status"),
            "unhealthy_components": [
                c for c, data in health.get("components", {}).items()
                if data.get("state") == "unhealthy"
            ],
            "degraded_components": list(health.get("degraded", {}).keys()),
            "total_requests": sum(
                v for k, v in metrics.get("counters", {}).items()
                if "request.count" in k
            ),
            "recent_errors": len(bundle.get("recent_errors", [])),
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(self, bundle: Dict[str, Any], path: str,
               fmt: str = "json") -> bool:
        """Export a bundle to disk (json | csv | text).  Never exports secrets."""
        bundle = self.redact(bundle)
        try:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if fmt == "json":
                target.write_text(
                    json.dumps(bundle, indent=2, default=str), encoding="utf-8"
                )
            elif fmt == "text":
                target.write_text(self._text_dump(bundle), encoding="utf-8")
            elif fmt == "csv":
                target.write_text(self._csv_dump(bundle), encoding="utf-8")
            else:
                return False
            return True
        except Exception:
            return False

    def export_json(self, bundle: Dict[str, Any]) -> str:
        return json.dumps(self.redact(bundle), indent=2, default=str)

    def export_csv(self, bundle: Dict[str, Any]) -> str:
        return self._csv_dump(self.redact(bundle))

    def export_text(self, bundle: Dict[str, Any]) -> str:
        return self._text_dump(self.redact(bundle))

    # ------------------------------------------------------------------
    # Dump helpers
    # ------------------------------------------------------------------

    def _text_dump(self, bundle: Dict[str, Any]) -> str:
        lines = [
            "AetherOS Diagnostics",
            "=" * 40,
            f"Version: {bundle.get('aetheros_version')}",
            f"OS: {bundle.get('collect', {}).get('platform', {}).get('os')} "
            f"{bundle.get('collect', {}).get('platform', {}).get('os_version', '')}",
            f"Python: {bundle.get('collect', {}).get('runtime', {}).get('python')}",
            f"Health: {bundle.get('health', {}).get('status')}",
        ]
        for name, data in bundle.get("health", {}).get("components", {}).items():
            lines.append(f"  {name}: {data.get('state')} — {data.get('message', '')}")
        lines.append(f"Recent errors: {len(bundle.get('recent_errors', []))}")
        return "\n".join(lines) + "\n"

    def _csv_dump(self, bundle: Dict[str, Any]) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["section", "key", "value"])
        writer.writerow(["version", "aetheros", bundle.get("aetheros_version")])
        for name, data in bundle.get("health", {}).get("components", {}).items():
            writer.writerow(["health", name, data.get("state")])
        for key, value in bundle.get("metrics", {}).get("counters", {}).items():
            writer.writerow(["metric", key, value])
        return buf.getvalue()


def _new_id() -> str:
    import uuid
    return uuid.uuid4().hex[:12]


_diagnostics_service: Optional[DiagnosticsService] = None


def get_diagnostics_service() -> DiagnosticsService:
    """Return the process-wide DiagnosticsService singleton."""
    global _diagnostics_service
    if _diagnostics_service is None:
        _diagnostics_service = DiagnosticsService()
    return _diagnostics_service