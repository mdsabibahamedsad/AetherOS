"""Backward-compatibility shim for :mod:`aetheros_cli.proxy.adapters.aetheros_portal`.

The adapter module was renamed from ``nous_portal`` to ``aetheros_portal`` as
part of the AetherOS rebranding. This shim re-exports the adapter class so
existing imports keep working unchanged. New code should import from
``aetheros_cli.proxy.adapters.aetheros_portal`` instead.
"""
from aetheros_cli.proxy.adapters.aetheros_portal import (  # noqa: F401
    AetherOSPortalAdapter,
    NousPortalAdapter,
)

__all__ = ["AetherOSPortalAdapter", "NousPortalAdapter"]
