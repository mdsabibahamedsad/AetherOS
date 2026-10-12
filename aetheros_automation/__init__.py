from __future__ import annotations

from aetheros_automation.core.engine import AutomationEngine
from aetheros_automation.core.config import AutomationConfigManager
from aetheros_automation.core.scheduler import TaskScheduler
from aetheros_automation.core.task_queue import TaskQueue
from aetheros_automation.lifecycle import AgentLifecycle, LifecycleRegistry, LifecycleState
from aetheros_automation.monitoring import TaskMonitor
from aetheros_automation.models.models import (
    AutomationConfig, Task, TaskStatus, Workflow, TaskStep,
    ExecutionMode, AgentRole, Permission, GraphExecutionMode,
    TaskPriority, RiskLevel, FailureType, ApprovalAction, ApprovalResponse,
)
from aetheros_automation.modes.controller import ModeController
from aetheros_automation.live.display import LiveDisplay

from aetheros_automation.orchestrator import TaskOrchestrator, ExecutionEngine, CheckpointManager
from aetheros_automation.multi_agent import AgentCollaborationManager, AgentMessaging, SubAgentManager
from aetheros_automation.routing import ModelRouter
from aetheros_automation.recovery import RetryHandler, FallbackHandler
from aetheros_automation.validation import ResultValidator
from aetheros_automation.templates import TaskTemplateManager
from aetheros_automation.nlp import NLPAutomationEngine

from aetheros_automation.browser_automation import (
    BrowserFacade, TabManager, BookmarkManager, HistoryManager,
    DownloadManager, WebSearchManager, BrowserWorkflowEngine,
    AIBrowserAssistant, ResearchMode, ComputerUseManager,
    PageAnalyzer, PromptInjectionProtection, BrowserPermissions,
    BrowserPermissionType, WorkflowNodeType, ComputerAction,
)

from aetheros_automation.communications import (
    ProviderManager, ProviderConnection, ConnectionStatus,
    AuthManager, OAuthFlow, OAuthToken,
    UnifiedInbox, UnifiedMessage, InboxFilter,
    ContactManager, UnifiedContact, ContactLink,
    MessageScheduler, ScheduledMessage, ScheduleRecurrence,
    CommsAIAssistant, ReplyStyle, DraftResult,
    MessageAutomationEngine, AutomationTrigger, AutomationAction,
    NotificationManager, NotificationRule, NotificationChannel,
    PrivacyManager, DataRetentionPolicy, ProcessingScope,
)

from aetheros_automation.knowledge import (
    KnowledgeGraphManager, EntityType, RelationType, GraphEntity, GraphRelation, EntityConfidence,
    UnifiedMemoryManager, MemoryType, MemoryEntry, MemoryConfidence, RetentionPolicy,
    CrossSourceSearch, SearchQuery, SearchResult, SearchSource, SearchType,
    ContextEngine, AgentContext, RelevantItem, ContextSource,
    IngestionManager, WatchFolder, IngestionStatus, FileTypeFilter,
    KnowledgeSpaceManager, KnowledgeSpace, SpaceVisibility, SpaceRole,
    PrivacyRuleManager, PrivacyRule, ProcessingLevel, DataCategory,
    DocumentIntelligence, ExtractedEntity, DocumentTopic, DocumentReference,
    ConversationIntelligence, ExtractedTask, ExtractedDecision, ConversationInsight,
    ProjectIntelligence, ProjectKnowledge, ProjectStatus,
    KnowledgeMaintenance, MaintenanceReport, DuplicateGroup,
    KnowledgeEncryption, EncryptionScheme,
    KnowledgeSyncManager, SyncStatus, SyncDirection, ConflictResolution,
    RetentionManager, RetentionSchedule, DataRetentionRule,
    PersonalContextEngine, PersonalContextResult,
)

__all__ = [
    "AutomationEngine",
    "AutomationConfigManager",
    "TaskScheduler",
    "TaskQueue",
    "AgentLifecycle",
    "LifecycleRegistry",
    "LifecycleState",
    "TaskMonitor",
    "ModeController",
    "LiveDisplay",
    "AutomationConfig",
    "Task",
    "TaskStatus",
    "Workflow",
    "TaskStep",
    "ExecutionMode",
    "AgentRole",
    "Permission",
    "GraphExecutionMode",
    "TaskPriority",
    "RiskLevel",
    "FailureType",
    "ApprovalAction",
    "ApprovalResponse",
    "TaskOrchestrator",
    "ExecutionEngine",
    "CheckpointManager",
    "AgentCollaborationManager",
    "AgentMessaging",
    "SubAgentManager",
    "ModelRouter",
    "RetryHandler",
    "FallbackHandler",
    "ResultValidator",
    "TaskTemplateManager",
    "NLPAutomationEngine",
    "BrowserFacade",
    "TabManager",
    "BookmarkManager",
    "HistoryManager",
    "DownloadManager",
    "WebSearchManager",
    "BrowserWorkflowEngine",
    "AIBrowserAssistant",
    "ResearchMode",
    "ComputerUseManager",
    "PageAnalyzer",
    "PromptInjectionProtection",
    "BrowserPermissions",
    "BrowserPermissionType",
    "WorkflowNodeType",
    "ComputerAction",
    "ProviderManager", "ProviderConnection", "ConnectionStatus",
    "AuthManager", "OAuthFlow", "OAuthToken",
    "UnifiedInbox", "UnifiedMessage", "InboxFilter",
    "ContactManager", "UnifiedContact", "ContactLink",
    "MessageScheduler", "ScheduledMessage", "ScheduleRecurrence",
    "CommsAIAssistant", "ReplyStyle", "DraftResult",
    "MessageAutomationEngine", "AutomationTrigger", "AutomationAction",
    "NotificationManager", "NotificationRule", "NotificationChannel",
    "PrivacyManager", "DataRetentionPolicy", "ProcessingScope",
]
