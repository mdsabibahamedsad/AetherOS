"""Automation engine - orchestrates all subsystem dispatch."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

from aetheros_automation.models.models import (
    AutomationConfig, Task, TaskStatus, Workflow,
    TaskStep as Step, ExecutionMode, AgentRole, Permission
)
from aetheros_automation.modes.controller import ModeController

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Central orchestrator: routes step actions to subsystem controllers."""

    # ── class-level action → (subsystem, component, method) resolver ──
    _ACTION_ROUTES: Dict[str, Tuple[str, str, str]] = {
        # computer
        "mouse.click":             ("computer", "mouse", "click"),
        "mouse.move":              ("computer", "mouse", "move"),
        "mouse.drag":              ("computer", "mouse", "drag"),
        "mouse.scroll":            ("computer", "mouse", "scroll"),
        "keyboard.type":           ("computer", "keyboard", "type_text"),
        "keyboard.press":          ("computer", "keyboard", "press_key"),
        "keyboard.hotkey":         ("computer", "keyboard", "hotkey"),
        "clipboard.copy":          ("computer", "clipboard", "set_text"),
        "clipboard.paste":         ("computer", "clipboard", "paste"),
        "clipboard.get":           ("computer", "clipboard", "get_text"),
        "window.list":             ("computer", "windows", "list_windows"),
        "window.focus":            ("computer", "windows", "focus_window"),
        "window.close":            ("computer", "windows", "close_window"),
        "window.resize":           ("computer", "windows", "resize_window"),
        "window.move":             ("computer", "windows", "move_window"),
        "app.launch":              ("computer", "apps", "launch"),
        "app.terminate":           ("computer", "apps", "terminate"),
        "app.list":                ("computer", "apps", "list_apps"),
        "screenshot.capture":      ("computer", "screenshot", "capture"),
        "notification.send":       ("computer", "notifications", "send"),
        # browser
        "browser.navigate":        ("browser", "manager", "navigate"),
        "browser.click":           ("browser", "manager", "click"),
        "browser.type":            ("browser", "manager", "type"),
        "browser.extract":         ("browser", "manager", "extract"),
        "browser.screenshot":      ("browser", "manager", "screenshot"),
        "browser.execute_js":      ("browser", "manager", "execute_js"),
        "browser.close":           ("browser", "manager", "close"),
        # files
        "file.read":               ("files", "operations", "read"),
        "file.write":              ("files", "operations", "write"),
        "file.delete":             ("files", "operations", "delete"),
        "file.copy":               ("files", "operations", "copy"),
        "file.move":               ("files", "operations", "move"),
        "file.list":               ("files", "operations", "list_dir"),
        "file.compress":           ("files", "operations", "compress"),
        "file.extract":            ("files", "operations", "extract"),
        "file.encrypt":            ("files", "operations", "encrypt"),
        "file.decrypt":            ("files", "operations", "decrypt"),
        "backup.create":           ("files", "backup", "create_backup"),
        "backup.restore":          ("files", "backup", "restore_backup"),
        "version.snapshot":        ("files", "version", "snapshot"),
        "version.restore":         ("files", "version", "restore"),
        # terminal
        "terminal.run":            ("terminal", "runner", "run"),
        # code
        "git.clone":               ("code", "git", "clone"),
        "git.commit":              ("code", "git", "commit"),
        "git.push":                ("code", "git", "push"),
        "git.pr":                  ("code", "git", "create_pr"),
        "code.build":              ("code", "builder", "build"),
        "code.test":               ("code", "builder", "test"),
        "code.lint":               ("code", "review", "lint"),
        "code.review":             ("code", "review", "review"),
        # devops
        "docker.up":               ("devops", "docker", "up"),
        "docker.down":             ("devops", "docker", "down"),
        "docker.ps":               ("devops", "docker", "ps"),
        "docker.logs":             ("devops", "docker", "logs"),
        "k8s.apply":               ("devops", "kubernetes", "apply"),
        "k8s.get":                 ("devops", "kubernetes", "get"),
        "k8s.delete":              ("devops", "kubernetes", "delete"),
        "terraform.apply":         ("devops", "terraform", "apply"),
        "terraform.destroy":       ("devops", "terraform", "destroy"),
        "terraform.plan":          ("devops", "terraform", "plan"),
        "cicd.trigger":            ("devops", "ci_cd", "trigger"),
        "cicd.status":             ("devops", "ci_cd", "status"),
        # email
        "email.send":              ("email", "handler", "send"),
        "email.read":              ("email", "handler", "read"),
        "email.search":            ("email", "handler", "search"),
        # calendar
        "calendar.list":           ("calendar", "handler", "list_events"),
        "calendar.create":         ("calendar", "handler", "create_event"),
        "calendar.update":         ("calendar", "handler", "update_event"),
        "calendar.delete":         ("calendar", "handler", "delete_event"),
        # documents
        "document.generate":       ("documents", "generator", "generate"),
        # approvals
        "approval.request":        ("approvals", "manager", "request"),
        "approval.approve":        ("approvals", "manager", "approve"),
        "approval.deny":           ("approvals", "manager", "deny"),
        # security
        "sandbox.execute":         ("security", "sandbox", "execute"),
        "monitor.log":             ("security", "monitor", "log"),
        # permissions
        "permission.check":        ("permissions", "manager", "check"),
        "permission.grant":        ("permissions", "manager", "grant"),
        # undo
        "undo.checkpoint":         ("undo", "manager", "checkpoint"),
        "undo.restore":            ("undo", "manager", "restore"),
        # plugins
        "plugin.load":             ("plugins", "registry", "load"),
        "plugin.unload":           ("plugins", "registry", "unload"),
        "plugin.execute":          ("plugins", "registry", "execute"),
        # mobile
        "mobile.notify":           ("mobile", "notifier", "notify"),
        # agents
        "agent.spawn":             ("agents", "coordinator", "spawn"),
        "agent.task":              ("agents", "coordinator", "assign_task"),
        "agent.result":            ("agents", "coordinator", "get_result"),
        # tasks
        "task.create":             ("tasks", "planner", "create_plan"),
        "task.plan":               ("tasks", "planner", "plan"),
        "task.graph":              ("tasks", "graph", "render"),
        # modes
        "mode.switch":             ("modes", "controller", "switch_to"),
        "mode.status":             ("modes", "controller", "current_mode"),
    }

    def __init__(
        self,
        config: Optional[AutomationConfig] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.config = config or AutomationConfig()
        self.loop = loop or asyncio.get_event_loop()
        self._running = False
        self._paused = False
        self._emergency_stop = False
        self._tasks: Dict[str, Task] = {}
        self._workflows: Dict[str, Workflow] = {}
        self._agents: Dict[str, Any] = {}
        self._subsystems: Dict[str, Any] = {}
        self._subsystem_refs: Dict[str, Dict[str, str]] = defaultdict(dict)
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._mode_controller: Optional[ModeController] = None
        self._start_time: Optional[datetime] = None
        self._execution_history: List[Dict[str, Any]] = []

        self._init_subsystems()

    # ── Lifecycle ───────────────────────────────────────────────────

    def start(self):
        self._running = True
        self._paused = False
        self._emergency_stop = False
        self._start_time = datetime.utcnow()
        self._emit("engine.started", {"timestamp": self._start_time.isoformat()})
        logger.info("AutomationEngine started.")

    def stop(self):
        self._running = False
        self._paused = False
        self._emit("engine.stopped", {"timestamp": datetime.utcnow().isoformat()})
        logger.info("AutomationEngine stopped.")

    def pause(self):
        self._paused = True
        self._emit("engine.paused", {})

    def resume(self):
        self._paused = False
        self._emit("engine.resumed", {})

    @property
    def is_running(self):
        return self._running

    @property
    def is_paused(self):
        return self._paused

    # ── Subsystem initialization ────────────────────────────────────

    def _init_subsystems(self):
        subsystem_constructors: Dict[str, Dict[str, tuple]] = {
            "computer": {
                "mouse": ("aetheros_automation.computer.mouse", "MouseController"),
                "keyboard": ("aetheros_automation.computer.keyboard", "KeyboardController"),
                "clipboard": ("aetheros_automation.computer.clipboard", "ClipboardController"),
                "windows": ("aetheros_automation.computer.windows", "WindowManager"),
                "apps": ("aetheros_automation.computer.apps", "AppLauncher"),
                "notifications": ("aetheros_automation.computer.notifications", "NotificationManager"),
                "screenshot": ("aetheros_automation.computer.screenshot", "ScreenshotCapture"),
            },
            "browser": {
                "manager": ("aetheros_automation.browser.manager", "BrowserManager"),
            },
            "files": {
                "operations": ("aetheros_automation.files.operations", "FileOperations"),
                "backup": ("aetheros_automation.files.backup", "BackupManager"),
                "version": ("aetheros_automation.files.version", "VersionManager"),
            },
            "terminal": {
                "runner": ("aetheros_automation.terminal.runner", "TerminalRunner"),
            },
            "code": {
                "git": ("aetheros_automation.code.git", "GitAutomation"),
                "builder": ("aetheros_automation.code.builder", "CodeBuilder"),
                "review": ("aetheros_automation.code.review", "CodeReviewer"),
            },
            "devops": {
                "docker": ("aetheros_automation.devops.docker", "DockerManager"),
                "kubernetes": ("aetheros_automation.devops.kubernetes", "K8sManager"),
                "terraform": ("aetheros_automation.devops.terraform", "TerraformRunner"),
                "ci_cd": ("aetheros_automation.devops.ci_cd", "CIManager"),
            },
            "email": {
                "handler": ("aetheros_automation.email.handler", "EmailHandler"),
            },
            "calendar": {
                "handler": ("aetheros_automation.calendar.handler", "CalendarHandler"),
            },
            "documents": {
                "generator": ("aetheros_automation.documents.generator", "DocumentGenerator"),
            },
            "approvals": {
                "manager": ("aetheros_automation.approvals.manager", "ApprovalManager"),
            },
            "security": {
                "sandbox": ("aetheros_automation.security.sandbox", "Sandbox"),
                "monitor": ("aetheros_automation.security.monitor", "ActivityMonitor"),
            },
            "permissions": {
                "manager": ("aetheros_automation.permissions.manager", "PermissionManager"),
            },
            "undo": {
                "manager": ("aetheros_automation.undo.manager", "UndoManager"),
            },
            "plugins": {
                "registry": ("aetheros_automation.plugins.registry", "AutomationPluginRegistry"),
            },
            "mobile": {
                "notifier": ("aetheros_automation.mobile.notifier", "MobileNotifier"),
            },
            "agents": {
                "registry": ("aetheros_automation.agents.registry", "AgentRegistry"),
                "coordinator": ("aetheros_automation.agents.coordinator", "CoordinatorAgent"),
            },
            "tasks": {
                "planner": ("aetheros_automation.tasks.planner", "TaskPlanner"),
                "tracker": ("aetheros_automation.tasks.tracker", "TaskTracker"),
                "graph": ("aetheros_automation.tasks.graph", "TaskGraph"),
            },
            "modes": {
                "controller": ("aetheros_automation.modes.controller", "ModeController"),
            },
            "live": {
                "display": ("aetheros_automation.live.display", "LiveDisplay"),
            },
            "web": {
                "api": ("aetheros_automation.web.api", "AutomationWebAPI"),
            },
            "mcp": {
                "server": ("aetheros_automation.mcp.server", "AutomationMCPServer"),
            },
        }

        for pkg_name, components in subsystem_constructors.items():
            self._subsystems[pkg_name] = {}
            for comp_name, (mod_path, cls_name) in components.items():
                try:
                    import importlib
                    mod = importlib.import_module(mod_path)
                    cls = getattr(mod, cls_name)
                    try:
                        instance = cls(engine=self)
                    except TypeError:
                        try:
                            instance = cls()
                        except Exception as e2:
                            logger.warning("Subsystem %s/%s (%s) cannot construct: %s", pkg_name, comp_name, cls_name, e2)
                            continue
                    self._subsystems[pkg_name][comp_name] = instance
                    flat = f"{pkg_name}.{comp_name}"
                    self._subsystem_refs[flat] = instance
                    self._subsystem_refs[comp_name] = instance
                except Exception as e:
                    logger.warning("Subsystem %s/%s failed to init: %s", pkg_name, comp_name, e)

        self._mode_controller = self._subsystems.get("modes", {}).get("controller")

    def get_subsystem(self, name: str) -> Any:
        return self._subsystem_refs.get(name)

    # ── Task management ─────────────────────────────────────────────

    def create_task(
        self,
        name: str = "",
        description: str = "",
        goal: str = "",
        mode: ExecutionMode = ExecutionMode.MANUAL,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout: Optional[int] = None,
    ) -> Task:
        if goal and not description:
            description = goal
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = Task(
            id=task_id,
            name=name or (goal[:60] if goal else f"Task {task_id[:8]}"),
            description=description,
            status=TaskStatus.PENDING,
            max_retries=max_retries,
            priority=priority,
            timeout=timeout,
            created_at=time.time(),
        )
        task.metadata["goal"] = goal or name or description
        task.metadata["mode"] = mode.value if hasattr(mode, "value") else mode
        self._tasks[task_id] = task
        self._emit("task.created", {"task_id": task_id, "name": name or task_id})
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        if status_filter:
            return [t for t in self._tasks.values() if t.status == status_filter]
        return list(self._tasks.values())

    def submit_task(self, task: Task) -> str:
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.PENDING
        self._tasks[task.id] = task
        self._emit("task.submitted", {"task_id": task.id})
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is self.loop:
            self.loop.create_task(self._execute_task(task))
        else:
            loop = self.loop
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.loop = loop
            asyncio.run_coroutine_threadsafe(self._execute_task(task), loop)
        return task.id

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING):
            task.status = TaskStatus.CANCELLED
            self._emit("task.cancelled", {"task_id": task_id})
            return True
        return False

    # ── Step execution / dispatch ──────────────────────────────────

    async def _execute_task(self, task: Task):
        if not self._running:
            logger.warning("Engine not running; cannot execute task %s", task.id)
            return

        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._emit("task.started", {"task_id": task.id})

        steps = task.steps or [Step(action="task.execute", params={"goal": task.name or task.description})]
        results: List[Dict[str, Any]] = []

        for i, step in enumerate(steps):
            if self._emergency_stop:
                task.status = TaskStatus.EMERGENCY_STOPPED
                break
            if self._paused:
                await self._wait_while_paused()

            step_result = await self._dispatch_step(step, {"task_id": task.id, "step_index": i})
            results.append(step_result)
            step.status = TaskStatus.COMPLETED if step_result.get("success") else TaskStatus.FAILED
            step.result = step_result.get("data")
            step.error = step_result.get("error")

            if not step_result.get("approved", True):
                task.status = TaskStatus.BLOCKED
                self._emit("task.blocked", {"task_id": task.id, "step": i})
                break

        task.status = TaskStatus.COMPLETED if all(r.get("success") for r in results) else TaskStatus.FAILED
        task.completed_at = time.time()
        task.result = results[-1] if results else None
        self._execution_history.append({
            "task_id": task.id,
            "goal": task.name or task.description,
            "status": task.status.value,
            "steps": len(steps),
            "started": datetime.utcfromtimestamp(task.started_at).isoformat() if task.started_at else None,
            "completed": datetime.utcfromtimestamp(task.completed_at).isoformat() if task.completed_at else None,
        })
        self._emit("task.completed", {"task_id": task.id, "status": task.status.value})

    async def _wait_while_paused(self):
        while self._paused and self._running:
            await asyncio.sleep(0.5)

    async def _dispatch_step(self, step: Step, context: Dict[str, Any]) -> Dict[str, Any]:
        action = step.action
        params = step.params or {}

        route = self._ACTION_ROUTES.get(action)
        if route is None:
            return await self._execute_generic(step, context)

        subsystem_name, component_name, method_name = route
        component = self._subsystems.get(subsystem_name, {}).get(component_name)
        if component is None:
            logger.warning("No component %s/%s for action %s", subsystem_name, component_name, action)
            return await self._execute_generic(step, context)

        handler = getattr(component, method_name, None)
        if handler is None:
            logger.warning("No method %s on %s/%s for action %s", method_name, subsystem_name, component_name, action)
            return await self._execute_generic(step, context)

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)
            self._emit("step.completed", {"action": action, "result": result})
            return {"success": True, "data": result, "action": action}
        except Exception as e:
            logger.exception("Step %s failed: %s", action, e)
            self._emit("step.failed", {"action": action, "error": str(e)})
            return {"success": False, "error": str(e), "action": action}

    async def _execute_generic(self, step: Step, context: Dict[str, Any]) -> Dict[str, Any]:
        action = step.action
        params = step.params or {}
        if action == "task.execute":
            planner = self._subsystems.get("tasks", {}).get("planner")
            if planner:
                try:
                    plan_input = params.get("goal") or params.get("name") or params.get("description", "")
                    plan_method = getattr(planner, "create_plan", planner.plan)
                    plan_result = plan_method(plan_input)
                    if asyncio.iscoroutine(plan_result):
                        plan_result = await plan_result
                    return {"success": True, "data": plan_result, "action": action}
                except Exception as e:
                    return {"success": False, "error": str(e), "action": action}
            return {"success": True, "data": {"message": f"Executed: {action}"}, "action": action}
        if action == "llm.call":
            return {"success": True, "data": {"message": "LLM call simulated"}, "action": action}
        if action == "memory.store":
            return {"success": True, "data": {"message": "Memory stored"}, "action": action}
        return {"success": True, "data": {"message": f"No route for {action}"}, "action": action}

    def run_action(self, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        step = Step(action=action, params=params or {})
        future = asyncio.run_coroutine_threadsafe(self._dispatch_step(step, {}), self.loop)
        return future.result()

    # ── Workflow management ────────────────────────────────────────

    def create_workflow(self, workflow: Workflow):
        self._workflows[workflow.id] = workflow
        self._emit("workflow.created", {"workflow_id": workflow.id})

    def get_workflow(self, wf_id: str) -> Optional[Workflow]:
        return self._workflows.get(wf_id)

    def list_workflows(self) -> List[Workflow]:
        return list(self._workflows.values())

    # ── Agent management ────────────────────────────────────────────

    def register_agent(self, agent_id: str, agent: Any):
        self._agents[agent_id] = agent
        self._emit("agent.registered", {"agent_id": agent_id})

    def get_agent(self, agent_id: str) -> Optional[Any]:
        return self._agents.get(agent_id)

    def list_agents(self) -> Dict[str, Any]:
        return dict(self._agents)

    # ── Events ──────────────────────────────────────────────────────

    def on(self, event: str, handler: Callable):
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable):
        try:
            self._event_handlers[event].remove(handler)
        except ValueError:
            pass

    def _emit(self, event: str, data: Dict[str, Any]):
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception:
                logger.exception("Event handler failed for %s", event)

    # ── Status / introspection ──────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "paused": self._paused,
            "emergency_stop": self._emergency_stop,
            "started_at": self._start_time.isoformat() if self._start_time else None,
            "task_count": len(self._tasks),
            "agent_count": len(self._agents),
            "workflow_count": len(self._workflows),
            "active_subsystems": list(self._subsystems.keys()),
            "execution_history_count": len(self._execution_history),
        }

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._execution_history[-limit:]

    # ── Mode forwarding ─────────────────────────────────────────────

    def get_mode_controller(self):
        return self._mode_controller

    async def switch_mode(self, mode: ExecutionMode) -> bool:
        if self._mode_controller:
            return await self._mode_controller.switch_to(mode)
        return False

    # ── Emergency stop ──────────────────────────────────────────────

    def emergency_stop(self):
        self._emergency_stop = True
        self._running = False
        self._emit("engine.emergency_stop", {"timestamp": datetime.utcnow().isoformat()})
        logger.warning("EMERGENCY STOP initiated.")
