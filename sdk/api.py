"""
SDK API Facades
===============

High-level, stable API facades that extension code uses to interact with
the Aetheros runtime. Each facade maps to a domain (tools, events,
workflows, memory, agents, etc.) and exposes a curated set of operations.

Extensions should **never** import directly from ``aetheros_cli`` or
``tools`` — these are internal. The SDK facades are the stable contract.
"""

from __future__ import annotations

import json
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# PluginAPI — plugin metadata and lifecycle
# ---------------------------------------------------------------------------

@dataclass
class PluginInfo:
    """Read-only metadata about a registered plugin."""
    name: str
    version: str
    description: str
    author: str
    kind: str
    enabled: bool
    tools_count: int
    hooks_count: int


class PluginAPI:
    """Query plugin registry and interact with other plugins.

    Usage::

        api = PluginAPI(ctx)
        plugins = api.list_plugins()
        info = api.get_plugin("disk-cleanup")
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def list_plugins(self) -> List[PluginInfo]:
        """Return metadata for all discovered plugins."""
        try:
            from aetheros_cli.plugins import get_plugin_manager
            mgr = get_plugin_manager()
            return [
                PluginInfo(
                    name=p["name"],
                    version=p.get("version", ""),
                    description=p.get("description", ""),
                    author="",
                    kind=p.get("kind", "standalone"),
                    enabled=p["enabled"],
                    tools_count=p.get("tools", 0),
                    hooks_count=p.get("hooks", 0),
                )
                for p in mgr.list_plugins()
            ]
        except Exception as exc:
            logger.warning("PluginAPI.list_plugins failed: %s", exc)
            return []

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """Get metadata for a specific plugin by name."""
        for p in self.list_plugins():
            if p.name == name:
                return p
        return None

    def is_enabled(self, name: str) -> bool:
        """Check whether a plugin is enabled."""
        info = self.get_plugin(name)
        return info is not None and info.enabled


# ---------------------------------------------------------------------------
# ToolAPI — register and query tools
# ---------------------------------------------------------------------------

@dataclass
class ToolDef:
    """Definition of a tool an extension can register."""
    name: str
    description: str
    parameters: Dict[str, Any]
    toolset: str = "sdk"


class ToolAPI:
    """Register and query tool definitions from extension code.

    Usage::

        api = ToolAPI(ctx)
        api.register_tool(
            name="my_tool",
            description="Does something useful",
            parameters={"type": "object", "properties": {...}},
            handler=my_handler,
        )
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        *,
        toolset: str = "sdk",
        check_fn: Optional[Callable[[], bool]] = None,
        requires_env: Optional[List[str]] = None,
        is_async: bool = False,
        override: bool = False,
    ) -> None:
        """Register a tool with the global tool registry.

        Args:
            name: Canonical tool name (snake_case).
            description: Human-readable description.
            parameters: JSON Schema object describing parameters.
            handler: Callable that receives ``(args_dict, **kwargs)``
                and returns a JSON string.
            toolset: Toolset grouping key (default ``"sdk"``).
            check_fn: Optional zero-arg callable returning bool —
                tool is hidden when it returns False.
            requires_env: Optional list of env var names needed.
            is_async: Whether handler is an async function.
            override: Set True to intentionally replace a built-in tool.
        """
        schema = {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
        # Delegate to the plugin context's register_tool
        self._ctx.register_tool(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            requires_env=requires_env,
            is_async=is_async,
            description=description,
            override=override,
        )

    def get_tool_def(self, name: str) -> Optional[ToolDef]:
        """Look up a registered tool's definition."""
        try:
            from tools.registry import registry
            entry = registry.get_entry(name)
            if entry is None:
                return None
            return ToolDef(
                name=entry.name,
                description=entry.description or entry.schema.get("description", ""),
                parameters=entry.schema.get("parameters", {}),
                toolset=entry.toolset,
            )
        except Exception:
            return None

    def list_tools(self, toolset: Optional[str] = None) -> List[ToolDef]:
        """List all registered tools, optionally filtered by toolset."""
        try:
            from tools.registry import registry
            entries = registry._snapshot_entries()
            result = []
            for entry in entries:
                if toolset and entry.toolset != toolset:
                    continue
                result.append(ToolDef(
                    name=entry.name,
                    description=entry.description or entry.schema.get("description", ""),
                    parameters=entry.schema.get("parameters", {}),
                    toolset=entry.toolset,
                ))
            return result
        except Exception:
            return []

    def dispatch_tool(self, name: str, args: Dict[str, Any], **kwargs) -> str:
        """Execute a tool by name.

        Args:
            name: Tool name.
            args: Arguments dict.
            **kwargs: Extra keyword args forwarded to the handler.

        Returns:
            JSON string result from the handler.
        """
        from tools.registry import registry
        return registry.dispatch(name, args, **kwargs)


# ---------------------------------------------------------------------------
# EventAPI — publish and subscribe to events
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """A typed event that extensions can emit and subscribe to."""
    type: str
    data: Dict[str, Any]
    source: str = ""


class EventAPI:
    """Publish and subscribe to lifecycle and custom events.

    Events are the **primary decoupling mechanism** — one extension emits,
    zero or more others react, without any direct import dependency.

    Usage::

        api = EventAPI(ctx)
        api.publish("file:created", {"path": "/tmp/test.txt"})

        @api.on("file:created")
        def handle_file_created(event):
            print(f"File created: {event.data['path']}")
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._handlers: Dict[str, List[Callable[[Event], None]]] = {}

    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to all subscribers.

        Args:
            event_type: Dot-separated event type (e.g. ``"file:created"``).
            data: Event payload dict.
        """
        event = Event(type=event_type, data=data, source=self._ctx.manifest.name)
        handlers = list(self._handlers.get(event_type, []))
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.warning(
                    "Event handler %s for '%s' raised: %s",
                    getattr(handler, "__name__", repr(handler)),
                    event_type, exc,
                )

    def on(self, event_type: str) -> Callable:
        """Decorator: register a handler for *event_type*.

        Usage::

            @event_api.on("file:created")
            def handle(event):
                ...
        """
        def decorator(func: Callable[[Event], None]) -> Callable[[Event], None]:
            self._handlers.setdefault(event_type, []).append(func)
            return func
        return decorator

    def off(self, event_type: str, handler: Callable) -> None:
        """Unregister a previously registered handler."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def list_event_types(self) -> List[str]:
        """Return sorted list of all registered event types."""
        return sorted(self._handlers.keys())


# ---------------------------------------------------------------------------
# WorkflowAPI — define and execute workflows
# ---------------------------------------------------------------------------

@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class WorkflowDef:
    """Definition of a multi-step workflow."""
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)


class WorkflowAPI:
    """Define and execute workflows — sequences of steps that compose tools,
    agent actions, and external calls.

    Usage::

        api = WorkflowAPI(ctx)
        wf = api.define_workflow("deploy", "Deploy to production")
        wf.steps.append(WorkflowStep("build", "run_command", {"cmd": "npm run build"}))
        wf.steps.append(WorkflowStep("test", "run_command", {"cmd": "npm test"}, depends_on=["build"]))
        api.register_workflow(wf)
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._workflows: Dict[str, WorkflowDef] = {}

    def define_workflow(self, name: str, description: str = "") -> WorkflowDef:
        """Create a new workflow definition.

        Returns a mutable ``WorkflowDef`` — add steps, then call
        ``register_workflow()`` to make it available.
        """
        wf = WorkflowDef(name=name, description=description)
        return wf

    def register_workflow(self, workflow: WorkflowDef) -> None:
        """Register a workflow so it can be discovered and executed."""
        self._workflows[workflow.name] = workflow

    def get_workflow(self, name: str) -> Optional[WorkflowDef]:
        """Look up a registered workflow by name."""
        return self._workflows.get(name)

    def list_workflows(self) -> List[WorkflowDef]:
        """Return all registered workflows."""
        return list(self._workflows.values())


# ---------------------------------------------------------------------------
# AgentAPI — interact with the running agent
# ---------------------------------------------------------------------------

class AgentAPI:
    """Interact with the running Aetheros agent session.

    Provides access to session metadata, model info, and the ability to
    inject messages or query state.

    Usage::

        api = AgentAPI(ctx)
        session_id = api.get_session_id()
        model = api.get_current_model()
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def get_session_id(self) -> Optional[str]:
        """Return the current session ID, or None if not in a session."""
        return getattr(self._ctx._manager._cli_ref, "session_id", None)

    def get_current_model(self) -> Optional[str]:
        """Return the model name currently in use."""
        cli = self._ctx._manager._cli_ref
        if cli and hasattr(cli, "agent") and cli.agent:
            return getattr(cli.agent, "model", None)
        return None

    def inject_message(self, content: str, role: str = "user") -> bool:
        """Inject a message into the active conversation.

        Delegates to the plugin context's inject_message().
        """
        return self._ctx.inject_message(content, role=role)


# ---------------------------------------------------------------------------
# MemoryAPI — access the memory system
# ---------------------------------------------------------------------------

class MemoryAPI:
    """Interact with the Aetheros memory/provider system.

    Usage::

        api = MemoryAPI(ctx)
        memories = api.search("what did we discuss about X")
        api.store("user preference", {"key": "theme", "value": "dark"})
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memory for entries matching *query*.

        Returns a list of dicts with at least ``content`` and ``score`` keys.
        """
        try:
            from agent.memory_manager import get_memory_manager
            mgr = get_memory_manager()
            results = mgr.search(query, limit=limit)
            return [
                {"content": r.get("content", ""), "score": r.get("score", 0.0)}
                for r in (results or [])
            ]
        except Exception as exc:
            logger.warning("MemoryAPI.search failed: %s", exc)
            return []

    def store(self, key: str, data: Dict[str, Any]) -> bool:
        """Store a value in memory.

        Returns True on success.
        """
        try:
            from agent.memory_manager import get_memory_manager
            mgr = get_memory_manager()
            mgr.store(key=key, data=data)
            return True
        except Exception as exc:
            logger.warning("MemoryAPI.store failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# InteractionAPI — respond to user interactions
# ---------------------------------------------------------------------------

class InteractionAPI:
    """Respond to user interactions — send messages, prompts, confirmations.

    Usage::

        api = InteractionAPI(ctx)
        api.send_message("Hello from my extension!")
        api.ask_confirm("Are you sure?")
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def send_message(self, text: str) -> None:
        """Send a message to the user (terminal output or gateway reply).

        In CLI mode this prints to stdout. In gateway mode it queues a reply.
        """
        from rich.console import Console
        Console().print(f"[dim]🔌 {self._ctx.manifest.name}:[/dim] {text}")

    def ask_confirm(self, prompt: str, default: bool = False) -> bool:
        """Ask the user for a yes/no confirmation.

        Returns the user's choice. In non-interactive contexts, returns
        *default*.
        """
        try:
            from rich.console import Console
            console = Console()
            if not sys.stdin.isatty():
                return default
            answer = input(f"  {prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
            if default:
                return answer not in {"n", "no"}
            return answer in {"y", "yes"}
        except Exception:
            return default


# ---------------------------------------------------------------------------
# EngineeringAPI — engineering subsystem access
# ---------------------------------------------------------------------------

class EngineeringAPI:
    """Access the engineering subsystem for code analysis, testing, and CI.

    Usage::

        api = EngineeringAPI(ctx)
        issues = api.analyze_code("src/main.py")
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def analyze_code(self, path: str) -> List[Dict[str, Any]]:
        """Run code analysis on a file or directory.

        Returns a list of issue dicts with ``severity``, ``message``, ``line``.
        """
        # Placeholder — actual analysis is delegated to the engineering tools
        try:
            from tools.registry import registry
            result = registry.dispatch("engineering_analyze", {"path": path})
            data = json.loads(result)
            return data.get("issues", []) if isinstance(data, dict) else []
        except Exception:
            return []


# ---------------------------------------------------------------------------
# ClusterAPI — distributed agent coordination
# ---------------------------------------------------------------------------

class ClusterAPI:
    """Interact with distributed agent clusters and swarm coordination.

    Usage::

        api = ClusterAPI(ctx)
        nodes = api.list_nodes()
        api.broadcast("event:cluster_status", {"status": "ok"})
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def list_nodes(self) -> List[Dict[str, Any]]:
        """Return list of known cluster nodes."""
        try:
            from swarm.registry import get_registry
            reg = get_registry()
            return [
                {"id": node_id, "role": info.get("role", ""), "status": info.get("status", "unknown")}
                for node_id, info in reg.list_agents().items()
            ]
        except Exception:
            return []

    def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast an event to all nodes in the cluster."""
        try:
            from swarm.communication import broadcast_event
            broadcast_event(event_type, data)
        except Exception as exc:
            logger.warning("ClusterAPI.broadcast failed: %s", exc)
