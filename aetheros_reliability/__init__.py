"""AetherOS Reliability and Self-Healing Layer.

A unified, safe, budgeted reliability subsystem that EXTENDS the existing
observability layer (``aetheros_observability``) rather than replacing it:

* ``states``      — recovery state machine (NORMAL → … → RECOVERY_MODE)
* ``events``      — structured recovery-event schema (recoveryId, traceId, …)
* ``heartbeat``   — component heartbeats + stale detection
* ``journal``     — durable recovery journal (SQLite) for safe restart
* ``checkpoint``  — safe checkpointing of mission/agent/task state
* ``watchdog``    — AetherOSWatchdog: crash/hang/heartbeat-timeout detection,
                    restart backoff, crash-loop protection, recovery triggers
* ``mission``     — interrupted-mission classification and recovery
* ``queue``       — durable job recovery + dead-letter queue
* ``ipc``         — IPC health / reconnect + capability revalidation
* ``backup``      — versioned, integrity-checked, atomic, rotated backups
* ``restore``     — RecoveryManager (preview → snapshot → restore → verify)
* ``config_recovery`` — configuration validation + last-known-good recovery
* ``database``    — SQLite integrity verification + corruption detection
* ``shutdown``    — coordinated graceful shutdown with per-stage timeouts
* ``startup``     — startup recovery: unclean shutdown, stale locks, pending ops
* ``modes``       — Safe Mode / Recovery Mode / Degraded Mode
* ``rca``         — root-cause analysis with confidence levels
* ``slas``        — recovery SLA metrics (MTTR, success rates, crash-loop rate)
* ``diagnostics`` — reliability diagnostic bundle (never exports secrets)
* ``service``     — unified ReliabilityService facade

Safety contract (see AGENTS.md + security control plane):
self-healing NEVER changes security policy, grants permissions, bypasses
approvals, restores revoked access, reactivates quarantined agents, deletes
evidence, or deletes user data.  Every automatic recovery is budgeted,
cooldown-bounded and auditable; high-risk recovery requires human approval.
"""

from __future__ import annotations

from aetheros_reliability.states import (
    RecoveryState,
    RecoveryStateMachine,
)
from aetheros_reliability.events import (
    RecoveryEvent,
    RecoveryEventStore,
    get_recovery_event_store,
)
from aetheros_reliability.heartbeat import (
    Heartbeat,
    HeartbeatRegistry,
    get_heartbeat_registry,
)
from aetheros_reliability.journal import (
    JournalStatus,
    RecoveryJournal,
    get_recovery_journal,
)
from aetheros_reliability.checkpoint import (
    CheckpointStore,
    get_checkpoint_store,
)
from aetheros_reliability.watchdog import (
    AetherOSWatchdog,
    ComponentMonitor,
    get_watchdog,
)
from aetheros_reliability.mission import (
    MissionClassification,
    MissionRecovery,
)
from aetheros_reliability.queue import (
    DeadLetterEntry,
    QueueRecovery,
)
from aetheros_reliability.ipc import (
    IPCChannel,
    IPCHealth,
)
from aetheros_reliability.backup import (
    BackupEntry,
    BackupIntegrity,
    BackupStore,
    get_backup_store,
)
from aetheros_reliability.restore import (
    RestorePreview,
    RecoveryManager,
    get_recovery_manager,
)
from aetheros_reliability.config_recovery import (
    ConfigRecovery,
    ConfigValidationResult,
    get_config_recovery,
)
from aetheros_reliability.database import (
    DatabaseHealth,
    DatabaseRecovery,
    get_database_recovery,
)
from aetheros_reliability.shutdown import (
    ShutdownCoordinator,
    get_shutdown_coordinator,
)
from aetheros_reliability.startup import (
    StartupRecoveryReport,
    StartupRecovery,
)
from aetheros_reliability.modes import (
    AetherOSMode,
    ModeController,
    get_mode_controller,
)
from aetheros_reliability.rca import (
    RCAConfidence,
    RootCauseAnalyzer,
    get_root_cause_analyzer,
)
from aetheros_reliability.slas import (
    RecoverySLAMetrics,
    get_recovery_sla_metrics,
)
from aetheros_reliability.diagnostics import (
    ReliabilityDiagnostics,
    get_reliability_diagnostics,
)
from aetheros_reliability.service import (
    ReliabilityService,
    get_reliability_service,
)

__all__ = [
    # states
    "RecoveryState", "RecoveryStateMachine",
    # events
    "RecoveryEvent", "RecoveryEventStore", "get_recovery_event_store",
    # heartbeat
    "Heartbeat", "HeartbeatRegistry", "get_heartbeat_registry",
    # journal
    "JournalStatus", "RecoveryJournal", "get_recovery_journal",
    # checkpoint
    "CheckpointStore", "get_checkpoint_store",
    # watchdog
    "AetherOSWatchdog", "ComponentMonitor", "get_watchdog",
    # mission
    "MissionClassification", "MissionRecovery",
    # queue
    "DeadLetterEntry", "QueueRecovery",
    # ipc
    "IPCChannel", "IPCHealth",
    # backup
    "BackupEntry", "BackupIntegrity", "BackupStore", "get_backup_store",
    # restore
    "RestorePreview", "RecoveryManager", "get_recovery_manager",
    # config
    "ConfigRecovery", "ConfigValidationResult", "get_config_recovery",
    # database
    "DatabaseHealth", "DatabaseRecovery", "get_database_recovery",
    # shutdown
    "ShutdownCoordinator", "get_shutdown_coordinator",
    # startup
    "StartupRecoveryReport", "StartupRecovery",
    # modes
    "AetherOSMode", "ModeController", "get_mode_controller",
    # rca
    "RCAConfidence", "RootCauseAnalyzer", "get_root_cause_analyzer",
    # slas
    "RecoverySLAMetrics", "get_recovery_sla_metrics",
    # diagnostics
    "ReliabilityDiagnostics", "get_reliability_diagnostics",
    # service
    "ReliabilityService", "get_reliability_service",
]