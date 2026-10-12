from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    Plan, OrchestrationTask, TaskType, TaskStatus, OrchestrationResult, ExecutionGraph,
    GraphNode, GraphEdge, NodeType, FailurePolicy, AgentLimits,
)

logger = logging.getLogger(__name__)


class ExecutionEngine:
    def __init__(self, planner=None, graph_engine=None, event_bus=None, store=None):
        self.planner = planner
        self.graph_engine = graph_engine
        self.event_bus = event_bus
        self.store = store
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def execute(self, plan: Plan, orchestrator=None) -> OrchestrationResult:
        if not plan.tasks:
            return OrchestrationResult(success=True, status="completed")
        graph = plan.execution_graph or self.graph_engine.build_from_plan(plan)
        plan.execution_graph = graph
        result = OrchestrationResult(
            plan_id=plan.id,
            status="running",
        )
        start_time = time.time()
        plan.status = "running"
        plan.started_at = start_time
        completed: set[str] = set()
        failed: set[str] = set()
        results: dict[str, dict] = {}
        try:
            for level_idx, level in enumerate(graph.levels):
                level_tasks = []
                for task_id in level:
                    task = self._find_task(plan, task_id)
                    if task:
                        level_tasks.append(task)
                if not level_tasks:
                    continue
                pending_approval = any(
                    t.requires_approval and not self._check_approval(t, orchestrator)
                    for t in level_tasks
                )
                if pending_approval:
                    for task in level_tasks:
                        if task.requires_approval:
                            task.status = TaskStatus.WAITING_APPROVAL
                            self._emit_task_event("task.waiting_approval", task, plan)
                    plan.status = "waiting_approval"
                    if self.store:
                        self.store.save_plan(plan)
                    break
                parallel_group = [t for t in level_tasks if t.task_type == TaskType.PARALLEL]
                sequential_group = [t for t in level_tasks if t.task_type != TaskType.PARALLEL]
                if parallel_group:
                    parallel_results = await asyncio.gather(
                        *[self._execute_task(t, plan, orchestrator, results) for t in parallel_group],
                        return_exceptions=True,
                    )
                    for t, r in zip(parallel_group, parallel_results):
                        if isinstance(r, Exception):
                            failed.add(t.id)
                            result.errors.append(str(r))
                            self._emit_task_event("task.failed", t, plan, error=str(r))
                        else:
                            completed.add(t.id)
                            results[t.id] = r or {}
                            self._emit_task_event("task.completed", t, plan)
                for task in sequential_group:
                    self._emit_task_event("task.started", task, plan)
                    task_res = await self._execute_task(task, plan, orchestrator, results)
                    if task_res is None:
                        completed.add(task.id)
                        results[task.id] = {}
                        self._emit_task_event("task.completed", task, plan)
                    elif isinstance(task_res, dict) and task_res.get("error"):
                        failed.add(task.id)
                        result.errors.append(task_res["error"])
                        self._emit_task_event("task.failed", task, plan, error=task_res["error"])
                    else:
                        completed.add(task.id)
                        if task_res:
                            results[task.id] = task_res
                        self._emit_task_event("task.completed", task, plan)
                if failed:
                    break
        except asyncio.CancelledError:
            result.status = "cancelled"
        except Exception as e:
            logger.exception("Plan execution failed: %s", e)
            result.status = "failed"
            result.error = str(e)
            result.errors.append(str(e))
        elapsed = time.time() - start_time
        result.tasks_completed = len(completed)
        result.tasks_failed = len(failed)
        result.total_duration = elapsed
        if result.status == "running":
            result.status = "completed" if not failed else "failed"
        if not result.success and result.error:
            result.success = False
        elif failed:
            result.success = False
        else:
            result.success = True
        return result

    async def _execute_task(
        self,
        task: OrchestrationTask,
        plan: Plan,
        orchestrator: Any,
        results: dict[str, dict],
    ) -> Optional[dict]:
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        if self.event_bus:
            self.event_bus.emit("task.started", {
                "task_id": task.id,
                "plan_id": plan.id,
                "task_name": task.name,
                "agent_role": task.agent_role.value if hasattr(task.agent_role, 'value') else str(task.agent_role),
            })
        max_retries = task.max_retries
        retry_delay = task.retry_delay
        start_time = time.time()
        for attempt in range(max_retries + 1):
            try:
                if task.task_type in (TaskType.WAIT,):
                    delay = task.metadata.get("delay", 1.0)
                    await asyncio.sleep(delay)
                    task.output = {"waited": delay}
                    task.status = TaskStatus.COMPLETED
                    return task.output
                if task.task_type in (TaskType.NOTIFY,):
                    if self.event_bus:
                        self.event_bus.emit("task.notification", {
                            "task_id": task.id,
                            "message": task.metadata.get("message", ""),
                            "plan_id": plan.id,
                        })
                    task.status = TaskStatus.COMPLETED
                    return {"notified": True}
                if orchestrator and hasattr(orchestrator, 'agent_manager'):
                    agent = orchestrator.agent_manager.get_agent_for_role(task.agent_role)
                    if agent:
                        agent_instance = orchestrator.agent_manager.spawn_agent(
                            task.agent_role, task.id
                        )
                        if agent_instance:
                            task.agent_id = agent_instance.id
                            if self.event_bus:
                                self.event_bus.emit("agent.assigned", {
                                    "task_id": task.id,
                                    "agent_id": agent_instance.id,
                                    "agent_role": task.agent_role.value if hasattr(task.agent_role, 'value') else str(task.agent_role),
                                })
                            if attempt > 0:
                                task.status = TaskStatus.RETRYING
                            task.progress = 50.0
                            task.output = {
                                "agent_id": agent_instance.id,
                                "status": "assigned",
                            }
                            task.status = TaskStatus.COMPLETED
                            task.completed_at = time.time()
                            task.actual_duration = time.time() - start_time
                            return task.output
                if attempt > 0:
                    task.status = TaskStatus.RETRYING
                await asyncio.sleep(0.1)
                task.output = {"executed": True, "task_type": task.task_type.value if hasattr(task.task_type, 'value') else str(task.task_type)}
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.actual_duration = time.time() - start_time
                return task.output
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("Task %s attempt %d/%d failed: %s", task.id, attempt + 1, max_retries + 1, e)
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    retry_delay *= 2
                else:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = time.time()
                    task.actual_duration = time.time() - start_time
                    if self.event_bus:
                        self.event_bus.emit("task.failed", {
                            "task_id": task.id,
                            "plan_id": plan.id,
                            "error": str(e),
                            "attempts": attempt + 1,
                        })
                    return {"error": str(e), "attempts": attempt + 1}
        task.status = TaskStatus.FAILED
        task.completed_at = time.time()
        return {"error": "max retries exceeded"}

    def _find_task(self, plan: Plan, task_id: str) -> Optional[OrchestrationTask]:
        for task in plan.tasks:
            if task.id == task_id:
                return task
            for sub in task.subtasks:
                if sub.id == task_id:
                    return sub
        return None

    def _check_approval(self, task: OrchestrationTask, orchestrator: Any) -> bool:
        if not task.requires_approval:
            return True
        if hasattr(task, 'approval_status') and task.approval_status == "approved":
            return True
        return False

    def _emit_task_event(self, event: str, task: OrchestrationTask, plan: Plan, **extra):
        if self.event_bus:
            self.event_bus.emit(event, {
                "task_id": task.id,
                "plan_id": plan.id,
                "task_name": task.name,
                "agent_role": task.agent_role.value if hasattr(task.agent_role, 'value') else str(task.agent_role),
                "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                **extra,
            })

    async def cancel_task(self, task_id: str) -> bool:
        running = self._running_tasks.get(task_id)
        if running and not running.done():
            running.cancel()
            return True
        return False
