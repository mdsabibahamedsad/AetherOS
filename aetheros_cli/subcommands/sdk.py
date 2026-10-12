"""
``aetheros sdk`` subcommand parser — SDK management commands.
"""

from __future__ import annotations

from typing import Callable


def build_sdk_parser(subparsers, *, cmd_sdk: Callable) -> None:
    """Attach the sdk subcommand to subparsers."""
    parser = subparsers.add_parser(
        "sdk",
        help="Developer SDK — create, build, validate, package plugins",
        description="AetherOS Developer SDK tools for building extensions.",
    )
    sdk_subparsers = parser.add_subparsers(dest="sdk_action")

    # sdk init — scaffold a new plugin
    init_parser = sdk_subparsers.add_parser(
        "init", help="Scaffold a new plugin from a template"
    )
    init_parser.add_argument(
        "name", help="Plugin name"
    )
    init_parser.add_argument(
        "--type", "-t",
        default="tool",
        choices=[
            "tool", "agent", "workflow", "memory", "model",
            "voice", "notification", "enterprise",
        ],
        help="Plugin template type (default: tool)",
    )
    init_parser.add_argument(
        "--description", "-d", default="", help="Plugin description"
    )
    init_parser.add_argument(
        "--author", "-a", default="", help="Plugin author"
    )
    init_parser.add_argument(
        "--output", "-o", default="", help="Output directory (default: current dir)"
    )

    # sdk build — build and package a plugin
    build_parser = sdk_subparsers.add_parser(
        "build", help="Build and package a plugin into a .aep file"
    )
    build_parser.add_argument(
        "directory", nargs="?", default=".",
        help="Plugin directory to build (default: current dir)",
    )
    build_parser.add_argument(
        "--output", "-o", default="", help="Output path for the .aep file"
    )
    build_parser.add_argument(
        "--compress", "-c", type=int, default=9, choices=range(0, 10),
        help="Compression level 0-9 (default: 9)",
    )

    # sdk validate — validate a plugin manifest
    validate_parser = sdk_subparsers.add_parser(
        "validate", help="Validate a plugin manifest"
    )
    validate_parser.add_argument(
        "path", nargs="?", default=".",
        help="Plugin directory or manifest file to validate",
    )

    # sdk package — alias for build
    package_parser = sdk_subparsers.add_parser(
        "package", help="Package a plugin (alias for build)"
    )
    package_parser.add_argument(
        "directory", nargs="?", default=".",
    )
    package_parser.add_argument("--output", "-o", default="")

    # sdk sign — sign a package
    sign_parser = sdk_subparsers.add_parser(
        "sign", help="Sign a plugin package with a private key"
    )
    sign_parser.add_argument("package", help="Path to the .aep file")
    sign_parser.add_argument(
        "--key", "-k", required=True, help="Path to the private key file"
    )
    sign_parser.add_argument(
        "--key-id", required=True, help="Identifier for the signing key"
    )

    # sdk verify — verify a package signature
    verify_parser = sdk_subparsers.add_parser(
        "verify", help="Verify a plugin package signature"
    )
    verify_parser.add_argument("package", help="Path to the .aep file")
    verify_parser.add_argument(
        "--key", "-k", required=True, help="Path to the public key file"
    )

    # sdk templates — list available templates
    templates_parser = sdk_subparsers.add_parser(
        "templates", aliases=["list-templates"],
        help="List available plugin templates",
    )

    # sdk publish — publish to marketplace
    publish_parser = sdk_subparsers.add_parser(
        "publish", help="Publish a plugin to the marketplace"
    )
    publish_parser.add_argument(
        "package", help="Path to the .aep package file"
    )
    publish_parser.add_argument(
        "--registry", "-r", default="",
        help="Registry URL (default: public marketplace)",
    )
    publish_parser.add_argument(
        "--api-key", help="Registry API key",
    )

    parser.set_defaults(func=cmd_sdk)
