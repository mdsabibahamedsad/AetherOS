"""
Agent Communication Fabric — configuration (master spec step 73).

The fabric is configured under the top-level ``communication:`` section of
``config.yaml``. Adding this section to :data:`DEFAULT_CONFIG` is additive —
the existing deep-merge handles it without a config-version bump, so no
migration is required and existing configs keep working (step 74).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover
    def get_aetheros_home() -> Path:  # type: ignore[misc]
        return Path.home() / ".aetheros"

#: Defaults for the ``communication:`` config section.
DEFAULT_COMMUNICATION_CONFIG: Dict[str, Any] = {
    # Protocol versions this build speaks (step 5).
    "protocol_versions": ["1.0"],
    # Message size / nesting limits (step 26).
    "message_limits": {
        "max_message_bytes": 256 * 1024,
        "max_payload_bytes": 192 * 1024,
        "max_metadata_bytes": 32 * 1024,
        "max_field_length": 512,
        "max_depth": 32,
        "max_capabilities": 256,
    },
    # Request/response timeouts (steps 29, 33).
    "timeouts": {
        "request_default_seconds": 30.0,
        "heartbeat_stale_seconds": 60.0,
    },
    # Authentication / signing (steps 14, 15).
    "authentication": {
        # Require a valid HMAC signature on sensitive message types.
        "require_signature": True,
        # Where the fabric signing key lives (defaults to
        # <AETHEROS_HOME>/comms/signing.key).
        "signing_key_path": "",
    },
    # Rate limits (step 27).
    "rate_limits": {
        "messages_per_second": 100,
        "burst_limit": 100,
        "requests_per_agent": 500,       # per minute
        "requests_per_mission": 5000,    # per mission
        "delegation_requests_per_agent": 50,  # per minute
        "broadcasts_per_agent_per_hour": 60,
    },
    # Trust zones (step 12).
    "trust_zones": {
        "default_zone": "ZONE_1",
        # Explicit cross-zone allowances: "ZONE_1->ZONE_3": ["capability", ...]
        # (empty capability list = unconditional for the pair).
        "cross_zone_allowances": {},
    },
    # Retry policy (step 34).
    "retry": {
        "max_attempts": 3,
        "base_delay_seconds": 0.2,
        "max_delay_seconds": 5.0,
    },
    # Circuit breaker (step 35).
    "circuit_breaker": {
        "failure_threshold": 5,
        "open_timeout_seconds": 10.0,
    },
    # Backpressure (step 36).
    "backpressure": {
        "max_in_flight": 32,
        "queue_limit": 512,
    },
    # Fallback chains (step 38).
    "fallback": {
        "enabled": True,
    },
    # Audit (step 58).
    "audit": {
        "enabled": True,
    },
    # Broadcast control (step 28): agent ids allowed to broadcast.
    "broadcast": {
        "allowed_agents": ["orchestrator", "coordinator", "security"],
    },
    # Replay protection retention (step 16).
    "replay": {
        "retention_seconds": 3600.0,
    },
    # Idempotency retention (step 32).
    "idempotency": {
        "ttl_seconds": 86400.0,
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursive merge; ``override`` values win over ``base``."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_communication_config(
        config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and merge the ``communication:`` section from ``config.yaml``.

    Reads the raw YAML (like the gateway does) and deep-merges over the
    defaults, so unset keys keep their defaults and unknown keys are
    preserved. Existing config files without a ``communication:`` section
    produce the defaults unchanged (backward compatible).
    """
    import yaml

    config_path = config_path or (get_aetheros_home() / "config.yaml")
    user_section: Dict[str, Any] = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            comm = raw.get("communication")
            if isinstance(comm, dict):
                user_section = comm
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Could not load communication config from %s: %s",
                config_path, exc)
    return _deep_merge(DEFAULT_COMMUNICATION_CONFIG, user_section)


#: Cache of the loaded communication config (mtime-keyed by the loader).
_COMM_CACHE: Dict[str, Any] = {}


def get_communication_config() -> Dict[str, Any]:
    """Return the effective communication config (cached)."""
    key = os.environ.get("AETHEROS_HOME", "default")
    if key not in _COMM_CACHE:
        _COMM_CACHE[key] = load_communication_config()
    return _COMM_CACHE[key]


def reset_communication_config() -> None:
    _COMM_CACHE.clear()