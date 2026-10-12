#!/usr/bin/env python3
"""
Command Gateway — Single Normalized Entry Point for All Requests

All user interactions (chat, voice, jarvis, hotkey, palette, automation, cron,
webhook, API, MCP) enter through this gateway. It normalizes requests into
TaskRequest objects, routes them through the capability system, and returns
results or task handles for long-running operations.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .models import Task, TaskRequest, TaskSource, TaskState, to_json_serializable
from .capability_registry import get_capability_registry
from .permission_model import get_permission_model
from .execution_engine import get_execution_engine
from .capability_router import get_capability_router

logger = logging.getLogger(__name__)


@dataclass
class GatewayConfig:
    """Configuration for the command gateway."""
    max_concurrent_tasks: int = 10
    default_timeout_seconds: int = 300
    enable_background_tasks: bool = True
    enable_streaming: bool = True
    auto_start_tasks: bool = True
    persist_tasks: bool = True
    task_retention_hours: int = 168  # 1 week


@dataclass
class TaskHandle:
    """Opaque handle for tracking a task."""
    task_id: str
    state: TaskState
    created_at: datetime
    source: TaskSource
    goal: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "source": self.source.value,
            "goal": self.goal,
        }


class CommandGateway:
    """
    Central command gateway for all AetherOS interactions.
    
    Normalizes all incoming requests (chat, voice, jarvis, automation, etc.)
    into TaskRequest objects and manages their lifecycle through the
    capability kernel.
    """
    
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = GatewayConfig(**(config or {}))
        self._tasks: Dict[str, Task] = {}
        self._task_handles: Dict[str, TaskHandle] = {}
        self._source_handlers: Dict[TaskSource, Callable] = {}
        self._lock = threading.RLock()
        self._task_counter = 0
        self._background_executor = None
        self._initialized = False
        
        # Component references (lazy-initialized)
        self._registry = None
        self._permission_model = None
        self._execution_engine = None
        self._router = None

    def _ensure_initialized(self) -> None:
        """Lazy initialization of components."""
        if self._initialized:
            return
        self._registry = get_capability_registry()
        self._permission_model = get_permission_model()
        self._execution_engine = get_execution_engine()
        self._router = get_capability_router()
        self._initialized = True

    def submit(self, request: TaskRequest) -> TaskHandle:
        """
        Submit a task request to the gateway.
        
        This is the main entry point for all external interactions.
        Returns a TaskHandle for tracking the task.
        """
        self._ensure_initialized()
        
        with self._lock:
            # Create task from request
            task = Task(
                id=request.id,
                goal=request.user_intent,
                request=request,
                state=TaskState.CREATED,
            )
            
            # Store task
            self._tasks[task.id] = task
            handle = TaskHandle(
                task_id=task.id,
                state=task.state,
                created_at=task.created_at,
                source=request.source,
                goal=request.user_intent,
            )
            self._task_handles[task.id] = handle
            
            # Process asynchronously if background tasks enabled
            if self.config.enable_background_tasks and self.config.auto_start_tasks:
                self._start_task_async(task)
            else:
                # Synchronous processing (for testing or when background disabled)
                self._process_task(task)
            
            logger.info(f"Submitted task {task.id} from {request.source.value}: {request.user_intent[:100]}")
            return handle

    def submit_chat(self, message: str, context: Dict[str, Any] | None = None, 
                   session_id: str | None = None) -> TaskHandle:
        """Submit a chat message."""
        request = TaskRequest(
            source=TaskSource.CHAT,
            user_intent=message,
            context=context or {},
            metadata={"session_id": session_id} if session_id else {},
        )
        return self.submit(request)

    def submit_voice(self, transcript: str, audio_data: bytes | None = None,
                    context: Dict[str, Any] | None = None) -> TaskHandle:
        """Submit a voice command."""
        request = TaskRequest(
            source=TaskSource.VOICE,
            user_intent=transcript,
            context=context or {},
            metadata={"audio_data": audio_data is not None} if audio_data else {},
        )
        return self.submit(request)

    def submit_jarvis(self, command: str, context: Dict[str, Any] | None = None) -> TaskHandle:
        """Submit a Jarvis mode command."""
        request = TaskRequest(
            source=TaskSource.JARVIS,
            user_intent=command,
            context=context or {},
        )
        return self.submit(request)

    def submit_automation(self, automation_id: str, trigger_data: Dict[str, Any] | None = None) -> TaskHandle:
        """Submit an automation trigger."""
        request = TaskRequest(
            source=TaskSource.AUTOMATION,
            user_intent=f"Run automation {automation_id}",
            context={"automation_id": automation_id, "trigger_data": trigger_data or {}},
            metadata={"automation_id": automation_id},
        )
        return self.submit(request)

    def submit_scheduled(self, cron_job_id: str, scheduled_time: datetime | None = None) -> TaskHandle:
        """Submit a scheduled cron job."""
        request = TaskRequest(
            source=TaskSource.CRON,
            user_intent=f"Execute cron job {cron_job_id}",
            context={"cron_job_id": cron_job_id, "scheduled_time": scheduled_time.isoformat() if scheduled_time else None},
            metadata={"cron_job_id": cron_job_id},
        )
        return self.submit(request)

    def submit_webhook(self, webhook_id: str, payload: Dict[str, Any]) -> TaskHandle:
        """Submit a webhook trigger."""
        request = TaskRequest(
            source=TaskSource.WEBHOOK,
            user_intent=f"Process webhook {webhook_id}",
            context={"webhook_id": webhook_id, "payload": payload},
            metadata={"webhook_id": webhook_id},
        )
        return self.submit(request)

    def submit_api(self, endpoint: str, params: Dict[str, Any], user_id: str | None = None) -> TaskHandle:
        """Submit an API request."""
        request = TaskRequest(
            source=TaskSource.API,
            user_intent=f"API call: {endpoint}",
            context={"endpoint": endpoint, "params": params},
            metadata={"user_id": user_id} if user_id else {},
        )
        return self.submit(request)

    def _start_task_async(self, task: Task) -> None:
        """Start task processing in background."""
        import threading
        thread = threading.Thread(target=self._process_task, args=(task,), daemon=True)
        thread.start()

    def _process_task(self, task: Task) -> None:
        """Main task processing pipeline."""
        try:
            # Phase 1: Understanding
            self._update_task_state(task, TaskState.UNDERSTANDING)
            understood_intent = self._understand_intent(task)
            
            # Phase 2: Planning
            self._update_task_state(task, TaskState.PLANNING)
            plan = self._create_plan(task, understood_intent)
            task.plan = plan
            
            # Phase 3: Permission Check
            permission_decision = self._check_permissions(task)
            if not permission_decision.allowed:
                if permission_decision.required_approval != "none":
                    self._update_task_state(task, TaskState.WAITING_FOR_APPROVAL)
                    # Wait for approval (would be implemented with event/queue)
                    self._wait_for_approval(task, permission_decision)
                else:
                    task.error = permission_decision.reason
                    self._update_task_state(task, TaskState.FAILED)
                    return
            
            # Phase 4: Execution
            self._update_task_state(task, TaskState.EXECUTING)
            self._execute_plan(task)
            
            # Phase 5: Verification
            self._update_task_state(task, TaskState.VERIFYING)
            self._verify_results(task)
            
            # Phase 6: Completion
            self._update_task_state(task, TaskState.COMPLETED)
            
        except Exception as e:
            logger.exception(f"Task {task.id} failed: {e}")
            task.error = str(e)
            self._update_task_state(task, TaskState.FAILED)
        finally:
            task.completed_at = datetime.now()
            self._persist_task(task)

    def _understand_intent(self, task: Task) -> str:
        """Analyze and understand the user's intent."""
        # For now, return the raw intent
        # In a full implementation, this would use an LLM to parse and structure the intent
        return task.goal

    def _create_plan(self, task: Task, understood_intent: str) -> List:
        """Create an execution plan for the task."""
        from .models import TaskStep
        
        # Route to appropriate capability
        routing = get_capability_router().route(understood_intent, task.request.context)
        
        # Create a simple single-step plan for now
        # In a full implementation, this would decompose into multiple steps
        step = TaskStep(
            name="Execute capability",
            description=f"Execute {routing.capability_id}",
            capability_id=routing.capability_id,
            tool_name=routing.tool_name,
            model_name=routing.model_name,
            input_data={"intent": understood_intent, **task.request.context},
        )
        return [step]

    def _check_permissions(self, task: Task) -> "PermissionDecision":
        """Check if the task has required permissions."""
        return get_permission_model().check_task_permissions(task)

    def _wait_for_approval(self, task: Task, decision: "PermissionDecision") -> None:
        """Wait for user approval (simplified - would use event system in production)."""
        # In a real implementation, this would block or register a callback
        # For now, we'll auto-approve for testing
        logger.warning(f"Task {task.id} waiting for approval: {decision.reason}")

    def _execute_plan(self, task: Task) -> None:
        """Execute the task plan step by step."""
        while task.can_execute_next():
            step = task.get_next_pending_step()
            if not step:
                break
            
            task.current_step_index = task.plan.index(step)
            step.state = TaskState.EXECUTING
            step.started_at = datetime.now()
            
            # Execute step
            result = get_execution_engine().execute_step(step, task)
            
            step.result = result.output
            step.error = result.error
            step.completed_at = datetime.now()
            
            if result.success:
                step.state = TaskState.COMPLETED
                task.artifacts.append({
                    "step_id": step.id,
                    "output": result.output,
                })
            else:
                step.state = TaskState.FAILED
                # Try recovery
                if task.recovery_attempts < task.max_recovery_attempts:
                    task.recovery_attempts += 1
                    recovery_result = get_execution_engine().attempt_recovery(step, result.error)
                    if recovery_result:
                        step.state = TaskState.RECOVERING
                        continue
                task.error = result.error
                break
            
            # Verify step
            if result.verification:
                step.verification_result = result.verification
                if not result.verification.get("passed", True):
                    step.state = TaskState.FAILED
                    task.error = "Verification failed"
                    break

    def _verify_results(self, task: Task) -> None:
        """Verify the final task results."""
        # Collect verification results from all steps
        task.verification_results = [
            step.verification_result for step in task.plan 
            if step.verification_result
        ]
        
        # Final verification
        if task.verification_results:
            all_passed = all(v.get("passed", True) for v in task.verification_results)
            if not all_passed:
                task.error = "Final verification failed"
                task.state = TaskState.FAILED

    def _update_task_state(self, task: Task, state: TaskState) -> None:
        """Update task state and progress."""
        task.state = state
        if task.progress:
            task.progress.state = state
        with self._lock:
            handle = self._task_handles.get(task.id)
            if handle:
                handle.state = state

    def _persist_task(self, task: Task) -> None:
        """Persist task state if configured."""
        if self.config.persist_tasks:
            # In a real implementation, this would save to database
            pass

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def get_task_handle(self, task_id: str) -> Optional[TaskHandle]:
        """Get a task handle by ID."""
        with self._lock:
            return self._task_handles.get(task_id)

    def list_tasks(
        self,
        state: TaskState | None = None,
        source: TaskSource | None = None,
        limit: int = 100,
    ) -> List[TaskHandle]:
        """List tasks with optional filters."""
        with self._lock:
            handles = list(self._task_handles.values())
            if state:
                handles = [h for h in handles if h.state == state]
            if source:
                handles = [h for h in handles if h.source == source]
            return handles[-limit:]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                return False
            task.state = TaskState.CANCELLED
            task.error = "Cancelled by user"
            task.completed_at = datetime.now()
            return True

    def pause_task(self, task_id: str) -> bool:
        """Pause a running task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state != TaskState.EXECUTING:
                return False
            task.state = TaskState.PAUSED
            return True

    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state != TaskState.PAUSED:
                return False
            task.state = TaskState.EXECUTING
            self._start_task_async(task)
            return True

    def register_source_handler(self, source: TaskSource, handler: Callable) -> None:
        """Register a custom handler for a task source."""
        with self._lock:
            self._source_handlers[source] = handler

    def get_stats(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        with self._lock:
            states = defaultdict(int)
            sources = defaultdict(int)
            for handle in self._task_handles.values():
                states[handle.state.value] += 1
                sources[handle.source.value] += 1
            return {
                "total_tasks": len(self._tasks),
                "by_state": dict(states),
                "by_source": dict(sources),
                "max_concurrent": self.config.max_concurrent_tasks,
            }

    def shutdown(self) -> None:
        """Shutdown the gateway gracefully."""
        with self._lock:
            # Cancel all running tasks
            for task in self._tasks.values():
                if task.state in (TaskState.CREATED, TaskState.UNDERSTANDING, 
                                  TaskState.PLANNING, TaskState.EXECUTING,
                                  TaskState.OBSERVING, TaskState.VERIFYING,
                                  TaskState.RECOVERING, TaskState.PAUSED):
                    task.state = TaskState.CANCELLED
                    task.error = "Gateway shutdown"
                    task.completed_at = datetime.now()


# Module-level instance
_gateway_instance: Optional[CommandGateway] = None


def get_command_gateway(config: Dict[str, Any] | None = None) -> CommandGateway:
    """Get the global command gateway instance."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = CommandGateway(config)
    return _gateway_instance