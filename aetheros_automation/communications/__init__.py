from aetheros_automation.communications.provider_manager import (
    ProviderManager, ProviderConnection, ConnectionStatus, ProviderType, AuthMethod, ProviderCapabilities,
)
from aetheros_automation.communications.auth_manager import AuthManager, OAuthFlow, OAuthToken, TokenStatus, AuthConfig
from aetheros_automation.communications.unified_inbox import UnifiedInbox, UnifiedMessage, InboxFilter, MessageType, MessagePriority, Conversation
from aetheros_automation.communications.contact_manager import ContactManager, UnifiedContact, ContactLink
from aetheros_automation.communications.scheduler import MessageScheduler, ScheduledMessage, ScheduleRecurrence, ScheduledMessageStatus
from aetheros_automation.communications.ai_assistant import CommsAIAssistant, ReplyStyle, DraftResult, AssistantContext, ConversationSummary
from aetheros_automation.communications.automation_engine import MessageAutomationEngine, AutomationTrigger, AutomationAction, AutomationRule, AutomationExecution
from aetheros_automation.communications.notification_manager import NotificationManager, NotificationRule, NotificationChannel, Notification, NotificationCategory, NotificationPriority
from aetheros_automation.communications.privacy_manager import PrivacyManager, DataRetentionPolicy, ProcessingScope, PrivacySettings

__all__ = [
    "ProviderManager", "ProviderConnection", "ConnectionStatus", "ProviderType", "AuthMethod", "ProviderCapabilities",
    "AuthManager", "OAuthFlow", "OAuthToken", "TokenStatus", "AuthConfig",
    "UnifiedInbox", "UnifiedMessage", "InboxFilter", "MessageType", "MessagePriority", "Conversation",
    "ContactManager", "UnifiedContact", "ContactLink",
    "MessageScheduler", "ScheduledMessage", "ScheduleRecurrence", "ScheduledMessageStatus",
    "CommsAIAssistant", "ReplyStyle", "DraftResult", "AssistantContext", "ConversationSummary",
    "MessageAutomationEngine", "AutomationTrigger", "AutomationAction", "AutomationRule", "AutomationExecution",
    "NotificationManager", "NotificationRule", "NotificationChannel", "Notification", "NotificationCategory", "NotificationPriority",
    "PrivacyManager", "DataRetentionPolicy", "ProcessingScope", "PrivacySettings",
]
