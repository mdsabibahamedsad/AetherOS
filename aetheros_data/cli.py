"""CLI for the canonical data layer (section 107).

Standalone usage (no god-file dependency)::

    python -m aetheros_data.cli storage status
    python -m aetheros_data.cli backup create --scope critical
    python -m aetheros_data.cli backup list
    python -m aetheros_data.cli backup verify <id>
    python -m aetheros_data.cli backup restore <id> --yes
    python -m aetheros_data.cli recovery status
    python -m aetheros_data.cli sync status
    python -m aetheros_data.cli data export --dest out.zip
    python -m aetheros_data.cli data import --path out.zip --authorize
    python -m aetheros_data.cli data integrity

Every command prints real backend state; nothing is faked.
"""

from __future__ import annotations

import argparse
import json
import sys


def _print(obj: object) -> None:
    print(json.dumps(obj, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    from aetheros_data import api

    p = argparse.ArgumentParser(prog="aetheros-data")
    sub = p.add_subparsers(dest="group", required=True)

    g = sub.add_parser("storage")
    g.add_argument("action", choices=["status", "check"])

    g = sub.add_parser("backup")
    g.add_argument("action", choices=["create", "list", "verify", "restore"])
    g.add_argument("backup_id", nargs="?")
    g.add_argument("--scope", default="critical")
    g.add_argument("--kind", default="FULL")
    g.add_argument("--yes", action="store_true")

    g = sub.add_parser("recovery")
    g.add_argument("action", choices=["status", "reconcile"])

    g = sub.add_parser("sync")
    g.add_argument("action", choices=["status", "pause", "resume"])

    g = sub.add_parser("data")
    g.add_argument("action", choices=["export", "import", "migrate", "integrity"])
    g.add_argument("--dest")
    g.add_argument("--path")
    g.add_argument("--authorize", action="store_true")

    args = p.parse_args(argv)
    try:
        if args.group == "storage":
            _print(api.storage_status())
        elif args.group == "backup":
            if args.action == "create":
                _print(api.backup_create(scope=args.scope, kind=args.kind))
            elif args.action == "list":
                _print(api.backup_list())
            elif args.action == "verify":
                if not args.backup_id:
                    print("backup_id required", file=sys.stderr)
                    return 2
                _print(api.backup_verify(args.backup_id))
            elif args.action == "restore":
                if not args.backup_id:
                    print("backup_id required", file=sys.stderr)
                    return 2
                _print(api.backup_restore(args.backup_id, assume_yes=args.yes))
        elif args.group == "recovery":
            _print(api.recovery_status())
        elif args.group == "sync":
            if args.action in ("status",):
                _print(api.sync_status())
            else:
                from aetheros_data.engine import get_engine
                from aetheros_data.sync import SyncEngine
                eng = SyncEngine(get_engine())
                eng.set_paused(args.action == "pause")
                _print({"ok": True, "paused": args.action == "pause"})
        elif args.group == "data":
            if args.action == "export":
                if not args.dest:
                    print("--dest required", file=sys.stderr)
                    return 2
                _print(api.data_export(args.dest))
            elif args.action == "import":
                if not args.path:
                    print("--path required", file=sys.stderr)
                    return 2
                _print(api.data_import(args.path, authorize=args.authorize))
            elif args.action in ("integrity", "migrate"):
                if args.action == "migrate":
                    from aetheros_data.engine import get_engine
                    e = get_engine()
                    _print({"ok": True, "schema_version": e.integrity_check()["schema_version"],
                            "note": "migrations apply automatically on engine init; legacy AETHEROS_HOME state is preserved, never deleted"})
                else:
                    _print(api.integrity_check())
    except PermissionError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
