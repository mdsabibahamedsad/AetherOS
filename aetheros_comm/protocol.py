"""
Agent Communication Fabric — protocol versioning (master spec step 5).

Every message carries a ``protocolVersion``. Version negotiation selects the
highest mutually-supported version; incompatible schemas are never silently
interpreted.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

#: The protocol version this build speaks. Bump on breaking wire-format
#: changes (new required fields, changed semantics).
PROTOCOL_VERSION = "1.0"

#: Versions this build understands (oldest -> newest).
SUPPORTED_PROTOCOL_VERSIONS: Tuple[str, ...] = ("1.0",)


class ProtocolError(Exception):
    """Raised when protocol versions cannot be negotiated."""


def negotiate_protocol(
    ours: Iterable[str],
    theirs: Iterable[str],
) -> str:
    """Select the highest protocol version both sides support.

    Example (master spec step 5):

        A supports {"1.0", "1.1"}, B supports {"1.1", "1.2"} -> "1.1"

    Raises :class:`ProtocolError` when there is no common version, so the
    caller never falls back to guessing an incompatible schema.
    """
    ours_set = set(ours)
    theirs_set = set(theirs)
    common = ours_set & theirs_set
    if not common:
        raise ProtocolError(
            "no common protocol version between "
            f"{sorted(ours_set)} and {sorted(theirs_set)}"
        )
    # Highest common version wins.
    return max(common)


def is_supported(version: str) -> bool:
    """Whether ``version`` is supported by this build."""
    return version in SUPPORTED_PROTOCOL_VERSIONS


def supported_versions() -> List[str]:
    """Return the list of supported versions (for agent cards / HELLO)."""
    return list(SUPPORTED_PROTOCOL_VERSIONS)