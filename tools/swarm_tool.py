"""Swarm agent tools (Master 42 section 29): orchestrated multi-agent runs.

Narrow, audited operations over a process-singleton MultiAgentOrchestrator
backed by LocalFunctionExecutor-safe defaults. Real LLM execution is
available per-task through DelegateExecutor when the caller opts in.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Dict

from tools.registry import registry

_lock = threading.Lock()
_orch = None


def _orch():
    global _orch
    with _lock:
        if _orch is None:
            from aetheros_swarm.orchestrator import MultiAgentOrchestrator
            _orch = MultiAgentOrchestrator()
        return _orch


def _ok(**kw: Any) -> str:
    return json.dumps(kw, ensure_ascii=False)


def _run_view(run) -> Dict[str, Any]:
    return {
        "run_id": run.run_id, "goal": run.goal, "status": run.status,
        "topology": run.decision.topology.value if run.decision else "",
        "mode": run.decision.mode if run.decision else "",
        "roles": run.decision.roles if run.decision else [],
        "tasks": [{"id": t.id, "goal": t.goal, "state": t.state.value,
                   "role": t.required_role, "agent": t.assigned_agent,
                   "deps": t.dependencies} for t in run.tasks],
        "agents": [{"id": a.id, "role": a.role, "status": a.status.value,
                    "tools": a.tools} for a in run.agents.values()],
        "final": run.final.to_dict() if run.final else None,
    }


def swarm_start(args: Dict[str, Any], **kw: Any) -> str:
    orch = _orch()
    run = orch.plan(args.get("goal", ""), force_single=bool(args.get("force_single", False)),
                    project_id=args.get("project_id", ""))
    if args.get("execute", True):
        orch.run(run)
    return _ok(success=True, **_run_view(run))


def swarm_status(args: Dict[str, Any], **kw: Any) -> str:
    run = _orch().get_run(args.get("run_id", ""))
    if run is None:
        return _ok(success=False, error="run not found")
    return _ok(success=True, **_run_view(run))


def swarm_stop(args: Dict[str, Any], **kw: Any) -> str:
    ok = _orch().stop(args.get("run_id", ""))
    return _ok(success=ok)


def swarm_pause(args: Dict[str, Any], **kw: Any) -> str:
    ok = _orch().pause(args.get("run_id", ""))
    return _ok(success=ok)


def swarm_resume(args: Dict[str, Any], **kw: Any) -> str:
    run = _orch().resume(args.get("run_id", ""))
    if run is None:
        return _ok(success=False, error="run not found or no checkpoint")
    return _ok(success=True, **_run_view(run))


def swarm_approve(args: Dict[str, Any], **kw: Any) -> str:
    ok = _orch().approvals.resolve(args.get("request_id", ""),
                                   bool(args.get("approved", True)))
    return _ok(success=ok)


def swarm_events(args: Dict[str, Any], **kw: Any) -> str:
    run = _orch().get_run(args.get("run_id", ""))
    if run is None:
        return _ok(success=False, error="run not found")
    evts = _orch().events.for_run(run.run_id, after_seq=int(args.get("after_seq", 0) or 0))
    return _ok(success=True, events=[{"seq": e.seq, "kind": e.kind, "task_id": e.task_id,
                                      "agent_id": e.agent_id, "at": e.timestamp,
                                      "detail": e.detail} for e in evts])


def swarm_trace(args: Dict[str, Any], **kw: Any) -> str:
    trace = _orch().tracer.trace_tree(args.get("run_id", ""))
    return _ok(success=True, trace=trace)


def _check() -> bool:
    return True


_COMMON = {"type": "object", "properties": {}, "additionalProperties": True}

registry.register(
    name="swarm_start", toolset="swarm",
    schema={"name": "swarm_start", "description": "Plan (and by default execute) a multi-agent swarm run for a goal. Set force_single to use one agent.",
            "parameters": {"type": "object", "properties": {
                "goal": {"type": "string"}, "force_single": {"type": "boolean"},
                "execute": {"type": "boolean"}, "project_id": {"type": "string"}},
                "required": ["goal"]}},
    handler=lambda args, **k: swarm_start(args, **k), check_fn=_check)

registry.register(
    name="swarm_status", toolset="swarm",
    schema={"name": "swarm_status", "description": "Get live run state: tasks, agents, final result.",
            "parameters": {"type": "object", "properties": {"run_id": {"type": "string"}},
                           "required": ["run_id"]}},
    handler=lambda args, **k: swarm_status(args, **k), check_fn=_check)

registry.register(
    name="swarm_stop", toolset="swarm",
    schema={"name": "swarm_stop", "description": "Cancel a run; cancellation propagates to all agents.",
            "parameters": {"type": "object", "properties": {"run_id": {"type": "string"}},
                           "required": ["run_id"]}},
    handler=lambda args, **k: swarm_stop(args, **k), check_fn=_check)

registry.register(
    name="swarm_pause", toolset="swarm",
    schema={"name": "swarm_pause", "description": "Pause a run and persist a checkpoint.",
            "parameters": {"type": "object", "properties": {"run_id": {"type": "string"}},
                           "required": ["run_id"]}},
    handler=lambda args, **k: swarm_pause(args, **k), check_fn=_check)

registry.register(
    name="swarm_resume", toolset="swarm",
    schema={"name": "swarm_resume", "description": "Resume a run from its checkpoint without restarting verified work.",
            "parameters": {"type": "object", "properties": {"run_id": {"type": "string"}},
                           "required": ["run_id"]}},
    handler=lambda args, **k: swarm_resume(args, **k), check_fn=_check)

registry.register(
    name="swarm_approve", toolset="swarm",
    schema={"name": "swarm_approve", "description": "Approve or reject a pending swarm approval request.",
            "parameters": {"type": "object", "properties": {
                "request_id": {"type": "string"}, "approved": {"type": "boolean"}},
                "required": ["request_id"]}},
    handler=lambda args, **k: swarm_approve(args, **k), check_fn=_check)

registry.register(
    name="swarm_events", toolset="swarm",
    schema={"name": "swarm_events", "description": "Sequenced run events for live UI/trace (after_seq for polling).",
            "parameters": {"type": "object", "properties": {
                "run_id": {"type": "string"}, "after_seq": {"type": "integer"}},
                "required": ["run_id"]}},
    handler=lambda args, **k: swarm_events(args, **k), check_fn=_check)

registry.register(
    name="swarm_trace", toolset="swarm",
    schema={"name": "swarm_trace", "description": "Execution trace tree with tokens/cost/duration per span.",
            "parameters": {"type": "object", "properties": {"run_id": {"type": "string"}},
                           "required": ["run_id"]}},
    handler=lambda args, **k: swarm_trace(args, **k), check_fn=_check)
