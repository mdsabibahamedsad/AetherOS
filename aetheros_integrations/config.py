"""AetherOS Integrations — configuration.

Resolves the ``integrations`` block from ``config.yaml`` into typed settings,
mirroring the loader used by the rest of the codebase.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class WebhookSettings:
    secret: str = ""
    default_max_attempts: int = 3
    retry_backoff_s: float = 2.0
    max_hops: int = 3
    timeout_s: float = 15.0
    replay_ttl_s: float = 86400 * 7


@dataclass
class SchedulerSettings:
    poll_interval_s: float = 5.0
    missed_job_window_s: float = 300.0
    max_simultaneous_runs: int = 8


@dataclass
class AuthSettings:
    token_ttl_s: float = 3600.0
    refresh_margin_s: float = 300.0
    device_poll_interval_s: float = 5.0
    device_timeout_s: float = 600.0
    jwt_issuer: str = "aetheros"
    vault_key_env: str = "AETHEROS_INTEGRATIONS_VAULT_KEY"


@dataclass
class MonitoringSettings:
    retention_s: float = 86400 * 30
    sample_limit: int = 10000


@dataclass
class IntegrationsSettings:
    enabled: bool = True
    data_dir: str = "integrations"
    webhook: WebhookSettings = field(default_factory=WebhookSettings)
    scheduler: SchedulerSettings = field(default_factory=SchedulerSettings)
    auth: AuthSettings = field(default_factory=AuthSettings)
    monitoring: MonitoringSettings = field(default_factory=MonitoringSettings)
    auto_enable_on_install: bool = False
    max_offline_queue: int = 5000


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str) -> str:
    return str(value) if value is not None else default


def _read_config() -> Dict[str, Any]:
    try:
        from aetheros_cli.config import cfg_get, load_config
        cfg = load_config()
        raw = cfg_get(cfg, "integrations", default=None)
        return raw if isinstance(raw, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not load config.yaml integrations block: %s", exc)
        return {}


def load_integrations_settings() -> IntegrationsSettings:
    raw = _read_config()
    settings = IntegrationsSettings(
        enabled=_as_bool(raw.get("enabled"), True),
        data_dir=_as_str(raw.get("data_dir"), "integrations"),
        auto_enable_on_install=_as_bool(raw.get("auto_enable_on_install"), False),
        max_offline_queue=_as_int(raw.get("max_offline_queue"), 5000),
    )

    wh = raw.get("webhook") or {}
    settings.webhook = WebhookSettings(
        secret=_as_str(wh.get("secret"), ""),
        default_max_attempts=_as_int(wh.get("default_max_attempts"), 3),
        retry_backoff_s=_as_float(wh.get("retry_backoff_s"), 2.0),
        max_hops=_as_int(wh.get("max_hops"), 3),
        timeout_s=_as_float(wh.get("timeout_s"), 15.0),
        replay_ttl_s=_as_float(wh.get("replay_ttl_s"), 86400 * 7),
    )

    sch = raw.get("scheduler") or {}
    settings.scheduler = SchedulerSettings(
        poll_interval_s=_as_float(sch.get("poll_interval_s"), 5.0),
        missed_job_window_s=_as_float(sch.get("missed_job_window_s"), 300.0),
        max_simultaneous_runs=_as_int(sch.get("max_simultaneous_runs"), 8),
    )

    au = raw.get("auth") or {}
    settings.auth = AuthSettings(
        token_ttl_s=_as_float(au.get("token_ttl_s"), 3600.0),
        refresh_margin_s=_as_float(au.get("refresh_margin_s"), 300.0),
        device_poll_interval_s=_as_float(au.get("device_poll_interval_s"), 5.0),
        device_timeout_s=_as_float(au.get("device_timeout_s"), 600.0),
        jwt_issuer=_as_str(au.get("jwt_issuer"), "aetheros"),
        vault_key_env=_as_str(au.get("vault_key_env"), "AETHEROS_INTEGRATIONS_VAULT_KEY"),
    )

    mo = raw.get("monitoring") or {}
    settings.monitoring = MonitoringSettings(
        retention_s=_as_float(mo.get("retention_s"), 86400 * 30),
        sample_limit=_as_int(mo.get("sample_limit"), 10000),
    )
    return settings


def get_aetheros_home() -> Path:
    try:
        from aetheros_constants import get_aetheros_home as _gah
        return _gah()
    except Exception:  # noqa: BLE001
        return Path(os.environ.get("AETHEROS_HOME", str(Path.home() / ".aetheros")))


def get_aetheros_dir(subpath: str) -> Path:
    try:
        from aetheros_constants import get_aetheros_dir as _gad
        return _gad(subpath, subpath)
    except Exception:  # noqa: BLE001
        path = get_aetheros_home() / subpath
        path.mkdir(parents=True, exist_ok=True)
        return path
