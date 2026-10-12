"""Orchestration Integration for AetherOS.

Provides integration between the new orchestration layer and existing
AetherOS systems (run_agent.py, delegate_tool.py, aetheros_automation).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from agent.orchestration import (
    # Core
    TaskSpec,
    TaskResult,
    TaskStatus,
    TaskPriority,
    TaskBudget,
    AgentRole,
    AgentIdentity,
    Plan,
    ExecutionState,
    # Components
    AgentRegistry,
    CapabilityRouter,
    AgentHealthMonitor,
    UnifiedSelector,
    HybridDecomposer,
    TaskGraphManager,
    TaskLifecycleManager,
    HandoffManager,
    VerificationOrchestrator,
    ApprovalManager,
    BudgetController,
    ObservabilityManager,
    QueueManager,
    create_recovery_system,
    StateStore,
    TaskStateManager,
    PlanStateManager,
    # Adapters
    CoreAgentAdapter,
    AutomationAgentAdapter,
    DelegateAgentAdapter,
    adapt_core_agent,
    adapt_automation_agent,
    adapt_delegate_agent,
    # Factory functions
    get_agent_registry,
    initialize_agent_registry,
    get_lifecycle_manager,
    create_observability_manager,
    create_budget_controller,
    create_queue_manager,
    create_verification_orchestrator,
    create_approval_manager,
    # Health checks
    create_liveness_check,
    create_readiness_check,
    create_model_availability_check,
    create_tool_availability_check,
    create_permissions_check,
)

logger = logging.getLogger(__name__)


class OrchestrationLayer:
    """Main orchestration layer facade.

    This is the primary interface for integrating the orchestration layer
    with existing AetherOS systems.
    """

    def __init__(self):
        self._initialized = False
        self._registry: Optional[AgentRegistry] = None
        self._router: Optional[CapabilityRouter] = None
        self._health: Optional[AgentHealthMonitor] = None
        self._selector: Optional[UnifiedSelector] = None
        self._decomposer: Optional[HybridDecomposer] = None
        self._graph: Optional[TaskGraphManager] = None
        self._lifecycle: Optional[TaskLifecycleManager] = None
        self._handoff: Optional[HandoffManager] = None
        self._verification: Optional[VerificationOrchestrator] = None
        self._approval: Optional[ApprovalManager] = None
        self._budget: Optional[BudgetController] = None
        self._observability: Optional[ObservabilityManager] = None
        self._queue: Optional[QueueManager] = None
        self._recovery: Optional[Dict[str, Any]] = None
        self._state_store: Optional[StateStore] = None
        self._task_state: Optional[TaskStateManager] = None
        self._plan_state: Optional[PlanStateManager] = None

    async def initialize(self) -> None:
        """Initialize all orchestration components."""
        if self._initialized:
            return

        # Initialize agent registry first
        self._registry = await initialize_agent_registry()

        # Register built-in agents
        await self._register_builtin_agents()

        # Initialize other components
        self._router = CapabilityRouter(self._registry)
        self._health = AgentHealthMonitor()
        await self._health.start()

        self._selector = UnifiedSelector(
            agent_registry=self._registry,
            capability_router=self._router,
        )

        self._decomposer = HybridDecomposer(
            agent_registry=self._registry,
            capability_router=self._router,
        )

        self._graph = TaskGraphManager()
        self._lifecycle = get_lifecycle_manager()
        self._handoff = HandoffManager(self._registry)
        self._verification = create_verification_orchestrator(self._registry)
        self._approval = create_approval_manager()
        self._budget = create_budget_controller()
        self._observability = create_observability_manager()
        self._queue = create_queue_manager()
        await self._queue.start()

        self._recovery = create_recovery_system()
        await self._recovery["deadlines"].start()

        self._state_store = StateStore()
        await self._state_store.start()

        self._task_state = TaskStateManager(self._state_store, self._recovery["checkpoints"])
        self._plan_state = PlanStateManager(self._state_store)

        self._initialized = True
        logger.info("Orchestration layer initialized")

    async def shutdown(self) -> None:
        """Shutdown all orchestration components."""
        if not self._initialized:
            return

        if self._queue:
            await self._queue.stop()
        if self._health:
            await self._health.stop()
        if self._recovery:
            await self._recovery["deadlines"].stop()
        if self._state_store:
            await self._state_store.stop()

        self._initialized = False
        logger.info("Orchestration layer shutdown")

    async def _register_builtin_agents(self) -> None:
        """Register built-in agent types."""
        # Core agent
        await self._registry.register(
            agent_type="core",
            factory=CoreAgentAdapter.create,
            role=AgentRole.COORDINATOR,
            tags={"core", "general"},
            priority=100,
        )

        # Automation agents (all roles)
        for role in AgentRole:
            if role != AgentRole.CUSTOM:
                await self._registry.register(
                    agent_type=f"automation:{role.value}",
                    factory=lambda config, r=role: AutomationAgentAdapter.create(config, r),
                    role=role,
                    tags={"automation", role.value},
                    priority=50,
                )

        # Delegate agent
        await self._registry.register(
            agent_type="delegate",
            factory=DelegateAgentAdapter.create,
            role=AgentRole.COORDINATOR,
            tags={"delegate", "subagent"},
            priority=30,
        )
        
        # Register health checks for all registered agents
        await self._register_agent_health_checks()

    async def _register_agent_health_checks(self) -> None:
        """Register health checks for all registered agents."""
        for reg_id, registration in self._registry._registrations.items():
            if not registration.enabled:
                continue
            # Create a sample agent instance to get health checks
            try:
                agent = await registration.factory()
                # Add built-in health checks for this agent type
                for check_name in ["liveness", "readiness", "model", "tools", "permissions"]:
                    check_name_full = f"{reg_id}_{check_name}"
                    if check_name_full not in self._health._checks:
                        # Create appropriate check based on type
                        if check_name == "liveness":
                            check = create_liveness_check(agent)
                        elif check_name == "readiness":
                            check = create_readiness_check(agent)
                        elif check_name == "model":
                            check = create_model_availability_check(agent)
                        elif check_name == "tools":
                            check = create_tool_availability_check(agent)
                        elif check_name == "permissions":
                            check = create_permissions_check(agent, [])
                        else:
                            continue
                        check.name = check_name_full
                        self._health.register_check(check)
            except Exception as e:
                logger.warning(f"Failed to register health checks for {reg_id}: {e}")

    # ── Task Execution ──────────────────────────────────────────────────

    async def execute_task(
        self,
        goal: str,
        description: str = "",
        required_capabilities: List[str] = None,
        preferred_agent_role: AgentRole = None,
        preferred_model: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        budget: TaskBudget = None,
        user_id: str = "",
        project_id: str = "",
        session_id: str = "",
    ) -> TaskResult:
        """Execute a single task through the orchestration layer."""
        if not self._initialized:
            await self.initialize()

        # Create task
        task = await self._task_state.create_task(
            goal=goal,
            description=description,
            required_capabilities=required_capabilities,
            priority=priority,
            budget=budget,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
        )

        if preferred_agent_role:
            task.preferred_agent_role = preferred_agent_role
        if preferred_model:
            task.preferred_model = preferred_model

        # Set up budget tracking
        self._budget.setup_task(task)

        # Register with lifecycle
        self._lifecycle.register_task(task)

        # Create checkpoint at start
        await self._recovery["checkpoints"].create_checkpoint(task, checkpoint_type="task_start")

        # Emit event
        await self._observability.emit_task_event(
            "task_created", task.task_id, f"Created task: {goal[:80]}"
        )

        try:
            # Route to best agent
            await self._lifecycle.transition(task.task_id, TaskStatus.PLANNING, "Routing to agent")
            agent = await self._router.route(task)

            if not agent:
                await self._lifecycle.fail_task(task.task_id, "No suitable agent found")
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error="No suitable agent found",
                )

            # Assign agent
            self._lifecycle.assign_agent(task.task_id, agent.identity.agent_id)
            await self._lifecycle.start_task(task.task_id)

            # Execute
            await self._observability.emit_task_event(
                "task_started", task.task_id, f"Executing with {agent.identity.name}"
            )

            result = await agent.execute_task(task)

            # Record metrics
            self._budget.record_execution(
                task,
                model=agent.identity.name,
                input_tokens=1000,  # Would come from actual execution
                output_tokens=2000,
                tool_calls=5,
            )

            # Verify result
            await self._lifecycle.verify_task(task.task_id)
            verification = await self._verification.verify_task_result(task, result)

            if not verification.verified:
                await self._lifecycle.fail_task(task.task_id, f"Verification failed: {verification.discrepancies}")
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"Verification failed: {verification.discrepancies}",
                )

            # Complete
            await self._lifecycle.complete_task(task.task_id, result=result)
            await self._recovery["checkpoints"].create_checkpoint(task, checkpoint_type="task_complete")

            await self._observability.emit_task_event(
                "task_completed", task.task_id, "Task completed successfully"
            )

            return result

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            await self._lifecycle.fail_task(task.task_id, str(e))
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
            )
        finally:
            self._budget.cleanup_task(task)

    async def execute_plan(self, plan: Plan) -> Dict[str, Any]:
        """Execute a multi-task plan."""
        if not self._initialized:
            await self.initialize()

        # Create plan state
        await self._plan_state.create_plan(plan)

        # Build task graph
        graph_id = f"graph-{plan.plan_id}"
        graph = self._graph.create_graph(graph_id)

        for task in plan.subtasks:
            self._graph.add_task(graph_id, task)

        for task_id, deps in plan.dependencies.items():
            for dep in deps:
                self._graph.add_dependency(graph_id, dep, task_id)

        # Execute graph
        from agent.orchestration.task_graph import GraphExecutionMode, ExecutionScheduler

        scheduler = ExecutionScheduler(
            graph_manager=self._graph,
            lifecycle_manager=self._lifecycle,
            agent_registry=self._registry,
        )

        result = await scheduler.execute_graph(graph_id, GraphExecutionMode.DEPENDENT)

        return result

    # ── Agent Management ────────────────────────────────────────────────

    async def get_agent(self, agent_type: str, config: Dict[str, Any], role: AgentRole = AgentRole.COORDINATOR):
        """Get an agent instance by type."""
        if agent_type == "core":
            return await CoreAgentAdapter.create(config, role)
        elif agent_type == "automation":
            return await AutomationAgentAdapter.create(config, role)
        elif agent_type == "delegate":
            return await DelegateAgentAdapter.create(config, role)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    def adapt_existing_agent(self, agent: Any, adapter_type: str) -> Any:
        """Adapt an existing agent to the universal interface."""
        if adapter_type == "core":
            return adapt_core_agent(agent)
        elif adapter_type == "automation":
            return adapt_automation_agent(agent)
        elif adapter_type == "delegate":
            return adapt_delegate_agent(agent)
        else:
            raise ValueError(f"Unknown adapter type: {adapter_type}")

    # ── Delegation Integration ──────────────────────────────────────────

    async def delegate_task(
        self,
        parent_agent_id: str,
        goal: str,
        context: str = "",
        toolsets: List[str] = None,
        model: str = None,
        max_iterations: int = None,
        role: str = "leaf",
    ) -> TaskResult:
        """Delegate a task to a subagent (integrates with delegate_tool.py)."""
        if not self._initialized:
            await self.initialize()

        # Create child task
        task = await self._task_state.create_task(
            goal=goal,
            description=context,
            required_capabilities=toolsets or [],
            user_id="",  # Would inherit from parent
            project_id="",
        )
        task.preferred_model = model or ""
        task.metadata["parent_agent_id"] = parent_agent_id
        task.metadata["delegate_role"] = role

        # Configure delegate adapter
        delegate = await DelegateAgentAdapter.create({
            "parent_agent_id": parent_agent_id,
            "delegate_role": role,
            "toolsets": toolsets,
            "model": model,
            "max_iterations": max_iterations,
        }, AgentRole.COORDINATOR)

        delegate.configure_for_task(task)

        # Execute
        result = await delegate.execute_task(task)

        return result

    # ── Health & Monitoring ────────────────────────────────────────────

    async def check_agent_health(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Check health of an agent."""
        return await self._health.force_health_check(agent_id)

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "registry": self._registry.get_registry_status() if self._registry else {},
            "health": self._health.get_latest_result if self._health else {},
            "queue": self._queue.get_all_stats() if self._queue else {},
            "budget": self._budget.budget.get_global_usage() if self._budget else {},
        }

    # ── Observability ──────────────────────────────────────────────────

    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get live progress for a task."""
        progress = self._observability.progress.get_progress(task_id)
        if progress:
            return {
                "task_id": progress.task_id,
                "status": progress.status.value,
                "progress": progress.progress,
                "current_step": progress.current_step,
                "current_agent": progress.current_agent,
                "current_tool": progress.current_tool,
                "errors": progress.errors,
                "warnings": progress.warnings,
            }
        return None

    def explain_task(self, task_id: str) -> str:
        """Get user-friendly explanation of task status."""
        progress = self._observability.progress.get_progress(task_id)
        if progress:
            return self._observability.explanation.explain_task_status(progress)
        return "Task not found"

    async def get_task_timeline(self, task_id: str) -> Dict[str, Any]:
        """Get complete task timeline."""
        return await self._observability.timeline.build_timeline(task_id)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def registry(self) -> Optional[AgentRegistry]:
        return self._registry

    @property
    def router(self) -> Optional[CapabilityRouter]:
        return self._router

    @property
    def lifecycle(self) -> Optional[TaskLifecycleManager]:
        return self._lifecycle

    @property
    def observability(self) -> Optional[ObservabilityManager]:
        return self._observability


# Global instance
_orchestration: Optional[OrchestrationLayer] = None


def get_orchestration() -> OrchestrationLayer:
    """Get the global orchestration layer instance."""
    global _orchestration
    if _orchestration is None:
        _orchestration = OrchestrationLayer()
    return _orchestration


async def initialize_orchestration() -> OrchestrationLayer:
    """Initialize the global orchestration layer."""
    orch = get_orchestration()
    await orch.initialize()
    return orch


async def shutdown_orchestration() -> None:
    """Shutdown the global orchestration layer."""
    global _orchestration
    if _orchestration:
        await _orchestration.shutdown()
        _orchestration = None


# Convenience functions for common operations
async def orchestrate_task(
    goal: str,
    description: str = "",
    required_capabilities: List[str] = None,
    preferred_agent_role: AgentRole = None,
    priority: TaskPriority = TaskPriority.NORMAL,
) -> TaskResult:
    """Quick task orchestration."""
    orch = get_orchestration()
    return await orch.execute_task(
        goal=goal,
        description=description,
        required_capabilities=required_capabilities,
        preferred_agent_role=preferred_agent_role,
        priority=priority,
    )


async def orchestrate_delegation(
    parent_agent_id: str,
    goal: str,
    context: str = "",
    toolsets: List[str] = None,
    role: str = "leaf",
) -> TaskResult:
    """Quick delegation orchestration."""
    orch = get_orchestration()
    return await orch.delegate_task(
        parent_agent_id=parent_agent_id,
        goal=goal,
        context=context,
        toolsets=toolsets,
        role=role,
    )


__all__ = [
    "OrchestrationLayer",
    "get_orchestration",
    "initialize_orchestration",
    "shutdown_orchestration",
    "orchestrate_task",
    "orchestrate_delegation",
]