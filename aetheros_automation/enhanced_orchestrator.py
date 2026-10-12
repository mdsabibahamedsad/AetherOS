from __future__ import annotations


import asyncio
import logging
import time
import uuid
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

# Import existing systems
from aetheros_automation.orchestrator.orchestrator import TaskOrchestrator as BaseTaskOrchestrator
from aetheros_automation.orchestrator.execution_engine import ExecutionEngine
from aetheros_automation.orchestrator.types import (
    OrchestrationPlan, 
    OrchestrationTask,
    ExecutionState
)
from aetheros_automation.routing.model_router import ModelRouter
from aetheros_automation.validation.validator import ResultValidator
from aetheros_automation.nlp.nlp_automation import NLPAutomationEngine
from aetheros_automation.identity.agent_identity import (
    AgentIdentity, AgentRole as IdentityAgentRole, AgentStatus, AutonomyLevel,
    identity_registry
)
from aetheros_automation.identity.lifecycle import (
    AgentLifecycleState, LifecycleTransition, lifecycle_registry
)

# Map between identity roles and automation roles (they serve different purposes)
ROLE_MAPPING = {
    IdentityAgentRole.GENERAL_AGENT: "coordinator",  # Maps to existing automation role
    IdentityAgentRole.PLANNER_AGENT: "planner",
    IdentityAgentRole.RESEARCH_AGENT: "research",
    IdentityAgentRole.CODING_AGENT: "developer",
    IdentityAgentRole.ANALYSIS_AGENT: "data",
    IdentityAgentRole.WRITING_AGENT: "writer",
    IdentityAgentRole.DATA_AGENT: "data",
    IdentityAgentRole.BROWSER_AGENT: "browser",
    IdentityAgentRole.SYSTEM_AGENT: "coordinator",
    IdentityAgentRole.SECURITY_AGENT: "security",
    IdentityAgentRole.REVIEW_AGENT: "review",
    IdentityAgentRole.VERIFICATION_AGENT: "qa",  # Verification maps to QA
    IdentityAgentRole.COORDINATOR_AGENT: "coordinator"
}


class EnhancedTaskOrchestrator(BaseTaskOrchestrator):
    """
    Enhanced Task Orchestrator that adds agent identity and lifecycle management
    while maintaining full backward compatibility with the base TaskOrchestrator.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with all base functionality plus enhancements"""
        super().__init__(*args, **kwargs)
        logger.info("EnhancedTaskOrchestrator initialized with identity and lifecycle management")
    
    async def create_agent_identity_for_task(self,
                                           task: OrchestrationTask,
                                           mission_id: str = None,
                                           workspace_id: str = None) -> AgentIdentity:
        """
        Create an agent identity specifically for executing a task.
        
        Args:
            task: The task to create identity for
            mission_id: Optional mission ID
            workspace_id: Optional workspace ID
            
        Returns:
            AgentIdentity: The created agent identity
        """
        # Map the task's agent role to our identity role system
        identity_role = self._map_to_identity_role(task.agent_role)
        
        # Select appropriate model and provider
        model_info = await self.model_router.select_model(
            task_type=task.agent_role.value,
            tools=task.tools
        )
        model = model_info.get("model", "gpt-4o")
        provider = model_info.get("provider", "openai")
        
        # Create the identity
        identity = AgentIdentity(
            role=identity_role,
            mission_id=mission_id,
            task_id=task.id,
            workspace_id=workspace_id,
            model=model,
            provider=provider,
            tools=task.tools,
            permission_scope=self._get_role_permissions(task.agent_role),
            metadata={
                "task_description": task.description,
                "estimated_duration": task.estimated_duration,
                "requires_approval": task.requires_approval,
                "max_retries": task.max_retries
            }
        )
        
        # Register and initialize lifecycle
        identity_registry.register(identity)
        lifecycle = lifecycle_registry.ensure(identity.agent_id)
        lifecycle.transition(AgentLifecycleState.INITIALIZING, {
            "task_id": task.id,
            "task_description": task.description
        })
        
        logger.debug(f"Created agent identity {identity.agent_id} for task {task.id}")
        return identity
    
    def _map_to_identity_role(self, automation_role: str) -> IdentityAgentRole:
        """Map automation role to identity role"""
        reverse_mapping = {v: k for k, v in ROLE_MAPPING.items()}
        return reverse_mapping.get(automation_role, IdentityAgentRole.GENERAL_AGENT)
    
    def _get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for a role (similar to base implementation)"""
        base = ["filesystem_read", "network"]
        role_perms: dict[str, List[str]] = {
            "developer": base + ["filesystem_write", "terminal", "execute_code", "git"],
            "browser": base + ["browser"],
            "research": base + ["browser", "web_search"],
            "writer": base + ["filesystem_write"],
            "security": base + ["filesystem_write", "terminal", "audit"],
            "deployment": base + ["filesystem_write", "terminal", "network"],
            "creative": base + ["filesystem_write", "image_generation"],
            "data": base + ["filesystem_write", "code_execution"],
            "communication": base + ["send_email", "send_message"],
            "file": base + ["filesystem_write", "filesystem_delete"],
        }
        return role_perms.get(role, base)
    
    async def execute_task_with_identity(self,
                                       task: OrchestrationTask,
                                       agent_identity: AgentIdentity = None,
                                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a task with full identity and lifecycle tracking.
        
        Args:
            task: The task to execute
            agent_identity: Optional pre-created agent identity
            context: Optional execution context
            
        Returns:
            Dict[str, Any]: The execution result
        """
        # Create identity if not provided
        if agent_identity is None:
            agent_identity = await self.create_agent_identity_for_task(task)
        
        # Activate the agent
        if not await self._activate_agent_identity(agent_identity):
            raise RuntimeError(f"Failed to activate agent identity: {agent_identity.agent_id}")
        
        try:
            # Update lifecycle to running
            lifecycle = lifecycle_registry.ensure(agent_identity.agent_id)
            lifecycle.transition(AgentLifecycleState.RUNNING, {
                "task_id": task.id,
                "started_at": time.time()
            })
            
            agent_identity.status = AgentStatus.RUNNING
            agent_identity.started_at = time.time()
            
            # Prepare execution context
            execution_context = context or {}
            execution_context.update({
                "agent_identity": agent_identity,
                "mission_id": agent_identity.mission_id,
                "workspace_id": agent_identity.workspace_id
            })
            
            # Execute using the base execution engine but with enhanced tracking
            result = await self.execution_engine.execute_task(
                task=task,
                agent=type('obj', (object,), {
                    'agent_id': agent_identity.agent_id,
                    'role': agent_identity.role.value,
                    'tools': agent_identity.tools,
                    'model': agent_identity.model,
                    'provider': agent_identity.provider
                })(),
                context=execution_context
            )
            
            # Update lifecycle to completed
            lifecycle.transition(AgentLifecycleState.COMPLETED, {
                "completed_at": time.time(),
                "result": result
            })
            
            agent_identity.status = AgentStatus.COMPLETED
            agent_identity.completed_at = time.time()
            agent_identity.result = str(result)[:500]  # Truncate for storage
            
            # Update usage tracking
            if isinstance(result, dict):
                agent_identity.token_usage = result.get("token_usage", 0)
                agent_identity.api_calls = result.get("api_calls", 0)
            
            logger.debug(f"Completed task {task.id} with agent {agent_identity.agent_id}")
            return result
            
        except Exception as e:
            # Handle failure
            logger.error(f"Task execution failed for agent {agent_identity.agent_id}: {e}")
            
            lifecycle = lifecycle_registry.ensure(agent_identity.agent_id)
            lifecycle.transition(AgentLifecycleState.FAILED, {
                "error": str(e),
                "failed_at": time.time()
            })
            
            agent_identity.status = AgentStatus.FAILED
            agent_identity.error = str(e)
            
            raise
    
    async def _activate_agent_identity(self, identity: AgentIdentity) -> bool:
        """Activate an agent identity"""
        lifecycle = lifecycle_registry.ensure(identity.agent_id)
        if lifecycle.transition(AgentLifecycleState.READY, {
            "activated_at": time.time()
        }):
            identity.status = AgentStatus.READY
            logger.debug(f"Activated agent identity: {identity.agent_id}")
            return True
        return False
    
    async def execute_enhanced_plan(self, plan_id: str) -> Dict[str, Any]:
        """
        Execute a plan with enhanced identity and lifecycle tracking.
        
        Args:
            plan_id: The plan ID to execute
            
        Returns:
            Dict[str, Any]: The execution result
        """
        # Get the plan
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        logger.info(f"Starting enhanced execution of plan {plan_id}: {plan.goal}")
        
        # Create execution state
        state = ExecutionState(
            plan_id=plan_id,
            pending_tasks=[t.id for t in plan.subtasks],
            started_at=time.time(),
        )
        self._execution_states[plan_id] = state
        
        # Emit start event
        await self._emit_event("plan.execution_started", {"plan_id": plan_id})
        
        # Update lifecycle
        lifecycle = lifecycle_registry.ensure(f"plan:{plan_id}")
        lifecycle.transition(AgentLifecycleState.EXECUTING, {
            "plan_id": plan_id,
            "goal": plan.goal
        })
        
        results: Dict[str, Any] = {}
        graph = plan.execution_graph
        levels = graph.get("levels", [])
        
        try:
            for level_idx, level in enumerate(levels):
                tasks_in_level = [t for t in plan.subtasks if t.id in level]
                parallel_tasks = [t for t in tasks_in_level
                                  if t.execution_mode.value == "PARALLEL"]
                sequential_tasks = [t for t in tasks_in_level
                                    if t.execution_mode.value != "PARALLEL"]
                
                # Execute parallel tasks
                if parallel_tasks:
                    parallel_results = await asyncio.gather(
                        *[self._execute_task_with_identity_enhanced(t, plan, state, results) 
                          for t in parallel_tasks],
                        return_exceptions=True,
                    )
                    for t, r in zip(parallel_tasks, parallel_results):
                        if isinstance(r, Exception):
                            results[t.id] = {"error": str(r), "success": False}
                            self._handle_task_failure(t, state, r)
                        else:
                            results[t.id] = r
                
                # Execute sequential tasks
                for task in sequential_tasks:
                    result = await self._execute_task_with_identity_enhanced(task, plan, state, results)
                    results[task.id] = result
                    
                    # Check for failure and potential early exit
                    if not result.get("success") and task.execution_mode.value != "FALLBACK":
                        stop_on_failure = self.config.metadata.get("stop_on_failure", True) \
                                        if hasattr(self.config, 'metadata') else True
                        if stop_on_failure:
                            self._handle_task_failure(task, state, Exception(result.get("error", "Unknown error")))
                            break
            
            # Determine final outcome
            state.updated_at = time.time()
            success = len(state.failed_tasks) == 0
            
            # Emit completion event
            await self._emit_event("plan.completed", {
                "plan_id": plan_id,
                "success": success
            })
            
            # Update lifecycle
            if success:
                lifecycle.transition(AgentLifecycleState.COMPLETED, {
                    "completed_at": time.time(),
                    "success": True
                })
            else:
                lifecycle.transition(AgentLifecycleState.FAILED, {
                    "failed_at": time.time(),
                    "success": False
                })
            
            # Build and return result
            result = self._build_result(plan, state, results, success)
            
            # Save execution history
            try:
                self.save_execution_history(plan_id, result)
            except Exception:
                logger.exception("Failed to save execution history for %s", plan_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            lifecycle.transition(AgentLifecycleState.FAILED, {
                "failed_at": time.time(),
                "error": str(e)
            })
            raise
    
    async def _execute_task_with_identity_enhanced(self,
                                                 task: OrchestrationTask,
                                                 plan: OrchestrationPlan,
                                                 state: ExecutionState,
                                                 previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single task with enhanced identity tracking.
        
        Args:
            task: The task to execute
            plan: The parent plan
            state: The execution state
            previous_results: Results from previous tasks
            
        Returns:
            Dict[str, Any]: The task execution result
        """
        # Emit task start
        await self._emit_event("task.started", {
            "task_id": task.id,
            "name": task.name
        })
        
        task.status = "running"  # Using string for compatibility with base system
        task.started_at = time.time()
        
        # Update task lifecycle
        task_lifecycle = lifecycle_registry.ensure(f"task:{task.id}")
        task_lifecycle.transition(AgentLifecycleState.EXECUTING, {
            "task_id": task.id,
            "task_name": task.name
        })
        
        if task.id in state.pending_tasks:
            state.pending_tasks.remove(task.id)
        state.running_tasks.append(task.id)
        state.current_task_id = task.id
        
        # Handle approval if required
        if task.requires_approval:
            task_lifecycle.transition(AgentLifecycleState.WAITING, {
                "task_id": task.id,
                "reason": "approval required"
            })
            
            approved = await self._request_approval(task)
            if not approved:
                task.status = "blocked"
                task_lifecycle.transition(AgentLifecycleState.BLOCKED, {
                    "task_id": task.id,
                    "reason": "approval denied"
                })
                if task.id in state.pending_tasks:
                    state.pending_tasks.remove(task.id)
                if task.id in state.running_tasks:
                    state.running_tasks.remove(task.id)
                state.failed_tasks.append(task.id)
                return {"success": False, "error": "Approval denied", "task_id": task.id}
        
        # Create or get agent identity for this task
        agent_identity = await self.create_agent_identity_for_task(
            task, 
            mission_id=plan.id,
            workspace_id=plan.metadata.get("workspace_id") if plan.metadata else None
        )
        
        # Execute the task with identity tracking
        try:
            result = await self.execute_task_with_identity(
                task=task,
                agent_identity=agent_identity,
                context={
                    "previous_results": previous_results,
                    "plan_id": plan.id,
                    "task_index": list(plan.subtasks).index(task) if task in plan.subtasks else 0
                }
            )
            
            # Validate result
            is_valid, validation_message = await self.validator.validate(
                result=result,
                task=task,
            )
            
            if is_valid:
                task_lifecycle.transition(AgentLifecycleState.REVIEWING, {
                    "task_id": task.id,
                    "reason": "validation passed"
                })
            else:
                # Handle validation failure similar to execution failure
                raise ValueError(f"Validation failed: {validation_message}")
            
        except Exception as exc:
            # Handle execution failure
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                wait = self.retry_handler.get_backoff(task.retry_count)
                
                await self._emit_event("task.retrying", {
                    "task_id": task.id,
                    "attempt": task.retry_count,
                    "max_retries": task.max_retries,
                    "wait": wait
                })
                
                await asyncio.sleep(wait)
                
                # Try with fallback model
                fallback_model = await self.model_router.get_fallback(
                    model=agent_identity.model, 
                    provider=agent_identity.provider
                )
                if fallback_model:
                    # Create new identity with fallback model
                    agent_identity.model = fallback_model["model"]
                    agent_identity.provider = fallback_model["provider"]
                
                try:
                    result = await self.execute_task_with_identity(
                        task=task,
                        agent_identity=agent_identity,
                        context={
                            "previous_results": previous_results,
                            "retry": True
                        }
                    )
                    is_valid, validation_message = await self.validator.validate(
                        result=result, task=task
                    )
                except Exception as exc:
                    is_valid = False
                    validation_message = f"Execution error: {exc}"
            
            if not is_valid:
                task.status = "failed"
                task.error = validation_message
                await self._emit_event("task.failed", {
                    "task_id": task.id,
                    "error": validation_message
                })
                task_lifecycle.transition(AgentLifecycleState.FAILED, {
                    "task_id": task.id,
                    "reason": "task failed"
                })
                
                if task.id in state.running_tasks:
                    state.running_tasks.remove(task.id)
                state.failed_tasks.append(task.id)
                return {"success": False, "error": validation_message, "task_id": task.id}
        
        # Task completed successfully
        task.status = "completed"
        task.completed_at = time.time()
        task.actual_duration = task.completed_at - task.started_at
        task.result = result
        task.progress = 100.0
        
        # Update agent identity
        agent_identity.status = AgentStatus.COMPLETED
        agent_identity.completed_at = time.time()
        agent_identity.result = str(result)[:500]
        
        if isinstance(result, dict):
            agent_identity.token_usage = result.get("token_usage", 0)
            agent_identity.api_calls = result.get("api_calls", 0)
        
        # Update lifecycles
        task_lifecycle.transition(AgentLifecycleState.COMPLETED, {
            "task_id": task.id,
            "duration": task.actual_duration
        })
        
        await self._emit_event("task.completed", {
            "task_id": task.id,
            "duration": task.actual_duration
        })
        
        if task.id in state.running_tasks:
            state.running_tasks.remove(task.id)
        state.completed_tasks.append(task.id)
        state.updated_at = time.time()
        
        # Save checkpoint
        checkpoint_id = await self.checkpoint_manager.save_checkpoint(
            plan_id=plan.id,
            task_id=task.id,
            result=result,
            state=state,
        )
        if checkpoint_id:
            task.checkpoint_data = task.checkpoint_data or {}
            task.checkpoint_data["checkpoint_id"] = checkpoint_id
        
        return {"success": True, "result": result, "task_id": task.id}
    
    def _handle_task_failure(self, task: OrchestrationTask, state: ExecutionState, exception: Exception) -> None:
        """Handle a task failure"""
        task.status = "failed"
        task.error = str(exception)
        
        task_lifecycle = lifecycle_registry.ensure(f"task:{task.id}")
        task_lifecycle.transition(AgentLifecycleState.FAILED, {
            "task_id": task.id,
            "reason": "task failed",
            "error": str(exception)
        })
        
        if task.id in state.running_tasks:
            state.running_tasks.remove(task.id)
        state.failed_tasks.append(task.id)
        
        logger.warning(f"Task {task.id} failed: {exception}")
    
    async def _request_approval(self, task: OrchestrationTask) -> bool:
        """Request approval for a task"""
        await self._emit_event("approval.requested", {
            "task_id": task.id,
            "name": task.name,
            "actions": [a.value for a in task.approval_actions],
            "description": task.description,
        })
        
        if not hasattr(self, '_approval_callback') or not self._approval_callback:
            return True
        
        callback = self._approval_callback
        response = await callback(task)
        return response in (
            "APPROVE_ONCE",
            "APPROVE_SESSION", 
            "ALWAYS_ALLOW"
        )
    
    def set_approval_callback(self, callback: Callable) -> None:
        """Set the approval callback"""
        self._approval_callback = callback
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to registered handlers"""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Event handler failed for {event_type}: {e}")
    
    def on(self, event_type: str, handler: Callable) -> None:
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def off(self, event_type: str, handler: Callable) -> None:
        """Unregister an event handler"""
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced statistics including identity and lifecycle info"""
        base_stats = {
            "total_plans": len(self._plans),
            "active_executions": len(self._execution_states),
            "available_models": len(self.model_router.list_available_models())
        }
        
        identity_stats = {
            "total_identities": len(identity_registry.list_all()),
            "identities_by_status": {}
        }
        
        # Count identities by status
        for identity in identity_registry.list_all():
            status = identity.status.value
            identity_stats["identities_by_status"][status] = identity_stats["identities_by_status"].get(status, 0) + 1
        
        lifecycle_stats = lifecycle_registry.get_state_distribution()
        
        return {
            **base_stats,
            **identity_stats,
            "lifecycle_distribution": {state.value: count for state, count in lifecycle_stats.items()}
        }

