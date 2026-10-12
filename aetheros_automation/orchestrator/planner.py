from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from aetheros_automation.models import AgentRole
from aetheros_automation.orchestrator.models import (
    ExecutionGraph, GraphEdge, GraphNode, NodeType,
    Objective, OrchestrationTask, Plan, PlanStep, RiskLevel,
    TaskPriority, TaskType, TaskStatus, ValidationRule
)

logger = logging.getLogger(__name__)


class TaskPlanner:
    """
    Enhanced task planner that creates sophisticated execution plans from objectives.
    """

    def __init__(self, model_router=None, template_manager=None):
        self.model_router = model_router
        self.template_manager = template_manager
        self._task_counter = 0
        self._step_counter = 0

    async def create_plan(self, objective: Objective) -> Plan:
        """
        Create a comprehensive execution plan from an objective.
        
        Args:
            objective: The objective to create a plan for
            
        Returns:
            A complete Plan with steps, tasks, dependencies, and execution graph
        """
        logger.info(f"Creating plan for objective: {objective.goal}")
        
        plan = Plan(
            goal=objective.goal,
            status="planning",
            created_at=time.time(),
            metadata={
                "context": objective.context,
                "constraints": objective.constraints,
                "priority": objective.priority.value if hasattr(objective.priority, 'value') else str(objective.priority),
                "output_format": objective.output_format,
                "max_budget": objective.max_budget,
                "user_id": objective.user_id,
                "session_id": objective.session_id,
            },
        )
        
        # Analyze the objective to understand its nature
        await self._analyze_objective(plan, objective)
        
        # Decompose the objective into detailed steps
        steps = await self._decompose_objective(objective)
        plan.steps = steps
        
        # Convert steps to tasks with proper task types
        tasks = await self._steps_to_enhanced_tasks(steps, objective)
        plan.tasks = tasks
        
        # Compute dependencies between tasks
        plan.dependencies = self._compute_smart_dependencies(tasks)
        
        # Determine required tools, agents, and permissions
        plan.required_tools = self._compute_required_tools(tasks)
        plan.required_agents = list(set(t.agent_role for t in tasks))
        plan.required_permissions = self._compute_required_permissions(tasks)
        
        # Estimate time and cost
        plan.estimated_time = self._estimate_total_duration(tasks)
        plan.estimated_cost = self._estimate_total_cost(tasks, objective)
        
        # Assess risk level
        plan.risk_level = self._assess_plan_risk(tasks, objective)
        
        # Build execution graph
        plan.execution_graph = self._build_execution_graph(tasks, plan.dependencies)
        
        # Add validation rules
        plan.metadata["validation_rules"] = self._generate_validation_rules(steps)
        
        plan.status = "ready"
        logger.info(f"Created plan {plan.id} with {len(tasks)} tasks")
        
        return plan

    async def _analyze_objective(self, plan: Plan, objective: Objective) -> None:
        """
        Analyze the objective to understand its characteristics.
        """
        goal_lower = objective.goal.lower()
        
        # Detect objective type
        objective_types = []
        
        # Research indicators
        if any(word in goal_lower for word in ["research", "investigate", "analyze", "study", "explore", "find"]):
            objective_types.append("research")
            
        # Development indicators
        if any(word in goal_lower for word in ["build", "create", "develop", "implement", "code", "program"]):
            objective_types.append("development")
            
        # Data processing indicators
        if any(word in goal_lower for word in ["data", "process", "transform", "analyze", "compute", "calculate"]):
            objective_types.append("data_processing")
            
        # Content creation indicators
        if any(word in goal_lower for word in ["write", "draft", "compose", "create content", "document"]):
            objective_types.append("content_creation")
            
        # System administration indicators
        if any(word in goal_lower for word in ["deploy", "install", "configure", "setup", "maintain"]):
            objective_types.append("system_admin")
            
        # Communication indicators
        if any(word in goal_lower for word in ["send", "email", "message", "notify", "communicate"]):
            objective_types.append("communication")
            
        # Automation indicators
        if any(word in goal_lower for word in ["automate", "schedule", "recurring", "periodic"]):
            objective_types.append("automation")
            
        plan.metadata["objective_types"] = objective_types
        
        # Estimate complexity based on goal length and complexity indicators
        complexity_indicators = [
            "and", "then", "after", "before", "if", "when", "while", "during",
            "multiple", "various", "different", "several", "several", "batch",
            "loop", "iterate", "recursive", "nested", "complex", "advanced"
        ]
        
        complexity_score = sum(1 for indicator in complexity_indicators if indicator in goal_lower)
        word_count = len(objective.goal.split())
        
        # Normalize complexity score
        if word_count > 0:
            normalized_complexity = min(1.0, (complexity_score * 0.1) + (word_count * 0.01))
        else:
            normalized_complexity = 0.0
            
        plan.metadata["complexity_score"] = normalized_complexity
        plan.metadata["word_count"] = word_count

    async def _decompose_objective(self, objective: Objective) -> List[PlanStep]:
        """
        Decompose an objective into detailed plan steps.
        Uses semantic analysis to break down complex goals.
        """
        steps = []
        goal_lower = objective.goal.lower()
        
        # Check if we have a template for this type of objective
        if self.template_manager:
            template = await self._find_matching_template(objective)
            if template:
                logger.info(f"Using template {template.id} for objective")
                return template.steps
        
        # Define step patterns for different types of objectives
        step_patterns = {
            "research": [
                ("Define research scope and objectives", AgentRole.PLANNER, ["read_file"], False),
                ("Gather information from multiple sources", AgentRole.RESEARCH, ["web_search", "web_extract", "read_file"], True),
                ("Analyze and synthesize findings", AgentRole.DATA, ["read_file", "search_files", "run_terminal"], False),
                ("Create research report with citations", AgentRole.WRITER, ["write_file", "read_file"], False),
                ("Review and validate research conclusions", AgentRole.REVIEW, ["read_file"], False)
            ],
            "development": [
                ("Analyze requirements and create specifications", AgentRole.PLANNER, ["read_file", "write_file"], False),
                ("Design system architecture and components", AgentRole.CREATIVE, ["write_file", "read_file"], False),
                ("Implement core functionality", AgentRole.CODING, ["write_file", "read_file", "run_terminal", "search_files"], True),
                ("Create unit tests and integration tests", AgentRole.QA, ["write_file", "read_file", "run_terminal"], False),
                ("Document code and create user guides", AgentRole.WRITER, ["write_file", "read_file"], False),
                ("Perform code review and quality assurance", AgentRole.REVIEW, ["read_file"], False)
            ],
            "data_processing": [
                ("Identify data sources and requirements", AgentRole.PLANNER, ["read_file"], False),
                ("Extract and collect data from sources", AgentRole.DATA, ["web_search", "read_file", "run_terminal"], True),
                ("Clean and preprocess raw data", AgentRole.DATA, ["read_file", "run_terminal", "write_file"], False),
                ("Analyze data and apply statistical methods", AgentRole.DATA, ["read_file", "run_terminal", "write_file"], False),
                ("Create visualizations and reports", AgentRole.CREATIVE, ["write_file", "read_file"], False),
                ("Validate results and create data dictionary", AgentRole.QA, ["read_file", "write_file"], False)
            ],
            "content_creation": [
                ("Research topic and gather source materials", AgentRole.RESEARCH, ["web_search", "read_file"], True),
                ("Create outline and structure for content", AgentRole.PLANNER, ["write_file", "read_file"], False),
                ("Write initial draft content", AgentRole.WRITER, ["write_file", "read_file"], False),
                ("Edit and refine content for clarity and style", AgentRole.WRITER, ["write_file", "read_file"], False),
                ("Add multimedia elements and formatting", AgentRole.CREATIVE, ["write_file", "read_file"], False),
                ("Proofread and finalize content", AgentRole.REVIEW, ["read_file"], False)
            ],
            "system_admin": [
                ("Assess current system state and requirements", AgentRole.SECURITY, ["read_file", "run_terminal"], False),
                ("Plan implementation approach and risk mitigation", AgentRole.PLANNER, ["read_file", "write_file"], False),
                ("Execute installation or configuration changes", AgentRole.CODING, ["run_terminal", "write_file"], False),
                ("Verify system functionality and performance", AgentRole.QA, ["read_file", "run_terminal"], False),
                ("Document changes and create operational procedures", AgentRole.WRITER, ["write_file", "read_file"], False)
            ],
            "communication": [
                ("Define communication objectives and audience", AgentRole.PLANNER, ["read_file"], False),
                ("Gather necessary information and resources", AgentRole.RESEARCH, ["read_file", "web_search"], False),
                ("Draft communication content", AgentRole.WRITER, ["write_file", "read_file"], False),
                ("Review and approve communication", AgentRole.REVIEW, ["read_file"], False),
                ("Deliver communication through appropriate channels", AgentRole.COMMUNICATION, ["send_message", "send_email"], False),
                ("Track responses and follow up as needed", AgentRole.COMMUNICATION, ["read_file"], False)
            ],
            "automation": [
                ("Identify repetitive tasks to automate", AgentRole.PLANNER, ["read_file"], False),
                ("Design automation workflow and triggers", AgentRole.PLANNER, ["write_file", "read_file"], False),
                ("Implement automation scripts and configurations", AgentRole.CODING, ["write_file", "read_file", "run_terminal"], True),
                ("Test automation with sample data", AgentRole.QA, ["read_file", "run_terminal"], False),
                ("Deploy automation and monitor performance", AgentRole.CODING, ["run_terminal"], False),
                ("Document automation and create maintenance guide", AgentRole.WRITER, ["write_file", "read_file"], False)
            ]
        }
        
        # Determine which patterns match the objective
        matched_patterns = []
        for pattern_type, patterns in step_patterns.items():
            if pattern_type in objective.context.get("objective_types", []):
                matched_patterns.extend(patterns)
        
        # If no specific patterns matched, use a general approach
        if not matched_patterns:
            matched_patterns = [
                ("Analyze objective and create action plan", AgentRole.PLANNER, ["read_file", "write_file"], False),
                ("Gather necessary information and resources", AgentRole.RESEARCH, ["web_search", "read_file"], True),
                ("Execute core tasks to achieve objective", AgentRole.CODING, ["write_file", "read_file", "run_terminal"], False),
                ("Verify results and quality assurance", AgentRole.QA, ["read_file"], False),
                ("Document outcomes and lessons learned", AgentRole.WRITER, ["write_file", "read_file"], False)
            ]
        
        # Convert patterns to PlanStep objects
        for i, (description, role, tools, parallelizable) in enumerate(matched_patterns):
            # Estimate duration and cost based on task type
            estimated_duration, estimated_cost = self._estimate_step_properties(role, tools, parallelizable)
            
            # Determine risk level
            risk_level = self._assess_step_risk(role, tools)
            
            # Determine if approval is required
            requires_approval = self._requires_approval(role, tools, description)
            
            step = PlanStep(
                id=f"step_{self._step_counter:03d}",
                description=description,
                agent_role=role,
                tools=tools.copy(),
                dependencies=[f"step_{j:03d}" for j in range(i)],  # Sequential by default
                estimated_duration=estimated_duration,
                estimated_cost=estimated_cost,
                risk_level=risk_level,
                requires_approval=requires_approval,
                parallelizable=parallelizable,
                fallback_steps=[],
                retry_count=0,
                validation_rules=[]
            )
            
            steps.append(step)
            self._step_counter += 1
        
        # If we still have no steps, create a fallback
        if not steps:
            steps.append(PlanStep(
                id="step_000",
                description=objective.goal[:100],
                agent_role=AgentRole.COORDINATOR,
                tools=["read_file", "write_file"],
                estimated_duration=60.0,
                estimated_cost=0.01,
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                parallelizable=False
            ))
        
        return steps

    def _estimate_step_properties(self, role: AgentRole, tools: List[str], parallelizable: bool) -> Tuple[float, float]:
        """
        Estimate duration and cost for a step based on role and tools.
        """
        base_duration = 30.0  # Base 30 seconds
        base_cost = 0.005     # Base $0.005
        
        # Role-based multipliers
        role_multipliers = {
            AgentRole.PLANNER: (1.5, 1.2),
            AgentRole.RESEARCH: (2.0, 1.5),
            AgentRole.CODING: (2.5, 2.0),
            AgentRole.WRITER: (1.2, 1.0),
            AgentRole.QA: (1.8, 1.3),
            AgentRole.CREATIVE: (1.8, 1.5),
            AgentRole.DATA: (2.0, 1.8),
            AgentRole.COMMUNICATION: (1.5, 1.2),
            AgentRole.SECURITY: (2.0, 2.0),
            AgentRole.BROWSER: (1.8, 1.5),
            AgentRole.FILE: (1.2, 1.0),
            AgentRole.COORDINATOR: (1.0, 1.0),
            AgentRole.COORDINATOR: (1.0, 1.0)
        }
        
        role_duration_mult, role_cost_mult = role_multipliers.get(role, (1.0, 1.0))
        
        # Tool-based adjustments
        tool_cost = 0.0
        expensive_tools = ["web_search", "browser_navigate", "image_generation", "run_terminal"]
        for tool in tools:
            if tool in expensive_tools:
                tool_cost += 0.01
        
        # Parallelization bonus (can reduce time but may increase coordination cost)
        duration_mult = role_duration_mult * (0.7 if parallelizable else 1.0)
        cost_mult = role_cost_mult * (1.2 if parallelizable else 1.0)  # Slight overhead for coordination
        
        estimated_duration = base_duration * duration_mult + tool_cost * 60  # Convert cost to time estimate
        estimated_cost = (base_cost * cost_mult) + tool_cost
        
        # Apply some randomness to avoid identical estimates
        import random
        estimated_duration *= (0.8 + random.random() * 0.4)  # 0.8x to 1.2x
        estimated_cost *= (0.8 + random.random() * 0.4)      # 0.8x to 1.2x
        
        return max(10.0, estimated_duration), max(0.001, estimated_cost)

    def _assess_step_risk(self, role: AgentRole, tools: List[str]) -> RiskLevel:
        """
        Assess risk level for a step based on role and tools.
        """
        high_risk_roles = {AgentRole.SECURITY, AgentRole.COMMUNICATION, AgentRole.CODING}
        medium_risk_roles = {AgentRole.DATA, AgentRole.FILE, AgentRole.BROWSER}
        
        high_risk_tools = {"run_terminal", "send_message", "send_email", "web_search"}
        medium_risk_tools = {"browser_navigate", "web_extract", "write_file", "patch"}
        
        risk_score = 0
        
        if role in high_risk_roles:
            risk_score += 2
        elif role in medium_risk_roles:
            risk_score += 1
            
        for tool in tools:
            if tool in high_risk_tools:
                risk_score += 2
            elif tool in medium_risk_tools:
                risk_score += 1
        
        if risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _requires_approval(self, role: AgentRole, tools: List[str], description: str) -> bool:
        """
        Determine if a step requires approval based on role, tools, and description.
        """
        description_lower = description.lower()
        
        # Always require approval for certain roles
        if role in {AgentRole.SECURITY, AgentRole.COMMUNICATION}:
            return True
            
        # Require approval for destructive or sensitive operations
        approval_triggers = [
            "delete", "remove", "destroy", "format", "install", "configure",
            "send", "email", "message", "deploy", "release", "publish",
            "admin", "root", "privilege", "permission", "access",
            "password", "token", "key", "secret", "credential"
        ]
        
        if any(trigger in description_lower for trigger in approval_triggers):
            return True
            
        # Require approval for certain tools
        approval_tools = {"send_message", "send_email", "run_terminal"}
        if any(tool in approval_tools for tool in tools):
            return True
            
        return False

    async def _steps_to_enhanced_tasks(self, steps: List[PlanStep], objective: Objective) -> List[OrchestrationTask]:
        """
        Convert plan steps to enhanced orchestrator tasks with proper task types.
        """
        tasks = []
        
        for step in steps:
            # Determine task type based on step properties
            task_type = TaskType.SEQUENTIAL
            if step.parallelizable:
                task_type = TaskType.PARALLEL
            elif step.requires_approval:
                task_type = TaskType.HUMAN_APPROVAL
            
            # Check if this should be a sub-agent task
            if self._should_be_sub_agent(step, objective):
                task_type = TaskType.SUB_AGENT
            
            task = OrchestrationTask(
                id=f"task_{len(tasks):03d}",
                name=step.description[:50],
                description=step.description,
                task_type=task_type,
                agent_role=step.agent_role,
                tools=step.tools.copy(),
                dependencies=step.dependencies.copy(),
                estimated_duration=step.estimated_duration,
                estimated_cost=step.estimated_cost,
                risk_level=step.risk_level,
                requires_approval=step.requires_approval,
                max_retries=step.retry_count or 3,
                validation_rules=[ValidationRule(field="completed", operator="exists", expected_value=True, 
                                             error_message="Task did not complete successfully")]
            )
            
            tasks.append(task)
        
        return tasks

    def _should_be_sub_agent(self, step: PlanStep, objective: Objective) -> bool:
        """
        Determine if a step should be executed as a sub-agent.
        """
        # Create sub-agents for complex, independent tasks
        if step.estimated_duration > 300:  # More than 5 minutes
            return True
            
        if step.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            return True
            
        # Complex research or development tasks
        if step.agent_role in {AgentRole.RESEARCH, AgentRole.CODING} and len(step.tools) > 3:
            return True
            
        return False

    def _compute_smart_dependencies(self, tasks: List[OrchestrationTask]) -> Dict[str, List[str]]:
        """
        Compute intelligent dependencies between tasks.
        Goes beyond simple sequential ordering to detect real dependencies.
        """
        dependencies = {task.id: [] for task in tasks}
        
        # Start with the sequential dependencies from steps
        for i, task in enumerate(tasks):
            # Add dependencies from the step definitions
            for dep in task.dependencies:
                if dep in dependencies:
                    dependencies[task.id].append(dep)
        
        # Add data flow dependencies
        for i, task in enumerate(tasks):
            for j, other_task in enumerate(tasks):
                if i != j:
                    # Check if task produces data that other_task consumes
                    if self._has_data_dependency(task, other_task):
                        if other_task.id not in dependencies[task.id]:
                            dependencies[task.id].append(other_task.id)
        
        # Add resource dependencies
        for i, task in enumerate(tasks):
            for j, other_task in enumerate(tasks):
                if i != j and task.agent_role == other_task.agent_role:
                    # Same role might need sequential execution for resource contention
                    if task.agent_role in {AgentRole.CODING, AgentRole.WRITER}:
                        if j < i:  # Earlier tasks of same type should complete first
                            if other_task.id not in dependencies[task.id]:
                                dependencies[task.id].append(other_task.id)
        
        return dependencies

    def _has_data_dependency(self, producer: OrchestrationTask, consumer: OrchestrationTask) -> bool:
        """
        Check if there's a data dependency between two tasks.
        """
        # Simple heuristic: if consumer reads files and producer writes files
        producer_writes = "write_file" in producer.tools
        consumer_reads = "read_file" in consumer.tools
        
        if producer_writes and consumer_reads:
            return True
            
        # If consumer searches files and producer creates/modifies files
        consumer_searches = "search_files" in consumer.tools
        producer_modifies = any(tool in producer.tools for tool in ["write_file", "patch"])
        
        if consumer_searches and producer_modifies:
            return True
            
        # If consumer uses terminal and producer creates scripts
        consumer_uses_terminal = "run_terminal" in consumer.tools
        producer_creates_scripts = "write_file" in producer.tools
        
        if consumer_uses_terminal and producer_creates_scripts:
            # Check if file extensions suggest scripts
            # This would be more sophisticated in a real implementation
            return True
            
        return False

    def _compute_required_tools(self, tasks: List[OrchestrationTask]) -> List[str]:
        """
        Compute the complete set of tools required by all tasks.
        """
        tools_set = set()
        for task in tasks:
            tools_set.update(task.tools)
        return sorted(list(tools_set))

    def _compute_required_permissions(self, tasks: List[OrchestrationTask]) -> List[str]:
        """
        Compute the complete set of permissions required by all tasks.
        """
        permissions_set = set()
        for task in tasks:
            # Map tools to permissions
            tool_to_permission = {
                "web_search": "network",
                "browser_navigate": "browser",
                "web_extract": "browser",
                "send_message": "external_communication",
                "send_email": "external_communication",
                "run_terminal": "terminal",
                "write_file": "filesystem_write",
                "read_file": "filesystem_read",
                "search_files": "filesystem_read",
                "patch": "filesystem_write",
                "file_operations": "filesystem_write",
                "image_generation": "image_generation",
                "execute_code": "execute_code",
                "code_execution": "execute_code",
                "git": "version_control"
            }
            
            for tool in task.tools:
                if tool in tool_to_permission:
                    permissions_set.add(tool_to_permission[tool])
        
        # Add role-based permissions
        role_to_permissions = {
            AgentRole.SECURITY: {"security_audit", "system_monitoring"},
            AgentRole.COMMUNICATION: {"external_communication"},
            AgentRole.FILE: {"filesystem_write", "filesystem_delete"},
            AgentRole.BROWSER: {"browser"},
            AgentRole.DATA: {"data_analysis"},
            AgentRole.CREATIVE: {"image_generation", "content_creation"},
            AgentRole.CODING: {"execute_code", "terminal", "version_control"},
            AgentRole.WRITER: {"filesystem_write"},
            AgentRole.QA: {"testing", "validation"},
            AgentRole.PLANNER: {"planning", "coordination"},
            AgentRole.COORDINATOR: {"basic_operations"}
        }
        
        for task in tasks:
            if task.agent_role in role_to_permissions:
                permissions_set.update(role_to_permissions[task.agent_role])
        
        return sorted(list(permissions_set))

    def _estimate_total_duration(self, tasks: List[OrchestrationTask]) -> float:
        """
        Estimate total duration considering parallel execution.
        """
        if not tasks:
            return 0.0
            
        # Group tasks by dependency levels
        levels = self._compute_dependency_levels(tasks)
        
        total_time = 0.0
        for level in levels:
            # In each level, tasks can run in parallel
            # The level time is the max of all task durations in that level
            level_tasks = [task for task in tasks if task.id in level]
            if level_tasks:
                level_duration = max(task.estimated_duration for task in level_tasks)
                total_time += level_duration
        
        return total_time

    def _estimate_total_cost(self, tasks: List[OrchestrationTask], objective: Objective) -> float:
        """
        Estimate total cost considering resource usage.
        """
        base_cost = sum(task.estimated_cost for task in tasks)
        
        # Adjust based on objective complexity
        complexity_factor = 1.0
        if "complexity_score" in objective.context:
            complexity_factor = 1.0 + objective.context["complexity_score"]
        
        # Add overhead for coordination and communication
        coordination_overhead = 0.1 * len(tasks)  # 10% per task for coordination
        
        total_cost = base_cost * complexity_factor + coordination_overhead
        
        # Apply objective budget constraint if specified
        if objective.max_budget > 0:
            total_cost = min(total_cost, objective.max_budget)
        
        return max(0.0, total_cost)

    def _assess_plan_risk(self, tasks: List[OrchestrationTask], objective: Objective) -> RiskLevel:
        """
        Assess overall risk level for the plan.
        """
        if not tasks:
            return RiskLevel.LOW
        
        # Count risks by level
        risk_counts = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 0, RiskLevel.HIGH: 0, RiskLevel.CRITICAL: 0}
        
        for task in tasks:
            risk_counts[task.risk_level] += 1
        
        # Weighted risk assessment
        weighted_score = (
            risk_counts[RiskLevel.LOW] * 0 +
            risk_counts[RiskLevel.MEDIUM] * 1 +
            risk_counts[RiskLevel.HIGH] * 2 +
            risk_counts[RiskLevel.CRITICAL] * 3
        ) / len(tasks)
        
        # Adjust for objective properties
        if objective.constraints:
            # More constraints = higher risk
            constraint_factor = min(1.5, 1.0 + len(objective.constraints) * 0.1)
            weighted_score *= constraint_factor
        
        if objective.max_budget > 0:
            # Budget constraint increases risk
            weighted_score *= 1.2
        
        if weighted_score >= 2.5:
            return RiskLevel.CRITICAL
        elif weighted_score >= 1.5:
            return RiskLevel.HIGH
        elif weighted_score >= 0.5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _compute_dependency_levels(self, tasks: List[OrchestrationTask]) -> List[List[str]]:
        """
        Compute dependency levels for parallel execution planning.
        Returns a list of levels, where each level contains task IDs that can run in parallel.
        """
        # Create adjacency list
        dependencies = {task.id: set(task.dependencies) for task in tasks}
        
        # Find tasks with no dependencies (level 0)
        levels = []
        remaining = set(task.id for task in tasks)
        
        while remaining:
            # Find tasks whose dependencies are all satisfied
            current_level = []
            for task_id in list(remaining):
                task_deps = dependencies.get(task_id, set())
                if task_deps.issubset(set().union(*[level for level in levels]) if levels else set()):
                    current_level.append(task_id)
            
            if not current_level:
                # Circular dependency or error - break by taking any remaining task
                if remaining:
                    current_level = [list(remaining)[0]]
                else:
                    break
            
            levels.append(current_level)
            # Remove completed tasks from remaining
            for task_id in current_level:
                remaining.discard(task_id)
        
        return levels

    def _build_execution_graph(self, tasks: List[OrchestrationTask], dependencies: Dict[str, List[str]]) -> ExecutionGraph:
        """
        Build an execution graph from tasks and dependencies.
        """
        nodes = []
        edges = []
        
        # Create nodes
        for task in tasks:
            node_type = NodeType.TASK
            if task.task_type == TaskType.PARALLEL:
                node_type = NodeType.PARALLEL
            elif task.task_type == TaskType.HUMAN_APPROVAL:
                node_type = NodeType.APPROVAL
            elif task.task_type == TaskType.SUB_AGENT:
                node_type = NodeType.SUB_GRAPH
            
            node = GraphNode(
                id=task.id,
                task_id=task.id,
                node_type=node_type,
                label=task.name,
                status=TaskStatus.PENDING,
                level=0  # Will be computed later
            )
            nodes.append(node)
        
        # Create edges
        for task_id, deps in dependencies.items():
            for dep_id in deps:
                edge = GraphEdge(
                    source=dep_id,
                    target=task_id,
                    edge_type="dependency"
                )
                edges.append(edge)
        
        # Compute levels for nodes
        levels = self._compute_dependency_levels(tasks)
        node_levels = {}
        for level_idx, level in enumerate(levels):
            for task_id in level:
                node_levels[task_id] = level_idx
        
        # Update node levels
        for node in nodes:
            node.level = node_levels.get(node.id, 0)
        
        # Find entry nodes (no incoming edges)
        all_targets = {edge.target for edge in edges}
        entry_nodes = [node.id for node in nodes if node.id not in all_targets]
        
        return ExecutionGraph(
            nodes=nodes,
            edges=edges,
            levels=levels,
            entry_nodes=entry_nodes
        )

    def _generate_validation_rules(self, steps: List[PlanStep]) -> List[ValidationRule]:
        """
        Generate validation rules for the plan based on steps.
        """
        rules = []
        
        # Add rule that each step should produce some output
        for step in steps:
            if step.tools:
                rules.append(ValidationRule(
                    field="output",
                    operator="exists",
                    expected_value=True,
                    error_message=f"Step '{step.description}' did not produce expected output"
                ))
        
        # Add rule for overall plan completion
        rules.append(ValidationRule(
            field="completed_steps",
            operator="gte",
            expected_value=len(steps),
            error_message=f"Plan did not complete all {len(steps)} steps"
        ))
        
        return rules

    async def _find_matching_template(self, objective: Objective) -> Optional[Any]:
        """
        Find a matching template for the objective.
        """
        if not self.template_manager:
            return None
        
        try:
            # Try to find template by objective type
            objective_types = objective.context.get("objective_types", [])
            for obj_type in objective_types:
                # Map objective types to template categories
                type_to_category = {
                    "research": "research_report",
                    "development": "software_development",
                    "data_processing": "data_analysis",
                    "content_creation": "content_creation",
                    "system_admin": "business_automation",
                    "communication": "email_campaign",
                    "automation": "business_automation"
                }
                
                if obj_type in type_to_category:
                    category = type_to_category[obj_type]
                    # In a real implementation, we would search templates by category
                    # For now, we'll return None to fall back to default planning
                    pass
            
            return None
        except Exception as e:
            logger.warning(f"Error finding template: {e}")
            return None