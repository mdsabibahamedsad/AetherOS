"""Trigger engine + condition evaluator (sections 7-8, 31).

Event -> Trigger Matcher -> Condition Evaluator -> Automation -> Run.
Conditions: IF/ELSE/AND/OR/NOT/THRESHOLD/CHANGE_DETECTED/TIME_WINDOW/
MEMORY_MATCH/TASK_STATE/RESEARCH_RESULT. Evaluated against a live context
dict supplied by the scheduler (no hidden globals).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_autonomy.models import AutomationDefinition


def eval_condition(cond: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    op = (cond.get("op") or "true").upper()
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "NOT":
        return not eval_condition(cond.get("cond", {"op": "true"}), ctx)
    if op == "AND":
        return all(eval_condition(c, ctx) for c in cond.get("conds", []))
    if op == "OR":
        return any(eval_condition(c, ctx) for c in cond.get("conds", []))
    if op == "IF":
        branch = cond.get("cond", {"op": "true"})
        if eval_condition(branch, ctx):
            return eval_condition(cond.get("then", {"op": "true"}), ctx)
        return eval_condition(cond.get("else", {"op": "true"}), ctx)
    if op == "THRESHOLD":
        try:
            return float(ctx.get(cond.get("key", ""), 0.0)) >= float(cond.get("value", 0.0))
        except (TypeError, ValueError):
            return False
    if op == "CHANGE_DETECTED":
        return ctx.get("change_class", "no_change") in cond.get("classes", ["meaningful_change",
            "major_change", "critical_change"])
    if op == "TIME_WINDOW":
        now = ctx.get("now", time.time())
        return float(cond.get("start", 0)) <= now <= float(cond.get("end", float("inf")))
    if op == "MEMORY_MATCH":
        return bool(cond.get("value", "") in str(ctx.get("memory_text", "")))
    if op == "TASK_STATE":
        return ctx.get("task_states", {}).get(cond.get("task", "")) == cond.get("state")
    if op == "RESEARCH_RESULT":
        return ctx.get("research", {}).get(cond.get("key", "")) == cond.get("value")
    if op == "EQ":
        return ctx.get(cond.get("key")) == cond.get("value")
    return False


EVENT_ALIASES = {
    "TASK_COMPLETED", "TASK_FAILED", "RESEARCH_COMPLETED", "FILE_CREATED",
    "FILE_CHANGED", "PROJECT_UPDATED", "MEMORY_UPDATED", "AGENT_COMPLETED",
    "SECURITY_EVENT", "SYSTEM_EVENT", "USER_EVENT", "SCHEDULE_DUE",
    "REPO_CHANGED", "WEB_CHANGED",
}


class TriggerEngine:
    def __init__(self, list_autos: Callable[[], List[AutomationDefinition]]) -> None:
        self._list = list_autos

    def match(self, event: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> List[AutomationDefinition]:
        """Return enabled automations whose trigger matches + conditions hold."""
        ctx = dict(ctx or {})
        ctx.setdefault("event", event)
        kind = str(event.get("kind", ""))
        out = []
        for auto in self._list():
            if not auto.enabled:
                continue
            trig = auto.trigger or {}
            if trig.get("event") and trig["event"] != kind:
                continue
            if trig.get("kind") == "schedule":
                continue  # schedules handled by Scheduler, not events
            if all(eval_condition(c, {**ctx, **event}) for c in auto.conditions):
                out.append(auto)
        return out
