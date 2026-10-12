"""Backward-compatibility shim for :mod:`agent.aetheros_portal_tags`.

The module was renamed from ``portal_tags`` to ``aetheros_portal_tags`` as
part of the AetherOS rebranding. This shim re-exports the full public API so
existing imports keep working unchanged. New code should import from
``agent.aetheros_portal_tags`` instead.
"""
from agent.aetheros_portal_tags import (  # noqa: F401
    aetheros_client_tag,
    aetheros_portal_tags,
)
from agent.aetheros_portal_tags import nous_portal_tags  # noqa: F401  (legacy alias)
