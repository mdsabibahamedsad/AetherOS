"""
Centralized deprecation framework for the Legacy (Hermes) → Aetheros migration.

Provides warn-once semantics, structured messages with version targets for
removal, and easy bulk cleanup when the migration window closes.

Usage::

    from agent.deprecation import deprecate_env_var

    # Inside any env-var read site:
    val = deprecate_env_var(
        preferred="AETHEROS_GATEWAY_SESSION",
        legacy="HERMES_GATEWAY_SESSION",
        default="",
        remove_at="1.0.0",
    )

Design
------
- Every deprecation warning fires at most once per (library, process) pair,
  keyed on the *legacy* name so the same legacy env var referenced from
  multiple call sites still produces one message.
- ``remove_at`` is a semver target so future cleanup sweeps can grep for
  ``remove_at=\"<current_version>\"`` and bulk-remove the flagged sites.
- The caller resolves the value (preferred wins); the helper handles the
  warning.
"""

from __future__ import annotations

import logging
import os
import warnings
from typing import Optional

logger = logging.getLogger(__name__)

# Internal registry of already-warned items so each (library, legacy_name)
# pair fires exactly once per process.
_warned: set[tuple[str, str]] = set()


def deprecate_env_var(
    preferred: str,
    legacy: str,
    default: str = "",
    *,
    remove_at: str = "1.0.0",
) -> str:
    """Resolve an env-var pair, preferring ``preferred`` over ``legacy``.

    Returns the value of ``preferred`` if set, otherwise the value of
    ``legacy``, otherwise ``default``.  Emits a one-shot deprecation
    warning on first fallback to the legacy name.

    Parameters
    ----------
    preferred:
        New canonical env-var name (e.g. ``AETHEROS_GATEWAY_SESSION``).
    legacy:
        Legacy env-var name (e.g. ``HERMES_GATEWAY_SESSION``).
    default:
        Fallback value when neither env var is set.
    remove_at:
        Semver version at which the legacy variable will be removed
        (``None`` = no removal planned).
    """
    preferred_val = os.environ.get(preferred)
    if preferred_val is not None:
        return preferred_val

    legacy_val = os.environ.get(legacy)
    if legacy_val is not None:
        _warn_once("env_var", legacy, preferred, remove_at)
        return legacy_val

    return default


def deprecate_env_flag(
    preferred: str,
    legacy: str,
    *,
    remove_at: str = "1.0.0",
) -> bool:
    """Resolve a boolean env-var pair, preferring ``preferred`` over ``legacy``.

    Truthy values: ``1``, ``true``, ``yes`` (case-insensitive).
    Returns ``False`` when neither is set.
    """
    val = deprecate_env_var(preferred, legacy, default="", remove_at=remove_at)
    return val.strip().lower() in ("1", "true", "yes", "on")


def _warn_once(
    kind: str,
    legacy_name: str,
    preferred_name: str,
    remove_at: str,
) -> None:
    """Emit a structured deprecation warning, at most once per process."""
    key = (kind, legacy_name)
    if key in _warned:
        return
    _warned.add(key)

    msg = (
        f"DeprecationWarning: `{legacy_name}` ({kind}) is deprecated. "
        f"Use `{preferred_name}` instead."
    )
    if remove_at:
        msg += f" Support for `{legacy_name}` will be removed in v{remove_at}."

    warnings.warn(msg, DeprecationWarning, stacklevel=3)
    logger.debug(msg)


def reset_warnings() -> None:
    """Clear the warn-once registry (useful in tests)."""
    _warned.clear()


def get_env_var_preferred(
    *,
    aetheros_name: str,
    legacy_name: str,
    default: str = "",
    remove_at: str = "1.0.0",
) -> str:
    """Convenience: resolve an env var preferring AETHEROS_* over HERMES_*.

    This is the short-hand for the common migration pattern where the
    preferred name is ``AETHEROS_*`` and the legacy name is ``HERMES_*``.
    """
    return deprecate_env_var(
        preferred=aetheros_name,
        legacy=legacy_name,
        default=default,
        remove_at=remove_at,
    )


def get_env_flag_preferred(
    *,
    aetheros_name: str,
    legacy_name: str,
    remove_at: str = "1.0.0",
) -> bool:
    """Convenience: resolve a boolean env var preferring AETHEROS_* over HERMES_*."""
    return deprecate_env_flag(
        preferred=aetheros_name,
        legacy=legacy_name,
        remove_at=remove_at,
    )
