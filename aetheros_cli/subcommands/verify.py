"""``aetheros verify`` subcommand parser.

Verify the integrity and security of plugins, code, dependencies, and configurations.
Integrates with aetheros_security for signature verification and security scanning.
"""

from __future__ import annotations

from typing import Callable


def build_verify_parser(subparsers, *, cmd_verify: Callable) -> None:
    """Attach the ``verify`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "verify",
        help="Verify integrity and security of plugins, code, and dependencies",
        description=(
            "Verify digital signatures, check hash integrity, validate plugin "
            "publishers, and audit dependencies for known vulnerabilities."
        ),
    )
    sub = parser.add_subparsers(
        dest="verify_command",
        metavar="<subcommand>",
    )

    # plugin
    plugin_p = sub.add_parser(
        "plugin",
        help="Verify a plugin's integrity",
        description="Check a plugin's digital signature, hash, and publisher verification.",
    )
    plugin_p.add_argument("name", help="Plugin name to verify")
    plugin_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # checksum / hash
    hash_p = sub.add_parser(
        "checksum",
        aliases=["hash"],
        help="Verify file checksum",
        description="Compute and verify a file's SHA-256 checksum.",
    )
    hash_p.add_argument("path", help="Path to file")
    hash_p.add_argument(
        "--expected",
        default=None,
        help="Expected hash value to compare against",
    )

    # dependency / deps
    dep_p = sub.add_parser(
        "dependency",
        aliases=["deps"],
        help="Verify a dependency's integrity",
        description="Check a dependency package for known vulnerabilities and integrity.",
    )
    dep_p.add_argument("name", help="Dependency package name")
    dep_p.add_argument(
        "--version",
        default=None,
        help="Package version to verify",
    )
    dep_p.add_argument(
        "--ecosystem",
        default="pypi",
        choices=["pypi", "npm"],
        help="Package ecosystem (default: pypi)",
    )

    # config
    cfg_p = sub.add_parser(
        "config",
        help="Verify configuration security",
        description="Check configuration for security issues like exposed secrets or unsafe settings.",
    )

    # sbom
    sbom_p = sub.add_parser(
        "sbom",
        help="Generate and verify SBOM",
        description="Generate or verify a Software Bill of Materials.",
    )
    sbom_p.add_argument(
        "--output",
        default=None,
        help="Output file path for SBOM",
    )
    sbom_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    parser.set_defaults(func=cmd_verify)
