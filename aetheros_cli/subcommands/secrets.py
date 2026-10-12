"""``aetheros secrets`` subcommand parser.

Manage secrets through the AetherOS Secrets Manager.
Integrates with aetheros_security.secrets SecretsManager.
"""

from __future__ import annotations

from typing import Callable


def build_secrets_parser(subparsers, *, cmd_secrets: Callable) -> None:
    """Attach the ``secrets`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "secrets",
        help="Manage secrets securely via the Secrets Manager",
        description=(
            "Securely store and manage API keys, OAuth tokens, SSH keys, "
            "passwords, and other sensitive data. Uses OS Keychain, Windows "
            "Credential Manager, macOS Keychain, GNOME Keyring, or encrypted local vault."
        ),
    )
    sub = parser.add_subparsers(
        dest="secrets_command",
        metavar="<subcommand>",
    )

    # store
    store_p = sub.add_parser(
        "store",
        help="Store a secret",
        description="Securely store a new secret value.",
    )
    store_p.add_argument("name", help="Secret name/identifier")
    store_p.add_argument("value", help="Secret value to store")
    store_p.add_argument(
        "--category",
        choices=["api_key", "oauth_token", "ssh_key", "jwt_token", "cookie", "certificate", "password", "generic"],
        default="generic",
        help="Secret category (default: generic)",
    )
    store_p.add_argument(
        "--description",
        default="",
        help="Human-readable description",
    )
    store_p.add_argument(
        "--expires-in",
        type=int,
        default=0,
        help="Expiry time in seconds (0 = no expiry)",
    )

    # retrieve
    retrieve_p = sub.add_parser(
        "retrieve",
        help="Retrieve a secret value",
        description="Retrieve a stored secret by name.",
    )
    retrieve_p.add_argument("name", help="Secret name to retrieve")
    retrieve_p.add_argument(
        "--no-expiry-check",
        action="store_true",
        help="Skip expiry check",
    )

    # list / ls
    list_p = sub.add_parser(
        "list",
        aliases=["ls"],
        help="List all secrets",
        description="List stored secrets with metadata (values are never shown).",
    )
    list_p.add_argument(
        "--category",
        choices=["api_key", "oauth_token", "ssh_key", "jwt_token", "cookie", "certificate", "password", "generic"],
        default=None,
        help="Filter by category",
    )
    list_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # delete
    delete_p = sub.add_parser(
        "delete",
        help="Delete a secret",
        description="Permanently delete a stored secret.",
    )
    delete_p.add_argument("name", help="Secret name to delete")

    # rotate
    rotate_p = sub.add_parser(
        "rotate",
        help="Rotate (update) a secret",
        description="Update an existing secret with a new value.",
    )
    rotate_p.add_argument("name", help="Secret name to rotate")
    rotate_p.add_argument("new_value", help="New secret value")

    # info
    info_p = sub.add_parser(
        "info",
        help="Show secret metadata",
        description="Show metadata for a secret (without revealing the value).",
    )
    info_p.add_argument("name", help="Secret name")

    # cleanup
    cleanup_p = sub.add_parser(
        "cleanup",
        help="Remove expired secrets",
        description="Remove all secrets that have passed their expiry time.",
    )

    # stats
    stats_p = sub.add_parser(
        "stats",
        help="Show secrets statistics",
        description="Display secrets storage statistics.",
    )
    stats_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # backend
    backend_p = sub.add_parser(
        "backend",
        help="Show active storage backend",
        description="Display which secret storage backend is currently active.",
    )
    backend_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    parser.set_defaults(func=cmd_secrets)
