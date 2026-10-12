from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_ENGINE: Any = None


def _get_engine() -> Any:
    global _ENGINE
    if _ENGINE is None:
        from aetheros_automation.core.engine import AutomationEngine

        _ENGINE = AutomationEngine()
        _ENGINE.start()
    return _ENGINE


def _run_async(coro: Any, timeout: float = 30) -> Any:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=timeout)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _task_goal(task: Any) -> str:
    return (
        task.metadata.get("goal", "") if hasattr(task, "metadata") and task.metadata else ""
    ) or getattr(task, "goal", "") or task.name or task.description or "Unnamed"


def _task_summary(task: Any) -> str:
    from aetheros_automation.models.models import TaskStatus

    status = task.status.value if task.status else "unknown"
    name = _task_goal(task)
    mode = (
        task.metadata.get("mode", "")
        if hasattr(task, "metadata") and task.metadata
        else ""
    ) or (getattr(task, "mode", None) or "N/A")
    return (
        f"  [{task.id}] {name}\n"
        f"    Status: {status}\n"
        f"    Mode:   {mode}\n"
        f"    Steps:  {len(task.steps) if hasattr(task, 'steps') and task.steps else 0}\n"
        f"    Created: {_fmt_dt(task.created_at) if hasattr(task, 'created_at') and task.created_at else '—'}"
        f"{'  |  Completed: ' + _fmt_dt(task.completed_at) if hasattr(task, 'completed_at') and task.completed_at else ''}\n"
        f"    Result:  {str(task.result)[:120] if hasattr(task, 'result') and task.result else '—'}"
    )


def _fmt_dt(ts) -> str:
    if hasattr(ts, "strftime"):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(ts, (int, float)):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    return str(ts) if ts else "—"


def run_cmd(args: list[str]) -> str:
    """aetheros run <action> [params...]"""
    if not args:
        return "Usage: aetheros run <action> [params...]"

    engine = _get_engine()
    action = args[0]
    params = {}
    for i in range(1, len(args), 2):
        if i + 1 < len(args):
            params[args[i].lstrip("-")] = args[i + 1]

    result = engine.run_action(action, params)
    return f"Action '{action}' executed.\n  Result: {result}"


def task_cmd(args: list[str]) -> str:
    """aetheros task create|list|show|cancel|pause|resume <id>"""
    if not args:
        return "Usage: aetheros task <create|list|show|cancel|pause|resume> [args...]"

    engine = _get_engine()
    sub = args[0]

    if sub == "create":
        goal = " ".join(args[1:]) if len(args) > 1 else "New Task"
        task = engine.create_task(goal=goal)
        engine.submit_task(task)
        return f"Task created and submitted.\n  ID:   {task.id}\n  Goal: {_task_goal(task)}"

    elif sub == "list":
        from aetheros_automation.models.models import TaskStatus

        status_filter = args[1] if len(args) > 1 else None
        sf = None
        if status_filter:
            try:
                sf = TaskStatus(status_filter.upper())
            except ValueError:
                return f"Unknown status: {status_filter}"
        tasks = engine.list_tasks(sf)
        if not tasks:
            return "No tasks found."
        return f"Tasks ({len(tasks)}):\n" + "\n".join(_task_summary(t) for t in tasks)

    elif sub == "show":
        if len(args) < 2:
            return "Usage: aetheros task show <task_id>"
        task = engine.get_task(args[1])
        if task is None:
            return f"Task {args[1]} not found."
        return _task_summary(task)

    elif sub == "cancel":
        if len(args) < 2:
            return "Usage: aetheros task cancel <task_id>"
        engine.cancel_task(args[1])
        return f"Task {args[1]} cancelled."

    elif sub == "pause":
        if len(args) < 2:
            return "Usage: aetheros task pause <task_id>"
        engine.pause()
        return f"Engine paused."

    elif sub == "resume":
        if len(args) < 2:
            return "Usage: aetheros task resume <task_id>"
        engine.resume()
        return f"Engine resumed."

    else:
        return f"Unknown subcommand: {sub}"


def automate_cmd(args: list[str]) -> str:
    """aetheros automate <task_description>"""
    if not args:
        return "Usage: aetheros automate <task_description>"

    description = " ".join(args)
    engine = _get_engine()
    task = engine.create_task(goal=description)

    out = f"Task created from description.\n  ID:   {task.id}\n  Goal: {_task_goal(task)}\n\nRunning task {task.id} ..."
    logger.info(out)

    engine.submit_task(task)

    status = _run_async(_await_task(engine, task.id), timeout=3600)
    return (
        f"Task completed.\n"
        f"  ID:     {task.id}\n"
        f"  Status: {task.status.value if task.status else 'unknown'}\n"
        f"  Result: {str(task.result)[:500] if task.result else '—'}"
    )


async def _await_task(engine: Any, task_id: str) -> str:
    while True:
        task = engine.get_task(task_id)
        if task and task.status.value in ("completed", "failed", "cancelled", "timeout", "emergency_stopped"):
            return task.status.value
        await asyncio.sleep(0.5)


def approvals_cmd(args: list[str]) -> str:
    """aetheros approvals list|respond <id> [approve|deny] [reason]"""
    engine = _get_engine()
    mgr = engine.get_subsystem("approvals.manager") or engine.get_subsystem("manager")
    if mgr is None:
        return "Approval manager not available."

    if not args or args[0] == "list":
        pending = getattr(mgr, "pending_approvals", [])
        if not pending:
            return "No pending approvals."
        lines = ["Pending approvals:"]
        for a in pending:
            lines.append(f"  [{a.id}] {a.action}: {a.description}")
        return "\n".join(lines)

    if args[0] == "respond" and len(args) >= 3:
        approval_id = args[1]
        approved = args[2].lower() in ("approve", "yes", "true", "1")
        reason = " ".join(args[3:]) if len(args) > 3 else ""
        result = _run_async(mgr.respond(approval_id, approved, reason))
        if result:
            return f"Approval {approval_id} {'approved' if approved else 'denied'}."
        return f"Approval {approval_id} not found."

    return "Usage: aetheros approvals list|respond <id> [approve|deny] [reason]"


def stop_cmd(args: list[str]) -> str:
    """aetheros stop <task_id|all>"""
    engine = _get_engine()
    if not args or args[0] == "all":
        engine.stop()
        return "Engine stopped. All tasks cancelled."
    engine.cancel_task(args[0])
    return f"Task {args[0]} cancelled."


def resume_cmd(args: list[str]) -> str:
    """aetheros resume <task_id>"""
    if not args:
        return "Usage: aetheros resume <task_id>"
    engine = _get_engine()
    engine.resume()
    return f"Engine resumed."


def rollback_cmd(args: list[str]) -> str:
    """aetheros rollback <task_id>"""
    if not args:
        return "Usage: aetheros rollback <task_id>"
    engine = _get_engine()
    undo_mgr = engine.get_subsystem("undo.manager") or engine.get_subsystem("manager")
    if undo_mgr is None:
        return "Undo manager not available."
    task_id = args[0]
    result = _run_async(undo_mgr.undo_task(task_id) if hasattr(undo_mgr, "undo_task") else None)
    if result:
        return f"Task {task_id} rolled back."
    return f"No undo actions found for task {task_id}."


def status_cmd(args: list[str]) -> str:
    """aetheros status"""
    engine = _get_engine()
    s = engine.get_status()
    lines = [
        "Aether Automation Engine Status",
        f"  Running:          {s.get('running', False)}",
        f"  Paused:           {s.get('paused', False)}",
        f"  Emergency Stop:   {s.get('emergency_stop', False)}",
        f"  Tasks:            {s.get('task_count', 0)}",
        f"  Agents:           {s.get('agent_count', 0)}",
        f"  Workflows:        {s.get('workflow_count', 0)}",
        f"  Active Subsytems: {', '.join(s.get('active_subsystems', []))}",
        f"  Execution History: {s.get('execution_history_count', 0)} events",
    ]
    return "\n".join(lines)


def mode_cmd(args: list[str]) -> str:
    """aetheros mode <manual|assisted|semi|full>"""
    from aetheros_automation.models.models import ExecutionMode

    if not args:
        return "Usage: aetheros mode <manual|assisted|semi|full>"

    engine = _get_engine()
    mode_map = {
        "manual": ExecutionMode.MANUAL,
        "assisted": ExecutionMode.ASSISTED,
        "semi": ExecutionMode.SEMI_AUTONOMOUS,
        "full": ExecutionMode.FULLY_AUTONOMOUS,
    }
    choice = args[0].lower()
    if choice not in mode_map:
        return f"Unknown mode: {choice}. Choose from: {', '.join(mode_map.keys())}"

    _run_async(engine.switch_mode(mode_map[choice]))
    return f"Mode switched to {choice}."


def agent_cmd(args: list[str]) -> str:
    """aetheros agent list|spawn|show"""
    engine = _get_engine()
    if not args or args[0] == "list":
        agents = engine.list_agents()
        if not agents:
            return "No agents registered."
        lines = [f"Agents ({len(agents)}):"]
        for aid, agent in agents.items():
            desc = getattr(agent, "description", getattr(agent, "role", ""))
            lines.append(f"  [{aid}] {desc}")
        return "\n".join(lines)

    if args[0] == "show" and len(args) > 1:
        agent = engine.get_agent(args[1])
        if agent is None:
            return f"Agent {args[1]} not found."
        return f"[{args[1]}] {getattr(agent, 'description', str(agent))}"

    return "Usage: aetheros agent list|show <id>"


def history_cmd(args: list[str]) -> str:
    """aetheros history [limit]"""
    engine = _get_engine()
    limit = int(args[0]) if args and args[0].isdigit() else 10
    history = engine.get_execution_history(limit=limit)
    if not history:
        return "No execution history."
    lines = [f"Execution History (last {len(history)}):"]
    for entry in history:
        lines.append(
            f"  [{entry['task_id'][:8]}] {entry['goal'][:60]} → {entry['status']}"
        )
    return "\n".join(lines)
