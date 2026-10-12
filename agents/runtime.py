"""Multi-agent runtime — lifecycle management for concurrent AI agent execution.

Each agent runs as an isolated Hermes AIAgent instance with its own
model, tools, and permissions. The runtime manages start/stop/status
and coordinates concurrent execution.
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from agents.models import AgentConfig, AgentStatus
from agents.permissions import PermissionRegistry, get_permission_registry
from agents import store

logger = logging.getLogger(__name__)


@dataclass
class AgentInstance:
    """A running agent instance with runtime state."""
    config: AgentConfig
    session_id: str = ""
    thread: threading.Thread | None = None
    agent_ref: Any = None  # Reference to the Hermes AIAgent instance
    started_at: str = ""
    error: str = ""
    status: str = AgentStatus.IDLE.value
    current_task: str = ""
    task_history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.config.id,
            "name": self.config.name,
            "session_id": self.session_id,
            "status": self.status,
            "started_at": self.started_at,
            "current_task": self.current_task,
            "error": self.error,
            "config": self.config.to_dict(),
        }


class AgentRuntime:
    """Multi-agent runtime that manages concurrent Hermes AIAgent instances.

    Typical usage:
        runtime = AgentRuntime()
        runtime.start("agent-id-123", goal="Build a web scraper")
        runtime.status("agent-id-123")
        runtime.stop("agent-id-123")
        runtime.list_running()
    """

    def __init__(self, permission_registry: PermissionRegistry | None = None):
        self._instances: dict[str, AgentInstance] = {}
        self._lock = threading.RLock()
        self._permissions = permission_registry or get_permission_registry()
        self._callbacks: dict[str, list[Callable]] = {}
        self._started = False

    def start(self) -> None:
        """Start the runtime (initializes tracking)."""
        self._started = True
        logger.info("Agent runtime started")

    def stop(self) -> None:
        """Stop all running agents and shutdown the runtime."""
        with self._lock:
            agent_ids = list(self._instances.keys())
        for agent_id in agent_ids:
            self.stop_agent(agent_id)
        self._started = False
        logger.info("Agent runtime stopped")

    # ── Agent lifecycle ─────────────────────────────────────────────

    def start_agent(self, agent_id: str, goal: str = "",
                    context: dict | None = None,
                    callback: Callable | None = None) -> AgentInstance:
        config = store.get_agent(agent_id)
        if not config:
            raise ValueError(f"Agent {agent_id} not found")
        if not config.enabled:
            raise ValueError(f"Agent {agent_id} is disabled")

        if agent_id in self._instances:
            instance = self._instances[agent_id]
            if instance.status == AgentStatus.RUNNING.value:
                raise RuntimeError(f"Agent {config.name} is already running")
            self._instances.pop(agent_id, None)

        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        instance = AgentInstance(
            config=config,
            session_id=session_id,
            status=AgentStatus.STARTING if hasattr(AgentStatus, 'STARTING') else AgentStatus.RUNNING.value,
            started_at=now,
            current_task=goal or "",
        )

        with self._lock:
            self._instances[agent_id] = instance

        # Register permissions
        self._permissions.register_agent(agent_id, config.permissions)

        # Update store
        store.save_agent(config)
        store.record_session_start(agent_id, session_id)

        # Start the agent in a background thread
        thread = threading.Thread(
            target=self._run_agent_thread,
            args=(agent_id, goal, context or {}, callback),
            daemon=True,
            name=f"agent-{config.name}",
        )
        instance.thread = thread
        thread.start()

        logger.info("Started agent '%s' (session=%s)", config.name, session_id)
        self._emit("agent_started", instance.to_dict())
        return instance

    def stop_agent(self, agent_id: str) -> bool:
        with self._lock:
            instance = self._instances.get(agent_id)
            if not instance:
                return False
            instance.status = AgentStatus.STOPPED.value
            self._permissions.unregister_agent(agent_id)

        config = store.get_agent(agent_id)
        if config:
            store.record_session_end(
                instance.session_id,
                tokens=config.metrics.total_tokens if hasattr(config.metrics, 'total_tokens') else 0,
                messages=config.metrics.total_messages if hasattr(config.metrics, 'total_messages') else 0,
            )
            config.status = AgentStatus.IDLE.value
            store.save_agent(config)

        logger.info("Stopped agent '%s'", instance.config.name if instance.config else agent_id)
        self._emit("agent_stopped", {"agent_id": agent_id})
        return True

    def get_instance(self, agent_id: str) -> AgentInstance | None:
        return self._instances.get(agent_id)

    def list_running(self) -> list[AgentInstance]:
        return [inst for inst in self._instances.values()
                if inst.status == AgentStatus.RUNNING.value]

    def list_all_instances(self) -> list[AgentInstance]:
        return list(self._instances.values())

    # ── Agent thread runner ─────────────────────────────────────────

    def _run_agent_thread(self, agent_id: str, goal: str,
                          context: dict, callback: Callable | None) -> None:
        config = store.get_agent(agent_id)
        if not config:
            self._set_error(agent_id, "Agent config not found")
            return

        instance = self._instances.get(agent_id)
        if not instance:
            return

        try:
            instance.status = AgentStatus.RUNNING.value
            self._emit("agent_status_change", {"agent_id": agent_id, "status": "running"})

            # Create the Hermes AIAgent
            result = self._execute_agent(config, goal, context)

            with self._lock:
                instance = self._instances.get(agent_id)
                if instance:
                    instance.status = AgentStatus.IDLE.value
                    instance.task_history.append({
                        "task": goal,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    })

            self._emit("agent_completed", {"agent_id": agent_id, "result": result})

            if callback:
                try:
                    callback(agent_id, result)
                except Exception as e:
                    logger.error("Agent callback failed: %s", e)

        except Exception as e:
            logger.error("Agent '%s' thread error: %s", config.name, e, exc_info=True)
            self._set_error(agent_id, str(e))

    def _execute_agent(self, config: AgentConfig, goal: str, context: dict) -> Any:
        """Execute an agent task using the Hermes AIAgent runtime.

        This creates a proper AIAgent instance and calls run_conversation.
        Falls back to delegate_task for simplicity when direct agent
        access isn't available.
        """
        try:
            return self._execute_via_aiagent(config, goal, context)
        except ImportError:
            return self._execute_via_delegate(config, goal, context)

    def _execute_via_aiagent(self, config: AgentConfig, goal: str, context: dict) -> dict:
        """Execute using a full Hermes AIAgent instance."""
        from run_agent import AIAgent

        # Map reasoning levels to AIAgent parameters
        reasoning_config = None
        if config.reasoning == "deep":
            reasoning_config = {"effort": "high"}
        elif config.reasoning == "fast":
            reasoning_config = {"effort": "low"}

        # Map personality to system prompt
        system_prompt = self._build_system_prompt(config)

        agent = AIAgent(
            model=config.models.get("reasoning") or config.models.get("coding", ""),
            provider=config.provider,
            max_iterations=config.max_iterations,
            temperature=config.temperature,
            platform="cli",
            reasoning_config=reasoning_config,
            quiet_mode=True,
        )

        # Inject system prompt via conversation history
        history = []
        if system_prompt:
            history.append({"role": "system", "content": system_prompt})

        result = agent.run_conversation(
            user_message=goal,
            conversation_history=history,
        )

        return {
            "response": result.get("final_response", ""),
            "messages": result.get("messages", []),
            "tokens_used": result.get("tokens_used", 0),
        }

    def _execute_via_delegate(self, config: AgentConfig, goal: str, context: dict) -> dict:
        """Fallback: execute using delegate_task tool."""
        from tools.delegate_tool import delegate_task

        toolsets = self._map_tools_to_toolsets(config.tools)
        context_str = context.get("context_str", "") if context else ""

        result = delegate_task(
            goal=goal,
            context=context_str,
            toolsets=toolsets,
        )

        try:
            import json
            parsed = json.loads(result) if isinstance(result, str) else result
        except (json.JSONDecodeError, TypeError):
            parsed = {"result": str(result)}

        return parsed

    def _build_system_prompt(self, config: AgentConfig) -> str:
        parts = []
        if config.prompt:
            parts.append(config.prompt)
        personality_descriptions = {
            "professional": "Be formal, precise, and business-oriented.",
            "friendly": "Be warm, approachable, and conversational.",
            "minimal": "Be brief and direct. Use minimal words.",
            "technical": "Be technically precise with detailed explanations.",
            "creative": "Be imaginative and exploratory.",
            "research": "Be analytical, thorough, and evidence-based.",
            "funny": "Be witty and humorous while staying helpful.",
        }
        desc = personality_descriptions.get(config.personality, "")
        if desc:
            parts.append(desc)
        if config.personality_custom:
            parts.append(config.personality_custom)
        return "\n\n".join(parts)

    def _map_tools_to_toolsets(self, tools: list[str]) -> list[str]:
        mapping = {
            "filesystem": "file", "browser": "browser", "python": "code_execution",
            "docker": "code_execution", "git": "terminal", "github": "terminal",
            "terminal": "terminal", "web_search": "web", "ocr": "vision",
            "vision": "vision", "voice": "tts", "email": "messaging",
            "calendar": "messaging", "mcp": "file", "computer_use": "browser",
        }
        toolsets = set()
        for tool in tools:
            ts = mapping.get(tool)
            if ts:
                toolsets.add(ts)
        return list(toolsets) if toolsets else ["file", "terminal", "web"]

    def _set_error(self, agent_id: str, error: str) -> None:
        with self._lock:
            instance = self._instances.get(agent_id)
            if instance:
                instance.status = AgentStatus.ERROR.value
                instance.error = error
        config = store.get_agent(agent_id)
        if config:
            config.status = AgentStatus.ERROR.value
            store.save_agent(config)
        self._emit("agent_error", {"agent_id": agent_id, "error": error})

    # ── Event system ────────────────────────────────────────────────

    def on(self, event: str, callback: Callable) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error("Event callback error for %s: %s", event, e)
