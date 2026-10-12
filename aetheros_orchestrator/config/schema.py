from __future__ import annotations

import json
from typing import Any


REQUIRED_KEYS: dict[str, type | tuple[type, ...]] = {
    "daemon.host": str,
    "daemon.port": int,
    "daemon.log_level": str,
    "daemon.workers": int,
    "orchestrator.startup_timeout": (int, float),
    "orchestrator.shutdown_timeout": (int, float),
    "orchestrator.healthcheck_interval": (int, float),
}

DEFAULTS: dict[str, Any] = {
    "daemon": {
        "host": "127.0.0.1",
        "port": 8765,
        "log_level": "INFO",
        "workers": 4,
        "reload": False,
    },
    "orchestrator": {
        "startup_timeout": 30.0,
        "shutdown_timeout": 15.0,
        "healthcheck_interval": 10.0,
        "auto_start": True,
    },
    "logging": {
        "format": "json",
        "output": ["console"],
        "otel_enabled": False,
        "otel_endpoint": "",
    },
    "api": {
        "rest_enabled": True,
        "websocket_enabled": True,
        "cors_origins": ["*"],
        "rate_limit": 100,
    },
    "subsystems": {
        "mcp": {"enabled": True, "port": 9001},
        "reasoning": {"enabled": True, "workers": 2},
        "skills": {"enabled": True, "watch": True},
        "platform": {"enabled": True},
        "knowledge": {"enabled": True, "vector_backend": "sqlite"},
        "ui": {"enabled": True, "type": "cli"},
        "desktop": {"enabled": False},
    },
}


def validate_config(cfg: dict) -> list[str]:
    errors: list[str] = []
    for key, expected_type in REQUIRED_KEYS.items():
        parts = key.split(".")
        val = cfg
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = None
                break
        if val is None:
            errors.append(f"missing required key: {key}")
        elif not isinstance(val, expected_type):
            errors.append(f"{key}: expected {expected_type.__name__}, got {type(val).__name__}")
    return errors
