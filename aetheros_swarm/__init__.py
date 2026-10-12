"""AetherOS Multi-Agent Swarm engine."""

from aetheros_swarm.models import (
    AgentInstance, AgentLifecycle, AgentMessage, AgentResult,
    ConsensusMode, FailureKind, MsgType, SideEffectTier,
    SwarmTask, SwarmTaskState, TaskBudget, Topology, VerificationPolicy,
)
from aetheros_swarm.registry import AgentRegistry, AgentDefinition, DEFINITIONS
from aetheros_swarm.decision import (
    OrchestrationDecision, OrchestrationDecisionEngine, TaskFeatures, analyze_goal,
)
from aetheros_swarm.decompose import TaskDecomposer, TopologyEngine
from aetheros_swarm.comms import (
    A2ALayer, AgentBlackboard, BlackboardEntry, MessageBus,
    build_handoff,
)
from aetheros_swarm.context import AgentContextPackage, ContextItem, ContextSelector
from aetheros_swarm.budgets import BudgetEngine, RunBudget
from aetheros_swarm.execute import ParallelExecutor, goal_signature
from aetheros_swarm.recovery import classify_error, plan_recovery, STRATEGY_TABLE
from aetheros_swarm.verify import (
    ConflictResolver, judge_debate, quality_gate, run_review_loop,
    synthesize, verify_result,
)
from aetheros_swarm.ops import (
    ApprovalQueue, ApprovalRequest, AuditLog, CheckpointStore,
    EventStream, RunEvent, RUN_EVENT_KINDS, Span, Tracer,
)
from aetheros_swarm.security import ToolAuthorizer
from aetheros_swarm.orchestrator import (
    DelegateExecutor, LocalFunctionExecutor, MultiAgentOrchestrator, SwarmRun,
)

__all__ = [
    "AgentInstance", "AgentLifecycle", "AgentMessage", "AgentResult",
    "ConsensusMode", "FailureKind", "MsgType", "SideEffectTier",
    "SwarmTask", "SwarmTaskState", "TaskBudget", "Topology", "VerificationPolicy",
    "AgentRegistry", "AgentDefinition", "DEFINITIONS",
    "OrchestrationDecision", "OrchestrationDecisionEngine", "TaskFeatures", "analyze_goal",
    "TaskDecomposer", "TopologyEngine",
    "A2ALayer", "AgentBlackboard", "BlackboardEntry", "MessageBus", "build_handoff",
    "AgentContextPackage", "ContextItem", "ContextSelector",
    "BudgetEngine", "RunBudget",
    "ParallelExecutor", "goal_signature",
    "classify_error", "plan_recovery", "STRATEGY_TABLE",
    "ConflictResolver", "judge_debate", "quality_gate", "run_review_loop",
    "synthesize", "verify_result",
    "ApprovalQueue", "ApprovalRequest", "AuditLog", "CheckpointStore",
    "EventStream", "RunEvent", "RUN_EVENT_KINDS", "Span", "Tracer",
    "ToolAuthorizer",
    "DelegateExecutor", "LocalFunctionExecutor", "MultiAgentOrchestrator", "SwarmRun",
]
