"""Backward-compatibility shim for :mod:`agent.aetheros_rate_guard`.

The module was renamed from ``nous_rate_guard`` to ``aetheros_rate_guard`` as
part of the AetherOS rebranding. This shim re-exports the full public API so
existing imports keep working unchanged. New code should import from
``agent.aetheros_rate_guard`` instead.
"""
from agent.aetheros_rate_guard import (  # noqa: F401
    aetheros_rate_limit_remaining,
    clear_aetheros_rate_limit,
    format_remaining,
    is_genuine_aetheros_rate_limit,
    record_aetheros_rate_limit,
)
from agent.aetheros_rate_guard import (  # noqa: F401  (legacy aliases)
    clear_nous_rate_limit,
    is_genuine_nous_rate_limit,
    nous_rate_limit_remaining,
    record_nous_rate_limit,
)
