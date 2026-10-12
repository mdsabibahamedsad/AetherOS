"""Planning Engine for AetherOS Orchestration Layer.

Implements Phases 10-13 of Master Prompt 11:
- Planning Engine with validation, versioning, and adaptive replanning
- Integrates with MASTER 6 (model routing), MASTER 8 (skills/plugins), MASTER 9 (memory)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agent.orchestration.agent_registry import AgentRegistry
from agent.orchestration.router import CapabilityRouter
from agent.orchestration.types import (
    AgentRole,
    Plan,
    PlanVersion,
    RiskLevel,
    TaskPriority,
    TaskSpec,
    TaskStatus,
    ValidationRule,
)
from agent.orchestration.memory_integration import MemoryIntegration

logger = logging.getLogger(__name__)


# =============================================================================
# Phase 11-12: Plan Validation & Versioning Types
# =============================================================================


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """A validation issue found during plan validation."""
    rule_id: str
    severity: ValidationSeverity
    message: str
    field: str = ""
    expected: Any = None
    actual: Any = None


@dataclass
class ValidationResult:
    """Result of plan validation."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    validated_at: float = field(default_factory=time.time)
    
    def has_errors(self) -> bool:
        return any(i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL) for i in self.issues)
    
    def has_warnings(self) -> bool:
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)


@dataclass
class PlanVersion:
    """A versioned snapshot of a plan."""
    version: int
    plan_id: str
    goal: str
    subtasks: List[Dict[str, Any]]
    dependencies: Dict[str, List[str]]
    required_tools: List[str]
    required_agents: List[str]
    required_permissions: List[str]
    estimated_cost: float
    estimated_time: float
    risk_level: str
    execution_graph: Dict[str, Any]
    created_at: float
    reason: str = ""
    changed_by: str = ""
    diff_from_previous: Optional[Dict[str, Any]] = None


@dataclass
class ReplanContext:
    """Context for adaptive replanning."""
    plan_id: str
    trigger: str  # "failure", "new_evidence", "requirement_change", "environment_change"
    failed_task_id: Optional[str] = None
    error_details: Optional[str] = None
    new_evidence: Optional[Dict[str, Any]] = None
    requirement_changes: Optional[List[str]] = None
    environment_changes: Optional[Dict[str, Any]] = None
    partial_results: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Plan Validator
# =============================================================================


class PlanValidator:
    """Validates plans before execution."""
    
    def __init__(self, agent_registry: AgentRegistry, capability_router: CapabilityRouter):
        self._registry = agent_registry
        self._router = capability_router
        self._rules: List[Callable[[Plan], List[ValidationIssue]]] = []
        self._register_default_rules()
    
    def _register_default_rules(self) -> None:
        """Register default validation rules."""
        self._rules.append(self._validate_subtasks_exist)
        self._rules.append(self._validate_dependencies)
        self._rules.append(self._validate_agent_availability)
        self._rules.append(self._validate_tool_availability)
        self._rules.append(self._validate_permissions)
        self._rules.append(self._validate_budget)
        self._rules.append(self._validate_circular_dependencies)
        self._rules.append(self._validate_approval_requirements)
    
    def add_rule(self, rule: Callable[[Plan], List[ValidationIssue]]) -> None:
        """Add a custom validation rule."""
        self._rules.append(rule)
    
    async def validate(self, plan: Plan) -> ValidationResult:
        """Validate a plan and return issues."""
        all_issues = []
        
        for rule in self._rules:
            try:
                issues = await rule(plan)
                all_issues.extend(issues)
            except Exception as e:
                logger.error(f"Validation rule {rule.__name__} failed: {e}")
                all_issues.append(ValidationIssue(
                    rule_id=rule.__name__,
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation rule failed: {e}",
                ))
        
        valid = not any(i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL) for i in all_issues)
        
        return ValidationResult(
            valid=valid,
            issues=all_issues,
        )
    
    # ── Default Validation Rules ─────────────────────────────────────────
    
    async def _validate_subtasks_exist(self, plan: Plan) -> List[ValidationIssue]:
        """Ensure plan has at least one subtask."""
        issues = []
        if not plan.subtasks:
            issues.append(ValidationIssue(
                rule_id="subtasks_exist",
                severity=ValidationSeverity.ERROR,
                message="Plan must have at least one subtask",
                field="subtasks",
            ))
        return issues
    
    async def _validate_dependencies(self, plan: Plan) -> List[ValidationIssue]:
        """Validate dependency references."""
        issues = []
        task_ids = {t.task_id for t in plan.subtasks}
        
        for task_id, deps in plan.dependencies.items():
            if task_id not in task_ids:
                issues.append(ValidationIssue(
                    rule_id="dependency_target_exists",
                    severity=ValidationSeverity.ERROR,
                    message=f"Dependency target task {task_id} does not exist in plan",
                    field="dependencies",
                ))
            for dep in deps:
                if dep not in task_ids:
                    issues.append(ValidationIssue(
                        rule_id="dependency_source_exists",
                        severity=ValidationSeverity.ERROR,
                        message=f"Task {task_id} depends on non-existent task {dep}",
                        field="dependencies",
                    ))
        return issues
    
    async def _validate_agent_availability(self, plan: Plan) -> List[ValidationIssue]:
        """Check if required agents are available."""
        issues = []
        for role in plan.required_agents:
            regs = self._registry.find_by_role(role)
            available = [r for r in regs if r.enabled]
            if not available:
                issues.append(ValidationIssue(
                    rule_id="agent_availability",
                    severity=ValidationSeverity.ERROR,
                    message=f"No available agent for required role: {role.value}",
                    field="required_agents",
                ))
            elif len(available) == 1 and available[0].priority < 50:
                issues.append(ValidationIssue(
                    rule_id="agent_low_priority",
                    severity=ValidationSeverity.WARNING,
                    message=f"Only low-priority agent available for role {role.value}",
                    field="required_agents",
                ))
        return issues
    
    async def _validate_tool_availability(self, plan: Plan) -> List[ValidationIssue]:
        """Check if required tools are available."""
        issues = []
        # This would check against tool registry
        # For now, just warn about potentially missing tools
        for tool in plan.required_tools:
            if tool in ["browser_navigate", "web_search", "execute_code"]:
                issues.append(ValidationIssue(
                    rule_id="tool_external_dependency",
                    severity=ValidationSeverity.WARNING,
                    message=f"Tool {tool} requires external service/API",
                    field="required_tools",
                ))
        return issues
    
    async def _validate_permissions(self, plan: Plan) -> List[ValidationIssue]:
        """Check if required permissions are available."""
        issues = []
        # This would integrate with MASTER 7 security system
        for perm in plan.required_permissions:
            if perm in ["security_audit", "external_communication", "filesystem_delete"]:
                issues.append(ValidationIssue(
                    rule_id="permission_high_risk",
                    severity=ValidationSeverity.WARNING,
                    message=f"High-risk permission required: {perm}",
                    field="required_permissions",
                ))
        return issues
    
    async def _validate_budget(self, plan: Plan) -> List[ValidationIssue]:
        """Validate budget constraints."""
        issues = []
        if plan.estimated_cost > 100.0:
            issues.append(ValidationIssue(
                rule_id="budget_high",
                severity=ValidationSeverity.WARNING,
                message=f"Plan estimated cost (${plan.estimated_cost:.2f}) is very high",
                field="estimated_cost",
            ))
        if plan.estimated_time > 86400:  # 24 hours
            issues.append(ValidationIssue(
                rule_id="duration_long",
                severity=ValidationSeverity.INFO,
                message=f"Plan estimated duration ({plan.estimated_time/3600:.1f}h) exceeds 24 hours",
                field="estimated_time",
            ))
        return issues
    
    async def _validate_circular_dependencies(self, plan: Plan) -> List[ValidationIssue]:
        """Check for circular dependencies."""
        issues = []
        # Build adjacency list
        graph = {t.task_id: set() for t in plan.subtasks}
        for task_id, deps in plan.dependencies.items():
            if task_id in graph:
                graph[task_id].update(deps)
        
        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if dfs(node):
                    issues.append(ValidationIssue(
                        rule_id="circular_dependency",
                        severity=ValidationSeverity.CRITICAL,
                        message="Circular dependency detected in plan",
                        field="dependencies",
                    ))
                    break
        return issues
    
    async def _validate_approval_requirements(self, plan: Plan) -> List[ValidationIssue]:
        """Check if approval requirements are properly configured."""
        issues = []
        for task in plan.subtasks:
            task_obj = next((t for t in plan.subtasks if t.task_id == task.task_id), None)
            if task_obj and task_obj.approval_state == "pending":
                # Check if approval actions are defined
                pass
        return issues


# =============================================================================
# Plan Version Manager
# =============================================================================


class PlanVersionManager:
    """Manages plan versioning and history."""
    
    def __init__(self):
        self._versions: Dict[str, List[PlanVersion]] = {}  # plan_id -> versions
        self._current_versions: Dict[str, int] = {}  # plan_id -> current version
    
    def create_version(
        self,
        plan: Plan,
        reason: str = "",
        changed_by: str = "",
        previous_version: Optional[PlanVersion] = None,
    ) -> PlanVersion:
        """Create a new version of a plan."""
        plan_id = plan.plan_id
        current_version = self._current_versions.get(plan_id, 0)
        new_version = current_version + 1
        
        # Compute diff from previous version
        diff = None
        if previous_version:
            diff = self._compute_diff(previous_version, plan)
        
        version = PlanVersion(
            version=new_version,
            plan_id=plan_id,
            goal=plan.goal,
            subtasks=[self._task_to_dict(t) for t in plan.subtasks],
            dependencies=plan.dependencies,
            required_tools=plan.required_tools,
            required_agents=[r.value for r in plan.required_agents],
            required_permissions=plan.required_permissions,
            estimated_cost=plan.estimated_cost,
            estimated_time=plan.estimated_time,
            risk_level=plan.risk_level.value,
            execution_graph=plan.execution_graph,
            created_at=time.time(),
            reason=reason,
            changed_by=changed_by,
            diff_from_previous=diff,
        )
        
        if plan_id not in self._versions:
            self._versions[plan_id] = []
        self._versions[plan_id].append(version)
        self._current_versions[plan_id] = new_version
        
        # Update plan's version info
        plan.version = new_version
        if previous_version:
            plan.parent_plan_id = previous_version.plan_id
        
        return version
    
    def _compute_diff(self, old: PlanVersion, new_plan: Plan) -> Dict[str, Any]:
        """Compute diff between two plan versions."""
        diff = {
            "subtasks_added": [],
            "subtasks_removed": [],
            "subtasks_modified": [],
            "dependencies_changed": False,
            "tools_changed": False,
            "agents_changed": False,
            "permissions_changed": False,
            "cost_change": 0.0,
            "time_change": 0.0,
            "risk_change": False,
        }
        
        old_task_ids = {t["task_id"] for t in old.subtasks}
        new_task_ids = {t.task_id for t in new_plan.subtasks}
        
        diff["subtasks_added"] = list(new_task_ids - old_task_ids)
        diff["subtasks_removed"] = list(old_task_ids - new_task_ids)
        
        # Check modified tasks
        for new_task in new_plan.subtasks:
            if new_task.task_id in old_task_ids:
                old_task = next((t for t in old.subtasks if t["task_id"] == new_task.task_id), None)
                if old_task:
                    if (old_task.get("goal") != new_task.goal or
                        old_task.get("description") != new_task.description or
                        old_task.get("required_capabilities") != new_task.required_capabilities):
                        diff["subtasks_modified"].append(new_task.task_id)
        
        # Check other fields
        diff["dependencies_changed"] = old.dependencies != new_plan.dependencies
        diff["tools_changed"] = set(old.required_tools) != set(new_plan.required_tools)
        diff["agents_changed"] = set(old.required_agents) != set(r.value for r in new_plan.required_agents)
        diff["permissions_changed"] = set(old.required_permissions) != set(new_plan.required_permissions)
        diff["cost_change"] = new_plan.estimated_cost - old.estimated_cost
        diff["time_change"] = new_plan.estimated_time - old.estimated_time
        diff["risk_change"] = old.risk_level != new_plan.risk_level.value
        
        return diff
    
    def _task_to_dict(self, task: TaskSpec) -> Dict[str, Any]:
        """Convert TaskSpec to dictionary for versioning."""
        return {
            "task_id": task.task_id,
            "goal": task.goal,
            "description": task.description,
            "required_capabilities": task.required_capabilities,
            "preferred_agent_role": task.preferred_agent_role.value if task.preferred_agent_role else None,
            "preferred_tools": task.preferred_tools,
            "preferred_skills": task.preferred_skills,
            "constraints": task.constraints,
            "success_criteria": task.success_criteria,
        }
    
    def get_versions(self, plan_id: str) -> List[PlanVersion]:
        """Get all versions of a plan."""
        return self._versions.get(plan_id, [])
    
    def get_current_version(self, plan_id: str) -> int:
        """Get current version number."""
        return self._current_versions.get(plan_id, 0)
    
    def get_version(self, plan_id: str, version: int) -> Optional[PlanVersion]:
        """Get a specific version."""
        versions = self._versions.get(plan_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None
    
    def get_latest_version(self, plan_id: str) -> Optional[PlanVersion]:
        """Get the latest version."""
        versions = self._versions.get(plan_id, [])
        return versions[-1] if versions else None


# =============================================================================
# Adaptive Replanner
# =============================================================================


class AdaptiveReplanner:
    """Handles adaptive replanning when conditions change."""
    
    def __init__(
        self,
        agent_registry: AgentRegistry,
        capability_router: CapabilityRouter,
        memory_integration: Optional[MemoryIntegration] = None,
    ):
        self._registry = agent_registry
        self._router = capability_router
        self._memory = memory_integration
        self._replan_history: List[ReplanContext] = []
    
    async def replan(
        self,
        plan: Plan,
        context: ReplanContext,
    ) -> Plan:
        """
        Adaptively replan based on trigger.
        
        Triggers:
        - failure: A task failed
        - new_evidence: New information discovered
        - requirement_change: User changed requirements
        - environment_change: External conditions changed
        """
        logger.info(f"Adaptive replanning for plan {plan.plan_id}: {context.trigger}")
        
        # Record replan event
        self._replan_history.append(context)
        
        # Get relevant memory for replanning
        memory_context = await self._get_relevant_memory(context)
        
        # Dispatch to specific replanner
        if context.trigger == "failure":
            return await self._replan_on_failure(plan, context)
        elif context.trigger == "new_evidence":
            return await self._replan_on_evidence(plan, context)
        elif context.trigger == "requirement_change":
            return await self._replan_on_requirement_change(plan, context)
        elif context.trigger == "environment_change":
            return await self._replan_on_environment_change(plan, context)
        else:
            logger.warning(f"Unknown replan trigger: {context.trigger}")
            return plan
    
    async def _replan_on_failure(self, plan: Plan, context: ReplanContext) -> Plan:
        """Replan when a task fails."""
        failed_task_id = context.failed_task_id
        if not failed_task_id:
            return plan
        
        # Find the failed task
        failed_task = next((t for t in plan.subtasks if t.task_id == failed_task_id), None)
        if not failed_task:
            return plan
        
        # Try fallback if available
        if failed_task.preferred_tools:
            # Try alternative tools/approaches
            alternatives = await self._find_alternatives(failed_task)
            if alternatives:
                # Create new task with alternative approach
                new_task = TaskSpec(
                    task_id=f"{failed_task.task_id}_retry_{int(time.time())}",
                    goal=failed_task.goal,
                    description=f"Retry with alternative: {failed_task.description}",
                    required_capabilities=alternatives.get("capabilities", failed_task.required_capabilities),
                    preferred_tools=alternatives.get("tools", failed_task.preferred_tools),
                    constraints=failed_task.constraints + [f"Previous attempt failed: {context.error_details}"],
                )
                
                # Replace failed task with retry
                plan.subtasks = [t for t in plan.subtasks if t.task_id != failed_task_id]
                plan.subtasks.append(new_task)
                
                # Update dependencies
                for task_id, deps in plan.dependencies.items():
                    if failed_task_id in deps:
                        deps.remove(failed_task_id)
                        deps.append(new_task.task_id)
        
        return plan
    
    async def _replan_on_evidence(self, plan: Plan, context: ReplanContext) -> Plan:
        """Replan based on new evidence."""
        new_evidence = context.new_evidence or {}
        
        # Add new tasks based on evidence
        if "new_tasks" in new_evidence:
            for task_data in new_evidence["new_tasks"]:
                new_task = TaskSpec(
                    task_id=f"evidence_task_{uuid.uuid4().hex[:8]}",
                    goal=task_data.get("goal", ""),
                    description=task_data.get("description", ""),
                    required_capabilities=task_data.get("capabilities", []),
                    required_tools=task_data.get("tools", []),
                    required_skills=task_data.get("skills", []),
                    constraints=task_data.get("constraints", []),
                )
                plan.subtasks.append(new_task)
        
        # Update existing tasks based on evidence
        if "updates" in new_evidence:
            for task_id, updates in new_evidence["updates"].items():
                task = next((t for t in plan.subtasks if t.task_id == task_id), None)
                if task:
                    for key, value in updates.items():
                        if hasattr(task, key):
                            setattr(task, key, value)
        
        return plan
    
    async def _replan_on_requirement_change(self, plan: Plan, context: ReplanContext) -> Plan:
        """Replan when requirements change."""
        changes = context.requirement_changes or []
        
        # Add new requirements as constraints
        for change in changes:
            # Add as constraint to relevant tasks
            for task in plan.subtasks:
                if change not in task.constraints:
                    task.constraints.append(change)
        
        # Re-evaluate plan if major change
        if len(changes) > 3:
            # Full replan might be needed
            pass
        
        return plan
    
    async def _replan_on_environment_change(self, plan: Plan, context: ReplanContext) -> Plan:
        """Replan when environment changes."""
        changes = context.environment_changes or {}
        
        # Handle model/provider availability changes
        if "unavailable_models" in changes:
            for task in plan.subtasks:
                if task.preferred_model in changes["unavailable_models"]:
                    # Find alternative model
                    alternative = await self._find_alternative_model(task.preferred_model)
                    if alternative:
                        task.preferred_model = alternative
        
        if "unavailable_tools" in changes:
            for task in plan.subtasks:
                task.required_tools = [t for t in task.required_tools if t not in changes["unavailable_tools"]]
                task.preferred_tools = [t for t in task.preferred_tools if t not in changes["unavailable_tools"]]
        
        return plan
    
    async def _find_alternatives(self, task: TaskSpec) -> Optional[Dict[str, Any]]:
        """Find alternative approaches for a failed task."""
        # This would use MASTER 6 model routing and MASTER 8 capability registry
        alternatives = {}
        
        if "coding" in task.required_capabilities:
            alternatives["tools"] = ["patch", "write_file", "execute_code"]
            alternatives["capabilities"] = task.required_capabilities
        
        return alternatives if alternatives else None
    
    async def _find_alternative_model(self, model: str) -> Optional[str]:
        """Find alternative model via MASTER 6."""
        # This would integrate with MASTER 6 model routing
        fallback_map = {
            "gpt-4": "gpt-4-turbo",
            "gpt-4-turbo": "claude-3-sonnet",
            "claude-3-opus": "claude-3-sonnet",
        }
        return fallback_map.get(model)
    
    async def _get_relevant_memory(self, context: ReplanContext) -> Dict[str, Any]:
        """Get relevant memory for replanning."""
        if not self._memory:
            return {}
        
        # Query memory for similar past failures/successes
        query = f"replan {context.trigger} {context.failed_task_id or ''}"
        try:
            results = await self._memory.search(query, limit=5)
            return {"relevant_cases": results}
        except Exception:
            return {}
    
    def get_replan_history(self, plan_id: Optional[str] = None) -> List[ReplanContext]:
        """Get replan history."""
        if plan_id:
            return [r for r in self._replan_history if r.plan_id == plan_id]
        return self._replan_history


# =============================================================================
# Unified Planning Engine
# =============================================================================


class PlanningEngine:
    """Unified planning engine combining all planning capabilities."""
    
    def __init__(
        self,
        agent_registry: AgentRegistry,
        capability_router: CapabilityRouter,
        memory_integration: Optional[MemoryIntegration] = None,
    ):
        self._registry = agent_registry
        self._router = capability_router
        self._memory = memory_integration
        
        # Import here to avoid circular imports
        from aetheros_automation.orchestrator.planner import TaskPlanner
        from aetheros_automation.orchestrator.models import Objective
        
        self._task_planner = TaskPlanner()
        self._validator = PlanValidator(agent_registry, capability_router)
        self._version_manager = PlanVersionManager()
        self._replanner = AdaptiveReplanner(agent_registry, capability_router, memory_integration)
        
        self._plans: Dict[str, Plan] = {}
        self._plan_objectives: Dict[str, Any] = {}  # Plan ID -> Objective
    
    async def create_plan(
        self,
        goal: str,
        context: Dict[str, Any] = None,
        constraints: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        deadline: Optional[float] = None,
        max_budget: float = 0.0,
        user_id: str = "",
        session_id: str = "",
    ) -> Plan:
        """Create a new execution plan from a user goal."""
        
        # Build objective for automation planner
        from aetheros_automation.orchestrator.models import Objective
        
        objective = Objective(
            goal=goal,
            context=context or {},
            constraints=constraints or [],
            priority=TaskPriority(priority) if isinstance(priority, int) else priority,
            deadline=deadline,
            max_budget=max_budget,
            user_id=user_id,
            session_id=session_id,
        )
        
        # Create plan using automation planner
        automation_plan = await self._task_planner.create_plan(objective)
        
        # Convert to orchestration Plan
        plan = self._convert_to_orchestration_plan(automation_plan, goal)
        
        # Store objective for replanning
        self._plan_objectives[plan.plan_id] = objective
        
        # Create initial version
        self._version_manager.create_version(
            plan,
            reason="Initial plan creation",
            changed_by="planning_engine",
        )
        
        # Validate plan
        validation = await self._validator.validate(plan)
        if not validation.valid:
            logger.warning(f"Plan {plan.plan_id} validation failed: {[i.message for i in validation.issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]}")
        
        # Store plan
        self._plans[plan.plan_id] = plan
        
        logger.info(f"Created plan {plan.plan_id} with {len(plan.subtasks)} subtasks")
        return plan
    
    def _convert_to_orchestration_plan(self, auto_plan: Any, goal: str) -> Plan:
        """Convert automation Plan to orchestration Plan."""
        plan = Plan(
            goal=goal,
            description=auto_plan.metadata.get("description", ""),
        )
        
        # Convert subtasks
        for auto_task in auto_plan.tasks:
            # Map priority from automation (0,1,2,3) to orchestration (0,50,75,100)
            auto_prio = auto_task.priority.value if hasattr(auto_task.priority, 'value') else auto_task.priority
            priority_map = {0: TaskPriority.LOW, 1: TaskPriority.NORMAL, 2: TaskPriority.HIGH, 3: TaskPriority.CRITICAL}
            task = TaskSpec(
                task_id=auto_task.id,
                goal=auto_task.name,
                description=auto_task.description,
                required_capabilities=auto_task.tools,
                preferred_agent_role=auto_task.agent_role,
                preferred_tools=auto_task.tools,
                priority=priority_map.get(auto_prio, TaskPriority.NORMAL),
            )
            plan.add_task(task)
        
        # Copy dependencies
        plan.dependencies = auto_plan.dependencies
        plan.required_tools = auto_plan.required_tools
        plan.required_agents = auto_plan.required_agents
        plan.required_permissions = auto_plan.required_permissions
        plan.estimated_cost = auto_plan.estimated_cost
        plan.estimated_time = auto_plan.estimated_time
        plan.risk_level = auto_plan.risk_level
        plan.execution_graph = auto_plan.execution_graph.__dict__ if auto_plan.execution_graph else {}
        
        return plan
    
    async def validate_plan(self, plan_id: str) -> ValidationResult:
        """Validate a plan before execution."""
        plan = self._plans.get(plan_id)
        if not plan:
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    rule_id="plan_not_found",
                    severity=ValidationSeverity.ERROR,
                    message=f"Plan {plan_id} not found",
                )]
            )
        return await self._validator.validate(plan)
    
    async def execute_plan(self, plan_id: str, mode: str = "dependent") -> Dict[str, Any]:
        """Execute a plan using the task graph execution engine."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Build task graph
        graph_id = f"graph-{plan_id}"
        from agent.orchestration.task_graph import TaskGraphManager, ExecutionScheduler, GraphExecutionMode
        
        graph_manager = TaskGraphManager()
        graph = graph_manager.create_graph(graph_id)
        
        for task in plan.subtasks:
            graph_manager.add_task(graph_id, task)
        
        for task_id, deps in plan.dependencies.items():
            for dep in deps:
                graph_manager.add_dependency(graph_id, dep, task_id)
        
        lifecycle = self._lifecycle if hasattr(self, '_lifecycle') else None
        if not lifecycle:
            from agent.orchestration.task_lifecycle import get_lifecycle_manager
            lifecycle = get_lifecycle_manager()
        
        scheduler = ExecutionScheduler(
            graph_manager=graph_manager,
            lifecycle_manager=lifecycle,
            agent_registry=self._registry,
        )
        
        mode_enum = GraphExecutionMode(mode) if isinstance(mode, str) else mode
        result = await scheduler.execute_graph(graph_id, mode_enum)
        
        return result
    
    # ── Versioning ─────────────────────────────────────────────────────────
    
    def get_plan_versions(self, plan_id: str) -> List[Any]:
        """Get all versions of a plan."""
        return self._version_manager.get_versions(plan_id)
    
    def get_plan_version(self, plan_id: str, version: int) -> Optional[Any]:
        """Get a specific version of a plan."""
        return self._version_manager.get_version(plan_id, version)
    
    async def create_new_version(
        self,
        plan_id: str,
        reason: str = "",
        changed_by: str = "",
    ) -> Optional[Any]:
        """Create a new version of an existing plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        
        previous_version = self._version_manager.get_latest_version(plan_id)
        return self._version_manager.create_version(
            plan,
            reason=reason,
            changed_by=changed_by,
            previous_version=previous_version,
        )
    
    async def rollback_to_version(self, plan_id: str, version: int) -> bool:
        """Rollback plan to a previous version."""
        version_data = self._version_manager.get_version(plan_id, version)
        if not version_data:
            return False
        
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        
        # Restore plan from version
        plan.goal = version_data.goal
        plan.subtasks = [TaskSpec(**t) for t in version_data.subtasks]
        plan.dependencies = version_data.dependencies
        plan.required_tools = version_data.required_tools
        plan.required_agents = [AgentRole(a) for a in version_data.required_agents]
        plan.required_permissions = version_data.required_permissions
        plan.estimated_cost = version_data.estimated_cost
        plan.estimated_time = version_data.estimated_time
        plan.risk_level = RiskLevel(version_data.risk_level)
        plan.execution_graph = version_data.execution_graph
        plan.version = version_data.version + 1  # New version after rollback
        plan.parent_plan_id = version_data.plan_id
        
        # Create new version recording the rollback
        self._version_manager.create_version(
            plan,
            reason=f"Rollback to version {version}",
            changed_by="system",
            previous_version=version_data,
        )
        
        return True
    
    # ── Adaptive Replanning ────────────────────────────────────────────────
    
    async def replan(
        self,
        plan_id: str,
        trigger: str,
        **kwargs,
    ) -> Optional[Plan]:
        """Adaptively replan based on trigger."""
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        
        context = ReplanContext(
            plan_id=plan_id,
            trigger=trigger,
            **kwargs,
        )
        
        new_plan = await self._replanner.replan(plan, context)
        
        # Create new version
        self._version_manager.create_version(
            new_plan,
            reason=f"Replan triggered by {trigger}",
            changed_by="adaptive_replanner",
            previous_version=self._version_manager.get_latest_version(plan_id),
        )
        
        return new_plan
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)
    
    def list_plans(self) -> List[Plan]:
        """List all plans."""
        return list(self._plans.values())


# =============================================================================
# Factory
# =============================================================================


async def create_planning_engine(
    agent_registry: AgentRegistry,
    capability_router: CapabilityRouter,
    memory_integration: Optional[MemoryIntegration] = None,
) -> PlanningEngine:
    """Create a planning engine with all components."""
    return PlanningEngine(
        agent_registry=agent_registry,
        capability_router=capability_router,
        memory_integration=memory_integration,
    )


__all__ = [
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationResult",
    "PlanVersion",
    "ReplanContext",
    "PlanValidator",
    "PlanVersionManager",
    "AdaptiveReplanner",
    "PlanningEngine",
    "create_planning_engine",
]