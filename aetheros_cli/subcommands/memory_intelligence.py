"""``aetheros memory-intelligence`` subcommand parser.

Follows the same extracted-parser pattern as ``reliability.py`` and
``memory.py``: the handler is injected via ``cmd_memory_intelligence`` so
this module does not import ``main`` (cycle avoidance).
"""

from __future__ import annotations

from typing import Callable


def build_memory_intelligence_parser(subparsers, *, cmd_memory_intelligence: Callable) -> None:
    """Attach the ``memory-intelligence`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "memory-intelligence",
        help="Memory & Knowledge Intelligence Fabric: status, recall, audit, export/import",
        description=(
            "Inspect and control the AetherOS Memory & Knowledge Intelligence "
            "Fabric: store status, secure recall, integrity, audit chain, "
            "export/import, retention and backup."
        ),
    )
    sub = parser.add_subparsers(dest="memory_intelligence_command")

    sub.add_parser("status", help="Show fabric status (store, audit, cache, conflicts)")

    # memory-intelligence recall <query>
    recall = sub.add_parser("recall", help="Secure recall of memory for a query")
    recall.add_argument("query", help="Search query")
    recall.add_argument("--user", default="", help="Actor user id (default: empty scope)")
    recall.add_argument("--workspace", default="", help="Actor workspace id")
    recall.add_argument("--session", default="", help="Actor session id")
    recall.add_argument("--agent", default="", help="Actor agent id")
    recall.add_argument("--top-k", type=int, default=0, help="Override retrieval top_k")

    # memory-intelligence integrity
    sub.add_parser("integrity", help="Run an integrity scan (checksums + audit chain)")

    # memory-intelligence audit
    audit = sub.add_parser("audit", help="Inspect the fabric audit log")
    audit.add_argument("--operation", default="", help="Filter by operation (write/recall/forget/...)")
    audit.add_argument("--limit", type=int, default=50, help="Max entries to show")
    audit.add_argument("--verify", action="store_true", help="Verify the hash chain")

    # memory-intelligence export
    export = sub.add_parser("export", help="Export entries to a validated JSON bundle")
    export.add_argument("destination", help="Output JSON file path")
    export.add_argument("--include-archived", action="store_true", help="Include archived entries")

    # memory-intelligence import
    import_ = sub.add_parser("import", help="Import a validated JSON bundle (strict)")
    import_.add_argument("source", help="Input JSON bundle path")

    # memory-intelligence retention
    retention = sub.add_parser("retention", help="Run TTL/archive/purge retention policy")
    retention.add_argument("--user", default="", help="Actor user id")
    retention.add_argument("--workspace", default="", help="Actor workspace id")

    # memory-intelligence backup
    backup = sub.add_parser("backup", help="Create a fabric-only backup copy")
    backup.add_argument("destination", help="Destination directory")

    # memory-intelligence restore
    restore = sub.add_parser("restore", help="Restore a fabric backup (re-validated)")
    restore.add_argument("source", help="Backup directory")

    parser.set_defaults(func=cmd_memory_intelligence)