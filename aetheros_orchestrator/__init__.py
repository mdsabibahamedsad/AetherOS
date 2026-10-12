"""AetherOS Integration Layer — unified daemon, event bus, lifecycle, and orchestrator."""

from __future__ import annotations

import os, signal, time

from aetheros_orchestrator.orchestrator import AetherosOrchestrator


__all__ = ["AetherosOrchestrator", "create_daemon"]


def create_daemon(config_path: str | None = None) -> AetherosOrchestrator:
    from aetheros_orchestrator.config.loader import load_unified_config
    cfg = load_unified_config(config_path)
    return AetherosOrchestrator(cfg)
