"""AetherOS AI Runtime & Chat Engine.

Comprehensive runtime layer that orchestrates providers, models, agents,
memory, gateway, chat, streaming, tools, context, and execution.

Every module is production-ready — fully typed, thread-safe, tested.

Model hub + provider fabric + intelligent model router (new in Master 45):
- ModelRecord/ProviderRecord with provenance tracking
- Unified ModelRegistry with trust/allow/block/pinning/deprecation
- Provider adapters: OpenAI, Anthropic, Local, CustomHTTP, MCPModel
- LocalInferenceManager with hardware probing
- ModelDecisionTrace for every routing decision
- Privacy redaction & classification
- Quality memory with recency decay
- 12 routing modes + 14 specialization profiles
- Circuit breaker + health monitoring
- Context budgeting + token accounting
- Structured tool-call normalization
- Structured output validation
- Multi-node compute mesh (explicit pairing, heartbeat, scheduler)
- Multi-format downloads (Ollama, HTTP with checksum)
- Inference runtime: streaming, cancel, retry, tokens, context budgeting
- Fallback chain with absolute privacy veto
- Escalation cascade: PRIMARY/SECONDARY/VERIFIER
- Token/cost accounting with Pricing integration
- Model cache + VRAM warm pool with LRU eviction
"""

from aetheros_runtime.runtime_manager import RuntimeManager, RuntimeState, RuntimeConfig
from aetheros_runtime.conversation_engine import (
    ConversationEngine, Conversation, ConversationFolder,
    ExportFormat,
)
from aetheros_runtime.context_engine import ContextEngine, ContextBundle
from aetheros_runtime.streaming_engine import (
    StreamingEngine, StreamChunk, StreamEvent,
    StreamState,
)
from aetheros_runtime.message_pipeline import (
    MessagePipeline, PipelineStage, MessageContext,
)
from aetheros_runtime.prompt_builder import PromptBuilder, PromptSection
from aetheros_runtime.agent_runtime import (
    AgentRuntime, AgentRole, AgentTask, AgentResult,
)
from aetheros_runtime.execution_queue import (
    ExecutionQueue, JobStatus, JobPriority, Job,
)
from aetheros_runtime.response_renderer import (
    ResponseRenderer, RenderBlock, BlockType,
)
from aetheros_runtime.code_executor import (
    CodeExecutor, CodeLanguage, ExecutionResult,
    SandboxMode,
)
from aetheros_runtime.filesystem_engine import (
    FileSystemEngine, FileInfo, FileChange,
)
from aetheros_runtime.workspace_manager import (
    WorkspaceManager, Workspace, Project,
)
from aetheros_runtime.memory_runtime import MemoryRuntime, MemoryEntry, MemoryType
from aetheros_runtime.reasoning_engine import (
    ReasoningEngine, ReasoningMode, ReasoningResult,
)
from aetheros_runtime.tool_calling import (
    ToolCallingInterface, ToolCall, ToolResult,
)
from aetheros_runtime.session_recovery import SessionRecovery, RecoveryPoint
from aetheros_runtime.notifications import NotificationBus, Notification, NotificationLevel
from aetheros_runtime.diagnostics import Diagnostics, MetricSnapshot
from aetheros_runtime.performance import PerformanceOptimizer as RuntimePerformanceOptimizer
from aetheros_runtime.health import HealthMonitor, CircuitBreaker, HealthState
from aetheros_runtime.privacy import PrivacyDecision, PrivacyRouter, classify_text, redact_for_cloud
from aetheros_runtime.router import IntelligentModelRouter, TaskRequirements, ModelDecisionTrace, QualityMemory, PROFILES, MODES
from aetheros_runtime.cache import ModelCache, WarmPool
from aetheros_runtime.runtime import ContextBudgetManager, UsageRecord, parse_usage, ToolCall, normalize_tool_call, validate_tool_arguments, validate_structured, FallbackPlan, build_fallback, run_with_fallback, ComputeNode, ComputeMesh, ModelDownloadManager

from aetheros_runtime.models import (
    DataClass, ProviderKind, HealthState, CircuitState,
    Provenance, Pricing, ModelRecord, ProviderRecord,
    EmbeddingModel, RerankerModel, VisionModel, AudioModel,
)

__all__ = [
    "RuntimeManager", "RuntimeState", "RuntimeConfig",
    "ConversationEngine", "Conversation", "ConversationFolder", "ExportFormat",
    "ContextEngine", "ContextBundle",
    "StreamingEngine", "StreamChunk", "StreamEvent", "StreamState",
    "MessagePipeline", "PipelineStage", "MessageContext",
    "PromptBuilder", "PromptSection",
    "AgentRuntime", "AgentRole", "AgentTask", "AgentResult",
    "ExecutionQueue", "JobStatus", "JobPriority", "Job",
    "ResponseRenderer", "RenderBlock", "BlockType",
    "CodeExecutor", "CodeLanguage", "ExecutionResult", "SandboxMode",
    "FileSystemEngine", "FileInfo", "FileChange",
    "WorkspaceManager", "Workspace", "Project",
    "MemoryRuntime", "MemoryEntry", "MemoryType",
    "ReasoningEngine", "ReasoningMode", "ReasoningResult",
    "ToolCallingInterface", "ToolCall", "ToolResult",
    "SessionRecovery", "RecoveryPoint",
    "NotificationBus", "Notification", "NotificationLevel",
    "Diagnostics", "MetricSnapshot",
    "RuntimePerformanceOptimizer",
    # New Master 45 modules
    "HealthMonitor", "CircuitBreaker", "HealthState", "CircuitState",
    "DataClass", "ProviderKind",
    "Provenance", "Pricing", "ModelRecord", "ProviderRecord",
    "EmbeddingModel", "RerankerModel", "VisionModel", "AudioModel",
    "PrivacyDecision", "PrivacyRouter", "classify_text", "redact_for_cloud",
    "IntelligentModelRouter", "TaskRequirements", "ModelDecisionTrace",
    "QualityMemory", "PROFILES", "MODES",
    "ModelCache", "WarmPool", "ContextBudgetManager", "UsageRecord",
    "parse_usage", "ToolCall", "normalize_tool_call", "validate_tool_arguments",
    "validate_structured", "FallbackPlan", "build_fallback", "run_with_fallback",
    "ComputeNode", "ComputeMesh", "ModelDownloadManager",
]