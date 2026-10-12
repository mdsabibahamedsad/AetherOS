"""``aetheros dashboard register`` — stub (removed).

This command previously registered a self-hosted dashboard OAuth client with
the AetherOS portal. That flow has been removed from Aetheros.
"""

from __future__ import annotations

import sys


def cmd_dashboard_register(args) -> None:
    print(
        "✗ `aetheros dashboard register` is not available. "
        "AetherOS portal client registration is no longer supported."
    )
    sys.exit(1)
