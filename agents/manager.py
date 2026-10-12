"""Agent Manager — CRUD, import/export, backup/restore, and lifecycle coordination."""

from __future__ import annotations

import datetime
import json
import logging
import zipfile
from pathlib import Path
from typing import Optional

from aetheros_constants import get_aetheros_home
from agents.models import AgentConfig, AgentStatus
from agents import store

logger = logging.getLogger(__name__)


class AgentManager:
    """High-level manager for agent lifecycle.

    Wraps the store with import/export, validation, and defaults.
    """

    def __init__(self):
        store.init_db()

    # ── CRUD ────────────────────────────────────────────────────────

    def list(self, include_disabled: bool = False) -> list[AgentConfig]:
        agents = store.list_agents()
        if not include_disabled:
            agents = [a for a in agents if a.enabled]
        return agents

    def get(self, agent_id: str) -> Optional[AgentConfig]:
        return store.get_agent(agent_id)

    def get_by_name(self, name: str) -> Optional[AgentConfig]:
        return next((a for a in self.list(include_disabled=True) if a.name.lower() == name.lower()), None)

    def create(self, config: AgentConfig) -> AgentConfig:
        config.validate()
        return store.save_agent(config)

    def update(self, agent_id: str, updates: dict) -> Optional[AgentConfig]:
        agent = store.get_agent(agent_id)
        if not agent:
            return None
        for key, value in updates.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        agent.validate()
        return store.save_agent(agent)

    def delete(self, agent_id: str) -> bool:
        return store.delete_agent(agent_id)

    def duplicate(self, agent_id: str, new_name: str = "") -> Optional[AgentConfig]:
        return store.duplicate_agent(agent_id, new_name)

    def rename(self, agent_id: str, new_name: str) -> Optional[AgentConfig]:
        return self.update(agent_id, {"name": new_name})

    def set_status(self, agent_id: str, status: str) -> Optional[AgentConfig]:
        return self.update(agent_id, {"status": status})

    # ── Export / Import ─────────────────────────────────────────────

    def export_agent(self, agent_id: str, output_path: str | Path | None = None) -> str:
        agent = store.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        data = agent.to_dict()
        if output_path is None:
            output_path = Path.cwd() / f"{agent.name.replace(' ', '_')}_agent.json"
        output_path = Path(output_path)
        output_path.write_text(json.dumps(data, indent=2))
        logger.info("Exported agent '%s' to %s", agent.name, output_path)
        return str(output_path)

    def import_agent(self, source: str | Path | dict) -> AgentConfig:
        if isinstance(source, dict):
            data = source
        else:
            source = Path(source)
            data = json.loads(source.read_text())
        config = AgentConfig.from_dict(data)
        config.id = ""  # Force new ID
        config.created_at = ""
        config.updated_at = ""
        config.version = 1
        config.status = AgentStatus.IDLE.value
        config.metrics = type(config.metrics)()
        validated = config.validate()
        return store.save_agent(validated)

    def export_all(self, output_path: str | Path) -> str:
        agents = store.list_agents()
        data = {"exported_at": datetime.datetime.utcnow().isoformat() + "Z", "agents": [a.to_dict() for a in agents]}
        output_path = Path(output_path)
        output_path.write_text(json.dumps(data, indent=2))
        logger.info("Exported %d agents to %s", len(agents), output_path)
        return str(output_path)

    def import_all(self, source: str | Path) -> list[AgentConfig]:
        source = Path(source)
        data = json.loads(source.read_text())
        results = []
        for agent_data in data.get("agents", []):
            try:
                results.append(self.import_agent(agent_data))
            except Exception as e:
                logger.warning("Failed to import agent: %s", e)
        return results

    # ── Backup / Restore ────────────────────────────────────────────

    def backup(self, output_path: str | Path | None = None) -> str:
        if output_path is None:
            ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = get_aetheros_home() / "backups" / f"agents_backup_{ts}.zip"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        agents = store.list_agents()
        with zipfile.ZipFile(str(output_path), "w", zipfile.ZIP_DEFLATED) as zf:
            manifest = {"exported_at": datetime.datetime.utcnow().isoformat() + "Z", "count": len(agents)}
            for agent in agents:
                zf.writestr(f"agents/{agent.id}.json", json.dumps(agent.to_dict(), indent=2))
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        logger.info("Backup created: %s (%d agents)", output_path, len(agents))
        return str(output_path)

    def restore(self, source: str | Path) -> list[AgentConfig]:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"Backup not found: {source}")

        results = []
        with zipfile.ZipFile(str(source), "r") as zf:
            for name in zf.namelist():
                if name.startswith("agents/") and name.endswith(".json"):
                    data = json.loads(zf.read(name))
                    try:
                        results.append(self.import_agent(data))
                    except Exception as e:
                        logger.warning("Failed to restore agent %s: %e", name, e)
        logger.info("Restored %d agents from %s", len(results), source)
        return results

    def share_export(self, agent_id: str) -> str:
        agent = store.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        data = agent.to_dict()
        share_data = {
            "format": "aetheros-agent-v1",
            "name": agent.name,
            "role": agent.role,
            "personality": agent.personality,
            "description": agent.description,
            "tools": agent.tools,
            "permissions": agent.permissions,
            "prompt": agent.prompt,
            "skills": agent.skills,
            "mcp_servers": agent.mcp_servers,
            "workflows": agent.workflows,
            "temperature": agent.temperature,
            "models": agent.models,
        }
        return json.dumps(share_data, indent=2)

    # ── Session tracking ────────────────────────────────────────────

    def start_session(self, agent_id: str, session_id: str) -> None:
        store.record_session_start(agent_id, session_id)
        self.set_status(agent_id, AgentStatus.RUNNING.value)

    def end_session(self, agent_id: str, session_id: str,
                    tokens: int = 0, messages: int = 0) -> None:
        store.record_session_end(session_id, tokens, messages)
        self.set_status(agent_id, AgentStatus.IDLE.value)
        agent = store.get_agent(agent_id)
        if agent:
            agent.metrics.sessions_run += 1
            agent.metrics.total_tokens += tokens
            agent.metrics.total_messages += messages
            agent.metrics.last_run = datetime.datetime.utcnow().isoformat() + "Z"
            store.save_agent(agent)
