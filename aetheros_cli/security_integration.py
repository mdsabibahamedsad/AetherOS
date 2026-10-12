"""
Phase 13 Security OS — Integration Helper

This module provides the registration hook that main.py calls to attach
all new security subcommands.  Call once from main.py's parser setup::

    from aetheros_cli.security_integration import register_security_subcommands
    register_security_subcommands(subparsers)

That single call registers:

    aetheros permissions   — Granular permission management
    aetheros secrets       — Secrets Manager (distinct from ``aetheros secrets bitwarden``)
    aetheros audit         — Audit log viewer
    aetheros sandbox       — Sandbox management
    aetheros verify        — Integrity verification
    aetheros scan          — Security scanning

IMPORTANT: The existing ``aetheros security audit`` (OSV.dev supply-chain audit)
still lives under the original ``aetheros security`` subcommand.  The new commands
are *separate* top-level subcommands of ``aetheros``, keeping the CLI surface
discoverable and orthogonal.

For the web backend, call ``register_security_api_routes(app)`` from
``web_server.py`` after the FastAPI app is created.
"""

from __future__ import annotations

import argparse
import sys

from aetheros_cli.subcommands.permissions import build_permissions_parser
from aetheros_cli.subcommands.audit import build_audit_parser
from aetheros_cli.subcommands.sandbox import build_sandbox_parser
from aetheros_cli.subcommands.scan import build_scan_parser
from aetheros_cli.subcommands.verify import build_verify_parser
from aetheros_cli.subcommands.secrets import build_secrets_parser
from aetheros_cli.subcommands.capsule import build_capsule_parser
from aetheros_cli.security_cmds import (
    cmd_permissions,
    cmd_secrets,
    cmd_audit,
    cmd_sandbox,
    cmd_verify,
    cmd_scan,
    cmd_capsule,
)


def register_security_subcommands(subparsers: argparse.Action) -> None:
    """Attach all Phase 13 security subcommands to the top-level parser."""
    build_permissions_parser(subparsers, cmd_permissions=cmd_permissions)
    build_secrets_parser(subparsers, cmd_secrets=cmd_secrets)
    build_audit_parser(subparsers, cmd_audit=cmd_audit)
    build_sandbox_parser(subparsers, cmd_sandbox=cmd_sandbox)
    build_verify_parser(subparsers, cmd_verify=cmd_verify)
    build_scan_parser(subparsers, cmd_scan=cmd_scan)
    build_capsule_parser(subparsers, cmd_capsule=cmd_capsule)


def register_security_api_routes(app) -> None:
    """Attach web security API routes to a FastAPI application."""
    from aetheros_cli.web_security_api import register_routes
    register_routes(app)


# Convenience: list registered commands when run directly.
if __name__ == "__main__":
    print("Phase 13 Security OS — registered subparsers:")
    for name in ("permissions", "secrets", "audit", "sandbox", "verify", "scan", "capsule"):
        print(f"  aetheros {name}")
    print()
    print("Web API routes prefix: /api/security/*")
