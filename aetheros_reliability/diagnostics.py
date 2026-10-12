"""Reliability diagnostic bundle — safe, redacted export.

Composes a focused reliability report: version, platform, component health,
recent recovery events, error summaries, config metadata, backup status,
last-known-good status and operating mode.

NEVER includes API keys, passwords, tokens or private keys — the config
summary is key-blocklisted and the whole payload passes through the
observability redactor before export.
"""

from __future__ import annotations

import json
import logging
import platform
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)

#: Config keys never echoed into a diagnostic bundle (defense in depth).
_CONFIG_BLOCKLIST = frozenset(
    {"api_key", "secret", "token", "password", "passwd", "auth", "credential"}
)


def _blocklisted(key: str) -> bool:
    k = key.lower()
    return any(b in k for b in _CONFIG_BLOCKLIST)


def _safe_config_summary(config: Optional[Dict[str, Any]],
                         depth: int = 0) -> Dict[str, Any]:
    if depth > 2:
        return {"...": True}
    out: Dict[str, Any] = {}
    for key, value in (config or {}).items():
        if _blocklisted(key):
            continue
        if isinstance(value, dict):
            out[key] = _safe_config_summary(value, depth + 1)
        elif isinstance(value, (list, tuple)):
            out[key] = value[:10]
        elif isinstance(value, str) and len(value) > 200:
            out[key] = value[:200] + "..."
        else:
            out[key] = value
    return out


class ReliabilityDiagnostics:
    """Builds and exports the reliability diagnostic bundle.

    Usage::

        rd = get_reliability_diagnostics()
        bundle = rd.bundle()
        rd.export(bundle, "reliability-diagnostics.json")
    """

    def bundle(self, *, config: Optional[Dict[str, Any]] = None,
               extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Assemble a complete, redacted reliability bundle."""
        bundle: Dict[str, Any] = {
            "generated_at": time.time(),
            "diagnostic_id": uuid.uuid4().hex[:12],
            "type": "reliability",
            "version": self._version(),
            "platform": {
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "python": sys.version.split()[0],
            },
            "health": self._health(),
            "mode": self._mode(),
            "recovery": self._recovery(),
            "watchdog": self._watchdog(),
            "journal": self._journal(),
            "backups": self._backups(),
            "last_known_good": self._lkg(),
            "errors": self._errors(),
            "config_summary": _safe_config_summary(config or {}),
        }
        if extra:
            bundle["extra"] = extra
        return self._redact(bundle)

    def export(self, bundle: Dict[str, Any], path: str) -> bool:
        """Export a bundle to disk (JSON).  Redacts before writing."""
        payload = self._redact(bundle)
        try:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2, default=str),
                              encoding="utf-8")
            return True
        except OSError:
            return False

    def validate(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Check required sections exist and no secrets leak."""
        issues = []
        for key in ("generated_at", "version", "platform", "health", "recovery"):
            if key not in bundle:
                issues.append(f"missing section: {key}")
        blob = json.dumps(bundle, default=str)
        for probe in ("sk-", "ghp_", "-----BEGIN", "xoxb-"):
            if probe in blob:
                issues.append(f"possible secret leak: {probe}")
        return {"valid": not issues, "issues": issues}

    # ------------------------------------------------------------------
    # Section collectors (all failure-isolated)
    # ------------------------------------------------------------------

    def _health(self) -> Dict[str, Any]:
        try:
            from aetheros_observability.health import get_health_service
            return get_health_service().summary()
        except Exception:
            return {"status": "unknown"}

    def _mode(self) -> Dict[str, Any]:
        try:
            from aetheros_reliability.modes import get_mode_controller
            return get_mode_controller().snapshot()
        except Exception:
            return {"mode": "normal"}

    def _recovery(self) -> Dict[str, Any]:
        try:
            from aetheros_observability.recovery import get_recovery_service
            rs = get_recovery_service()
            return {
                "history": rs.history(limit=20),
                "crash_loops": rs.crash_loops(),
            }
        except Exception:
            return {"history": []}

    def _watchdog(self) -> Dict[str, Any]:
        try:
            from aetheros_reliability.watchdog import get_watchdog
            return get_watchdog().status()
        except Exception:
            return {}

    def _journal(self) -> Dict[str, Any]:
        try:
            from aetheros_reliability.journal import get_recovery_journal
            return get_recovery_journal().stats()
        except Exception:
            return {}

    def _backups(self) -> Dict[str, Any]:
        try:
            from aetheros_reliability.backup import get_backup_store
            entries = get_backup_store().list()
            return {
                "count": len(entries),
                "latest": entries[0].to_dict() if entries else None,
                "all_valid": all(e.valid for e in entries),
            }
        except Exception:
            return {"count": 0}

    def _lkg(self) -> Dict[str, Any]:
        try:
            from aetheros_reliability.config_recovery import get_config_recovery
            cr = get_config_recovery()
            return {
                "has_last_known_good": cr.has_last_known_good(),
                "config_valid": cr.validate().valid,
            }
        except Exception:
            return {"has_last_known_good": False}

    def _errors(self) -> Dict[str, Any]:
        try:
            from aetheros_observability.incidents import get_incident_detector
            return get_incident_detector().summary()
        except Exception:
            return {"active_count": 0}

    def _version(self) -> str:
        try:
            from aetheros_cli import __version__
            return str(__version__)
        except Exception:
            return "unknown"

    def _redact(self, payload: Any) -> Any:
        try:
            from aetheros_observability.redaction import redact_payload
            return redact_payload(payload)
        except Exception:
            return payload

    def summarize(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "version": bundle.get("version"),
            "health_status": bundle.get("health", {}).get("status"),
            "mode": bundle.get("mode", {}).get("mode"),
            "recovery_attempts": len(bundle.get("recovery", {}).get("history", [])),
            "backup_count": bundle.get("backups", {}).get("count", 0),
            "has_last_known_good": bundle.get("last_known_good", {}).get("has_last_known_good"),
        }


_diag: Optional[ReliabilityDiagnostics] = None
_diag_lock = threading.Lock()


def get_reliability_diagnostics() -> ReliabilityDiagnostics:
    """Return the process-wide ReliabilityDiagnostics singleton."""
    global _diag
    if _diag is None:
        with _diag_lock:
            if _diag is None:
                _diag = ReliabilityDiagnostics()
    return _diag