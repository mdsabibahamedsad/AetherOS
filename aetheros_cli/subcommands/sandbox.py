"""``aetheros sandbox`` subcommand parser.

Manage isolated sandboxes for running plugins, MCP servers, agents, and tasks.
Integrates with aetheros_security.sandbox SandboxManager.
"""

from __future__ import annotations

from typing import Callable


def build_sandbox_parser(subparsers, *, cmd_sandbox: Callable) -> None:
    """Attach the ``sandbox`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "sandbox",
        help="Manage isolated execution sandboxes",
        description=(
            "Create, manage, and inspect isolated sandboxes. Supports Firejail "
            "(Linux), Windows Sandbox, macOS App Sandbox, Docker/Podman containers, "
            "and restricted Python execution environments."
        ),
    )
    sub = parser.add_subparsers(
        dest="sandbox_command",
        metavar="<subcommand>",
    )

    # list
    list_p = sub.add_parser(
        "list",
        aliases=["ls"],
        help="List sandboxes",
        description="Show all sandboxes with their status, backend, and isolation mode.",
    )
    list_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # create
    create_p = sub.add_parser(
        "create",
        help="Create a new sandbox",
        description="Create a new sandbox with the specified configuration.",
    )
    create_p.add_argument("name", help="Sandbox name")
    create_p.add_argument(
        "--backend",
        choices=["firejail", "docker", "podman", "windows_sandbox", "macos_sandbox", "restricted_python", "none"],
        default="restricted_python",
        help="Sandbox backend (default: restricted_python)",
    )
    create_p.add_argument(
        "--mode",
        choices=["full", "standard", "relaxed", "none"],
        default="standard",
        help="Isolation level (default: standard)",
    )
    create_p.add_argument(
        "--max-memory",
        type=int,
        default=512,
        help="Maximum memory in MB (default: 512)",
    )
    create_p.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum execution time in seconds (default: 300)",
    )
    create_p.add_argument(
        "--network",
        action="store_true",
        help="Allow network access",
    )

    # destroy
    destroy_p = sub.add_parser(
        "destroy",
        help="Destroy a sandbox",
        description="Destroy an existing sandbox and clean up its resources.",
    )
    destroy_p.add_argument("name", help="Sandbox name to destroy")

    # execute / exec
    exec_p = sub.add_parser(
        "execute",
        aliases=["exec"],
        help="Execute a command in a sandbox",
        description="Run a command inside an existing sandbox with resource limits.",
    )
    exec_p.add_argument("name", help="Sandbox name")
    exec_p.add_argument("command", help="Command to execute")
    exec_p.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Execution timeout in seconds",
    )

    # config
    config_p = sub.add_parser(
        "config",
        help="Show sandbox configuration",
        description="Display the configuration of a specific sandbox.",
    )
    config_p.add_argument("name", help="Sandbox name")

    # backend
    backend_p = sub.add_parser(
        "backend",
        help="Show active sandbox backend",
        description="Display which sandbox backend is currently detected and active.",
    )
    backend_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # stats
    stats_p = sub.add_parser(
        "stats",
        help="Show sandbox statistics",
        description="Display sandbox usage statistics.",
    )
    stats_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    parser.set_defaults(func=cmd_sandbox)
