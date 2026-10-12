"""``aetheros scan`` subcommand parser.

Run security scans on code, plugins, secrets, and dependencies.
Integrates with aetheros_security AI security, DLP, and threat detection.
"""

from __future__ import annotations

from typing import Callable


def build_scan_parser(subparsers, *, cmd_scan: Callable) -> None:
    """Attach the ``scan`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "scan",
        help="Run security scans on code, plugins, files, and dependencies",
        description=(
            "Comprehensive security scanning. Detects prompt injection, sensitive "
            "data leaks, malware patterns, dependency vulnerabilities, and "
            "configuration issues before execution."
        ),
    )
    sub = parser.add_subparsers(
        dest="scan_command",
        metavar="<subcommand>",
    )

    # code
    code_p = sub.add_parser(
        "code",
        help="Scan code for security issues",
        description="Analyze source code for vulnerabilities, injection patterns, and unsafe constructs.",
    )
    code_p.add_argument("path", help="Path to file or directory to scan")
    code_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    code_p.add_argument(
        "--risk-threshold",
        type=float,
        default=0.5,
        help="Risk score threshold for warnings (0.0-1.0, default: 0.5)",
    )

    # plugin
    plugin_p = sub.add_parser(
        "plugin",
        help="Scan a plugin for security issues",
        description="Scan a plugin for malware, suspicious patterns, and permission overreach.",
    )
    plugin_p.add_argument("name", help="Plugin name to scan")
    plugin_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # file
    file_p = sub.add_parser(
        "file",
        help="Scan a file for sensitive data",
        description="Scan a file for exposed secrets, API keys, passwords, and PII.",
    )
    file_p.add_argument("path", help="Path to file to scan")
    file_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # prompt
    prompt_p = sub.add_parser(
        "prompt",
        help="Scan a prompt for injection attempts",
        description="Analyze user input for prompt injection patterns and unsafe instructions.",
    )
    prompt_p.add_argument("text", help="Prompt text to scan")
    prompt_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # dependency / deps
    dep_p = sub.add_parser(
        "dependency",
        aliases=["deps"],
        help="Scan dependencies for vulnerabilities",
        description="Scan installed dependencies for known vulnerabilities via OSV.dev.",
    )
    dep_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    # all
    all_p = sub.add_parser(
        "all",
        help="Run all security scans",
        description="Run a comprehensive scan covering code, plugins, files, and dependencies.",
    )
    all_p.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    parser.set_defaults(func=cmd_scan)
