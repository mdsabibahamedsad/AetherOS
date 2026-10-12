"""Web API endpoints for the browser-based agent dashboard.

Provides JSON APIs for the web UI to list, create, update, delete,
and interact with agents. Designed for the Hermes web server.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from agents.manager import AgentManager
from agents.runtime import AgentRuntime
from agents.marketplace import (
    get_marketplace_catalog, get_featured_agents, get_installed_marketplace_agents,
    install_from_marketplace, uninstall_marketplace_agent,
)
from agents.collaboration import CollaborationEngine
from agents import store

logger = logging.getLogger(__name__)

_runtime: AgentRuntime | None = None
_collab: CollaborationEngine | None = None


def init_api() -> None:
    """Initialize the agent web API."""
    global _runtime, _collab
    store.init_db()
    _runtime = AgentRuntime()
    _runtime.start()
    _collab = CollaborationEngine(runtime=_runtime)
    logger.info("Agent web API initialized")


def shutdown_api() -> None:
    """Shutdown the agent web API."""
    global _runtime
    if _runtime:
        _runtime.stop()
    logger.info("Agent web API shut down")


# ── Agent CRUD API ─────────────────────────────────────────────────


def list_agents_api() -> list[dict]:
    """GET /api/agents — list all agents."""
    mgr = AgentManager()
    return [a.to_dict() for a in mgr.list(include_disabled=True)]


def get_agent_api(agent_id: str) -> dict | None:
    """GET /api/agents/<id> — get agent details."""
    mgr = AgentManager()
    agent = mgr.get(agent_id) or mgr.get_by_name(agent_id)
    if agent:
        result = agent.to_dict()
        if _runtime:
            inst = _runtime.get_instance(agent.id)
            if inst:
                result["runtime"] = inst.to_dict()
        result["sessions"] = store.get_agent_sessions(agent.id)
        return result
    return None


def create_agent_api(data: dict) -> dict:
    """POST /api/agents — create a new agent."""
    from agents.models import AgentConfig
    config = AgentConfig.from_dict(data)
    mgr = AgentManager()
    result = mgr.create(config)
    return result.to_dict()


def update_agent_api(agent_id: str, data: dict) -> dict | None:
    """PUT /api/agents/<id> — update an agent."""
    mgr = AgentManager()
    result = mgr.update(agent_id, data)
    return result.to_dict() if result else None


def delete_agent_api(agent_id: str) -> bool:
    """DELETE /api/agents/<id> — delete an agent."""
    mgr = AgentManager()
    return mgr.delete(agent_id)


def duplicate_agent_api(agent_id: str, new_name: str = "") -> dict | None:
    """POST /api/agents/<id>/duplicate — duplicate an agent."""
    mgr = AgentManager()
    result = mgr.duplicate(agent_id, new_name)
    return result.to_dict() if result else None


# ── Agent Runtime API ──────────────────────────────────────────────


def start_agent_api(agent_id: str, goal: str = "") -> dict:
    """POST /api/agents/<id>/start — start an agent."""
    global _runtime
    if not _runtime:
        _runtime = AgentRuntime()
        _runtime.start()
    try:
        instance = _runtime.start_agent(agent_id, goal=goal)
        return {"status": "started", "session_id": instance.session_id, "agent": instance.to_dict()}
    except (ValueError, RuntimeError) as e:
        return {"status": "error", "error": str(e)}


def stop_agent_api(agent_id: str) -> dict:
    """POST /api/agents/<id>/stop — stop an agent."""
    global _runtime
    if not _runtime:
        return {"status": "error", "error": "Runtime not initialized"}
    ok = _runtime.stop_agent(agent_id)
    return {"status": "stopped" if ok else "not_found"}


def get_agent_status_api(agent_id: str) -> dict:
    """GET /api/agents/<id>/status — get agent runtime status."""
    global _runtime
    if not _runtime:
        mgr = AgentManager()
        agent = mgr.get(agent_id)
        if agent:
            return {"agent_id": agent_id, "status": agent.status, "running": False}
        return {"agent_id": agent_id, "status": "not_found", "running": False}

    instance = _runtime.get_instance(agent_id)
    if instance:
        return {"agent_id": agent_id, "status": instance.status,
                "running": instance.status == "running",
                "current_task": instance.current_task,
                "started_at": instance.started_at}
    mgr = AgentManager()
    agent = mgr.get(agent_id)
    if agent:
        return {"agent_id": agent_id, "status": agent.status, "running": False}
    return {"agent_id": agent_id, "status": "not_found", "running": False}


def list_running_agents_api() -> list[dict]:
    """GET /api/agents/running — list all running agents."""
    global _runtime
    if not _runtime:
        return []
    return [inst.to_dict() for inst in _runtime.list_running()]


def get_dashboard_stats_api() -> dict:
    """GET /api/agents/dashboard — aggregate dashboard stats."""
    mgr = AgentManager()
    agents = mgr.list(include_disabled=True)
    running = list_running_agents_api() if _runtime else []

    total_tokens = sum(a.metrics.total_tokens for a in agents)
    total_sessions = sum(a.metrics.sessions_run for a in agents)

    return {
        "total_agents": len(agents),
        "running_agents": len(running),
        "total_sessions": total_sessions,
        "total_tokens": total_tokens,
        "agents": {a.id: {"name": a.name, "status": a.status, "avatar": a.avatar.to_dict()} for a in agents},
    }


# ── Marketplace API ────────────────────────────────────────────────


def get_marketplace_api(category: str | None = None) -> list[dict]:
    """GET /api/marketplace — browse the marketplace."""
    return get_marketplace_catalog(category)


def install_marketplace_api(package_id: str) -> dict:
    """POST /api/marketplace/install — install from marketplace."""
    agent = install_from_marketplace(package_id)
    if agent:
        return {"status": "installed", "agent": agent.to_dict()}
    return {"status": "error", "error": f"Package '{package_id}' not found"}


def uninstall_marketplace_api(agent_id: str) -> dict:
    """POST /api/marketplace/uninstall — uninstall a marketplace agent."""
    ok = uninstall_marketplace_agent(agent_id)
    return {"status": "uninstalled" if ok else "error"}


def get_installed_marketplace_api() -> list[dict]:
    """GET /api/marketplace/installed — list installed packages."""
    return get_installed_marketplace_agents()


# ── Collaboration API ──────────────────────────────────────────────


def delegate_task_api(from_agent: str, to_agent: str, goal: str) -> dict:
    """POST /api/collab/delegate — delegate a task between agents."""
    global _collab
    if not _collab:
        _collab = CollaborationEngine(runtime=_runtime)
    task = _collab.delegate(from_agent, to_agent, goal)
    return task.to_dict()


def send_message_api(from_agent: str, to_agent: str, content: str) -> dict:
    """POST /api/collab/message — send a message between agents."""
    global _collab
    if not _collab:
        _collab = CollaborationEngine(runtime=_runtime)
    msg = _collab.send_message(from_agent, to_agent, content)
    return msg


def create_pipeline_api(name: str, steps: list[dict]) -> dict:
    """POST /api/collab/pipeline — create a collaboration pipeline."""
    global _collab
    if not _collab:
        _collab = CollaborationEngine(runtime=_runtime)
    pipeline = _collab.create_pipeline(name, steps)
    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "steps": [s.to_dict() for s in pipeline.steps],
        "status": pipeline.status,
    }
