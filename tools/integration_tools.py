#!/usr/bin/env python3
"""
Integration Tools Module

Agent-facing tools that let the model operate the Enterprise Integration
Platform: list/install integrations, run provider actions, send webhooks,
and trigger workflows. All are service-gated on the integrations platform
being importable; provider health and credentials are reported honestly.
"""

import json
import logging
from typing import Any, Awaitable, Dict

from tools.registry import registry

logger = logging.getLogger(__name__)


def _json_ok(data: Dict[str, Any]) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)


def _check_integrations_available() -> bool:
    try:
        import aetheros_integrations  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _get_platform():
    from aetheros_integrations import get_platform

    return get_platform()


INTEGRATION_LIST_SCHEMA = {
    "name": "integration_list",
    "description": "List installed integrations and their health status.",
    "parameters": {
        "type": "object",
        "properties": {
            "provider": {"type": "string", "description": "Optional provider key filter (e.g. github)."},
        },
        "required": [],
    },
}


def _handle_integration_list(args: Dict[str, Any], **kw: Any) -> str:
    provider = str(args.get("provider") or "").strip() or None
    try:
        platform = _get_platform()
        instances = [i.to_dict() for i in platform.manager.list(provider_key=provider)]
        checks = {c["integration_id"]: c.get("health") for c in platform.manager.health_all()}
        for inst in instances:
            inst["health"] = checks.get(inst["id"], "unknown")
        return _json_ok({"success": True, "instances": instances, "count": len(instances)})
    except Exception as exc:  # noqa: BLE001
        return _json_ok({"success": False, "error": str(exc)})


INTEGRATION_PROVIDERS_SCHEMA = {
    "name": "integration_providers",
    "description": "List available integration providers (messaging, email, calendar, storage, devops, knowledge, productivity, crm, database).",
    "parameters": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Optional category filter."},
        },
        "required": [],
    },
}


def _handle_integration_providers(args: Dict[str, Any], **kw: Any) -> str:
    category = str(args.get("category") or "").strip() or None
    try:
        platform = _get_platform()
        providers = platform.manager.list_providers(category)
        return _json_ok({"success": True, "providers": providers, "count": len(providers)})
    except Exception as exc:  # noqa: BLE001
        return _json_ok({"success": False, "error": str(exc)})


INTEGRATION_RUN_SCHEMA = {
    "name": "integration_run",
    "description": "Run a provider action on an installed integration, e.g. send a Telegram message, create a GitHub issue, or save a note to a local vault.",
    "parameters": {
        "type": "object",
        "properties": {
            "integration_id": {"type": "string", "description": "ID of the installed integration."},
            "action": {"type": "string", "description": "Provider method name, e.g. send_message, create_issue, create_record, run_query."},
            "args": {"type": "object", "description": "Keyword arguments for the action."},
        },
        "required": ["integration_id", "action"],
    },
}


def _handle_integration_run(args: Dict[str, Any], **kw: Any) -> str:
    integration_id = str(args.get("integration_id") or "").strip()
    action = str(args.get("action") or "").strip()
    call_args = args.get("args") or {}
    if not integration_id or not action:
        return _json_ok({"success": False, "error": "integration_id and action required"})
    try:
        platform = _get_platform()
        provider = platform.manager.get_provider(integration_id)
        method = getattr(provider, action, None)
        if method is None:
            return _json_ok({"success": False, "error": f"action {action} not supported by this provider"})
        result = method(**call_args)
        return _json_ok({"success": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _json_ok({"success": False, "error": str(exc)})


INTEGRATION_WEBHOOK_SCHEMA = {
    "name": "integration_webhook",
    "description": "Send a signed outgoing webhook (with retry, backoff, and dedup).",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Destination URL."},
            "event": {"type": "string", "description": "Event name, e.g. notify.new_issue."},
            "payload": {"type": "object", "description": "JSON payload."},
        },
        "required": ["url"],
    },
}


def _handle_integration_webhook(args: Dict[str, Any], **kw: Any) -> str:
    url = str(args.get("url") or "").strip()
    event = str(args.get("event") or "").strip()
    payload = args.get("payload") or {}
    if not url:
        return _json_ok({"success": False, "error": "url required"})
    try:
        platform = _get_platform()
        delivery = platform.webhooks.deliver(url, payload, event=event)
        return _json_ok({"success": True, "delivery": delivery.to_dict()})
    except Exception as exc:  # noqa: BLE001
        return _json_ok({"success": False, "error": str(exc)})


INTEGRATION_WORKFLOW_SCHEMA = {
    "name": "integration_workflow",
    "description": "Register and run a workflow definition. The definition must have: name, trigger_type ('manual' or 'event'), trigger, steps[] with id/type/name and params.",
    "parameters": {
        "type": "object",
        "properties": {
            "definition": {"type": "object", "description": "WorkflowDefinition-compatible dict."},
            "variables": {"type": "object", "description": "Variables injected into the run."},
        },
        "required": ["definition"],
    },
}


def _handle_integration_workflow(args: Dict[str, Any], **kw: Any) -> str:
    definition = args.get("definition") or {}
    variables = args.get("variables") or {}
    if not definition:
        return _json_ok({"success": False, "error": "definition required"})
    try:
        from aetheros_integrations.models import WorkflowDefinition

        platform = _get_platform()
        wf = WorkflowDefinition(**definition)
        platform.workflow_engine.register(wf)
        run = platform.workflow_engine.trigger(wf.id, variables)
        return _json_ok({"success": True, "run": run.to_dict()})
    except Exception as exc:  # noqa: BLE001
        return _json_ok({"success": False, "error": str(exc)})


registry.register(
    name="integration_list",
    toolset="integration",
    schema=INTEGRATION_LIST_SCHEMA,
    handler=_handle_integration_list,
    check_fn=_check_integrations_available,
    emoji="🧩",
)

registry.register(
    name="integration_providers",
    toolset="integration",
    schema=INTEGRATION_PROVIDERS_SCHEMA,
    handler=_handle_integration_providers,
    check_fn=_check_integrations_available,
    emoji="🗂️",
)

registry.register(
    name="integration_run",
    toolset="integration",
    schema=INTEGRATION_RUN_SCHEMA,
    handler=_handle_integration_run,
    check_fn=_check_integrations_available,
    emoji="⚡",
)

registry.register(
    name="integration_webhook",
    toolset="integration",
    schema=INTEGRATION_WEBHOOK_SCHEMA,
    handler=_handle_integration_webhook,
    check_fn=_check_integrations_available,
    emoji="🔗",
)

registry.register(
    name="integration_workflow",
    toolset="integration",
    schema=INTEGRATION_WORKFLOW_SCHEMA,
    handler=_handle_integration_workflow,
    check_fn=_check_integrations_available,
    emoji="🔄",
)
