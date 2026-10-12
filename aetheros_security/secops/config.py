"""
SecOps configuration.

Loaded from the ``security.secops`` block in ``config.yaml`` (mirrors the
``security.control_plane`` block added in the security control-plane phase).
All SecOps behavioral settings live in config — never in ``.env``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SecOpsConfig:
    """Runtime configuration for the Security Operations layer."""

    enabled: bool = True
    max_events: int = 20000
    persist_events: bool = False
    # Detection
    detection_enabled: bool = True
    auto_contain_high_severity: bool = False
    auto_contain_critical_severity: bool = True
    # Alerting
    alert_cooldown_seconds: float = 300.0
    alert_dedup_window_seconds: float = 300.0
    escalate_after_seconds: float = 1800.0
    # Health
    health_report_interval_seconds: float = 60.0
    # Learning
    learning_enabled: bool = True
    learning_auto_apply: bool = False  # changes always require explicit approval
    # Forensics / retention
    retention_days: int = 30
    evidence_max_entries: int = 500

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SecOpsConfig":
        cfg = cls()
        if not data:
            return cfg
        for key in cls.__dataclass_fields__:  # type: ignore[arg-type]
            if key in data and data[key] is not None:
                setattr(cfg, key, data[key])
        return cfg


def load_secops_config(config: Optional[Dict[str, Any]] = None) -> SecOpsConfig:
    """Load the SecOps config from a resolved config dict.

    The caller (CLI/gateway loader) passes the user config YAML dict.  When
    omitted, attempts a direct read of the ``security.secops`` key via the
    default config path.
    """
    if config is None:
        try:
            from aetheros_cli.config import load_config
            resolved = load_config()
            config = resolved.get("security", {})
        except Exception:
            return SecOpsConfig()
        return SecOpsConfig.from_dict(config.get("secops", {}))
    security = config.get("security", {}) if isinstance(config, dict) else {}
    secops = security.get("secops", {}) if isinstance(security, dict) else {}
    return SecOpsConfig.from_dict(secops)


#: Default config block emitted into config.yaml / DEFAULT_CONFIG
def default_secops_config_block() -> Dict[str, Any]:
    return {
        "enabled": True,
        "max_events": 20000,
        "persist_events": False,
        "detection_enabled": True,
        "auto_contain_high_severity": False,
        "auto_contain_critical_severity": True,
        "alert_cooldown_seconds": 300.0,
        "alert_dedup_window_seconds": 300.0,
        "escalate_after_seconds": 1800.0,
        "health_report_interval_seconds": 60.0,
        "learning_enabled": True,
        "learning_auto_apply": False,
        "retention_days": 30,
        "evidence_max_entries": 500,
    }