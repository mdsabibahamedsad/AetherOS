"""``aetheros reliability`` CLI handler.

Read-only commands (status, health, watchdog status, journal, backup list/
verify, diagnostics, sla, spof, lkg) are safe and never mutate state.
Mutating commands (watchdog start/stop/reset, backup create/prune, restore,
safe-mode/recovery-mode enter/exit, lkg --update) operate on the reliability
layer and — for restore — require an explicit confirmation prompt unless
``--yes`` is given.  Restore is destructive and is deliberately NEVER part of
autonomous self-healing.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from aetheros_constants import display_aetheros_home


def _fmt_ts(ts: Any) -> str:
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return "—"


def _fmt_age(ts: Any) -> str:
    try:
        age = int(__import__("time").time() - float(ts))
    except (TypeError, ValueError):
        return "—"
    if age < 60:
        return f"{age}s"
    if age < 3600:
        return f"{age // 60}m"
    if age < 86400:
        return f"{age // 3600}h"
    return f"{age // 86400}d"


def _ok(msg: str) -> None:
    print(f"✓ {msg}")


def _warn(msg: str) -> None:
    print(f"⚠ {msg}")


def _err(msg: str) -> None:
    print(f"✗ {msg}")


def reliability_command(args) -> int:
    """Dispatch ``aetheros reliability <subcommand>``."""
    sub = getattr(args, "reliability_command", None)
    handlers = {
        None: _cmd_status,
        "": _cmd_status,
        "status": _cmd_status,
        "health": _cmd_health,
        "watchdog": _cmd_watchdog,
        "journal": _cmd_journal,
        "backup": _cmd_backup,
        "restore": _cmd_restore,
        "safe-mode": _cmd_safe_mode,
        "recovery-mode": _cmd_recovery_mode,
        "diagnostics": _cmd_diagnostics,
        "sla": _cmd_sla,
        "spof": _cmd_spof,
        "lkg": _cmd_lkg,
    }
    handler = handlers.get(sub)
    if handler is None:
        print(f"unknown reliability subcommand: {sub}", file=__import__("sys").stderr)
        return 2
    return handler(args)


# ---------------------------------------------------------------------------
# Read-only commands
# ---------------------------------------------------------------------------


def _svc():
    from aetheros_reliability.service import get_reliability_service

    return get_reliability_service()


def _cmd_status(args) -> int:
    s = _svc().status()
    print("Reliability status")
    print("  Home:            %s" % display_aetheros_home())
    print("  Mode:            %s" % s["mode"])
    print("  Recovery state:  %s" % s["recovery_state"])
    print("  Watchdog:        %s" % ("running" if s["watchdog_running"] else "stopped"))
    print("  Backups:         %d" % s["backups"]["count"])
    print("  LKG config:      %s" % ("present" if s["last_known_good"]["exists"] else "absent"))
    if s["degraded_components"]:
        print("  Degraded:        %s" % ", ".join(s["degraded_components"]))
    crash = s["watchdog"].get("crash_loops") or []
    if crash:
        _warn("Crash loops: %s" % ", ".join(crash))
    return 0


def _cmd_health(args) -> int:
    h = _svc().health()
    print("Health: %s" % ("OK" if h["ok"] else "ISSUES DETECTED"))
    print("  Mode:            %s" % h["mode"])
    print("  Recovery state:  %s" % h["recovery_state"])
    for comp, status in h.get("components", {}).items():
        print("  %-16s %s" % (comp, status))
    if not h["ok"]:
        return 1
    return 0


def _cmd_watchdog(args) -> int:
    from aetheros_reliability.watchdog import get_watchdog

    action = getattr(args, "watchdog_action", None) or "status"
    wd = get_watchdog()
    if action == "start":
        if wd.start():
            _ok("Watchdog started")
        else:
            _err("Watchdog failed to start")
            return 1
        return 0
    if action == "stop":
        wd.stop()
        _ok("Watchdog stopped")
        return 0
    if action == "reset":
        wd.reset_component(args.component)
        _ok("Reset watchdog state for %s" % args.component)
        return 0
    status = wd.status()
    print("Watchdog: %s" % ("running" if status["running"] else "stopped"))
    print("  Interval:        %.0fs" % status["interval"])
    print("  Ticks:           %d" % status["ticks"])
    for cid, mon in status["monitored"].items():
        print("  %-16s restarts=%d crash_loop=%s last=%s" % (
            cid, mon["restart_count"], mon["crash_looping"],
            mon["last_failure"] or "—",
        ))
    return 0


def _cmd_journal(args) -> int:
    from aetheros_reliability.journal import get_recovery_journal

    journal = get_recovery_journal()
    if getattr(args, "pending", False):
        ops = journal.pending(limit=getattr(args, "recent", 20))
    else:
        ops = journal.recent(limit=getattr(args, "recent", 20))
    if not ops:
        print("Recovery journal: no operations")
        return 0
    print("Recovery journal (%d shown)" % len(ops))
    for op in ops:
        print("  [%s] %s/%s  %s" % (
            op.get("status", "?"),
            op.get("component", "?"),
            op.get("operation", "?"),
            _fmt_ts(op.get("started_at")),
        ))
    return 0


def _cmd_backup(args) -> int:
    from aetheros_reliability.backup import get_backup_store

    store = get_backup_store()
    if getattr(args, "list", False):
        entries = store.list()
        if not entries:
            print("No reliability backups yet.")
            return 0
        print("Backups (%d)" % len(entries))
        for e in entries:
            marker = "" if e.valid else "  [INVALID]"
            print("  %-24s files=%d  %s%s" % (
                e.backup_id, e.file_count, _fmt_age(e.created_at), marker,
            ))
        return 0
    if getattr(args, "verify", None):
        bid = _resolve_backup_id(args.verify)
        ok, report = store.verify(bid)
        if ok:
            _ok("Backup %s verified (%d files)" % (bid, report.get("file_count", 0)))
            return 0
        _err("Backup %s FAILED verification: %s" % (
            bid, report.get("reason", "unknown"),
        ))
        return 1
    if getattr(args, "prune", None):
        removed = store.prune(keep=args.prune)
        _ok("Pruned %d backups (keeping newest %d)" % (len(removed), args.prune))
        return 0
    entry = store.create(label=getattr(args, "label", "") or "")
    if entry is None:
        _err("Backup failed — see logs for details")
        return 1
    _ok("Created backup %s (%d files)" % (entry.backup_id, entry.file_count))
    return 0


def _cmd_restore(args) -> int:
    from aetheros_reliability.restore import get_recovery_manager

    manager = get_recovery_manager()
    try:
        backup_id = _resolve_backup_id(args.backup_id)
        preview = manager.preview(backup_id, scope=args.scope)
    except ValueError as exc:
        _err("Restore not possible: %s" % exc)
        return 1
    print("Restore preview")
    print("  Backup:          %s" % preview.backup_id)
    print("  Created:         %s" % _fmt_ts(preview.created_at))
    print("  Version:         %s (schema %d)" % (preview.app_version, preview.schema_version))
    print("  Scope:           %s" % preview.scope)
    print("  Files in backup: %d" % preview.files_in_backup)
    print("  Files to restore:%d" % preview.files_to_restore)
    if preview.will_overwrite:
        print("  Will overwrite:  %d file(s)" % len(preview.will_overwrite))
        for rel in preview.will_overwrite[:10]:
            print("    - %s" % rel)
    if preview.may_be_lost:
        _warn("Files that may be lost (not in this scope): %d" % len(preview.may_be_lost))
    if getattr(args, "dry_run", False):
        _ok("Dry run — nothing restored.")
        return 0
    if not getattr(args, "yes", False):
        answer = input("Type 'restore' to confirm restore of %s: " % preview.backup_id).strip()
        if answer.lower() != "restore":
            _err("Restore cancelled.")
            return 1
    result = manager.restore(preview.backup_id, scope=args.scope, snapshot=True)
    if result.get("restored"):
        _ok("Restored %d file(s); verification passed." % result.get("file_count", 0))
        return 0
    _err("Restore failed: %s" % result.get("error", "unknown"))
    return 1


def _cmd_diagnostics(args) -> int:
    from aetheros_reliability.diagnostics import get_reliability_diagnostics

    bundle = get_reliability_diagnostics().bundle()
    if getattr(args, "output", ""):
        if get_reliability_diagnostics().export(bundle, args.output):
            _ok("Diagnostics bundle written to %s" % args.output)
        else:
            _err("Failed to write diagnostics bundle")
            return 1
        return 0
    print(json.dumps(bundle, indent=2, default=str))
    return 0


def _cmd_sla(args) -> int:
    from aetheros_reliability.slas import get_recovery_sla_metrics

    sla = get_recovery_sla_metrics().summary()
    print("Recovery SLA metrics")
    print("  MTTR:                  %s" % (
        f"{sla['mttr_ms']:.0f} ms" if sla["mttr_ms"] is not None else "—",
    ))
    print("  Recovery success rate: %s" % (
        f"{sla['recovery_success_rate']:.1%}" if sla["recovery_success_rate"] is not None else "—",
    ))
    print("  Recovery attempts:     %d" % sla["recovery_attempts"])
    print("  Backup success rate:   %s" % (
        f"{sla['backup_success_rate']:.1%}" if sla["backup_success_rate"] is not None else "—",
    ))
    print("  Restore success rate:  %s" % (
        f"{sla['restore_success_rate']:.1%}" if sla["restore_success_rate"] is not None else "—",
    ))
    print("  Crash-loop rate:       %s" % (
        f"{sla['crash_loop_rate']:.1%}" if sla["crash_loop_rate"] is not None else "—",
    ))
    return 0


def _cmd_spof(args) -> int:
    report = _spof_report()
    print("Reliability SPOF audit")
    for item in report["items"]:
        print("  %s %-46s %s" % (
            "✗" if item["critical"] else "·",
            item["name"],
            "CRITICAL" if item["critical"] else "covered",
        ))
    print("Summary: %d critical, %d covered" % (
        report["critical"], report["covered"],
    ))
    return 1 if report["critical"] else 0


def _cmd_lkg(args) -> int:
    from aetheros_reliability.config_recovery import get_config_recovery

    cr = get_config_recovery()
    valid = cr.validate()
    print("Last-known-good config")
    print("  Current config valid:  %s" % ("yes" if valid.valid else "no"))
    if valid.issues:
        print("  Issues:                %s" % "; ".join(valid.issues))
    print("  LKG present:           %s" % ("yes" if cr.has_last_known_good() else "no"))
    if getattr(args, "update", False):
        if cr.update_last_known_good():
            _ok("Updated last-known-good from current config.")
        else:
            _err("Refused to update LKG: current config is not valid.")
            return 1
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_backup_id(value: str) -> str:
    """Resolve the literal ``latest`` to the newest backup id."""
    if value == "latest":
        from aetheros_reliability.backup import get_backup_store

        entry = get_backup_store().latest()
        if entry is None:
            raise ValueError("no backups exist yet")
        return entry.backup_id
    return value


# ---------------------------------------------------------------------------
# Mode commands
# ---------------------------------------------------------------------------


def _cmd_safe_mode(args) -> int:
    from aetheros_reliability.modes import get_mode_controller

    mc = get_mode_controller()
    if args.action == "enter":
        if mc.enter_safe_mode(reason=getattr(args, "reason", ""), operator=True):
            _ok("Entered Safe Mode.")
        else:
            _warn("Already in Safe Mode or a mode change was rejected.")
    else:
        if mc.exit_safe_mode():
            _ok("Exited Safe Mode.")
        else:
            _warn("Was not in Safe Mode.")
    return 0


def _cmd_recovery_mode(args) -> int:
    from aetheros_reliability.modes import get_mode_controller

    mc = get_mode_controller()
    if args.action == "enter":
        if mc.enter_recovery_mode(reason=getattr(args, "reason", ""), operator=True):
            _ok("Entered Recovery Mode.")
        else:
            _warn("Already in Recovery Mode or a mode change was rejected.")
    else:
        if mc.exit_recovery_mode():
            _ok("Exited Recovery Mode.")
        else:
            _warn("Was not in Recovery Mode.")
    return 0


# ---------------------------------------------------------------------------
# SPOF audit
# ---------------------------------------------------------------------------


def _spof_report() -> Dict[str, Any]:
    """Audit single points of failure across the reliability layer."""
    from aetheros_reliability.journal import get_recovery_journal
    from aetheros_reliability.watchdog import get_watchdog

    watchdog = get_watchdog()
    journal = get_recovery_journal()
    # Initialize the journal (lazily created) so the audit reflects reality.
    try:
        journal.stats()
        journal_ok = journal.db_path.exists()
    except Exception:
        journal_ok = False
    items = [
        {
            "name": "Watchdog daemon thread",
            "critical": not watchdog.running,
            "detail": "bounded daemon thread — dies with the process, as designed",
        },
        {
            "name": "Recovery journal (SQLite)",
            "critical": not journal_ok,
            "detail": "durable restart metadata",
        },
        {
            "name": "AETHEROS_HOME on single disk",
            "critical": False,
            "detail": "backups stored under same home; off-site copy not automatic",
        },
        {
            "name": "Single process watchdog",
            "critical": False,
            "detail": "one watchdog per process; gateway/CLI each own their own",
        },
    ]
    critical = sum(1 for i in items if i["critical"])
    return {
        "items": items,
        "critical": critical,
        "covered": len(items) - critical,
    }