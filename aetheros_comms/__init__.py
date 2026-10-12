"""AetherOS Communication OS — unified coordination layer over existing adapters.

Provides the missing abstractions (message model, channel types, send gate,
recipient verification, sensitive-data detection, draft pipeline, phishing
defense, notification center) while delegating actual I/O to the proven
gateway adapters and API providers. No existing module is rewritten.
"""

from aetheros_comms.model import (
    Channel, Sensitivity, Priority, SendStatus,
    CommunicationAttachment, Identity, ContactPoint,
    CommAccount, Recipient, CommunicationMessage,
    ProviderCapability, ProviderInfo,
    KNOWN_PROVIDERS, get_provider_info, register_provider,
)
from aetheros_comms.gate import (
    verify_recipients, scan_sensitive_data, check_message_sensitivity,
    GateVerdict, evaluate_send_gate, compute_idempotency_key,
)
from aetheros_comms.security import (
    MessageThreatAssessment, assess_message_threat,
    scan_for_injection, InboundVerdict, evaluate_inbound,
)
from aetheros_comms.draft import (
    DraftStage, DraftRecord, DraftPipeline,
    Notification, NotificationCenter,
    log_comm_action,
)

__all__ = [
    # Model
    "Channel", "Sensitivity", "Priority", "SendStatus",
    "CommunicationAttachment", "Identity", "ContactPoint",
    "CommAccount", "Recipient", "CommunicationMessage",
    "ProviderCapability", "ProviderInfo",
    "KNOWN_PROVIDERS", "get_provider_info", "register_provider",
    # Gate
    "verify_recipients", "scan_sensitive_data", "check_message_sensitivity",
    "GateVerdict", "evaluate_send_gate", "compute_idempotency_key",
    # Security
    "MessageThreatAssessment", "assess_message_threat",
    "scan_for_injection", "InboundVerdict", "evaluate_inbound",
    # Draft / notifications / audit
    "DraftStage", "DraftRecord", "DraftPipeline",
    "Notification", "NotificationCenter", "log_comm_action",
]
