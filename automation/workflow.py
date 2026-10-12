"""
Workflow definitions and DAG mechanics (Master 13 Phases 18-21, 24-25).

A workflow attaches to an automation record as::

    "workflow": {
        "steps": [
            {"id": "research", "prompt": "Research X",
             "depends_on": [], "max_turns": 30},
            {"id": "verify",   "prompt": "Verify findings",
             "depends_on": ["research"]},
            {"id": "report",   "prompt": "Write the report",
             "depends_on": ["research"],
             "condition": [{"path": "steps.research.status",
                            "op": "eq", "value": "done"}]},
            {"id": "publish",  "prompt": "Publish",
             "depends_on": ["report"], "approval_required": true}
        ],
        "concurrency": 2,
        "on_failure": "stop"
    }

Versioning (Phase 19): runs snapshot ``definition_version`` at start; edits
bump it via the standard watched-field mechanism, so in-flight runs keep
executing their starting version while new dispatches pick up the new one.

Branching conditions reuse the trigger filter operator set — structured
comparisons only, never code execution.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

FAILURE_POLICIES = ("stop", "skip", "continue", "pause")
ON_FAILURE_STEP = ("stop", "skip", "continue")
MAX_STEPS = 32
MAX_OUTPUT_CONTEXT_CHARS = 8000


def normalize_workflow(value: Any) -> Optional[Dict[str, Any]]:
    """Validate + canonicalize a workflow spec. None/empty → None."""
    if value is None or value == "" or value == {}:
        return None
    if not isinstance(value, dict):
        raise ValueError("workflow must be a mapping")
    raw_steps = value.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("workflow.steps must be a non-empty list")
    if len(raw_steps) > MAX_STEPS:
        raise ValueError(f"workflow supports at most {MAX_STEPS} steps")

    steps: List[Dict[str, Any]] = []
    seen: set = set()
    for raw in raw_steps[:MAX_STEPS]:
        if not isinstance(raw, dict):
            raise ValueError("each workflow step must be a mapping")
        sid = str(raw.get("id") or "").strip()
        prompt = str(raw.get("prompt") or "").strip()
        script = str(raw.get("script") or "").strip() or None
        if not sid or any(ch.isspace() for ch in sid):
            raise ValueError(f"Invalid step id {raw.get('id')!r}")
        if sid in seen:
            raise ValueError(f"Duplicate step id {sid!r}")
        if not prompt and not script:
            raise ValueError(f"Step {sid!r} needs a prompt or a script")
        deps_raw = raw.get("depends_on") or []
        if isinstance(deps_raw, str):
            deps_raw = [d.strip() for d in deps_raw.split(",") if d.strip()]
        deps: List[str] = []
        for dep in deps_raw:
            dep_text = str(dep).strip()
            if dep_text == sid:
                raise ValueError(f"Step {sid!r} cannot depend on itself")
            if dep_text and dep_text not in deps:
                deps.append(dep_text)
        condition = _normalize_condition(raw.get("condition"))
        on_failure = str(raw.get("on_failure") or "stop").strip().lower()
        if on_failure not in ON_FAILURE_STEP:
            raise ValueError(
                f"step.on_failure {on_failure!r} unsupported; "
                f"allowed: {', '.join(ON_FAILURE_STEP)}"
            )
        max_turns = raw.get("max_turns")
        if max_turns not in (None, ""):
            try:
                max_turns = int(max_turns)
            except (TypeError, ValueError):
                raise ValueError(
                    f"step.max_turns for {sid!r} must be an integer"
                ) from None
            if max_turns <= 0:
                raise ValueError(f"step.max_turns for {sid!r} must be positive")
        else:
            max_turns = None
        attempts = raw.get("attempts")
        if attempts in (None, ""):
            attempts = 1
        else:
            try:
                attempts = int(attempts)
            except (TypeError, ValueError):
                raise ValueError(f"step.attempts for {sid!r} must be an integer") from None
            if attempts < 1 or attempts > 10:
                raise ValueError(f"step.attempts for {sid!r} must be 1..10")
        steps.append({
            "id": sid,
            "prompt": prompt,
            "script": script,
            "depends_on": deps,
            "condition": condition,
            "approval_required": bool(raw.get("approval_required", False)),
            "max_turns": max_turns,
            "attempts": attempts,
            "on_failure": on_failure,
        })
        seen.add(sid)

    unknown = {
        dep for step in steps for dep in step["depends_on"]
    } - seen
    if unknown:
        raise ValueError(
            f"Unknown dependency/ies: {', '.join(sorted(unknown))}"
        )
    order = topo_order(steps)
    concurrency_raw = value.get("concurrency", 1)
    try:
        concurrency = int(concurrency_raw)
    except (TypeError, ValueError):
        raise ValueError("workflow.concurrency must be an integer") from None
    if concurrency < 1 or concurrency > 4:
        raise ValueError("workflow.concurrency must be 1..4")
    on_fail = str(value.get("on_failure") or "stop").strip().lower()
    if on_fail not in FAILURE_POLICIES:
        raise ValueError(
            f"workflow.on_failure {on_fail!r} unsupported; "
            f"allowed: {', '.join(FAILURE_POLICIES)}"
        )
    return {
        "steps": steps,
        "order": order,
        "concurrency": concurrency,
        "on_failure": on_fail,
    }


def _normalize_condition(raw: Any) -> List[Dict[str, Any]]:
    if raw in (None, "", []):
        return []
    from automation.triggers import _normalize_filters

    return _normalize_filters(raw)


def topo_order(steps: List[Dict[str, Any]]) -> List[str]:
    """Kahn topological sort; raises ValueError on cycles."""
    by_id = {s["id"]: s for s in steps}
    indegree = {s["id"]: len(s["depends_on"]) for s in steps}
    children: Dict[str, List[str]] = {s["id"]: [] for s in steps}
    for step in steps:
        for dep in step["depends_on"]:
            children[dep].append(step["id"])
    queue = sorted([sid for sid, deg in indegree.items() if deg == 0])
    order: List[str] = []
    while queue:
        sid = queue.pop(0)
        order.append(sid)
        for child in children[sid]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
        queue.sort()
    if len(order) != len(steps):
        stuck = sorted(set(indegree) - set(order))
        raise ValueError(f"workflow contains a dependency cycle involving: {', '.join(stuck)}")
    return order


def ready_steps(run_steps: Dict[str, Dict[str, Any]], workflow: Dict[str, Any]) -> List[str]:
    """Pending steps whose dependencies are all done and conditions pass."""
    results = _results_view(run_steps)
    ready: List[str] = []
    for step in workflow["steps"]:
        state = run_steps.get(step["id"])
        if not state or state.get("status") != "pending":
            continue
        if any(
            run_steps.get(dep, {}).get("status") != "done"
            for dep in step["depends_on"]
        ):
            continue
        if not evaluate_condition(step.get("condition"), results):
            # Condition false → branch not taken; mark skipped (Phase 21).
            state["status"] = "skipped"
            state["skip_reason"] = "condition not met"
            logger.info("Step '%s' skipped: condition not met", step["id"])
            continue
        ready.append(step["id"])
    return ready


def evaluate_condition(condition: List[Dict[str, Any]], results: Dict[str, Any]) -> bool:
    """Evaluate structured step conditions against upstream step results."""
    if not condition:
        return True
    scope = {"steps": results}
    from automation.triggers import resolve_path

    for flt in condition:
        path = flt["path"]
        if not path.startswith("steps."):
            path = f"steps.{path}"
        found, value = resolve_path(scope, path)
        op = flt["op"]
        expected = flt.get("value")
        if op == "exists":
            ok = found
        elif not found:
            ok = False
        elif op == "eq":
            ok = value == expected
        elif op == "ne":
            ok = value != expected
        elif op == "in":
            candidates = expected if isinstance(expected, (list, tuple, set)) else [expected]
            ok = value in candidates
        elif op == "prefix":
            ok = (
                isinstance(value, str)
                and isinstance(expected, str)
                and value.startswith(expected)
            )
        else:
            ok = False
        if not ok:
            return False
    return True


def _results_view(run_steps: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    view: Dict[str, Any] = {}
    for sid, state in run_steps.items():
        view[sid] = {
            "status": state.get("status"),
            "output": str(state.get("output") or ""),
            "error": str(state.get("error") or ""),
        }
    return view


def build_step_prompt(step: Dict[str, Any], run_steps: Dict[str, Dict[str, Any]]) -> str:
    """Compose a step prompt with upstream outputs injected as context."""
    parts: List[str] = [step["prompt"]]
    for dep in step["depends_on"]:
        state = run_steps.get(dep) or {}
        output = str(state.get("output") or "").strip()
        if not output:
            continue
        if len(output) > MAX_OUTPUT_CONTEXT_CHARS:
            output = output[:MAX_OUTPUT_CONTEXT_CHARS] + "\n\n[... truncated ...]"
        parts.append(
            f"\n## Output from step '{dep}'\n"
            "Use it as context for your work.\n\n"
            f"```\n{output}\n```"
        )
    return "\n".join(parts)


def describe_workflow(workflow: Optional[Dict[str, Any]]) -> str:
    if not isinstance(workflow, dict) or not workflow.get("steps"):
        return "(single-prompt automation)"
    lines = ["workflow:"]
    for sid in workflow.get("order") or [s["id"] for s in workflow["steps"]]:
        step = next(s for s in workflow["steps"] if s["id"] == sid)
        flags = []
        if step["approval_required"]:
            flags.append("approval")
        if step["on_failure"] != "stop":
            flags.append(f"on_failure={step['on_failure']}")
        suffix = f" [{', '.join(flags)}]" if flags else ""
        deps = f" <- {','.join(step['depends_on'])}" if step["depends_on"] else ""
        label = step["prompt"][:60] if step["prompt"] else f"script:{step['script']}"
        lines.append(f"  {sid}: {label}{suffix}{deps}")
    if (workflow.get("concurrency") or 1) > 1:
        lines.append(f"  parallel up to {workflow['concurrency']}")
    return "\n".join(lines)
