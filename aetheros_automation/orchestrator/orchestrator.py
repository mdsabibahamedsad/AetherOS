from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from aetheros_automation.models.models import (
    AgentRole, ApprovalAction, ApprovalResponse, AutomationConfig,
    ExecutionMode, FailureType, GraphExecutionMode, RiskLevel,
    Task, TaskPriority, TaskStatus, Workflow,
)
from aetheros_automation.orchestrator.types import AgentAssignment, AgentMessage, ExecutionState, OrchestrationPlan, OrchestrationTask
from aetheros_automation.orchestrator.execution_engine import ExecutionEngine
from aetheros_automation.orchestrator.checkpoint import CheckpointManager
from aetheros_automation.lifecycle.states import LifecycleState
from aetheros_automation.lifecycle.manager import AgentLifecycle, LifecycleRegistry
from aetheros_automation.multi_agent.collaboration import AgentCollaborationManager
from aetheros_automation.routing.model_router import ModelRouter
from aetheros_automation.recovery.retry import RetryHandler
from aetheros_automation.validation.validator import ResultValidator
from aetheros_automation.templates.templates import TaskTemplateManager
from aetheros_automation.nlp.nlp_automation import NLPAutomationEngine

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    def __init__(
        self,
        config: AutomationConfig | None = None,
        execution_engine: ExecutionEngine | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        collaboration_manager: AgentCollaborationManager | None = None,
        model_router: ModelRouter | None = None,
        retry_handler: RetryHandler | None = None,
        validator: ResultValidator | None = None,
        template_manager: TaskTemplateManager | None = None,
        nlp_engine: NLPAutomationEngine | None = None,
    ):
        self.config = config or AutomationConfig()
        self.execution_engine = execution_engine or ExecutionEngine()
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.collaboration_manager = collaboration_manager or AgentCollaborationManager()
        self.model_router = model_router or ModelRouter()
        self.retry_handler = retry_handler or RetryHandler()
        self.validator = validator or ResultValidator()
        self.template_manager = template_manager or TaskTemplateManager()
        self.nlp_engine = nlp_engine or NLPAutomationEngine()

        self._plans: dict[str, OrchestrationPlan] = {}
        self._execution_states: dict[str, ExecutionState] = {}
        self._agent_assignments: dict[str, AgentAssignment] = {}
        self._sub_agents: dict[str, list[str]] = {}
        self._agent_messages: list[AgentMessage] = []
        self._event_handlers: dict[str, list[Callable]] = {}
        self._active_agents: dict[str, dict[str, Any]] = {}
        self._limits: dict[str, Any] = self._default_limits()

        self._lifecycle = LifecycleRegistry()
        self._lifecycle_events = True

        # Resolve the persistent orchestrations dir.  Uses the profile-aware
        # AETHEROS_HOME when no explicit path is configured so each profile
        # gets its own state (see AGENTS.md "Profiles").
        try:
            from aetheros_constants import get_aetheros_home
            _default_orch_dir = str(get_aetheros_home() / "automation" / "orchestrations")
        except Exception:  # pragma: no cover - fallback for standalone use
            _default_orch_dir = os.path.expanduser("~/.aetheros/automation/orchestrations")
        self._orchestrations_dir = os.path.expanduser(
            self.config.metadata.get("orchestrations_dir", _default_orch_dir)
        ) if hasattr(self.config, 'metadata') else _default_orch_dir
        os.makedirs(self._orchestrations_dir, exist_ok=True)

        # Bridge the execution engine's tool-level events onto the
        # orchestrator's event bus so subscribers see the whole flow.
        try:
            self.execution_engine.on("tool.called", lambda d: self._emit("tool.called", d))
            self.execution_engine.on("tool.started", lambda d: self._emit("tool.started", d))
            self.execution_engine.on("tool.completed", lambda d: self._emit("tool.completed", d))
        except AttributeError:
            pass

    def _default_limits(self) -> dict[str, Any]:
        return {
            "max_steps": 100,
            "max_time": 3600.0,
            "max_cost": 10.0,
            "max_tokens": 1000000,
            "max_sub_agents": 10,
            "max_parallel_tasks": 5,
            "max_tool_calls": 500,
        }

    def on(self, event: str, handler: Callable):
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable):
        if event in self._event_handlers:
            try:
                self._event_handlers[event].remove(handler)
            except ValueError:
                pass

    def _emit(self, event: str, data: dict[str, Any]):
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception:
                logger.exception("Event handler failed for %s", event)

    # ── lifecycle integration ────────────────────────────────────────────

    def _transition(self, entity_id: str, target: LifecycleState, reason: str = ""):
        """Move a plan/task through the unified lifecycle (see
        ``aetheros_automation.lifecycle``). Never raises into the caller's
        execution path; illegal transitions are logged and skipped."""
        if not getattr(self, "_lifecycle_events", True):
            return None
        try:
            tracker = self._lifecycle.ensure(entity_id)
            tracker.transition(target, reason=reason)
            self._emit("task.state_changed", {
                "entity_id": entity_id,
                "state": target.value,
                "reason": reason,
            })
            return tracker
        except Exception as exc:
            logger.debug("Lifecycle transition skipped for %s: %s", entity_id, exc)
            return None

    def lifecycle(self, entity_id: str) -> AgentLifecycle | None:
        return self._lifecycle.get(entity_id)

    def lifecycle_snapshot(self) -> list[dict[str, Any]]:
        return self._lifecycle.snapshot()

    async def understand_objective(self, user_request: str) -> OrchestrationPlan:
        plan = OrchestrationPlan(
            id=uuid.uuid4().hex[:12],
            goal=user_request,
            created_at=time.time(),
        )
        self._plans[plan.id] = plan
        self._emit("plan.analyzing", {"plan_id": plan.id, "goal": user_request})
        return plan

    async def analyze_task(self, plan: OrchestrationPlan) -> OrchestrationPlan:
        self._emit("plan.analyzing", {"plan_id": plan.id})
        return plan

    async def create_execution_plan(self, plan: OrchestrationPlan) -> OrchestrationPlan:
        tasks = await self._decompose_into_subtasks(plan)
        plan.subtasks = tasks
        plan.execution_graph = self._build_execution_graph(tasks)
        plan.estimated_cost = await self._estimate_cost(plan)
        plan.estimated_time = await self._estimate_time(plan)
        plan.risk_level = await self._assess_risk(plan)
        self._emit("plan.created", {"plan_id": plan.id, "task_count": len(tasks)})
        self._transition(plan.id, LifecycleState.PLANNING, "plan created")
        return plan

    async def _decompose_into_subtasks(self, plan: OrchestrationPlan) -> list[OrchestrationTask]:
        goal = plan.goal.lower()
        tasks: list[OrchestrationTask] = []

        segments = [s.strip() for s in goal.replace("?", ".").replace("!", ".").split(".") if s.strip()]

        for i, segment in enumerate(segments[:15]):
            seg_lower = segment.lower()
            role = self._infer_role(seg_lower)
            requires_approval = self._check_approval_required(seg_lower)
            approval_actions = self._check_approval_actions(seg_lower)

            task = OrchestrationTask(
                id=uuid.uuid4().hex[:12],
                name=segment[:80],
                description=segment,
                agent_role=role,
                tools=self._infer_tools(seg_lower),
                dependencies=[],
                requires_approval=requires_approval,
                approval_actions=approval_actions,
                max_retries=3,
                estimated_duration=self._estimate_task_duration(seg_lower),
                created_at=time.time(),
            )
            tasks.append(task)

        for i in range(1, len(tasks)):
            tasks[i].dependencies.append(tasks[i - 1].id)

        return tasks

    def _infer_role(self, text: str) -> AgentRole:
        role_map: list[tuple[list[str], AgentRole]] = [
            (["research", "search", "investigate", "find", "gather", "collect"], AgentRole.RESEARCH),
            (["code", "develop", "program", "implement", "build", "create app"], AgentRole.DEVELOPER),
            (["write", "document", "draft", "compose", "author"], AgentRole.WRITER),
            (["browse", "navigate", "scrape", "web"], AgentRole.BROWSER),
            (["test", "verify", "validate", "qa"], AgentRole.QA),
            (["deploy", "release", "publish"], AgentRole.DEPLOYMENT),
            (["security", "audit", "permission", "threat"], AgentRole.SECURITY),
            (["remember", "store", "memory", "recall"], AgentRole.MEMORY),
            (["plan", "organize", "coordinate"], AgentRole.PLANNER),
            (["creative", "design", "art", "generate", "imagine"], AgentRole.CREATIVE),
            (["data", "analyze", "statistic", "dashboard", "report"], AgentRole.DATA),
            (["email", "message", "communicate", "notify", "send"], AgentRole.COMMUNICATION),
            (["review", "check", "proofread", "examine", "inspect"], AgentRole.REVIEW),
            (["file", "save", "open", "read file", "write file"], AgentRole.FILE),
        ]
        for keywords, role in role_map:
            if any(k in text for k in keywords):
                return role
        return AgentRole.COORDINATOR

    def _infer_tools(self, text: str) -> list[str]:
        tools: list[str] = []
        tool_map: list[tuple[list[str], str]] = [
            (["search", "research", "web", "find"], "web_search"),
            (["browse", "navigate", "web page"], "browser_navigate"),
            (["file", "save", "read", "write"], "file_operations"),
            (["terminal", "command", "run", "shell"], "terminal"),
            (["code", "develop", "program"], "code_execution"),
            (["email", "send"], "send_message"),
            (["image", "picture", "vision"], "vision"),
            (["data", "analyze", "chart"], "data_analysis"),
        ]
        for keywords, tool in tool_map:
            if any(k in text for k in keywords):
                tools.append(tool)
        return tools

    def _check_approval_required(self, text: str) -> bool:
        keywords = ["delete", "remove", "destroy", "payment", "spend", "buy",
                     "install", "modify system", "access sensitive"]
        return any(k in text for k in keywords)

    def _check_approval_actions(self, text: str) -> list[ApprovalAction]:
        actions: list[ApprovalAction] = []
        if any(k in text for k in ["delete", "remove", "destroy"]):
            actions.append(ApprovalAction.DESTRUCTIVE_ACTION)
        if any(k in text for k in ["payment", "spend", "buy"]):
            actions.append(ApprovalAction.PAYMENT)
        if any(k in text for k in ["password", "token", "key", "secret", "credential"]):
            actions.append(ApprovalAction.SENSITIVE_DATA)
        if any(k in text for k in ["email", "message", "send to", "post"]):
            actions.append(ApprovalAction.EXTERNAL_COMMUNICATION)
        if any(k in text for k in ["install", "modify system", "change config"]):
            actions.append(ApprovalAction.DANGEROUS_ACTION)
        if any(k in text for k in ["permission", "escalate", "admin"]):
            actions.append(ApprovalAction.PERMISSION_ESCALATION)
        return actions

    def _estimate_task_duration(self, text: str) -> float:
        if any(k in text for k in ["research", "investigate", "find"]):
            return 120.0
        if any(k in text for k in ["code", "develop", "implement", "build"]):
            return 300.0
        if any(k in text for k in ["browse", "scrape", "navigate"]):
            return 60.0
        if any(k in text for k in ["analyze", "data", "report"]):
            return 180.0
        if any(k in text for k in ["write", "compose", "draft"]):
            return 120.0
        return 60.0

    def _build_execution_graph(self, tasks: list[OrchestrationTask]) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []

        for task in tasks:
            nodes.append({
                "id": task.id,
                "name": task.name,
                "status": task.status.value,
                "role": task.agent_role.value,
                "mode": task.execution_mode.value,
            })
            for dep_id in task.dependencies:
                edges.append({"from": dep_id, "to": task.id})

        levels: list[list[str]] = []
        remaining = {t.id for t in tasks}
        completed: set[str] = set()

        while remaining:
            level: list[str] = []
            for tid in list(remaining):
                task = next((t for t in tasks if t.id == tid), None)
                if task and all(d in completed for d in task.dependencies):
                    level.append(tid)
            if not level:
                level = list(remaining)
            levels.append(level)
            for tid in level:
                remaining.discard(tid)
                completed.add(tid)

        return {
            "nodes": nodes,
            "edges": edges,
            "levels": levels,
        }

    async def _estimate_cost(self, plan: OrchestrationPlan) -> float:
        base_cost = len(plan.subtasks) * 0.01
        for task in plan.subtasks:
            if task.agent_role in (AgentRole.DEVELOPER, AgentRole.CREATIVE):
                base_cost += 0.02
        return base_cost

    async def _estimate_time(self, plan: OrchestrationPlan) -> float:
        total = sum(t.estimated_duration for t in plan.subtasks)
        return total

    async def _assess_risk(self, plan: OrchestrationPlan) -> RiskLevel:
        high_risk_count = 0
        for task in plan.subtasks:
            if task.requires_approval:
                high_risk_count += 1
            if task.agent_role in (AgentRole.SECURITY, AgentRole.DEPLOYMENT):
                high_risk_count += 1
        if high_risk_count >= 3:
            return RiskLevel.CRITICAL
        if high_risk_count >= 2:
            return RiskLevel.HIGH
        if high_risk_count >= 1:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    async def select_agent(self, task: OrchestrationTask) -> AgentAssignment:
        assignment = AgentAssignment(
            agent_id=uuid.uuid4().hex[:12],
            role=task.agent_role,
            name=f"{task.agent_role.value}-{task.id[:8]}",
            tools=task.tools,
            permissions=self._get_role_permissions(task.agent_role),
            instructions=task.description,
        )

        model_info = await self.model_router.select_model(
            task_type=task.agent_role.value,
            tools=task.tools,
        )
        assignment.model = model_info.get("model", "gpt-4o")
        assignment.provider = model_info.get("provider", "openai")

        self._agent_assignments[assignment.agent_id] = assignment
        return assignment

    def _get_role_permissions(self, role: AgentRole) -> list[str]:
        base = ["filesystem_read", "network"]
        role_perms: dict[AgentRole, list[str]] = {
            AgentRole.DEVELOPER: base + ["filesystem_write", "terminal", "execute_code", "git"],
            AgentRole.BROWSER: base + ["browser"],
            AgentRole.RESEARCH: base + ["browser", "web_search"],
            AgentRole.WRITER: base + ["filesystem_write"],
            AgentRole.SECURITY: base + ["filesystem_write", "terminal", "audit"],
            AgentRole.DEPLOYMENT: base + ["filesystem_write", "terminal", "network"],
            AgentRole.CREATIVE: base + ["filesystem_write", "image_generation"],
            AgentRole.DATA: base + ["filesystem_write", "code_execution"],
            AgentRole.COMMUNICATION: base + ["send_email", "send_message"],
            AgentRole.FILE: base + ["filesystem_write", "filesystem_delete"],
        }
        return role_perms.get(role, base)

    async def create_sub_agent(
        self,
        parent_id: str,
        role: AgentRole,
        goal: str,
        instructions: str = "",
        limited: bool = True,
    ) -> AgentAssignment:
        sub = AgentAssignment(
            agent_id=uuid.uuid4().hex[:12],
            role=role,
            name=f"sub-{role.value}-{uuid.uuid4().hex[:6]}",
            tools=self._infer_tools(goal),
            permissions=self._get_role_permissions(role),
            instructions=instructions or goal,
            parent_agent_id=parent_id,
            is_sub_agent=True,
            limits={
                "max_steps": 20 if limited else 50,
                "max_time": 300.0 if limited else 600.0,
                "max_tool_calls": 50 if limited else 200,
            },
        )

        if parent_id not in self._sub_agents:
            self._sub_agents[parent_id] = []
        self._sub_agents[parent_id].append(sub.agent_id)
        self._agent_assignments[sub.agent_id] = sub
        self._emit("sub_agent.created", {
            "parent_id": parent_id,
            "sub_agent_id": sub.agent_id,
            "role": role.value,
        })
        return sub

    async def terminate_sub_agent(self, sub_agent_id: str):
        sub = self._agent_assignments.pop(sub_agent_id, None)
        if sub:
            parent = sub.parent_agent_id
            if parent in self._sub_agents:
                try:
                    self._sub_agents[parent].remove(sub_agent_id)
                except ValueError:
                    pass
            self._emit("sub_agent.terminated", {
                "sub_agent_id": sub_agent_id,
                "parent_id": parent,
            })

    async def send_agent_message(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: str = "text",
        content: str = "",
        data: Any = None,
        task_id: str = "",
    ) -> AgentMessage:
        msg = AgentMessage(
            id=uuid.uuid4().hex[:12],
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            data=data,
            task_id=task_id,
            created_at=time.time(),
        )
        self._agent_messages.append(msg)
        self._emit("agent.message", {
            "message_id": msg.id,
            "from": sender_id,
            "to": receiver_id,
            "type": message_type,
        })
        return msg

    def get_agent_messages(self, agent_id: str, limit: int = 50) -> list[AgentMessage]:
        return [m for m in self._agent_messages if m.receiver_id == agent_id][-limit:]

    async def execute_plan(self, plan_id: str) -> dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        state = ExecutionState(
            plan_id=plan_id,
            pending_tasks=[t.id for t in plan.subtasks],
            started_at=time.time(),
        )
        self._execution_states[plan_id] = state
        self._emit("plan.execution_started", {"plan_id": plan_id})
        self._transition(plan_id, LifecycleState.EXECUTING, "execution started")

        results: dict[str, Any] = {}
        graph = plan.execution_graph
        levels = graph.get("levels", [])

        for level_idx, level in enumerate(levels):
            tasks_in_level = [t for t in plan.subtasks if t.id in level]
            parallel_tasks = [t for t in tasks_in_level
                              if t.execution_mode == GraphExecutionMode.PARALLEL]
            sequential_tasks = [t for t in tasks_in_level
                                if t.execution_mode != GraphExecutionMode.PARALLEL]

            if parallel_tasks:
                parallel_results = await asyncio.gather(
                    *[self._execute_single_task(t, plan, state, results) for t in parallel_tasks],
                    return_exceptions=True,
                )
                for t, r in zip(parallel_tasks, parallel_results):
                    if isinstance(r, Exception):
                        results[t.id] = {"error": str(r), "success": False}
                        if t.id in state.running_tasks:
                            state.running_tasks.remove(t.id)
                        if t.id not in state.failed_tasks:
                            state.failed_tasks.append(t.id)
                    else:
                        results[t.id] = r

            for task in sequential_tasks:
                result = await self._execute_single_task(task, plan, state, results)
                results[task.id] = result
                if not result.get("success") and task.execution_mode != GraphExecutionMode.FALLBACK:
                    if self.config.metadata.get("stop_on_failure", True) \
                       if hasattr(self.config, 'metadata') else True:
                        if task.id in state.running_tasks:
                            state.running_tasks.remove(task.id)
                        if task.id not in state.failed_tasks:
                            state.failed_tasks.append(task.id)
                        self._emit("plan.failed", {"plan_id": plan_id, "task_id": task.id})
                        self._transition(plan_id, LifecycleState.FAILED, "task failed")
                        result = self._build_result(plan, state, results, False)
                        try:
                            self.save_execution_history(plan_id, result)
                        except Exception:
                            logger.exception("Failed to save execution history for %s", plan_id)
                        return result

        state.updated_at = time.time()
        success = len(state.failed_tasks) == 0
        self._emit("plan.completed", {"plan_id": plan_id, "success": success})
        if success:
            self._transition(plan_id, LifecycleState.COMPLETED, "plan completed")
        else:
            self._transition(plan_id, LifecycleState.FAILED, "tasks failed")
        result = self._build_result(plan, state, results, success)
        try:
            self.save_execution_history(plan_id, result)
        except Exception:
            logger.exception("Failed to save execution history for %s", plan_id)
        return result

    async def _execute_single_task(
        self,
        task: OrchestrationTask,
        plan: OrchestrationPlan,
        state: ExecutionState,
        previous_results: dict[str, Any],
    ) -> dict[str, Any]:
        self._emit("task.started", {"task_id": task.id, "name": task.name})
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._transition(f"task:{task.id}", LifecycleState.EXECUTING, "task started")
        if task.id in state.pending_tasks:
            state.pending_tasks.remove(task.id)
        state.running_tasks.append(task.id)
        state.current_task_id = task.id

        if task.requires_approval:
            self._transition(f"task:{task.id}", LifecycleState.WAITING, "approval required")
            approved = await self._request_approval(task)
            if not approved:
                task.status = TaskStatus.BLOCKED
                self._transition(f"task:{task.id}", LifecycleState.BLOCKED, "approval denied")
                if task.id in state.pending_tasks:
                    state.pending_tasks.remove(task.id)
                if task.id in state.running_tasks:
                    state.running_tasks.remove(task.id)
                state.failed_tasks.append(task.id)
                return {"success": False, "error": "Approval denied", "task_id": task.id}

        agent = await self.select_agent(task)

        self._active_agents[agent.agent_id] = {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "role": agent.role.value,
            "task_id": task.id,
            "status": "running",
            "model": agent.model,
            "provider": agent.provider,
            "started_at": time.time(),
        }
        self._emit("agent.started", {"agent_id": agent.agent_id, "task_id": task.id})

        try:
            result = await self.execution_engine.execute_task(
                task=task,
                agent=agent,
                context={"previous_results": previous_results, "plan_id": plan.id},
            )

            is_valid, validation_message = await self.validator.validate(
                result=result,
                task=task,
            )
            if is_valid:
                self._transition(f"task:{task.id}", LifecycleState.REVIEWING, "validation passed")
        except Exception as exc:
            is_valid = False
            validation_message = f"Execution error: {exc}"
            result = {"success": False, "error": str(exc), "task_id": task.id}

        if not is_valid:
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                wait = self.retry_handler.get_backoff(task.retry_count)
                self._emit("task.retrying", {
                    "task_id": task.id,
                    "attempt": task.retry_count,
                    "max_retries": task.max_retries,
                    "wait": wait,
                })
                await asyncio.sleep(wait)

                fallback_model = await self.model_router.get_fallback(
                    model=agent.model, provider=agent.provider
                )
                if fallback_model:
                    agent.model = fallback_model["model"]
                    agent.provider = fallback_model["provider"]

                try:
                    result = await self.execution_engine.execute_task(
                        task=task, agent=agent,
                        context={"previous_results": previous_results, "retry": True},
                    )
                    is_valid, validation_message = await self.validator.validate(
                        result=result, task=task
                    )
                except Exception as exc:
                    is_valid = False
                    validation_message = f"Execution error: {exc}"
                    result = {"success": False, "error": str(exc), "task_id": task.id}

            if not is_valid:
                task.status = TaskStatus.FAILED
                task.error = validation_message
                self._emit("task.failed", {"task_id": task.id, "error": validation_message})
                self._transition(f"task:{task.id}", LifecycleState.FAILED, "task failed")
                self._active_agents[agent.agent_id]["status"] = "failed"
                if task.id in state.running_tasks:
                    state.running_tasks.remove(task.id)
                state.failed_tasks.append(task.id)
                return {"success": False, "error": validation_message, "task_id": task.id}

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.actual_duration = task.completed_at - task.started_at
        task.result = result
        task.progress = 100.0

        self._active_agents[agent.agent_id]["status"] = "completed"
        self._emit("task.completed", {"task_id": task.id, "duration": task.actual_duration})
        self._transition(f"task:{task.id}", LifecycleState.COMPLETED, "task completed")
        if task.id in state.running_tasks:
            state.running_tasks.remove(task.id)
        state.completed_tasks.append(task.id)
        state.updated_at = time.time()

        checkpoint_id = await self.checkpoint_manager.save_checkpoint(
            plan_id=plan.id,
            task_id=task.id,
            result=result,
            state=self._execution_states.get(plan.id),
        )
        if checkpoint_id:
            task.checkpoint_data["checkpoint_id"] = checkpoint_id

        return {"success": True, "result": result, "task_id": task.id}

    async def _request_approval(self, task: OrchestrationTask) -> bool:
        self._emit("approval.requested", {
            "task_id": task.id,
            "name": task.name,
            "actions": [a.value for a in task.approval_actions],
            "description": task.description,
        })

        if not hasattr(self, '_approval_callback') or not self._approval_callback:
            return True

        callback = self._approval_callback
        response = await callback(task)
        return response in (ApprovalResponse.APPROVE_ONCE,
                           ApprovalResponse.APPROVE_SESSION,
                           ApprovalResponse.ALWAYS_ALLOW)

    def set_approval_callback(self, callback: Callable):
        self._approval_callback = callback

    def set_limits(self, limits: dict[str, Any]):
        self._limits.update(limits)

    def _build_result(
        self,
        plan: OrchestrationPlan,
        state: ExecutionState,
        results: dict[str, Any],
        success: bool,
    ) -> dict[str, Any]:
        return {
            "plan_id": plan.id,
            "goal": plan.goal,
            "success": success,
            "results": results,
            "completed_tasks": state.completed_tasks,
            "failed_tasks": state.failed_tasks,
            "duration": time.time() - state.started_at,
            "estimated_cost": plan.estimated_cost,
            "total_cost": sum(
                r.get("cost", 0) for r in results.values()
                if isinstance(r, dict)
            ),
        }

    async def pause_plan(self, plan_id: str):
        state = self._execution_states.get(plan_id)
        if state:
            state.paused = True
            self._emit("plan.paused", {"plan_id": plan_id})
            self._transition(plan_id, LifecycleState.PAUSED, "plan paused")

    async def resume_plan(self, plan_id: str):
        state = self._execution_states.get(plan_id)
        if state:
            state.paused = False
            self._emit("plan.resumed", {"plan_id": plan_id})
            self._transition(plan_id, LifecycleState.EXECUTING, "plan resumed")

    async def cancel_plan(self, plan_id: str):
        state = self._execution_states.get(plan_id)
        if state:
            state.cancelled = True
            self._emit("plan.cancelled", {"plan_id": plan_id})
            self._transition(plan_id, LifecycleState.CANCELLED, "plan cancelled")

    async def archive_plan(self, plan_id: str):
        """Move a completed plan to the terminal ``Archived`` state."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        self._emit("plan.archived", {"plan_id": plan_id})
        self._transition(plan_id, LifecycleState.ARCHIVED, "plan archived")

    async def restart_plan(self, plan_id: str):
        state = self._execution_states.get(plan_id)
        if state:
            state.completed_tasks.clear()
            state.failed_tasks.clear()
            state.running_tasks.clear()
            state.pending_tasks = [t.id for t in self._plans[plan_id].subtasks]
            state.paused = False
            state.cancelled = False
            state.started_at = time.time()
            self._emit("plan.restarted", {"plan_id": plan_id})

    async def retry_failed_tasks(self, plan_id: str):
        plan = self._plans.get(plan_id)
        state = self._execution_states.get(plan_id)
        if not plan or not state:
            return

        failed_ids = list(state.failed_tasks)
        state.failed_tasks.clear()

        for task_id in failed_ids:
            task = next((t for t in plan.subtasks if t.id == task_id), None)
            if task:
                task.retry_count = 0
                task.status = TaskStatus.PENDING
                task.error = ""
                state.pending_tasks.append(task_id)

        self._emit("plan.retry", {"plan_id": plan_id, "tasks": failed_ids})

    def get_plan(self, plan_id: str) -> OrchestrationPlan | None:
        return self._plans.get(plan_id)

    def get_state(self, plan_id: str) -> ExecutionState | None:
        return self._execution_states.get(plan_id)

    def list_plans(self) -> list[OrchestrationPlan]:
        return list(self._plans.values())

    def get_active_agents(self) -> list[dict[str, Any]]:
        return [
            a for a in self._active_agents.values()
            if a["status"] == "running"
        ]

    def get_agent_activity(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._active_agents.values())[-limit:]

    async def process_natural_language(self, request: str) -> OrchestrationPlan:
        plan = await self.nlp_engine.process(request)
        self._plans[plan.id] = plan
        return plan

    async def run(
        self,
        goal: str,
        params: dict[str, Any] | None = None,
        approval_callback: Callable | None = None,
    ) -> dict[str, Any]:
        """Run a goal end-to-end: understand -> plan -> execute.

        Returns a dict with a ``summary`` key (plus full plan/result details),
        matching the surface used by ``aetheros_jarvis.mission.MissionManager``.
        """
        params = params or {}
        plan = await self.understand_objective(goal)
        if params.get("template"):
            plan = await self.run_from_template(params["template"], params)
        else:
            plan = await self.create_execution_plan(plan)
        if approval_callback is not None:
            self.set_approval_callback(approval_callback)
        result = await self.execute_plan(plan.id)
        result["summary"] = (
            f"{len(result.get('completed_tasks', []))} tasks completed for '{goal}'."
        )
        return result

    async def run_from_template(self, template_name: str, params: dict[str, Any]) -> OrchestrationPlan:
        template = self.template_manager.get_template(template_name)
        if template:
            plan = await self.template_manager.apply_template(template, params)
            self._plans[plan.id] = plan
            return plan
        raise ValueError(f"Template '{template_name}' not found")

    def save_plan(self, plan: OrchestrationPlan):
        path = os.path.join(self._orchestrations_dir, f"{plan.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            data = {
                "id": plan.id,
                "goal": plan.goal,
                "subtasks": [
                    {
                        "id": t.id, "name": t.name, "description": t.description,
                        "agent_role": t.agent_role.value,
                        "tools": t.tools, "dependencies": t.dependencies,
                        "execution_mode": t.execution_mode.value,
                        "status": t.status.value, "progress": t.progress,
                        "estimated_duration": t.estimated_duration,
                    }
                    for t in plan.subtasks
                ],
                "estimated_cost": plan.estimated_cost,
                "estimated_time": plan.estimated_time,
                "risk_level": plan.risk_level.value,
                "created_at": plan.created_at,
                "execution_graph": plan.execution_graph,
            }
            json.dump(data, f, indent=2, default=str)

    def save_execution_history(self, plan_id: str, result: dict[str, Any]) -> str:
        """Durably record a plan's execution outcome (results, task statuses,
        lifecycle transitions) keyed by plan id.

        Returns the history file path. ``~/.aetheros/automation/orchestrations/
        <plan_id>.history.json`` — the same directory as :meth:`save_plan`.
        """
        plan = self._plans.get(plan_id)
        lifecycle = self._lifecycle.get(plan_id)
        history = {
            "plan_id": plan_id,
            "goal": (plan.goal if plan else ""),
            "saved_at": time.time(),
            "success": result.get("success", False),
            "duration": result.get("duration", 0.0),
            "completed_tasks": result.get("completed_tasks", []),
            "failed_tasks": result.get("failed_tasks", []),
            "task_statuses": {
                t.id: t.status.value
                for t in (plan.subtasks if plan else [])
            },
            "lifecycle": lifecycle.snapshot() if lifecycle else None,
        }
        path = os.path.join(self._orchestrations_dir, f"{plan_id}.history.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)
        return path

    def load_execution_history(self, plan_id: str) -> dict[str, Any] | None:
        path = os.path.join(self._orchestrations_dir, f"{plan_id}.history.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.exception("Failed to load execution history %s: %s", plan_id, e)
            return None

    def load_plan(self, plan_id: str) -> OrchestrationPlan | None:
        path = os.path.join(self._orchestrations_dir, f"{plan_id}.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            plan = OrchestrationPlan(
                id=data["id"], goal=data["goal"],
                estimated_cost=data.get("estimated_cost", 0.0),
                estimated_time=data.get("estimated_time", 0.0),
                risk_level=RiskLevel(data.get("risk_level", "low")),
                created_at=data.get("created_at", 0.0),
                execution_graph=data.get("execution_graph", {}),
            )
            for td in data.get("subtasks", []):
                task = OrchestrationTask(
                    id=td["id"], name=td["name"], description=td.get("description", ""),
                    agent_role=AgentRole(td.get("agent_role", "coordinator")),
                    tools=td.get("tools", []),
                    dependencies=td.get("dependencies", []),
                    execution_mode=GraphExecutionMode(td.get("execution_mode", "sequential")),
                    status=TaskStatus(td.get("status", "pending")),
                    progress=td.get("progress", 0.0),
                    estimated_duration=td.get("estimated_duration", 0.0),
                )
                plan.subtasks.append(task)
            return plan
        except Exception as e:
            logger.exception("Failed to load plan %s: %s", plan_id, e)
            return None
