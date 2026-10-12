"""Automation agent tools (Master 43): narrow audited operations over the
process-singleton AutomationService. No raw store/scheduler exposure.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Dict

from tools.registry import registry

_lock = threading.Lock()
_svc = None


def _svc_fn():
    global _svc
    with _lock:
        if _svc is None:
            from aetheros_autonomy.service import AutomationService
            _svc = AutomationService()
            _svc.initialize()
        return _svc


def _ok(**kw: Any) -> str:
    return json.dumps(kw, ensure_ascii=False)


def auto_create(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().create(args.get("definition", {}),
                                                owner=args.get("owner", "")))


def auto_preview(args: Dict[str, Any], **kw: Any) -> str:
    p = _svc_fn().preview(args.get("id", ""))
    return _ok(success=p is not None, preview=p)


def auto_enable(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=_svc_fn().enable(args.get("id", "")))


def auto_disable(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=_svc_fn().disable(args.get("id", "")))


def auto_delete(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=_svc_fn().delete(args.get("id", "")))


def auto_run(args: Dict[str, Any], **kw: Any) -> str:
    r = _svc_fn().run_now(args.get("id", ""),
                          dry_run=bool(args.get("dry_run", False)))
    return _ok(success=r is not None, run=r)


def auto_runs(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, runs=_svc_fn().runs(args.get("id", ""),
                                                 int(args.get("limit", 50) or 50)))


def auto_search(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, automations=_svc_fn().search(
        query=args.get("query", ""), status=args.get("status", ""),
        trigger=args.get("trigger", ""), project=args.get("project", "")))


def auto_build(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().build_from_text(
        args.get("text", ""), tz=args.get("timezone", "UTC")))


def auto_template(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().from_template(
        args.get("name", ""), args.get("arg", "")))


def auto_health(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().health())


def auto_stop_all(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().emergency_stop())


def _check() -> bool:
    return True


registry.register(
    name="automation_create", toolset="automation",
    schema={"name": "automation_create", "description": "Create automation (DRAFT, needs approval to activate).",
            "parameters": {"type": "object", "properties": {
                "definition": {"type": "object"}, "owner": {"type": "string"}},
                "required": ["definition"]}},
    handler=lambda args, **k: auto_create(args, **k), check_fn=_check)

registry.register(
    name="automation_preview", toolset="automation",
    schema={"name": "automation_preview", "description": "Show plan preview: trigger, actions, tools, risks, budget.",
            "parameters": {"type": "object", "properties": {"id": {"type": "string"}},
                           "required": ["id"]}},
    handler=lambda args, **k: auto_preview(args, **k), check_fn=_check)

registry.register(
    name="automation_enable", toolset="automation",
    schema={"name": "automation_enable", "description": "Activate a reviewed automation.",
            "parameters": {"type": "object", "properties": {"id": {"type": "string"}},
                           "required": ["id"]}},
    handler=lambda args, **k: auto_enable(args, **k), check_fn=_check)

registry.register(
    name="automation_disable", toolset="automation",
    schema={"name": "automation_disable", "description": "Pause/disable an automation.",
            "parameters": {"type": "object", "properties": {"id": {"type": "string"}},
                           "required": ["id"]}},
    handler=lambda args, **k: auto_disable(args, **k), check_fn=_check)

registry.register(
    name="automation_delete", toolset="automation",
    schema={"name": "automation_delete", "description": "Delete an automation definition.",
            "parameters": {"type": "object", "properties": {"id": {"type": "string"}},
                           "required": ["id"]}},
    handler=lambda args, **k: auto_delete(args, **k), check_fn=_check)

registry.register(
    name="automation_run", toolset="automation",
    schema={"name": "automation_run", "description": "Run now (dry_run shows would-do without side effects).",
            "parameters": {"type": "object", "properties": {
                "id": {"type": "string"}, "dry_run": {"type": "boolean"}},
                "required": ["id"]}},
    handler=lambda args, **k: auto_run(args, **k), check_fn=_check)

registry.register(
    name="automation_runs", toolset="automation",
    schema={"name": "automation_runs", "description": "List runs with states, durations, costs.",
            "parameters": {"type": "object", "properties": {
                "id": {"type": "string"}, "limit": {"type": "integer"}}}},
    handler=lambda args, **k: auto_runs(args, **k), check_fn=_check)

registry.register(
    name="automation_search", toolset="automation",
    schema={"name": "automation_search", "description": "Search automations by name/trigger/project/status.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"}, "status": {"type": "string"},
                "trigger": {"type": "string"}, "project": {"type": "string"}}}},
    handler=lambda args, **k: auto_search(args, **k), check_fn=_check)

registry.register(
    name="automation_build", toolset="automation",
    schema={"name": "automation_build", "description": "Build DRAFT automation from natural language + plan preview.",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string"}, "timezone": {"type": "string"}},
                "required": ["text"]}},
    handler=lambda args, **k: auto_build(args, **k), check_fn=_check)

registry.register(
    name="automation_template", toolset="automation",
    schema={"name": "automation_template", "description": "Instantiate a template (returns safety card).",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"}, "arg": {"type": "string"}},
                "required": ["name"]}},
    handler=lambda args, **k: auto_template(args, **k), check_fn=_check)

registry.register(
    name="automation_health", toolset="automation",
    schema={"name": "automation_health", "description": "Measured automation health + metrics.",
            "parameters": {"type": "object", "properties": {}}},
    handler=lambda args, **k: auto_health(args, **k), check_fn=_check)

registry.register(
    name="automation_stop_all", toolset="automation",
    schema={"name": "automation_stop_all", "description": "EMERGENCY STOP all automations.",
            "parameters": {"type": "object", "properties": {}}},
    handler=lambda args, **k: auto_stop_all(args, **k), check_fn=_check)
