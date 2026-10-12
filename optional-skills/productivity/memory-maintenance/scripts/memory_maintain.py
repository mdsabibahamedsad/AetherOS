#!/usr/bin/env python3
"""Scheduled memory-maintenance wrapper for ``aetherres cron --no-agent``.

Runs the same lifecycle pass as ``aetherres memory maintain`` and prints a
report **only** when the pass actually changed something.  Empty stdout means
"clean tick" — the contract ``--no-agent`` cron jobs use to stay silent, so a
weekly job only messages the user when decay, dedup, redaction, or repair did
real work.

Usage:
    python memory_maintain.py [--dry-run] [--no-decay] [--no-purge]
        [--no-repair] [--halflife-days N]

Copy this file into ``$AETHEROS_HOME/scripts/`` and schedule it:

    aetherres cron create "every 1w" --no-agent \\
        --script memory_maintain.py --deliver telegram

Exit codes: 0 on success (silent or not), 2 on a hard failure (so the cron
scheduler's error path fires instead of silently dropping the run).
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict


def _count(section: Dict[str, Any], key: str) -> int:
    return int(section.get(key, 0) or 0)


def run_maintenance(
    store: Any,
    *,
    decay: bool = True,
    purge: bool = True,
    repair: bool = True,
    halflife_days: float = 90.0,
    dry_run: bool = False,
) -> str:
    """Run the lifecycle pass and return a report string ("" when no change)."""
    from tools.memory_lifecycle import lifecycle_stats, maintain

    before = lifecycle_stats(store)
    report = maintain(
        store,
        decay=decay,
        purge=purge,
        repair=repair,
        halflife_days=halflife_days,
        dry_run=dry_run,
    )
    after = lifecycle_stats(store) if not dry_run else before

    repair_r = report.get("repair", {})
    secrets_r = report.get("secrets", {})
    recon_r = report.get("reconsolidate", {})
    decay_r = report.get("decay", {})
    conflict_r = report.get("conflicts", {})

    changed = {
        "rewritten": _count(repair_r, "rewritten"),
        "backed_up": _count(repair_r, "backed_up"),
        "redacted": _count(secrets_r, "redacted"),
        "merged": _count(recon_r, "merged"),
        "archived_over_budget": _count(recon_r, "archived"),
        "decayed": _count(decay_r, "decayed"),
        "expired": _count(decay_r, "archived"),
        "conflicts_resolved": _count(conflict_r, "resolved"),
    }
    delta = int(after.get("total", 0)) - int(before.get("total", 0))

    if not any(changed.values()) and delta == 0:
        return ""

    lines = []
    prefix = "dry-run" if dry_run else "memory-maintenance"
    lines.append(f"[{prefix}] {before.get('total', 0)} -> {after.get('total', 0)} entries ({delta:+d})")
    for key, label in (
        ("rewritten", "files repaired"),
        ("backed_up", "files backed up"),
        ("redacted", "secrets redacted"),
        ("merged", "duplicates merged"),
        ("archived_over_budget", "archived over budget"),
        ("decayed", "entries decayed"),
        ("expired", "entries expired"),
        ("conflicts_resolved", "conflicts resolved"),
    ):
        if changed[key]:
            lines.append(f"  - {label}: {changed[key]}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report without mutating.")
    parser.add_argument("--no-decay", action="store_true", help="Skip the decay pass.")
    parser.add_argument("--no-purge", action="store_true", help="Skip secret redaction.")
    parser.add_argument("--no-repair", action="store_true", help="Skip file repair.")
    parser.add_argument("--halflife-days", type=float, default=90.0, help="Decay half-life in days.")
    args = parser.parse_args(argv)

    try:
        from tools.memory_tool import MemoryStore
    except Exception as exc:
        print(f"memory_maintain.py: cannot import tools.memory_tool: {exc}", file=sys.stderr)
        return 2

    store = MemoryStore()
    try:
        store.load_from_disk()
        out = run_maintenance(
            store,
            decay=not args.no_decay,
            purge=not args.no_purge,
            repair=not args.no_repair,
            halflife_days=args.halflife_days,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"memory_maintain.py: maintenance failed: {exc}", file=sys.stderr)
        return 2

    if out:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
