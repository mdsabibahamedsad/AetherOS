#!/usr/bin/env python3
"""
AetherOS Personal Assistant Runtime — The Single Canonical Runtime.

This is the ONE brain that all user-facing entry points (Chat, Jarvis, Voice,
Command Palette, Automation, Scheduled Jobs, API, MCP, External Events)
route through. It consolidates:

- aetheros_runtime (core runtime, agent runtime, router)
- aetheros_ai_runtime (model routing, providers, quality memory)
- aetheros_jarvis (Jarvis lifecycle, subsystems)
- aetheros_automation (orchestrator, approvals, recovery, background jobs)
- aetheros_capability (capability registry, command gateway, permission model,
  execution engine, capability router, planner)

Into ONE canonical PersonalAssistantRuntime.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Set

# Import existing subsystems
from aetheros_runtime import (
    normalize_tool_call,
    validate_tool_arguments,
    validate_structured,
    ContextBudgetManager,
    UsageRecord,
    parse_usage,
    build_fallback,
    run_with_fallback,
    ModelDownloadManager,
    ComputeMesh,
)
from aetheros_runtime.router import (
    IntelligentModelRouter,
    TaskRequirements,
    ModelDecisionTrace,
    QualityMemory,
    PROFILES,
    DEFAULT_WEIGHTS,
    MODES,
)
from aetheros_runtime.agent_runtime import (
    AgentRole,
    AgentTask,
    AgentResult,
    AgentRuntime,
)
from aetheros_ai_runtime.adapters import (
    InferenceEvent,
    InferenceRequest,
    ProviderAdapter,
    classify_error,
    NON_RETRYABLE,
    RETRYABLE,
)
from aetheros_jarvis.runtime import JarvisRuntime, JarvisState, JarvisConfig

# Import our capability kernel
from aetheros_capability import (
    CapabilityRegistry,
    CapabilitySpec,
    CapabilityCategory,
    ToolReference,
    ModelReference,
    CommandGateway,
    TaskRequest,
    TaskSource,
    PermissionModel,
    RiskLevel,
    PermissionDecision,
    ExecutionEngine,
    ExecutionResult,
    CapabilityRouter,
    RoutingDecision,
    get_parameterizer,
    get_planner,
    Parameterizer,
    Planner,
    ParameterizationResult,
    Plan,
    PlanStep,
)

# Optional: TaskOrchestrator (lazy loaded)
_TaskOrchestrator = None

def _get_task_orchestrator():
    global _TaskOrchestrator
    if _TaskOrchestrator is None:
        try:
            from aetheros_automation.orchestrator.orchestrator import TaskOrchestrator
            _TaskOrchestrator = TaskOrchestrator
        except ImportError:
            pass
    return _TaskOrchestrator

logger = logging.getLogger(__name__)


# =============================================================================
# UNIFIED TYPES
# =============================================================================

class RequestSource(Enum):
    """Source of an assistant request."""
    CHAT = "chat"
    VOICE = "voice"
    JARVIS = "jarvis"
    GLOBAL_HOTKEY = "global_hotkey"
    COMMAND_PALETTE = "command_palette"
    AUTOMATION = "automation"
    SCHEDULED_JOB = "scheduled_job"
    API = "api"
    MCP = "mcp"
    EXTERNAL_EVENT = "external_event"
    WEBHOOK = "webhook"


class AssistantMode(Enum):
    """Assistant operating mode."""
    ASSIST = "assist"          # Suggest before acting
    EXECUTE = "execute"        # Auto-execute low-risk actions
    AUTONOMOUS = "autonomous"  # Multi-step with policy-controlled approvals
    PRIVATE = "private"        # Prefer local processing
    RESEARCH = "research"      # Prioritize evidence and citations
    CODING = "coding"          # Prioritize repo/tool/test workflow
    JARVIS = "jarvis"          # Voice + real-time computer control


@dataclass
class AssistantRequest:
    """Normalized request entering the assistant runtime."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: RequestSource = RequestSource.CHAT
    user_input: str = ""
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    requested_mode: Optional[AssistantMode] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None


@dataclass
class Entity:
    """Extracted entity from user input."""
    type: str
    value: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Constraint:
    """Constraint on the assistant's behavior."""
    type: str
    value: Any
    description: str = ""


@dataclass
class AssistantIntent:
    """Structured intent representation."""
    objective: str
    entities: List[Entity] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    requested_outcome: str = ""
    urgency: str = "normal"
    deadline: Optional[str] = None
    risk_tolerance: RiskLevel = RiskLevel.MEDIUM
    requires_external_side_effects: bool = False


class TaskState(Enum):
    """Unified task lifecycle states."""
    CREATED = "created"
    UNDERSTANDING = "understanding"
    CONTEXT_GATHERING = "context_gathering"
    PLANNING = "planning"
    CAPABILITY_SELECTION = "capability_selection"
    POLICY_CHECK = "policy_check"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    EXECUTING = "executing"
    OBSERVING = "observing"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    WAITING_EXTERNAL = "waiting_external"


@dataclass
class TaskStep:
    """Single step in an execution plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    capability_id: str = ""
    tool_name: str = ""
    model_name: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected_output: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    state: TaskState = TaskState.CREATED
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    verification_result: Optional[Dict[str, Any]] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Task:
    """Unified task representation with full lifecycle."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    goal: str = ""
    request: Optional[AssistantRequest] = None
    intent: Optional[AssistantIntent] = None
    
    # Planning
    plan: List[TaskStep] = field(default_factory=list)
    current_step_index: int = 0
    
    # Execution
    state: TaskState = TaskState.CREATED
    
    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recovery
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    
    # Checkpoint
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def get_current_step(self) -> Optional[TaskStep]:
        if 0 <= self.current_step_index < len(self.plan):
            return self.plan[self.current_step_index]
        return None
    
    def get_next_ready_step(self) -> Optional[TaskStep]:
        for i, step in enumerate(self.plan):
            if step.state == TaskState.CREATED:
                deps_met = all(
                    self.plan[dep_idx].state == TaskState.COMPLETED
                    for dep_idx in step.dependencies
                    if dep_idx < len(self.plan)
                )
                if deps_met:
                    return step
        return None
    
    def can_execute_next(self) -> bool:
        return self.get_next_ready_step() is not None


@dataclass
class ApprovalRequest:
    """Request for human approval."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    step_id: str = ""
    capability_id: str = ""
    tool_name: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    reason: str = ""
    tool_arguments: Dict[str, Any] = field(default_factory=dict)
    data_being_sent: Dict[str, Any] = field(default_factory=dict)
    target: str = ""
    reversibility: str = "reversible"
    requested_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: str = "pending"  # pending, approved, denied, expired
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssistantResult:
    """Structured result from assistant execution."""
    status: str  # completed, partial, failed, blocked, cancelled, waiting
    summary: str
    verified: bool
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    pending_actions: List[Dict[str, Any]] = field(default_factory=list)
    blockers: List[Dict[str, Any]] = field(default_factory=list)
    follow_ups: List[Dict[str, Any]] = field(default_factory=list)
    trace: Optional[Dict[str, Any]] = None


# =============================================================================
# PERSONAL ASSISTANT RUNTIME
# =============================================================================

class PersonalAssistantRuntime:
    """
    The ONE canonical Personal Assistant Runtime.
    
    All entry points (Chat, Jarvis, Voice, Command Palette, Automation,
    Scheduled Jobs, API, MCP, External Events) route through this runtime.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._lock = threading.RLock()
        self._initialized = False
        
        # Core components (initialized on demand)
        self._capability_registry: Optional[CapabilityRegistry] = None
        self._command_gateway: Optional[CommandGateway] = None
        self._permission_model: Optional[PermissionModel] = None
        self._execution_engine: Optional[ExecutionEngine] = None
        self._capability_router: Optional[CapabilityRouter] = None
        self._parameterizer: Optional[Parameterizer] = None
        self._planner: Optional[Planner] = None
        
        # Legacy subsystem wrappers
        self._agent_runtime: Optional[AgentRuntime] = None
        self._model_router: Optional[IntelligentModelRouter] = None
        self._jarvis_runtime: Optional[JarvisRuntime] = None
        self._orchestrator: Optional[object] = None  # TaskOrchestrator (lazy loaded)
        
        # Task management
        self._tasks: Dict[str, Task] = {}
        self._task_history: List[Task] = []
        self._max_history = 1000
        
        # Approval management
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        self._approval_history: List[ApprovalRequest] = []
        self._approval_callbacks: List[Callable[[ApprovalRequest], None]] = []
        
        # Background job management
        self._background_jobs: Dict[str, Task] = {}
        self._job_schedulers: Dict[str, threading.Timer] = {}
        
        # Event streaming
        self._event_listeners: List[Callable[[Dict[str, Any]], None]] = []
        
        # Checkpoint persistence
        self._checkpoint_dir: Optional[str] = None
        
        # Stats
        self._stats = {
            "total_requests": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "approvals_requested": 0,
            "approvals_approved": 0,
            "approvals_denied": 0,
        }
    
    # -------------------------------------------------------------------------
    # INITIALIZATION
    # -------------------------------------------------------------------------
    
    def initialize(self, checkpoint_dir: Optional[str] = None) -> bool:
        """Initialize the personal assistant runtime."""
        with self._lock:
            if self._initialized:
                return True
            
            self._checkpoint_dir = checkpoint_dir
            
            # Initialize capability kernel
            self._capability_registry = CapabilityRegistry(self.config)
            self._capability_registry.initialize()
            self._capability_registry.discover_and_register_capabilities()
            
            # Filter config for CommandGateway
            gateway_config = {k: v for k, v in self.config.items() 
                             if k in ('max_concurrent_tasks', 'default_timeout_seconds', 'enable_background_tasks', 
                                     'enable_streaming', 'auto_start_tasks', 'persist_tasks', 'task_retention_hours')}
            self._command_gateway = CommandGateway(gateway_config)
            self._permission_model = PermissionModel(self.config)
            self._execution_engine = ExecutionEngine(self.config)
            self._execution_engine.register_default_recovery_strategies()
            self._execution_engine.register_default_verification_strategies()
            
            self._capability_router = CapabilityRouter(self.config)
            self._capability_router.initialize()
            
            self._parameterizer = get_parameterizer(self.config)
            self._planner = get_planner(self.config)
            
            # Initialize legacy subsystems
            self._agent_runtime = AgentRuntime()
            self._model_router = IntelligentModelRouter(
                list_models=lambda: [],  # Will be replaced with real provider
                quality=QualityMemory(),
            )
            
            self._jarvis_runtime = JarvisRuntime()
            self._jarvis_runtime.initialize()
            
            orch_cls = _get_task_orchestrator()
            if orch_cls:
                self._orchestrator = orch_cls()
            
            # Load checkpoints if available
            if self._checkpoint_dir:
                self._load_checkpoints()
            
            self._initialized = True
            logger.info("PersonalAssistantRuntime initialized")
            return True
    
    def _ensure_initialized(self):
        if not self._initialized:
            self.initialize()
    
    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------
    
    def execute(self, request: AssistantRequest) -> AssistantResult:
        """
        Main entry point for all assistant requests.
        
        This is the single canonical entry point that all user-facing
        interfaces (Chat, Jarvis, Voice, Command Palette, Automation, etc.)
        must use.
        """
        self._ensure_initialized()
        self._stats["total_requests"] += 1
        
        # Create task from request
        task = self._create_task(request)
        
        # Execute asynchronously for background tasks, sync for foreground
        if request.source in (RequestSource.AUTOMATION, RequestSource.SCHEDULED_JOB):
            self._start_task_async(task)
            return AssistantResult(
                status="waiting",
                summary=f"Task {task.id[:8]} queued for background execution",
                verified=False,
            )
        else:
            self._execute_task(task)
            return self._build_result(task)
    
    async def execute_async(self, request: AssistantRequest) -> AssistantResult:
        """Async version of execute for native async callers."""
        self._ensure_initialized()
        self._stats["total_requests"] += 1
        
        task = self._create_task(request)
        await self._execute_task_async(task)
        return self._build_result(task)
    
    def pause(self, task_id: str) -> bool:
        """Pause a running task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state not in (TaskState.EXECUTING, TaskState.OBSERVING, TaskState.VERIFYING):
                return False
            task.state = TaskState.PAUSED
            self._checkpoint_task(task)
            return True
    
    def resume(self, task_id: str) -> bool:
        """Resume a paused task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state != TaskState.PAUSED:
                return False
            task.state = TaskState.EXECUTING
            self._start_task_async(task)
            return True
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                return False
            task.state = TaskState.CANCELLED
            task.error = "Cancelled by user"
            task.completed_at = datetime.now()
            return True
    
    def approve(self, task_id: str, approval_id: str) -> bool:
        """Approve a pending approval request."""
        with self._lock:
            approval = self._pending_approvals.get(approval_id)
            if not approval or approval.task_id != task_id:
                return False
            if approval.status != "pending":
                return False
            if approval.expires_at and datetime.now() > approval.expires_at:
                approval.status = "expired"
                return False
            
            approval.status = "approved"
            approval.decided_at = datetime.now()
            approval.decided_by = "user"
            
            self._approval_history.append(approval)
            del self._pending_approvals[approval_id]
            self._stats["approvals_approved"] += 1
            
            # Resume the task
            task = self._tasks.get(task_id)
            if task and task.state == TaskState.WAITING_FOR_APPROVAL:
                task.state = TaskState.EXECUTING
                self._start_task_async(task)
            
            return True
    
    def reject(self, task_id: str, approval_id: str) -> bool:
        """Reject a pending approval request."""
        with self._lock:
            approval = self._pending_approvals.get(approval_id)
            if not approval or approval.task_id != task_id:
                return False
            if approval.status != "pending":
                return False
            
            approval.status = "denied"
            approval.decided_at = datetime.now()
            approval.decided_by = "user"
            
            self._approval_history.append(approval)
            del self._pending_approvals[approval_id]
            self._stats["approvals_denied"] += 1
            
            # Fail the task
            task = self._tasks.get(task_id)
            if task:
                task.state = TaskState.FAILED
                task.error = f"Approval denied: {approval.reason}"
                task.completed_at = datetime.now()
            
            return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)
    
    def list_tasks(
        self,
        state: Optional[TaskState] = None,
        source: Optional[RequestSource] = None,
        limit: int = 100,
    ) -> List[Task]:
        """List tasks with optional filters."""
        with self._lock:
            tasks = list(self._tasks.values())
            if state:
                tasks = [t for t in tasks if t.state == state]
            if source:
                tasks = [t for t in tasks if t.request and t.request.source == source]
            return tasks[-limit:]
    
    def subscribe(self, task_id: str, listener: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        """Subscribe to task events."""
        # In a full implementation, this would use a proper event system
        def unsubscribe():
            pass
        return unsubscribe
    
    def get_stats(self) -> Dict[str, Any]:
        """Get runtime statistics."""
        with self._lock:
            return {
                **self._stats,
                "active_tasks": len([t for t in self._tasks.values() if t.state == TaskState.EXECUTING]),
                "pending_approvals": len(self._pending_approvals),
                "background_jobs": len(self._background_jobs),
            }
    
    def shutdown(self) -> None:
        """Shutdown the runtime gracefully."""
        with self._lock:
            # Cancel all running tasks
            for task in self._tasks.values():
                if task.state in (TaskState.CREATED, TaskState.UNDERSTANDING, TaskState.CONTEXT_GATHERING,
                                  TaskState.PLANNING, TaskState.CAPABILITY_SELECTION, TaskState.POLICY_CHECK,
                                  TaskState.EXECUTING, TaskState.OBSERVING, TaskState.VERIFYING,
                                  TaskState.RECOVERING, TaskState.PAUSED, TaskState.WAITING_EXTERNAL):
                    task.state = TaskState.CANCELLED
                    task.error = "Runtime shutdown"
                    task.completed_at = datetime.now()
            
            # Cancel background job schedulers
            for timer in self._job_schedulers.values():
                timer.cancel()
            self._job_schedulers.clear()
            
            # Save checkpoints
            if self._checkpoint_dir:
                self._save_checkpoints()
            
            # Shutdown subsystems
            if self._jarvis_runtime:
                self._jarvis_runtime.shutdown()
            
            logger.info("PersonalAssistantRuntime shutdown complete")
    
    # -------------------------------------------------------------------------
    # INTERNAL TASK MANAGEMENT
    # -------------------------------------------------------------------------
    
    def _create_task(self, request: AssistantRequest) -> Task:
        """Create a task from a request."""
        task = Task(
            id=request.id,
            goal=request.user_input,
            request=request,
        )
        with self._lock:
            self._tasks[task.id] = task
        return task
    
    def _execute_task(self, task: Task) -> None:
        """Execute a task synchronously."""
        self._run_task_loop(task)
    
    async def _execute_task_async(self, task: Task) -> None:
        """Execute a task asynchronously."""
        self._run_task_loop(task)
    
    def _start_task_async(self, task: Task) -> None:
        """Start task execution in background thread."""
        thread = threading.Thread(target=self._run_task_loop, args=(task,), daemon=True)
        thread.start()
    
    def _run_task_loop(self, task: Task) -> None:
        """Main task execution loop."""
        try:
            # Phase 1: Understanding
            task.state = TaskState.UNDERSTANDING
            self._emit_event({"type": "intent.detected", "task_id": task.id})
            task.intent = self._understand_intent(task)
            
            # Phase 2: Context Gathering
            task.state = TaskState.CONTEXT_GATHERING
            self._emit_event({"type": "context.loaded", "task_id": task.id})
            context = self._gather_context(task)
            
            # Phase 3: Planning
            task.state = TaskState.PLANNING
            self._emit_event({"type": "plan.created", "task_id": task.id})
            task.plan = self._create_plan(task, context)
            
            # Phase 4: Capability Selection
            task.state = TaskState.CAPABILITY_SELECTION
            self._select_capabilities(task)
            
            # Phase 5: Policy Check
            task.state = TaskState.POLICY_CHECK
            permission = self._check_permissions(task)
            if not permission.allowed:
                if permission.required_approval != "none":
                    task.state = TaskState.WAITING_FOR_APPROVAL
                    self._request_approval(task, permission)
                    return
                else:
                    task.state = TaskState.FAILED
                    task.error = permission.reason
                    task.completed_at = datetime.now()
                    return
            
            # Phase 6: Execution Loop
            task.state = TaskState.EXECUTING
            task.started_at = datetime.now()
            self._execute_plan(task)
            
            # Phase 7: Verification
            if task.state == TaskState.EXECUTING:
                task.state = TaskState.VERIFYING
                self._verify_results(task)
            
            # Phase 8: Completion
            if task.state != TaskState.FAILED:
                task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()
            
        except Exception as e:
            logger.exception(f"Task {task.id} failed: {e}")
            task.state = TaskState.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
        finally:
            self._record_task_completion(task)
            self._emit_event({"type": "task.completed", "task_id": task.id, "state": task.state.value})
    
    def _understand_intent(self, task: Task) -> AssistantIntent:
        """Parse user input into structured intent."""
        # In a full implementation, this would use an LLM
        # For now, use simple heuristics
        goal = task.goal.lower()
        
        intent_type = "question"
        if any(w in goal for w in ["create", "build", "make", "generate", "write"]):
            intent_type = "creation"
        elif any(w in goal for w in ["fix", "repair", "debug", "solve"]):
            intent_type = "action"
        elif any(w in goal for w in ["find", "search", "look up", "research"]):
            intent_type = "research"
        elif any(w in goal for w in ["monitor", "watch", "keep checking", "automate"]):
            intent_type = "monitoring"
        elif any(w in goal for w in ["email", "message", "send", "notify"]):
            intent_type = "communication"
        elif any(w in goal for w in ["schedule", "calendar", "meeting", "appointment"]):
            intent_type = "system_action"
        
        # Extract entities (simplified)
        entities = []
        # Could use NLP here
        
        return AssistantIntent(
            objective=task.goal,
            entities=entities,
            constraints=[],
            requested_outcome=task.goal,
            urgency="normal",
            risk_tolerance=RiskLevel.MEDIUM,
            requires_external_side_effects=any(w in goal for w in ["send", "email", "message", "post", "publish", "delete", "buy", "order"]),
        )
    
    def _gather_context(self, task: Task) -> Dict[str, Any]:
        """Gather relevant context for the task."""
        context = {}
        
        # Add request context
        if task.request:
            context.update(task.request.context)
        
        # Add relevant memory (would query memory system)
        # context["memory"] = self._get_relevant_memory(task)
        
        # Add current project/session info
        # context["project"] = self._get_current_project()
        
        # Add available capabilities
        caps = self._capability_registry.list_capabilities(available_only=True)
        context["available_capabilities"] = [c.id for c in caps]
        
        return context
    
    def _create_plan(self, task: Task, context: Dict[str, Any]) -> List[TaskStep]:
        """Create an execution plan for the task."""
        if not task.intent:
            return []
        
        # Use the planner
        plan = self._planner.create_plan(task.request)
        
        # Convert Plan to TaskStep list
        steps = []
        for step in plan.steps:
            task_step = TaskStep(
                id=step.id,
                name=step.name,
                description=step.description,
                capability_id=step.capability_id,
                tool_name=step.tool_name,
                input_data=step.input_template,
                expected_output=step.expected_output,
                dependencies=step.dependencies,
            )
            steps.append(task_step)
        
        return steps
    
    def _select_capabilities(self, task: Task) -> None:
        """Select optimal capabilities for each plan step."""
        for step in task.plan:
            if step.capability_id and step.tool_name:
                continue  # Already specified
            
            # Route to best capability
            routing = self._capability_router.route(step.description or task.goal)
            step.capability_id = routing.capability_id
            step.tool_name = routing.tool_name or ""
            step.model_name = routing.model_name or ""
    
    def _check_permissions(self, task: Task) -> PermissionDecision:
        """Check if task has required permissions."""
        # Check each step's capability
        for step in task.plan:
            cap_id = step.capability_id
            if not cap_id:
                continue
            
            cap_spec = self._capability_registry.get_capability_spec(cap_id)
            category = cap_spec.category.value if cap_spec else None
            
            decision = self._permission_model.check_capability_permission(
                cap_id,
                category=category,
                tool_name=step.tool_name,
                context={
                    "user_permissions": task.request.permissions.get("granted", []) if task.request else [],
                    "risk_tolerance": task.request.context.get("risk_tolerance", RiskLevel.MEDIUM) if task.request else RiskLevel.MEDIUM
                }
            )
            
            if not decision.allowed:
                return decision
        
        return PermissionDecision(allowed=True, risk_level=RiskLevel.NONE)
    
    def _request_approval(self, task: Task, permission: PermissionDecision) -> None:
        """Request human approval for a capability."""
        # Find the step that needs approval
        step = task.get_current_step() or (task.plan[0] if task.plan else None)
        if not step:
            return
        
        approval = ApprovalRequest(
            task_id=task.id,
            step_id=step.id,
            capability_id=step.capability_id,
            tool_name=step.tool_name,
            risk_level=permission.risk_level,
            reason=permission.reason,
            tool_arguments=step.input_data,
            target=step.capability_id,
        )
        
        with self._lock:
            self._pending_approvals[approval.id] = approval
            self._stats["approvals_requested"] += 1
        
        # Notify callbacks
        for callback in self._approval_callbacks:
            try:
                callback(approval)
            except Exception as e:
                logger.warning(f"Approval callback error: {e}")
        
        self._emit_event({"type": "approval.required", "approval_id": approval.id, "task_id": task.id})
    
    def _execute_plan(self, task: Task) -> None:
        """Execute the task plan step by step."""
        while task.can_execute_next():
            step = task.get_next_ready_step()
            if not step:
                break
            
            task.current_step_index = task.plan.index(step)
            step.state = TaskState.EXECUTING
            step.started_at = datetime.now()
            
            self._emit_event({"type": "tool.started", "task_id": task.id, "step_id": step.id, "tool": step.tool_name})
            
            # Execute step
            result = self._execution_engine.execute_step(step, task)
            
            step.result = result.output
            step.error = result.error
            step.completed_at = datetime.now()
            
            # Observation
            task.state = TaskState.OBSERVING
            observations = self._observation_engine.observe(step, result, task)
            
            # Verification
            task.state = TaskState.VERIFYING
            verification = self._verification_engine.verify(step, result, observations, task)
            step.verification_result = verification
            
            success = all(v.get("passed", True) for v in verification.values())
            if success and not any(v.get("required", False) for v in verification.values() if not v.get("passed", True)):
                step.state = TaskState.COMPLETED
                task.artifacts.append({"step_id": step.id, "output": result.output})
            else:
                # Recovery
                recovery = self._recovery_engine.attempt_recovery(step, result.error or "Verification failed")
                if recovery and recovery.success:
                    step.result = recovery.output
                    step.state = TaskState.COMPLETED
                    task.artifacts.append({"step_id": step.id, "output": recovery.output})
                else:
                    step.state = TaskState.FAILED
                    task.state = TaskState.FAILED
                    task.error = result.error or "Verification failed"
                    break
            
            self._emit_event({"type": "tool.completed", "task_id": task.id, "step_id": step.id, "success": success})
            
            # Checkpoint after each step
            self._checkpoint_task(task)
        
        # Create final result
        if task.state != TaskState.FAILED:
            task.result = {
                "summary": self._generate_summary(task),
                "artifacts": task.artifacts,
                "steps_completed": len([s for s in task.plan if s.state == TaskState.COMPLETED]),
            }
    
    def _verify_results(self, task: Task) -> None:
        """Final verification of task results."""
        # Run final verification strategies
        pass
    
    def _generate_summary(self, task: Task) -> str:
        """Generate a human-readable summary of task execution."""
        completed = len([s for s in task.plan if s.state == TaskState.COMPLETED])
        total = len(task.plan)
        return f"Completed {completed}/{total} steps for: {task.goal[:100]}"
    
    def _build_result(self, task: Task) -> AssistantResult:
        """Build the final assistant result."""
        if task.state == TaskState.COMPLETED:
            status = "completed"
        elif task.state == TaskState.PARTIAL:
            status = "partial"
        elif task.state == TaskState.FAILED:
            status = "failed"
        elif task.state == TaskState.BLOCKED:
            status = "blocked"
        elif task.state == TaskState.CANCELLED:
            status = "cancelled"
        elif task.state == TaskState.WAITING_FOR_APPROVAL:
            status = "waiting"
        else:
            status = "partial"
        
        return AssistantResult(
            status=status,
            summary=self._generate_summary(task),
            verified=all(
                s.state == TaskState.COMPLETED and 
                (not s.verification_result or all(v.get("passed", True) for v in s.verification_result.values()))
                for s in task.plan
            ),
            artifacts=task.artifacts,
            actions=[{"step_id": s.id, "tool": s.tool_name, "output": s.result} for s in task.plan],
        )
    
    def _record_task_completion(self, task: Task) -> None:
        """Record task completion in history."""
        with self._lock:
            self._task_history.append(task)
            if len(self._task_history) > self._max_history:
                self._task_history.pop(0)
            
            if task.state == TaskState.COMPLETED:
                self._stats["completed_tasks"] += 1
            elif task.state == TaskState.FAILED:
                self._stats["failed_tasks"] += 1
    
    def _checkpoint_task(self, task: Task) -> None:
        """Save task checkpoint for recovery."""
        checkpoint = {
            "task_id": task.id,
            "timestamp": datetime.now().isoformat(),
            "state": task.state.value,
            "current_step_index": task.current_step_index,
            "plan": [
                {
                    "id": s.id,
                    "state": s.state.value,
                    "result": s.result,
                    "error": s.error,
                }
                for s in task.plan
            ],
            "artifacts": task.artifacts,
        }
        task.checkpoints.append(checkpoint)
        
        # Persist to disk if configured
        if self._checkpoint_dir:
            import json
            path = f"{self._checkpoint_dir}/checkpoint_{task.id}.json"
            try:
                with open(path, "w") as f:
                    json.dump(checkpoint, f, default=str)
            except Exception as e:
                logger.warning(f"Failed to save checkpoint: {e}")
    
    def _load_checkpoints(self) -> None:
        """Load task checkpoints from disk."""
        if not self._checkpoint_dir:
            return
        import glob
        import json
        for path in glob.glob(f"{self._checkpoint_dir}/checkpoint_*.json"):
            try:
                with open(path) as f:
                    checkpoint = json.load(f)
                # Restore task from checkpoint (simplified)
                logger.info(f"Loaded checkpoint: {path}")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint {path}: {e}")
    
    def _save_checkpoints(self) -> None:
        """Save all task checkpoints to disk."""
        for task in self._tasks.values():
            self._checkpoint_task(task)
    
    # -------------------------------------------------------------------------
    # EVENT STREAMING
    # -------------------------------------------------------------------------
    
    def _emit_event(self, event: Dict[str, Any]) -> None:
        """Emit a runtime event to all listeners."""
        event["timestamp"] = datetime.now().isoformat()
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.warning(f"Event listener error: {e}")
    
    def add_event_listener(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Add an event listener."""
        with self._lock:
            self._event_listeners.append(listener)
    
    # -------------------------------------------------------------------------
    # OBSERVATION / VERIFICATION / RECOVERY ENGINES
    # -------------------------------------------------------------------------
    
    class _ObservationEngine:
        def observe(self, step: TaskStep, result: ExecutionResult, task: Task) -> Dict[str, Any]:
            return {
                "tool": step.tool_name,
                "output_keys": list(result.output.keys()) if isinstance(result.output, dict) else [],
                "has_error": result.error is not None,
                "timestamp": datetime.now().isoformat(),
            }
    
    class _VerificationEngine:
        def verify(self, step: TaskStep, result: ExecutionResult, observations: Dict[str, Any], task: Task) -> Dict[str, Dict[str, Any]]:
            results = {}
            
            # Basic tool success
            results["tool_success"] = {
                "passed": result.success,
                "required": True,
                "error": result.error,
            }
            
            # Non-empty output
            has_output = bool(result.output and (not isinstance(result.output, dict) or len(result.output) > 0))
            results["non_empty_output"] = {
                "passed": has_output,
                "required": False,
            }
            
            return results
    
    class _RecoveryEngine:
        def attempt_recovery(self, step: TaskStep, error: str) -> Optional[ExecutionResult]:
            from aetheros_capability import get_execution_engine
            engine = get_execution_engine()
            return engine.attempt_recovery(step, error)
    
    _observation_engine = _ObservationEngine()
    _verification_engine = _VerificationEngine()
    _recovery_engine = _RecoveryEngine()
    
    # -------------------------------------------------------------------------
    # BACKGROUND JOBS
    # -------------------------------------------------------------------------
    
    def schedule_job(
        self,
        name: str,
        request: AssistantRequest,
        schedule: Dict[str, Any],  # cron, interval, etc.
    ) -> str:
        """Schedule a recurring background job."""
        job_id = str(uuid.uuid4())
        
        # In a full implementation, this would use a proper scheduler
        # For now, create a simple interval timer
        if schedule.get("type") == "interval":
            interval = schedule.get("seconds", 3600)
            
            def run_job():
                self.execute(request)
            
            timer = threading.Timer(interval, run_job)
            timer.daemon = True
            timer.start()
            
            with self._lock:
                self._job_schedulers[job_id] = timer
        
        return job_id
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job."""
        with self._lock:
            timer = self._job_schedulers.pop(job_id, None)
            if timer:
                timer.cancel()
                return True
        return False
    
    # -------------------------------------------------------------------------
    # JARVIS INTEGRATION
    # -------------------------------------------------------------------------
    
    def start_jarvis(self) -> bool:
        """Start the Jarvis subsystem."""
        if self._jarvis_runtime:
            return self._jarvis_runtime.start()
        return False
    
    def stop_jarvis(self) -> bool:
        """Stop the Jarvis subsystem."""
        if self._jarvis_runtime:
            return self._jarvis_runtime.shutdown()
        return False
    
    def get_jarvis_state(self) -> Optional[JarvisState]:
        """Get current Jarvis state."""
        if self._jarvis_runtime:
            return self._jarvis_runtime.state
        return None
    
    # -------------------------------------------------------------------------
    # MODEL ROUTING INTEGRATION
    # -------------------------------------------------------------------------
    
    def route_model(self, requirements: TaskRequirements) -> ModelDecisionTrace:
        """Route to optimal model for a task."""
        return self._model_router.route(requirements)
    
    # -------------------------------------------------------------------------
    # LEGACY COMPATIBILITY
    # -------------------------------------------------------------------------
    
    def submit_chat(self, message: str, context: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None) -> str:
        """Legacy chat submission."""
        request = AssistantRequest(
            source=RequestSource.CHAT,
            user_input=message,
            context=context or {},
            metadata={"session_id": session_id} if session_id else {},
        )
        handle = self.execute(request)
        return handle.id if hasattr(handle, 'id') else ""
    
    def submit_voice(self, transcript: str, audio_data: Optional[bytes] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """Legacy voice submission."""
        request = AssistantRequest(
            source=RequestSource.VOICE,
            user_input=transcript,
            context=context or {},
            metadata={"audio_data": audio_data is not None} if audio_data else {},
        )
        handle = self.execute(request)
        return handle.id if hasattr(handle, 'id') else ""
    
    def submit_jarvis(self, command: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Legacy Jarvis submission."""
        request = AssistantRequest(
            source=RequestSource.JARVIS,
            user_input=command,
            context=context or {},
        )
        handle = self.execute(request)
        return handle.id if hasattr(handle, 'id') else ""
    
    def submit_automation(self, automation_id: str, trigger_data: Optional[Dict[str, Any]] = None) -> str:
        """Legacy automation submission."""
        request = AssistantRequest(
            source=RequestSource.AUTOMATION,
            user_input=f"Run automation {automation_id}",
            context={"automation_id": automation_id, "trigger_data": trigger_data or {}},
            metadata={"automation_id": automation_id},
        )
        handle = self.execute(request)
        return handle.id if hasattr(handle, 'id') else ""


# Module-level singleton
_assistant_runtime: Optional[PersonalAssistantRuntime] = None


def get_personal_assistant_runtime(config: Optional[Dict[str, Any]] = None) -> PersonalAssistantRuntime:
    """Get the global PersonalAssistantRuntime singleton."""
    global _assistant_runtime
    if _assistant_runtime is None:
        _assistant_runtime = PersonalAssistantRuntime(config)
    return _assistant_runtime


def initialize_personal_assistant(config: Optional[Dict[str, Any]] = None, checkpoint_dir: Optional[str] = None) -> PersonalAssistantRuntime:
    """Initialize the personal assistant runtime."""
    runtime = get_personal_assistant_runtime(config)
    runtime.initialize(checkpoint_dir)
    return runtime