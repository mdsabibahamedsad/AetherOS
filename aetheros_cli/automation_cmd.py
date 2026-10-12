"""CLI subcommand: ``aetheros automation`` (Master 13 core foundation).

Inspects and controls scheduled automations on the cron spine:

    aetheros automation                     # status overview
    aetheros automation list [--all]
    aetheros automation show <name|id>
    aetheros automation dryrun <name|id> [--occurrences N]
    aetheros automation estop [on REASON | off]
    aetheros automation policy <ref> --set POLICY [--max-age-hours H]
    aetheros automation limits <ref> [--max-runtime SEC] [--max-turns N] [--clear]
    aetheros automation recover <ref>
"""

from __future__ import annotations

import argparse
import time
from typing import Any, Dict, List, Optional


def _jobs_module():
    from cron import jobs as cron_jobs

    return cron_jobs


def _automation_state(job: Dict[str, Any], running_ids=None) -> str:
    from automation.model import lifecycle_of

    try:
        from cron import scheduler as cron_scheduler

        ids = running_ids
        if ids is None:
            with getattr(cron_scheduler, "_running_lock"):
                ids = set(getattr(cron_scheduler, "_running_job_ids", ()) or ())
        return lifecycle_of(job, running_ids=ids)
    except Exception:
        return lifecycle_of(job)


def cmd_status(_args: argparse.Namespace) -> int:
    from automation.guard import estop_active, safe_mode_enabled
    from automation.model import AutomationState

    cron_jobs = _jobs_module()
    all_jobs = [_normalize(cron_jobs, j) for j in cron_jobs.load_jobs()]

    counts: Dict[str, int] = {}
    for job in all_jobs:
        state = _automation_state(job)
        counts[state] = counts.get(state, 0) + 1

    print("Automation status")
    print("  total:      %d" % len(all_jobs))
    for state in sorted(counts):
        print("  %-12s %d" % (state, counts[state]))

    estop = estop_active()
    if estop:
        print("\n  EMERGENCY STOP ACTIVE")
        print("    reason: %s" % (estop.get("reason") or "(none given)"))
        print("    since:  %s" % (estop.get("at") or "?"))
        print("    lift with: aetheros automation estop off")
    else:
        print("\n  emergency stop: inactive")
    print("  safe mode:      %s" % ("on" if safe_mode_enabled() else "off"))
    return 0


def _normalize(cron_jobs, job: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return cron_jobs._normalize_job_record(dict(job))
    except Exception:
        return dict(job)


def cmd_list(args: argparse.Namespace) -> int:
    cron_jobs = _jobs_module()
    records = [_normalize(cron_jobs, j) for j in cron_jobs.load_jobs()]
    if not args.all:
        records = [r for r in records if r.get("enabled", True)]
    if not records:
        print("No automations.")
        return 0

    width = max((len(str(r.get("name") or r.get("id") or "?")) for r in records), default=4)
    width = min(max(width, 4), 40)
    header = "  %-12s %-*s %-24s %-14s %s" % (
        "STATE",
        width,
        "NAME",
        "SCHEDULE",
        "TIMEZONE",
        "ID",
    )
    print(header)
    for job in records:
        schedule = str(job.get("schedule_display") or "?")[:24]
        print(
            "  %-12s %-*s %-24s %-14s %s"
            % (
                _automation_state(job),
                width,
                str(job.get("name") or job["id"])[:width],
                schedule,
                str(job.get("timezone") or "-"),
                job["id"],
            )
        )
    return 0


def _resolve(ref: str) -> Optional[Dict[str, Any]]:
    cron_jobs = _jobs_module()
    try:
        return cron_jobs.resolve_job_ref(ref)
    except cron_jobs.AmbiguousJobReference as exc:
        print(exc)
        return None


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _print_preview(schedule: Any, tz_name: Optional[str], count: int) -> None:
    from automation.schedule_time import preview_next_runs

    runs = preview_next_runs(schedule, count=count, tz_name=tz_name)
    if not runs:
        print("  upcoming runs: (none computable)")
        return
    print("  upcoming runs (%s):" % (tz_name or "scheduler default timezone"))
    for run in runs:
        print("    - %s" % run.strftime("%Y-%m-%d %H:%M:%S %Z"))


def _print_details(job: Dict[str, Any]) -> None:
    from automation.model import validate_automation
    from automation.schedule_time import effective_missed_policy

    print("Automation: %s" % job.get("name"))
    print("  id:          %s" % job["id"])
    print("  version:     %s" % job.get("definition_version", 1))
    print("  schedule:    %s" % job.get("schedule_display"))
    print("  timezone:    %s" % (job.get("timezone") or "(scheduler default)"))
    policy, max_late = effective_missed_policy(job)
    print("  miss policy: %s (max late %ss)" % (policy, max_late))
    limits = job.get("resource_limits")
    if limits:
        print(
            "  limits:      max_runtime=%ss max_turns=%s"
            % (limits.get("max_runtime_seconds", "-"), limits.get("max_turns", "-"))
        )
    breaker = job.get("breaker")
    if breaker:
        print(
            "  breaker:     threshold=%s cooldown=%ss"
            % (breaker.get("failure_threshold"), breaker.get("cooldown_seconds"))
        )
    streak = int(job.get("failure_streak") or 0)
    opens = int(job.get("breaker_opens") or 0)
    if streak or opens:
        print(
            "  health:      failure_streak=%d breaker_opens=%d%s"
            % (streak, opens, " [OPEN]" if job.get("breaker_opened_at") else "")
        )
    if job.get("quarantined"):
        print("  QUARANTINED: %s" % (job.get("quarantine_reason") or ""))
    problems = validate_automation(job)
    if problems:
        print("  problems:")
        for problem in problems:
            print("    - %s" % problem)
    _print_preview(job.get("schedule"), job.get("timezone"), count=5)


def cmd_show(args: argparse.Namespace) -> int:
    job = _resolve(args.ref)
    if not job:
        print("Automation not found: %s" % args.ref)
        return 1
    _print_details(job)
    return 0


def cmd_dryrun(args: argparse.Namespace) -> int:
    """Phase 50/67: plan without executing — no agent run, no delivery."""
    job = _resolve(args.ref)
    if not job:
        print("Automation not found: %s" % args.ref)
        return 1

    print("DRY RUN — nothing will execute or be delivered\n")

    print("Planned trigger:")
    kind = (job.get("schedule") or {}).get("kind")
    print("  kind:     %s" % kind)
    print("  prompt:   %s" % (str(job.get("prompt") or "")[:160] or "(none)"))
    skills = job.get("skills") or []
    if skills:
        print("  skills:   %s" % ", ".join(skills))
    if job.get("script"):
        print("  script:   %s%s" % (job.get("script"), " (no_agent)" if job.get("no_agent") else ""))

    _print_preview(job.get("schedule"), job.get("timezone"), count=args.occurrences)

    print("Planned resources:")
    limits = job.get("resource_limits") or {}
    print("  model:         %s" % (job.get("model") or "(configured default)"))
    print("  provider:      %s" % (job.get("provider") or "(configured default)"))
    print(
        "  max turns:     %s"
        % (limits.get("max_turns") or "(agent default)")
    )
    print(
        "  max runtime:   %s"
        % (
            "%ss" % limits.get("max_runtime_seconds")
            if limits.get("max_runtime_seconds")
            else "(inactivity timeout only)"
        )
    )

    try:
        from aetheros_cli.config import load_config
        from cron.scheduler import (
            _resolve_cron_disabled_toolsets,
            _resolve_cron_enabled_toolsets,
        )

        cfg = load_config() or {}
        enabled = _resolve_cron_enabled_toolsets(job, cfg)
        disabled = _resolve_cron_disabled_toolsets(cfg)
        print("  toolsets:      %s" % (", ".join(enabled) if enabled else "(default set)"))
        if disabled:
            print("  denied:        %s" % ", ".join(disabled))
    except Exception:
        print("  toolsets:      (resolution unavailable)")

    print("Planned external effects:")
    if job.get("deliver", "local") == "local":
        print("  delivery: local only")
    else:
        try:
            from cron.scheduler import _resolve_delivery_targets

            targets = _resolve_delivery_targets(job)
            if targets:
                for target in targets:
                    print(
                        "  deliver to: %s:%s%s"
                        % (
                            target["platform"],
                            target["chat_id"],
                            ":%s" % target["thread_id"] if target.get("thread_id") else "",
                        )
                    )
            else:
                print("  deliver: (no resolvable target — output stays local)")
        except Exception:
            print("  deliver: %s (resolution unavailable)" % job.get("deliver"))

    from automation.model import validate_automation

    problems = validate_automation(job)
    if problems:
        print("\nValidation problems:")
        for problem in problems:
            print("  - %s" % problem)
        return 1
    print("\nValidation: OK")

    try:
        from automation.conflicts import conflicts_for

        found = conflicts_for(str(job["id"]), cron_jobs.load_jobs())
        if found:
            print("\nSchedule conflicts (informational — nothing blocked):")
            for conflict in found:
                print("  - [%s] %s" % (conflict["kind"], conflict["detail"]))
            print("  review with: aetheros automation list --all")
    except Exception:
        pass  # conflict scan is advisory only — never fail the dry run
    return 0


def cmd_estop(args: argparse.Namespace) -> int:
    from automation.guard import estop_active, set_estop

    if args.estop_action == "on":
        record = set_estop(True, reason=(args.reason or "").strip())
        print("EMERGENCY STOP engaged at %s" % (record or {}).get("at"))
        if args.reason:
            print("Reason: %s" % args.reason.strip())
        print("All background automation is paused until: aetheros automation estop off")
        return 0
    if args.estop_action == "off":
        set_estop(False)
        print("Emergency stop lifted — background automation resumes on the next tick.")
        return 0
    active = estop_active()
    if active:
        print("EMERGENCY STOP ACTIVE — reason: %s (since %s)" % (active.get("reason") or "?", active.get("at") or "?"))
    else:
        print("Emergency stop is not active.")
    return 0


def cmd_policy(args: argparse.Namespace) -> int:
    job = _resolve(args.ref)
    if not job:
        print("Automation not found: %s" % args.ref)
        return 1
    updates: Dict[str, Any] = {}
    if args.set:
        updates["missed_policy"] = args.set
    if args.max_age_hours is not None:
        if args.max_age_hours <= 0:
            print("--max-age-hours must be positive")
            return 1
        updates["missed_policy_max_age_seconds"] = int(args.max_age_hours * 3600)
    if not updates:
        from automation.schedule_time import effective_missed_policy

        policy, max_late = effective_missed_policy(job)
        print("%s: policy=%s (max late %ss)" % (job.get("name"), policy, max_late))
        return 0
    updated = _jobs_module().update_job(job["id"], updates)
    if updated is None:
        print("Update failed for %s" % job["id"])
        return 1
    print("%s: missed-schedule policy updated" % updated.get("name"))
    return 0


def cmd_limits(args: argparse.Namespace) -> int:
    job = _resolve(args.ref)
    if not job:
        print("Automation not found: %s" % args.ref)
        return 1
    if args.clear:
        _jobs_module().update_job(job["id"], {"resource_limits": None})
        print("%s: resource limits cleared" % job.get("name"))
        return 0
    current = dict(job.get("resource_limits") or {})
    if args.max_runtime is not None:
        if args.max_runtime <= 0:
            print("--max-runtime must be positive")
            return 1
        current["max_runtime_seconds"] = int(args.max_runtime)
    if args.max_turns is not None:
        if args.max_turns <= 0:
            print("--max-turns must be positive")
            return 1
        current["max_turns"] = int(args.max_turns)
    if not current:
        print("%s: no resource limits set" % job.get("name"))
        return 0
    updated = _jobs_module().update_job(job["id"], {"resource_limits": current})
    if updated is None:
        print("Update failed for %s" % job["id"])
        return 1
    print(
        "%s: limits now max_runtime=%ss max_turns=%s"
        % (
            updated.get("name"),
            current.get("max_runtime_seconds", "-"),
            current.get("max_turns", "-"),
        )
    )
    return 0


def cmd_recover(args: argparse.Namespace) -> int:
    from automation.guard import recover_automation

    job = _resolve(args.ref)
    if not job:
        print("Automation not found: %s" % args.ref)
        return 1
    if recover_automation(job["id"]):
        print("%s: quarantine and breaker state cleared" % job.get("name"))
        return 0
    print("Recover failed for %s" % job["id"])
    return 1


def cmd_trigger(args: argparse.Namespace) -> int:
    cron_jobs = _jobs_module()
    job = _resolve(args.ref)
    if not job:
        print("Automation not found: %s" % args.ref)
        return 1
    if args.clear:
        updated = cron_jobs.update_job(job["id"], {"trigger": None})
        if updated is None:
            print("Update failed for %s" % job["id"])
            return 1
        print("%s: event trigger cleared (schedule-driven only)" % updated.get("name"))
        return 0

    trigger: Dict[str, Any] = {
        "kind": "event",
        "event_types": [t.strip() for t in args.event_types.split(",") if t.strip()],
    }
    filters = []
    for spec in args.filter or []:
        text = str(spec)
        if "=" not in text:
            print("--filter must look like payload.path=value (got %r)" % text)
            return 1
        path, value = text.split("=", 1)
        filters.append({"path": path.strip(), "op": "eq", "value": value})
    if filters:
        trigger["filters"] = filters
    if args.cooldown is not None:
        trigger["cooldown_seconds"] = args.cooldown
    if args.allow_untrusted:
        trigger["allow_untrusted"] = True

    updates: Dict[str, Any] = {"trigger": trigger}
    if args.remove_schedule:
        updates["schedule"] = None
    try:
        updated = cron_jobs.update_job(job["id"], updates)
    except ValueError as exc:
        print("Trigger rejected: %s" % exc)
        return 1
    if updated is None:
        print("Update failed for %s" % job["id"])
        return 1
    from automation.triggers import describe_trigger

    print("%s: %s" % (updated.get("name"), describe_trigger(updated.get("trigger"))))
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    """Recent automation bus events — the observable side of triggering."""
    from automation.events import get_bus

    entries = get_bus().recent(limit=args.limit, event_type=args.type or "")
    if not entries:
        print("No events recorded yet.")
        return 0
    print("%-26s %-9.9s %-24s %s" % ("TYPE", "TRUST", "SOURCE", "AGE"))
    now = time.time()
    for entry in entries:
        age = max(0, int(now - float(entry.get("timestamp") or now)))
        print(
            "%-26s %-9.9s %-24.24s %6ss"
            % (
                str(entry.get("event_type")),
                str(entry.get("trust")),
                str(entry.get("source")),
                age,
            )
        )
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    """Resolve a pending approval as APPROVED and re-arm the automation."""
    from automation import approvals
    from automation.events import publish_internal

    job = _resolve(args.ref)
    if not job:
        print("Automation not found: %s" % args.ref)
        return 1
    request = approvals.resolve(job["id"], approve=True)
    if request is None:
        print("No pending approval for %s" % job.get("name"))
        return 1

    cron_jobs = _jobs_module()
    cron_jobs.update_job(
        job["id"], {"next_run_at": _now_iso(), "state": "scheduled"}
    )
    cron_jobs.apply_job_field_updates(
        job["id"], {"state": "scheduled", "paused_reason": None}
    )
    publish_internal("automation.approved", {
        "automation_id": job["id"], "run_id": request.get("run_id"),
    }, source="user")
    print("%s: approved — workflow resumes on the next tick" % job.get("name"))
    return 0


def cmd_deny(args: argparse.Namespace) -> int:
    """Resolve a pending approval as DENIED; the run fails without executing."""
    from automation import approvals, runs as run_store
    from automation.events import publish_internal

    job = _resolve(args.ref)
    if not job:
        print("Automation not found: %s" % args.ref)
        return 1
    request = approvals.resolve(job["id"], approve=False)
    if request is None:
        print("No pending approval for %s" % job.get("name"))
        return 1
    run = run_store.load_run(str(request.get("run_id") or ""))
    if run is not None and run.get("status") in run_store.ACTIVE_STATUSES:
        step_id = str(request.get("step_id") or "")
        if step_id in run.get("steps", {}):
            run_store.mark_step(run, step_id, "failed", error="approval denied")
        run_store.finish_run(run, "cancelled")
    publish_internal("automation.cancelled", {
        "automation_id": job["id"], "run_id": request.get("run_id"),
    }, source="user")
    print("%s: denied — run cancelled without executing the gated step" % job.get("name"))
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    """Execution history / timeline (Phase 71)."""
    from automation import runs as run_store

    ref = getattr(args, "ref", None)
    automation_id = None
    name = "all automations"
    if ref:
        job = _resolve(ref)
        if not job:
            print("Automation not found: %s" % ref)
            return 1
        automation_id = job["id"]
        name = str(job.get("name"))
    entries = run_store.list_runs(automation_id=automation_id, limit=args.limit)
    if not entries:
        print("No workflow runs recorded for %s." % name)
        return 0
    for run in entries:
        done = sum(
            1 for s in run.get("steps", {}).values() if s.get("status") == "done"
        )
        total = len(run.get("steps", {}))
        progress = "%d/%d" % (done, total) if total else "-"
        print(
            "%s  %-9.9s v%-4s steps=%-5s %s"
            % (
                str(run.get("created_at"))[:19],
                run.get("status"),
                run.get("definition_version", 1),
                progress,
                run.get("run_id"),
            )
        )
        for sid, state in (run.get("steps") or {}).items():
            marker = {"done": "+", "failed": "x", "skipped": "-", "running": ">",
                      "pending": ".", "waiting_approval": "?"}.get(state.get("status"), "?")
            note = str(state.get("error") or "")[:80]
            suffix = f"  {note}" if note else ""
            print("    [%s] %-14.14s%s%s" % (marker, sid, "", suffix))
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    """Request cooperative cancellation of an active workflow run (Phase 47)."""
    from automation import runs as run_store
    from automation.events import publish_internal

    job = _resolve(args.ref)
    if not job:
        print("Automation not found: %s" % args.ref)
        return 1
    run = run_store.active_run_for(job["id"])
    if run is None:
        print("%s: no active workflow run" % job.get("name"))
        return 1
    run_store.request_cancel(run)
    publish_internal("automation.cancelled", {
        "automation_id": job["id"], "run_id": run["run_id"],
    }, source="user")
    print("%s: cancellation requested — stops at the next step boundary" % job.get("name"))
    return 0


def dispatch_automation_command(args: argparse.Namespace) -> int:
    """Entry point for bare ``aetheros automation`` and explicit dispatch."""
    command = getattr(args, "automation_command", None)
    if not command:
        return cmd_status(args)
    if command == "estop":
        if getattr(args, "estop_action", None) is None:
            args.estop_action = "status"
        if args.estop_action == "on":
            args.reason = " ".join(getattr(args, "reason", []) or []).strip()
        return cmd_estop(args)
    handlers = {
        "status": cmd_status,
        "list": cmd_list,
        "show": cmd_show,
        "dryrun": cmd_dryrun,
        "policy": cmd_policy,
        "limits": cmd_limits,
        "recover": cmd_recover,
        "trigger": cmd_trigger,
        "events": cmd_events,
        "approve": cmd_approve,
        "deny": cmd_deny,
        "runs": cmd_runs,
        "cancel": cmd_cancel,
    }
    handler = handlers.get(command)
    if handler is None:
        print("Unknown automation command: %s" % command)
        return 1
    return handler(args)


def build_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "automation",
        help="Inspect and control scheduled automations (Master 13)",
        description="Manage automations: schedules, missed-run policies, "
        "resource limits, circuit breaker recovery and the global emergency stop.",
    )
    parser.set_defaults(func=lambda _a: cmd_status(_a))
    subs = parser.add_subparsers(dest="automation_command", metavar="COMMAND")

    subs.add_parser("status", help="Overview of automations, breaker and stop state").set_defaults(
        func=cmd_status
    )

    p_list = subs.add_parser("list", help="List automations with lifecycle states")
    p_list.add_argument("--all", action="store_true", help="Include paused/quarantined")
    p_list.set_defaults(func=cmd_list)

    p_show = subs.add_parser("show", help="Show one automation in detail")
    p_show.add_argument("ref", help="Name or ID")
    p_show.set_defaults(func=cmd_show)

    p_dry = subs.add_parser("dryrun", help="Plan a run without executing anything")
    p_dry.add_argument("ref", help="Name or ID")
    p_dry.add_argument("--occurrences", type=int, default=5, help="Preview N upcoming times")
    p_dry.set_defaults(func=cmd_dryrun)

    p_estop = subs.add_parser("estop", help="Global background-automation emergency stop")
    p_estop.add_argument("estop_action", nargs="?", choices=("on", "off"), default=None)
    p_estop.add_argument("reason", nargs="*", default=[], help="Optional reason when engaging")
    p_estop.add_argument("--status", action="store_true", help="Show current state")
    def _estop(args: argparse.Namespace) -> int:
        if args.estop_action is None:
            args.estop_action = "status"
        if args.estop_action == "on":
            args.reason = " ".join(args.reason).strip()
        return cmd_estop(args)
    p_estop.set_defaults(func=_estop)

    p_policy = subs.add_parser("policy", help="Set the missed-schedule policy")
    p_policy.add_argument("ref", help="Name or ID")
    p_policy.add_argument(
        "--set",
        choices=("catch_up", "skip", "run_on_start", "run_next_interval", "ask_user"),
        default=None,
    )
    p_policy.add_argument("--max-age-hours", type=float, default=None,
                          help="Bound for run_on_start/ask_user lateness")
    p_policy.set_defaults(func=cmd_policy)

    p_limits = subs.add_parser("limits", help="Per-automation resource limits")
    p_limits.add_argument("ref", help="Name or ID")
    p_limits.add_argument("--max-runtime", type=int, default=None, metavar="SECONDS")
    p_limits.add_argument("--max-turns", type=int, default=None)
    p_limits.add_argument("--clear", action="store_true", help="Remove all limits")
    p_limits.set_defaults(func=cmd_limits)

    p_recover = subs.add_parser("recover", help="Clear quarantine/breaker state")
    p_recover.add_argument("ref", help="Name or ID")
    p_recover.set_defaults(func=cmd_recover)

    p_trigger = subs.add_parser("trigger", help="Attach an event trigger to an automation")
    p_trigger.add_argument("ref", help="Name or ID")
    p_trigger.add_argument(
        "--event-types",
        dest="event_types",
        default=None,
        help="Comma-separated event types (e.g. file.created,webhook.received)",
    )
    p_trigger.add_argument(
        "--filter",
        action="append",
        default=None,
        metavar="PATH=VALUE",
        help="Equality filter, repeatable (e.g. payload.route=alerts)",
    )
    p_trigger.add_argument("--cooldown", type=int, default=None, metavar="SECONDS")
    p_trigger.add_argument(
        "--allow-untrusted",
        action="store_true",
        help="Match external events (webhooks/files); payloads stay untrusted",
    )
    p_trigger.add_argument(
        "--remove-schedule",
        action="store_true",
        help="Detach the cron schedule (pure event-driven automation)",
    )
    p_trigger.add_argument("--clear", action="store_true", help="Remove the trigger")
    def _trigger(args: argparse.Namespace) -> int:
        if not args.clear and not args.event_types:
            print("--event-types is required (or use --clear)")
            return 1
        return cmd_trigger(args)
    p_trigger.set_defaults(func=_trigger)

    p_events = subs.add_parser("events", help="Show recent automation bus events")
    p_events.add_argument("--limit", type=int, default=20)
    p_events.add_argument("--type", default="", help="Filter by event type")
    p_events.set_defaults(func=cmd_events)

    p_approve = subs.add_parser("approve", help="Approve a pending workflow step")
    p_approve.add_argument("ref", help="Name or ID")
    p_approve.set_defaults(func=cmd_approve)

    p_deny = subs.add_parser("deny", help="Deny a pending workflow step")
    p_deny.add_argument("ref", help="Name or ID")
    p_deny.set_defaults(func=cmd_deny)

    p_runs = subs.add_parser("runs", help="Workflow execution history/timeline")
    p_runs.add_argument("ref", nargs="?", default=None, help="Name or ID (optional)")
    p_runs.add_argument("--limit", type=int, default=10)
    p_runs.set_defaults(func=cmd_runs)

    p_cancel = subs.add_parser("cancel", help="Cancel the active workflow run")
    p_cancel.add_argument("ref", help="Name or ID")
    p_cancel.set_defaults(func=cmd_cancel)

    return parser
