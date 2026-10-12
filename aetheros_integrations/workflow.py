"""AetherOS Integrations — Workflow Builder and Engine.

Programmatic + declarative (dict) workflow definition with steps that call
provider tools, sub-agents, HTTP endpoints, conditions, loops, transforms,
and human-approval gates. A ``WorkflowEngine`` executes definitions against
an ``IntegrationManager`` and an optional agent-call resolver.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_integrations.events import EventBus
from aetheros_integrations.models import WorkflowDefinition, WorkflowRun, WorkflowStep
from aetheros_integrations.monitoring import Monitor
from aetheros_integrations.security import AuditLog, redact_sensitive_text

logger = logging.getLogger(__name__)


class WorkflowBuilder:
    """Fluent builder for workflow definitions."""

    def __init__(self, name: str = "", description: str = ""):
        self._def = WorkflowDefinition(name=name, description=description)
        self._step_ids: set = set()

    def trigger(self, trigger: str, trigger_type: str = "event") -> "WorkflowBuilder":
        self._def.trigger = trigger
        self._def.trigger_type = trigger_type
        return self

    def variables(self, variables: Dict[str, Any]) -> "WorkflowBuilder":
        self._def.variables.update(variables)
        return self

    def step(
        self,
        type_: str,
        name: str,
        *,
        provider: str = "",
        action: str = "",
        params: Optional[Dict[str, Any]] = None,
        next: Optional[List[str]] = None,
        condition: Optional[str] = None,
        loop_over: str = "",
        on_error: str = "fail",
    ) -> "WorkflowBuilder":
        step = WorkflowStep(
            id=_uniq(name, self._step_ids),
            type=type_,
            name=name,
            provider=provider,
            action=action,
            params=params or {},
            next=next or [],
            condition=condition,
            loop_over=loop_over,
            on_error=on_error,
        )
        self._step_ids.add(step.id)
        self._def.steps.append(step)
        return self

    def build(self) -> WorkflowDefinition:
        return self._def


def _uniq(name: str, used: set) -> str:
    base = name.lower().replace(" ", "_").replace("-", "_") or "step"
    candidate = base
    i = 1
    while candidate in used:
        candidate = f"{base}_{i}"
        i += 1
    return candidate


class StepExecutor:
    """Executes a single workflow step against providers or local ops."""

    def __init__(
        self,
        manager,
        *,
        agent_caller: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        http: Any = None,
        event_bus: Optional[EventBus] = None,
        dirpath=None,
    ):
        self._manager = manager
        self._agent_caller = agent_caller
        self._event_bus = event_bus
        self._dirpath = dirpath
        import httpx

        self._http = http or httpx.Client(timeout=30.0)

    def close(self) -> None:
        try:
            self._http.close()
        except Exception:  # noqa: BLE001
            pass

    def execute(self, step: WorkflowStep, ctx: Dict[str, Any]) -> Any:
        step_type = step.type
        if step_type == "condition":
            return self._eval_condition(step, ctx)
        if step_type == "loop":
            return self._run_loop(step, ctx)
        if step_type == "transform":
            return self._transform(step, ctx)
        if step_type == "wait":
            return {"waited_s": step.params.get("seconds", 0)}
        if step_type == "approval":
            return {"requires_approval": True, "approval_key": step.params.get("approval_key", "")}
        if step_type == "notify":
            return self._notify(step, ctx)
        if step_type == "http":
            return self._http_call(step, ctx)
        if step_type == "agent":
            return self._agent_call(step, ctx)
        if step_type == "tool":
            return self._tool_call(step, ctx)
        if step_type == "memory":
            return self._store_memory(step, ctx)
        raise ValueError(f"Unknown step type: {step_type}")

    def _tool_call(self, step: WorkflowStep, ctx: Dict[str, Any]) -> Any:
        if not step.provider:
            raise ValueError(f"tool step '{step.name}' has no provider")
        integration_id = step.params.get("integration_id", "")
        provider = self._manager.get_provider(integration_id)
        action = step.action or "send_message"
        method = getattr(provider, action, None)
        if method is None:
            raise NotImplementedError(f"provider {step.provider} has no action {action}")
        args = _interpolate(step.params.get("args", {}), ctx)
        result = method(**args)
        return result

    def _agent_call(self, step: WorkflowStep, ctx: Dict[str, Any]) -> Any:
        if self._agent_caller is None:
            raise RuntimeError("No agent caller installed on workflow engine")
        return self._agent_caller(step.params.get("prompt", ""), _interpolate(step.params.get("input", {}), ctx))

    def _http_call(self, step: WorkflowStep, ctx: Dict[str, Any]) -> Any:
        method = step.params.get("method", "GET").upper()
        url = _interpolate_str(str(step.params.get("url", "")), ctx)
        headers = _interpolate(step.params.get("headers", {}), ctx)
        body = step.params.get("body")
        resp = self._http.request(method, url, headers=headers, json=body)
        try:
            data = resp.json()
        except (ValueError, json.JSONDecodeError):
            data = resp.text[:2000]
        return {"status": resp.status_code, "data": data}

    def _notify(self, step: WorkflowStep, ctx: Dict[str, Any]) -> Any:
        integration_id = step.params.get("integration_id", "")
        channel = step.params.get("channel", "")
        message = _interpolate_str(str(step.params.get("message", "")), ctx)
        provider = self._manager.get_provider(integration_id)
        return provider.send_message(channel=channel, text=message)

    def _store_memory(self, step: WorkflowStep, ctx: Dict[str, Any]) -> Any:
        from aetheros_integrations.context import IntegrationMemory

        content = _interpolate_str(str(step.params.get("content", "")), ctx)
        key = step.params.get("key", "")
        memory = IntegrationMemory(dirpath=self._dirpath)
        return memory.store(key=key, content=content, source=step.params.get("source", "workflow"))

    def _eval_condition(self, step: WorkflowStep, ctx: Dict[str, Any]) -> Dict[str, Any]:
        expr = step.condition or step.params.get("expression", "")
        result = _eval_expr(expr, ctx)
        return {"result": bool(result), "expression": expr, "value": result}

    def _run_loop(self, step: WorkflowStep, ctx: Dict[str, Any]) -> Dict[str, Any]:
        iterable = ctx.get(step.loop_over or step.params.get("over", ""), [])
        results = []
        for i, item in enumerate(iterable or []):
            item_ctx = {**ctx, "_loop_index": i, "_loop_item": item}
            results.append(item_ctx)
        return {"iterations": len(results), "items": results}

    def _transform(self, step: WorkflowStep, ctx: Dict[str, Any]) -> Dict[str, Any]:
        expr = step.params.get("expression", "")
        return {"value": _eval_expr(expr, ctx)}


class WorkflowEngine:
    """Executes workflow definitions. Deterministic, auditable, resumable."""

    def __init__(
        self,
        manager,
        *,
        agent_caller: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        event_bus: Optional[EventBus] = None,
        monitor: Optional["Monitor"] = None,
        audit: Optional[AuditLog] = None,
        approval_resolver: Optional[Callable[[WorkflowRun, str], bool]] = None,
        dirpath=None,
    ):
        self._manager = manager
        self._event_bus = event_bus or EventBus(dirpath=dirpath)
        self._monitor = monitor
        self._audit = audit
        self._approval_resolver = approval_resolver
        self._executor = StepExecutor(manager, agent_caller=agent_caller, event_bus=event_bus, dirpath=dirpath)
        self._lock = threading.RLock()
        self._runs: Dict[str, WorkflowRun] = {}
        self._steps: Dict[str, WorkflowStep] = {}
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._event_bus.subscribe("*", self._on_event)

    def close(self) -> None:
        self._executor.close()

    def set_approval_resolver(self, resolver: Callable[[WorkflowRun, str], bool]) -> None:
        self._approval_resolver = resolver

    # -- registration -----------------------------------------------------

    def register(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        by_id: Dict[str, WorkflowStep] = {}
        for step in definition.steps:
            if not step.id:
                raise ValueError(f"workflow step missing id: {step.name}")
            by_id[step.id] = step
        with self._lock:
            self._workflows[definition.id] = definition
            self._steps.update(by_id)
        if definition.trigger_type == "event":
            self._event_bus.subscribe(definition.trigger, self._make_trigger_handler(definition.id))
        return definition

    def unregister(self, workflow_id: str) -> bool:
        with self._lock:
            if workflow_id in self._workflows:
                del self._workflows[workflow_id]
                return True
        return False

    def list_workflows(self) -> List[WorkflowDefinition]:
        with self._lock:
            return list(self._workflows.values())

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition:
        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"No workflow {workflow_id}")
            return self._workflows[workflow_id]

    # -- triggering -------------------------------------------------------

    def trigger(self, workflow_id: str, variables: Optional[Dict[str, Any]] = None) -> WorkflowRun:
        wf = self.get_workflow(workflow_id)
        run = WorkflowRun(
            workflow_id=wf.id,
            workflow_name=wf.name,
            variables={**wf.variables, **(variables or {})},
        )
        with self._lock:
            self._runs[run.id] = run
        try:
            self._run(run, wf)
        finally:
            pass
        return run

    def _make_trigger_handler(self, workflow_id: str):
        def handler(envelope):
            self.trigger(workflow_id, {"_event": envelope.to_dict()})

        return handler

    def _on_event(self, envelope) -> None:
        pass  # used to keep EventBus ref alive; per-workflow triggers handle routing

    # -- execution --------------------------------------------------------

    def _run(self, run: WorkflowRun, wf: WorkflowDefinition) -> None:
        started = time.perf_counter()
        try:
            for step in wf.steps:
                run.current_step = step.id
                result = self._execute_step(run, step)
                run.step_results.append({"step": step.id, "type": step.type, "result": _sanitize(result)})
                if step.type == "approval":
                    run.approval_required = True
                    run.status = "awaiting_approval"
                    approved = self._resolve_approval(run, step.params.get("approval_key", ""))
                    run.approval_required = False
                    if not approved:
                        run.status = "cancelled"
                        run.finished_at = time.time()
                        self._emit_workflow_event(run, "cancelled")
                        return
                if step.type == "condition" and result.get("result") is False:
                    break
            run.status = "success"
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.error = str(exc)
            logger.warning("Workflow %s failed: %s", run.workflow_id, exc)
        finally:
            run.finished_at = time.time()
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            if self._monitor:
                self._monitor.record(run.workflow_id, "workflow_latency_ms", latency_ms, extra={"run": run.id, "status": run.status})
                self._monitor.record(run.workflow_id, "workflow_status", 1.0 if run.status == "success" else 0.0, extra={"status": run.status})
            if self._audit:
                self._audit.record("workflow.completed", target=run.workflow_id, detail={"run": run.id, "status": run.status, "latency_ms": latency_ms})
            self._emit_workflow_event(run, run.status)

    def _execute_step(self, run: WorkflowRun, step: WorkflowStep) -> Any:
        started = time.perf_counter()
        try:
            result = self._executor.execute(step, run.variables)
            if self._monitor:
                self._monitor.record(run.workflow_id, f"step_{step.id}_ms", round((time.perf_counter() - started) * 1000, 2))
            return result
        except Exception as exc:  # noqa: BLE001
            if step.on_error == "continue":
                return {"error": str(exc)}
            if step.on_error == "retry":
                return self._execute_step(run, step)
            raise

    def _resolve_approval(self, run: WorkflowRun, key: str) -> bool:
        if self._approval_resolver is not None:
            return self._approval_resolver(run, key)
        return False  # deny by default

    def _emit_workflow_event(self, run: WorkflowRun, status: str) -> None:
        if self._event_bus:
            self._event_bus.publish(
                "workflow.completed",
                {"run_id": run.id, "workflow_id": run.workflow_id, "status": status},
                kind="workflow",
                source="workflow_engine",
                dedup_key=f"wf-run:{run.id}:{status}",
            )

    # -- introspection ----------------------------------------------------

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self, workflow_id: str = "", limit: int = 50) -> List[WorkflowRun]:
        with self._lock:
            items = list(self._runs.values())
        if workflow_id:
            items = [r for r in items if r.workflow_id == workflow_id]
        items.sort(key=lambda r: r.started_at, reverse=True)
        return items[:limit]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _interpolate(data: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _resolve_value(v, ctx) for k, v in data.items()}


def _interpolate_str(text: str, ctx: Dict[str, Any]) -> str:
    out = text
    for k, v in ctx.items():
        if isinstance(v, (str, int, float)):
            out = out.replace("{{" + k + "}}", str(v))
    return out


def _resolve_value(value: Any, ctx: Dict[str, Any]) -> Any:
    if isinstance(value, str) and "{{" in value:
        return _interpolate_str(value, ctx)
    if isinstance(value, dict):
        return _interpolate(value, ctx)
    if isinstance(value, list):
        return [_resolve_value(v, ctx) for v in value]
    return value


def _eval_expr(expr: str, ctx: Dict[str, Any]) -> Any:
    """Tiny safe expression evaluator: supports `x == y`, `x != y`, `x in y`, truthiness of ctx keys."""
    expr = expr.strip()
    if not expr:
        return True
    for op in ("==", "!=", " in ", " not in "):
        if op in expr:
            left, right = expr.split(op, 1)
            lv = _lookup(left.strip(), ctx)
            rv = _lookup(right.strip(), ctx)
            if op == "==":
                return lv == rv
            if op == "!=":
                return lv != rv
            if op == " in ":
                return lv in (rv if isinstance(rv, (list, dict, str)) else str(rv))
            if op == " not in ":
                return lv not in (rv if isinstance(rv, (list, dict, str)) else str(rv))
    return bool(_lookup(expr, ctx))


def _lookup(key: str, ctx: Dict[str, Any]) -> Any:
    key = key.strip()
    if key.startswith('"') and key.endswith('"'):
        return key[1:-1]
    parts = [p for p in key.split(".") if p]
    cur: Any = ctx
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p, None)
        else:
            return None
    return cur


def _sanitize(value: Any) -> Any:
    """Recursively redact sensitive string shapes for run logs."""
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value
