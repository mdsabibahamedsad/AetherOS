"""Load ``observability`` settings from config.yaml (best-effort).

The unified observability service reads its behavior from the standard
AetherOS config loader so operators control telemetry through config.yaml
— never through new env vars.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "retention_days": 30,
    "capture_content": False,
    "incident_thresholds": {
        "error_spike_count": 5,
        "latency_spike_ms": 10000,
        "window_seconds": 300,
    },
    "recovery_enabled": True,
    "recovery_max_attempts": 3,
}


def load_observability_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return merged observability config (defaults + user config)."""
    user_cfg: Dict[str, Any] = {}
    if config is None:
        try:
            from aetheros_cli.config import load_config
            loaded = load_config() or {}
        except Exception:
            loaded = {}
        user_cfg = loaded.get("observability") or {}
    elif isinstance(config, dict):
        user_cfg = config.get("observability") or {}

    merged: Dict[str, Any] = dict(_DEFAULTS)
    if isinstance(user_cfg, dict):
        for key, value in user_cfg.items():
            if key == "incident_thresholds" and isinstance(value, dict):
                merged["incident_thresholds"] = {
                    **_DEFAULTS["incident_thresholds"], **value}
            else:
                merged[key] = value
    return merged


def apply_observability_config(config: Optional[Dict[str, Any]] = None) -> None:
    """Apply observability config to the process-wide singletons.

    Safe to call more than once; re-applies thresholds and recovery
    budget each time.
    """
    from aetheros_observability.incidents import (
        AlertSeverity, ThresholdRule,
        get_incident_detector,
    )
    from aetheros_observability.recovery import get_recovery_service
    from aetheros_observability.service import get_observability_service

    cfg = load_observability_config(config)
    service = get_observability_service()
    service.enabled = bool(cfg.get("enabled", True))

    detector: IncidentDetector = get_incident_detector()
    thresholds = cfg.get("incident_thresholds") or {}
    detector.clear_rules()
    window = float(thresholds.get("window_seconds", 300))
    detector.add_rule(ThresholdRule(
        name="error_spike",
        metric="error_count",
        threshold=float(thresholds.get("error_spike_count", 5)),
        window_seconds=window,
        severity=AlertSeverity.ERROR,
        component="",
    ))
    detector.add_rule(ThresholdRule(
        name="latency_spike",
        metric="latency_ms",
        threshold=float(thresholds.get("latency_spike_ms", 10000)),
        window_seconds=window,
        severity=AlertSeverity.WARNING,
        component="",
    ))

    # Recovery budget default from config (per-action max attempts).
    max_attempts = int(cfg.get("recovery_max_attempts", 3))
    recovery = get_recovery_service()
    # Only update policies that already exist with a default max_attempts.
    from aetheros_observability.recovery import RecoveryPolicy
    for action, policy in list(recovery._policies.items()):
        if policy.max_attempts == 3:
            recovery._policies[action] = RecoveryPolicy(
                action=policy.action, trigger=policy.trigger,
                precondition=policy.precondition, risk=policy.risk,
                rollback=policy.rollback, max_attempts=max_attempts,
                cooldown_seconds=policy.cooldown_seconds,
                audit_event=policy.audit_event,
            )