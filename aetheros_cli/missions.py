"""CLI for the Aetheros mission engine — ``aetheros mission …`` subcommand.

Drives the shared mission lifecycle (``aetheros_jarvis.mission.MissionManager``)
through the real agent execution engine (``AgentExecutionEngine``), so a
``aetheros mission run <id>`` executes each step with an actual AIAgent run
rather than the legacy simulation.  Mirrors the ``kanban`` CLI shape: a
``build_parser`` attached to the top-level subparsers, a ``mission_command``
argparse dispatcher, and a ``run_slash`` entry for ``/mission``.
"""

from __future__ import annotations

import argparse
import logging
import shlex
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_SLASH_MISSION_HELP = """\
Mission mode — decompose a goal into approved steps and execute them.

Usage:
  /mission create <goal>            create a mission from a goal
  /mission plan <id> [steps...]     attach concrete steps to a mission
  /mission approve <id>             approve an awaiting mission
  /mission run <id>                 execute the mission
  /mission list                     list missions
  /mission show <id>                show a mission + report
"""


def _get_manager():
    """Build a MissionManager wired to the real agent execution engine.

    Imported lazily so a missing automation package degrades to an error
    message rather than breaking ``aetheros`` startup.  The manager is a
    process-global so missions persist across ``aetheros mission …``
    invocations within one process (and one interactive session)."""
    global _MANAGER
    if _MANAGER is None:
        from aetheros_jarvis.mission import MissionManager

        _MANAGER = MissionManager()
    return _MANAGER


_MANAGER = None


def _describe_step(step) -> str:
    status = getattr(step, "status", None)
    status_str = status.value if hasattr(status, "value") else str(status or "pending")
    result = getattr(step, "result", "") or ""
    line = f"  - {step.description} [{status_str}]"
    if result:
        line += f"\n      result: {str(result)[:400]}"
    return line


def build_parser(parent_subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Attach the ``mission`` subcommand tree under an existing subparsers.

    Returns the top-level ``mission`` parser so the caller can
    ``set_defaults(func=cmd_mission)``.
    """
    mission_parser = parent_subparsers.add_parser(
        "mission",
        help="Mission engine — plan and execute multi-step autonomous goals",
        description=(
            "Create a mission from a goal, attach concrete steps, approve, "
            "and execute.  Each step runs through the real agent execution "
            "engine as an AIAgent sub-run."
        ),
    )
    sub = mission_parser.add_subparsers(dest="mission_action")

    create_p = sub.add_parser("create", help="Create a mission from a goal")
    create_p.add_argument("goal", nargs="+", help="Mission goal")
    sub.add_parser("list", help="List all missions")

    show_p = sub.add_parser("show", help="Show a mission and its report")
    show_p.add_argument("mission_id", help="Mission id")

    plan_p = sub.add_parser("plan", help="Attach concrete steps to a mission")
    plan_p.add_argument("mission_id", help="Mission id")
    plan_p.add_argument("steps", nargs="*", help="Step descriptions (default: one step from the goal)")
    plan_p.add_argument("--no-approval", action="store_true",
                        help="Plan does not require approval (auto-approved)")

    approve_p = sub.add_parser("approve", help="Approve an awaiting mission")
    approve_p.add_argument("mission_id", help="Mission id")
    approve_p.add_argument("--deny", action="store_true", help="Deny instead of approve")

    run_p = sub.add_parser("run", help="Execute a mission")
    run_p.add_argument("mission_id", help="Mission id")
    run_p.add_argument("--auto-approve", action="store_true",
                       help="Auto-approve without prompting")

    mission_parser.set_defaults(_mission_parser=mission_parser)
    return mission_parser


def mission_command(args: argparse.Namespace) -> int:
    """Entry point from ``aetheros mission …`` argparse dispatch."""
    action = getattr(args, "mission_action", None)
    if action is None:
        parser = getattr(args, "_mission_parser", None)
        if parser is not None:
            parser.print_help()
        else:
            print("usage: aetheros mission <action> [options]")
        return 0

    try:
        if action == "create":
            return _cmd_create(args)
        if action == "list":
            return _cmd_list(args)
        if action == "show":
            return _cmd_show(args)
        if action == "plan":
            return _cmd_plan(args)
        if action == "approve":
            return _cmd_approve(args)
        if action == "run":
            return _cmd_run(args)
        print(f"mission: unknown action {action!r}", file=__import__("sys").stderr)
        return 1
    except Exception as exc:
        print(f"mission: {exc}", file=__import__("sys").stderr)
        logger.exception("mission command %s failed", action)
        return 1


def _cmd_create(args) -> int:
    goal = " ".join(args.goal) if hasattr(args, "goal") and args.goal else ""
    if not goal:
        print("usage: aetheros mission create <goal>")
        return 2
    mm = _get_manager()
    plan = mm.create(goal, approval_required=True)
    print(f"Created mission {plan.id}: {plan.goal}")
    print(f"  status: {plan.status.value}")
    print(f"Next: `aetheros mission plan {plan.id} ...` then approve + run.")
    return 0


def _cmd_list(args) -> int:
    mm = _get_manager()
    missions = mm.list_missions()
    if not missions:
        print("No missions yet. Create one with `aetheros mission create <goal>`.")
        return 0
    for plan in missions:
        steps_done = sum(1 for s in plan.steps if str(getattr(s, "status", "")).endswith("completed"))
        print(f"  {plan.id}  [{plan.status.value}]  {plan.goal}  ({len(plan.steps)} steps)")
    return 0


def _cmd_show(args) -> int:
    mm = _get_manager()
    plan = mm.get(args.mission_id)
    if plan is None:
        print(f"mission: unknown mission {args.mission_id!r}")
        return 1
    print(f"Mission {plan.id}: {plan.goal}")
    print(f"  status: {plan.status.value}")
    print(f"  approval_required: {plan.approval_required}")
    print("  steps:")
    for step in plan.steps:
        print(_describe_step(step))
    report = mm.report(args.mission_id)
    if report is not None:
        print(f"  report status: {report.status.value}")
        if report.summary:
            print(f"  summary: {report.summary}")
        for err in report.errors:
            print(f"  error: {err}")
    return 0


def _cmd_plan(args) -> int:
    mm = _get_manager()
    plan = mm.get(args.mission_id)
    if plan is None:
        print(f"mission: unknown mission {args.mission_id!r}")
        return 1
    if args.steps:
        steps = [{"description": s, "tool": "agent", "params": {}} for s in args.steps]
    else:
        steps = [{"description": plan.goal, "tool": "agent", "params": {}}]
    updated = mm.plan(plan.id, steps)
    if updated is None:
        print(f"mission: unknown mission {args.mission_id!r}")
        return 1
    status = updated.status.value if hasattr(updated.status, "value") else updated.status
    print(f"Planned {len(updated.steps)} step(s) for mission {plan.id} [{status}]")
    if plan.approval_required and not args.no_approval:
        print(f"Next: `aetheros mission approve {plan.id}` then `aetheros mission run {plan.id}`")
    else:
        print(f"Next: `aetheros mission run {plan.id}`")
    return 0


def _cmd_approve(args) -> int:
    mm = _get_manager()
    plan = mm.approve(args.mission_id, approved=not args.deny)
    if plan is None:
        print(f"mission: unknown mission {args.mission_id!r}")
        return 1
    status = plan.status.value if hasattr(plan.status, "value") else plan.status
    print(f"Mission {plan.id} -> {status}")
    return 0


def _cmd_run(args) -> int:
    mm = _get_manager()
    if args.auto_approve:
        mm.set_approval_callback(lambda plan: True)
    report = mm.execute(args.mission_id)
    status = report.status.value if hasattr(report.status, "value") else report.status
    print(f"Mission {report.mission_id} finished [{status}] in "
          f"{report.completed_at - report.started_at:.1f}s")
    if report.summary:
        print(f"  summary: {report.summary}")
    for step in report.steps:
        step_status = step.status.value if hasattr(step.status, "value") else step.status
        print(f"  - {step.description} [{step_status}]")
        if step.result:
            print(f"      result: {str(step.result)[:400]}")
    if report.errors:
        print("  errors:")
        for err in report.errors:
            print(f"    - {err}")
    return 0 if status == "completed" else 1


def run_slash(rest: str) -> str:
    """Execute a ``/mission …`` string and return captured stdout/stderr.

    ``rest`` is everything after ``/mission`` (may be empty).  Used from both
    the interactive CLI and the gateway so formatting is identical.
    """
    import contextlib
    import io

    tokens = shlex.split(rest) if rest and rest.strip() else []

    if not tokens or tokens[0] in {"help", "--help", "-h", "?"}:
        return _SLASH_MISSION_HELP

    _wrap = argparse.ArgumentParser(prog="/mission-wrap", add_help=False)
    _wrap.exit_on_error = False  # type: ignore[attr-defined]
    _top_sub = _wrap.add_subparsers(dest="_top")
    mission_parser = build_parser(_top_sub)
    mission_parser.prog = "/mission"
    mission_parser.exit_on_error = False  # type: ignore[attr-defined]

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            args = mission_parser.parse_args(tokens)
            rc = mission_command(args)
        if rc != 0:
            return buf.getvalue().strip() or f"/mission: failed ({rc})"
        return buf.getvalue().strip()
    except SystemExit as exc:  # argparse --help path
        return buf.getvalue().strip() or _SLASH_MISSION_HELP
    except Exception as exc:  # pragma: no cover - defensive
        return f"(._.) mission error: {exc}"
