"""
AetherOS Kernel v2.0 — Multi-Agent AI Operating System Layer

The kernel is the central orchestrator that boots, coordinates, and manages
all AI components. It delegates to existing Aetheros infrastructure
(AIAgent, tool registry, cron) while adding structured lifecycle management,
event-driven communication, planning, execution control, and multi-agent
orchestration.

Usage:
    from kernel import Kernel

    config = KernelConfig(enable_multi_agent=True)
    kernel = Kernel(config)
    kernel.boot()

    plan = kernel.planner.create_plan("Deploy the application")
    kernel.executor.run_agent(agent, "Build the project")
    kernel.agent_manager.start_agent("research-1")

    kernel.shutdown()
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus, EventTopics
from kernel.lifecycle import LifecycleManager, ServiceRegistration, ComponentState
from kernel.registry import AgentRegistry as ComponentRegistry, ComponentEntry
from kernel.scheduler import KernelScheduler
from kernel.planner import Planner, PlanStatus
from kernel.executor import Executor
from kernel.router import Router
from kernel.workspace import WorkspaceManager
from kernel.context import ContextManager
from kernel.permissions import PermissionManager
from kernel.task_graph import TaskGraph
from kernel.telemetry import TelemetryCollector
from kernel.state_manager import StateManager

from kernel.agent_manager import AgentManager
from kernel.agent_registry import AgentRegistry
from kernel.inter_agent import InterAgentBus
from kernel.supervisor import SupervisorAgent
from kernel.reviewer import ReviewerAgent
from kernel.critic import CriticAgent
from kernel.reflection import ReflectionEngine
from kernel.approval import ApprovalLayer
from kernel.artifact_manager import ArtifactManager
from kernel.scheduling_engine import SchedulingEngine

logger = logging.getLogger(__name__)


@dataclass
class KernelConfig:
    enable_scheduler: bool = True
    enable_telemetry: bool = True
    enable_state_persistence: bool = True
    enable_event_bus: bool = True
    auto_discover_components: bool = True
    enable_multi_agent: bool = True
    enable_supervisor: bool = True
    enable_approvals: bool = True
    enable_reflection: bool = True
    enable_artifact_storage: bool = True
    enable_inter_agent_bus: bool = True
    state_save_interval: float = 30.0
    health_check_interval: float = 30.0
    verbose: bool = False
    state_dir: Optional[str] = None
    artifact_dir: Optional[str] = None


class Kernel:
    def __init__(self, config: KernelConfig = None):
        self.config = config or KernelConfig()
        self._booted = False
        self._shutdown_flag = False
        self._boot_time: Optional[float] = None

        self.event_bus = EventBus() if self.config.enable_event_bus else None
        self.lifecycle = LifecycleManager(self.event_bus)
        self.registry = ComponentRegistry(self.event_bus)
        self.router = Router(self.event_bus)

        self.planner = Planner(self.event_bus)
        self.executor = Executor(self.event_bus)
        self.scheduler = KernelScheduler(self.event_bus)
        self.workspace = WorkspaceManager(self.event_bus)
        self.context = ContextManager(self.event_bus)
        self.permissions = PermissionManager(self.event_bus)
        self.telemetry = TelemetryCollector(self.event_bus) if self.config.enable_telemetry else None
        self.state = StateManager(self.event_bus, state_dir=self.config.state_dir) if self.config.enable_state_persistence else None

        self.agent_manager = AgentManager() if self.config.enable_multi_agent else None
        self.agent_registry = AgentRegistry() if self.config.enable_multi_agent else None
        self.inter_agent = InterAgentBus(self.event_bus) if self.config.enable_inter_agent_bus else None
        self.supervisor = SupervisorAgent(self.event_bus) if self.config.enable_supervisor else None
        self.reviewer = ReviewerAgent(self.event_bus) if self.config.enable_multi_agent else None
        self.critic = CriticAgent(self.event_bus) if self.config.enable_multi_agent else None
        self.reflection = ReflectionEngine(self.event_bus) if self.config.enable_reflection else None
        self.approvals = ApprovalLayer(self.event_bus) if self.config.enable_approvals else None
        self.artifacts = ArtifactManager(storage_dir=self.config.artifact_dir, event_bus=self.event_bus) if self.config.enable_artifact_storage else None
        self.scheduling = SchedulingEngine(self.event_bus) if self.config.enable_multi_agent else None

        self._state_save_timer: Optional[threading.Timer] = None
        self._discovery_complete = False

    def boot(self) -> None:
        if self._booted:
            logger.warning("Kernel: already booted")
            return
        self._boot_time = time.time()
        logger.info("AetherOS Kernel v2.0 booting...")
        self._register_core_services()
        self._wire_event_listeners()
        self.lifecycle.start()
        if self.config.auto_discover_components:
            self._discover_components()
        if self.state:
            self.state.load()
        if self.config.enable_scheduler and self.scheduler:
            self.scheduler.start()
            self.scheduler.add_existing_cron_jobs()
        if self.state and self.config.state_save_interval > 0:
            self._start_state_save_timer()
        self._install_signal_handlers()
        self._booted = True
        boot_duration = time.time() - self._boot_time
        logger.info("AetherOS Kernel v2.0 booted in %.2fs: %d services, %d tools, %d workspaces",
                     boot_duration, len(self.lifecycle.get_all()),
                     len(self.registry.find(kind="tool")), len(self.workspace.list_workspaces()))
        if self.event_bus:
            self.event_bus.emit(EventTopics.LIFECYCLE_STARTED, {
                "boot_time": boot_duration, "services": list(self.lifecycle.get_all().keys()),
                "version": "2.0.0", "multi_agent": self.config.enable_multi_agent,
            })

    def _register_core_services(self) -> None:
        services = [
            ServiceRegistration(name="event_bus", description="Kernel event system", health_fn=lambda: self.event_bus is not None),
            ServiceRegistration(name="registry", description="Component discovery registry", health_fn=lambda: len(self.registry.list_tools()) > 0),
            ServiceRegistration(name="planner", description="Goal-to-plan conversion engine", dependencies=["registry"]),
            ServiceRegistration(name="executor", description="Agent and tool execution engine", dependencies=["registry"]),
            ServiceRegistration(name="router", description="Request routing to handlers"),
            ServiceRegistration(name="context", description="Shared context across agents"),
            ServiceRegistration(name="workspace", description="Workspace and session management"),
            ServiceRegistration(name="permissions", description="Centralized permission checking"),
        ]
        if self.scheduler:
            services.append(ServiceRegistration(name="scheduler", description="Background job scheduler",
                stop_fn=lambda s: self.scheduler.stop(), health_fn=lambda: self.scheduler.is_healthy()))
        if self.telemetry:
            services.append(ServiceRegistration(name="telemetry", description="Metrics and telemetry collector",
                stop_fn=lambda s: self.telemetry.shutdown()))
        if self.state:
            services.append(ServiceRegistration(name="state_manager", description="Kernel state persistence",
                stop_fn=lambda s: self.state.shutdown(), health_fn=lambda: self.state._state_file.exists()))
        if self.agent_manager:
            services.append(ServiceRegistration(name="agent_manager", description="Multi-agent lifecycle manager"))
        if self.inter_agent:
            services.append(ServiceRegistration(name="inter_agent_bus", description="Inter-agent communication bus"))
        if self.supervisor:
            services.append(ServiceRegistration(name="supervisor", description="Agent monitoring daemon",
                start_fn=lambda s: self.supervisor.start(), stop_fn=lambda s: self.supervisor.stop()))
        if self.approvals:
            services.append(ServiceRegistration(name="approvals", description="Human approval layer"))
        if self.artifacts:
            services.append(ServiceRegistration(name="artifacts", description="Artifact storage and versioning"))
        if self.scheduling:
            services.append(ServiceRegistration(name="scheduling", description="Advanced scheduling engine",
                start_fn=lambda s: self.scheduling.start(), stop_fn=lambda s: self.scheduling.stop()))
        for svc in services:
            self.lifecycle.register(svc)

    def _wire_event_listeners(self) -> None:
        if not self.event_bus:
            return
        self.event_bus.subscribe(EventTopics.AGENT_ERROR,
            lambda e: self.telemetry and self.telemetry.record_error("agent", e.data.get("error", "unknown")),
            description="agent_error_telemetry")
        self.event_bus.subscribe(EventTopics.TOOL_STARTED,
            lambda e: self.telemetry and self.telemetry.increment("tool.calls", {"tool": e.data.get("tool_name", "unknown")}),
            description="tool_call_telemetry")
        self.event_bus.subscribe(EventTopics.TASK_COMPLETED,
            lambda e: self.state and self.state.set(f"tasks.{e.data.get('plan_id', '?')}.completed", time.time()),
            description="task_completed_state")
        self.event_bus.subscribe(EventTopics.SYSTEM_ERROR,
            lambda e: self.telemetry and self.telemetry.record_error("system", e.data.get("error", "unknown"),
                labels={"component": e.data.get("component", "?")}),
            description="system_error_telemetry")

    def _discover_components(self) -> None:
        if self._discovery_complete:
            return
        logger.info("Kernel: discovering components...")
        tool_count = self.registry.discover_from_tool_registry()
        plugin_count = self.registry.discover_from_plugins()
        mcp_count = self.registry.discover_from_mcp()
        self.permissions.integrate_file_safety()
        self._discovery_complete = True
        logger.info("Kernel: discovered %d tools, %d plugins, %d MCP servers", tool_count, plugin_count, mcp_count)

    def rediscover_components(self) -> Dict[str, int]:
        self._discovery_complete = False
        self.registry = ComponentRegistry(self.event_bus)
        counts = self.registry.discover_all()
        self.permissions.integrate_file_safety()
        return counts

    def shutdown(self) -> None:
        if self._shutdown_flag:
            return
        self._shutdown_flag = True
        logger.info("Kernel: shutting down...")
        if self.event_bus:
            self.event_bus.emit(EventTopics.SYSTEM_SHUTDOWN, source="kernel")
        if self._state_save_timer:
            self._state_save_timer.cancel()
        if self.state:
            self.state.persist(force=True)
            self.state.shutdown()
        if self.scheduling:
            self.scheduling.stop()
        if self.supervisor:
            self.supervisor.stop()
        if self.inter_agent:
            self.inter_agent.shutdown()
        if self.scheduler:
            self.scheduler.stop()
        self.workspace.shutdown()
        self.lifecycle.shutdown()
        if self.event_bus:
            self.event_bus.shutdown()
        uptime = time.time() - (self._boot_time or time.time())
        logger.info("AetherOS Kernel v2.0 shut down (uptime: %.1fs)", uptime)

    def is_running(self) -> bool:
        return self._booted and not self._shutdown_flag

    def _start_state_save_timer(self) -> None:
        def _save_loop():
            while not self._shutdown_flag and self.state:
                time.sleep(self.config.state_save_interval)
                try:
                    self.state.persist()
                except Exception as exc:
                    logger.debug("Kernel: periodic state save failed: %s", exc)
        thread = threading.Thread(target=_save_loop, daemon=True, name="kernel-state-save")
        thread.start()

    def _install_signal_handlers(self) -> None:
        def _handle_signal(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info("Kernel: received %s, shutting down...", sig_name)
            self.shutdown()
        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        except (ValueError, RuntimeError):
            pass

    def health(self) -> Dict[str, Any]:
        return {
            "booted": self._booted,
            "running": self.is_running(),
            "uptime_seconds": time.time() - (self._boot_time or time.time()),
            "services": self.lifecycle.health_summary(),
            "registry": self.registry.snapshot(),
            "components": len(self.lifecycle.get_all()),
        }

    def status(self) -> Dict[str, Any]:
        result = {
            "kernel": {"booted": self._booted, "running": self.is_running(),
                       "uptime_seconds": (time.time() - self._boot_time) if self._boot_time else 0, "version": "2.0.0"},
            "services": self.lifecycle.health_summary(),
            "registry": self.registry.snapshot(),
            "planner": {"active_plans": len(self.planner.list_plans()),
                        "pending_plans": len(self.planner.list_plans(status=PlanStatus.APPROVED))},
            "scheduler": self.scheduler.get_stats() if self.scheduler else {},
            "executor": self.executor.get_stats(),
            "workspace": self.workspace.stats(),
            "permissions": self.permissions.get_stats(),
            "telemetry": self.telemetry.summary() if self.telemetry else {},
        }
        if self.agent_manager: result["agent_manager"] = self.agent_manager.get_stats()
        if self.agent_registry: result["agent_registry"] = self.agent_registry.get_stats()
        if self.inter_agent: result["inter_agent"] = self.inter_agent.get_stats()
        if self.supervisor: result["supervisor"] = self.supervisor.get_stats()
        if self.reviewer: result["reviewer"] = self.reviewer.get_stats()
        if self.critic: result["critic"] = self.critic.get_stats()
        if self.reflection: result["reflection"] = self.reflection.get_stats()
        if self.approvals: result["approvals"] = self.approvals.get_stats()
        if self.artifacts: result["artifacts"] = self.artifacts.get_stats()
        if self.scheduling: result["scheduling"] = self.scheduling.get_stats()
        return result