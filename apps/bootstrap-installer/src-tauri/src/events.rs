//! Event types streamed from Rust → React.
//!
//! Phase 5 adds two new stage names consumed by the offline-installer path:
//! `resolve_packages` and `install_packages`.  These replace the old
//! fetch → download → verify → extract → install chain when the
//! package-manager path is active (online or offline bundle).
//!
//! Phase 6 adds setup-wizard stage names consumed by the first-run setup
//! wizard path: `setup_wizard` is emitted when the wizard starts after
//! bootstrap completes on a fresh install.
//!
//! These mirror `apps/desktop/electron/bootstrap-runner.cjs`'s event shape
//! 1:1 so the React installer code can be roughly identical to the Electron
//! install-overlay we'll replace.
//!
//! The Tauri event channel name is `"bootstrap"` for all of these — the
//! `type` discriminator on each payload is how the frontend routes.

use serde::{Deserialize, Serialize};

/// Stage definition as reported by `install.ps1 -Manifest`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StageInfo {
    pub name: String,
    pub title: String,
    pub category: String,
    /// `needs_user_input=true` stages run with -NonInteractive and emit
    /// skipped=true; the post-install wizard takes over for those.
    #[serde(rename = "needs_user_input", alias = "needsUserInput")]
    pub needs_user_input: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    pub stages: Vec<StageInfo>,
    #[serde(rename = "protocol_version", alias = "protocolVersion", default)]
    pub protocol_version: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StageResultPayload {
    pub stage: String,
    pub ok: bool,
    #[serde(default)]
    pub skipped: bool,
    #[serde(default)]
    pub reason: Option<String>,
    /// install.ps1 may attach stage-specific structured data here.
    #[serde(default)]
    pub data: Option<serde_json::Value>,
}

/// Run-state for a single stage as we transition through it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum StageState {
    Running,
    Succeeded,
    Skipped,
    Failed,
}

/// Which pipe a raw log line came from. Reported as structured metadata so
/// the UI can style stderr subtly rather than mislabeling it as an error:
/// Package managers and build tools write progress to stderr by design.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum LogStream {
    Stdout,
    Stderr,
}

/// The single event channel `bootstrap` emits these. `type` discriminates.
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum BootstrapEvent {
    /// Sent once at the start with the full stage list.
    Manifest {
        stages: Vec<StageInfo>,
        #[serde(rename = "protocolVersion")]
        protocol_version: Option<u32>,
    },
    /// Stage state transition. `result` populated only on terminal states.
    Stage {
        name: String,
        state: StageState,
        #[serde(rename = "durationMs", skip_serializing_if = "Option::is_none")]
        duration_ms: Option<u64>,
        #[serde(skip_serializing_if = "Option::is_none")]
        result: Option<StageResultPayload>,
        #[serde(skip_serializing_if = "Option::is_none")]
        error: Option<String>,
    },
    /// Raw stdout/stderr line from install.ps1 (or our wrapper). `stream`
    /// tells the UI which pipe it came from so stderr can be styled subtly
    /// instead of being mislabeled as an error.
    Log {
        #[serde(skip_serializing_if = "Option::is_none")]
        stage: Option<String>,
        line: String,
        stream: LogStream,
    },
    /// Sent once when all stages complete successfully.
    Complete {
        #[serde(rename = "installRoot")]
        install_root: String,
        marker: Option<serde_json::Value>,
    },
    /// Sent once if the run aborts.
    Failed {
        #[serde(skip_serializing_if = "Option::is_none")]
        stage: Option<String>,
        error: String,
    },
}

// ---------------------------------------------------------------------------
// Phase 7 — Model lifecycle events
// ---------------------------------------------------------------------------

/// Events specific to the model download pipeline. Sent on the
/// `"model-download"` Tauri event channel.
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum ModelEvent {
    /// A model download made progress (or completed).
    DownloadProgress {
        id: String,
        model_id: String,
        downloaded: u64,
        total: Option<u64>,
        speed: f64,
        status: String,
        progress_pct: f64,
    },
    /// A health check completed for a model.
    HealthResult {
        model_id: String,
        status: String,
        issues: Vec<String>,
    },
    /// The full health report finished.
    HealthReportComplete {
        total_models: usize,
        healthy: usize,
        corrupted: usize,
        missing: usize,
    },
    /// A model was installed or removed from the registry.
    RegistryChanged {
        action: String,
        model_id: String,
        model_name: String,
    },
    /// Local AI engines were detected.
    EnginesDetected {
        engine_count: usize,
        total_models: usize,
    },
}

impl ModelEvent {
    pub const DOWNLOAD_CHANNEL: &'static str = "model-download";
    pub const HEALTH_CHANNEL: &'static str = "model-health";
    pub const REGISTRY_CHANNEL: &'static str = "model-registry";
    pub const ENGINE_CHANNEL: &'static str = "model-engines";
}

// ---------------------------------------------------------------------------
// Phase 8 — Update lifecycle events
// ---------------------------------------------------------------------------

/// Events specific to the auto-update system. Sent on `"update-lifecycle"`.
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum UpdateLifecycleEvent {
    /// A new version was detected.
    UpdateAvailable {
        current_version: String,
        new_version: String,
        is_security: bool,
        is_hotfix: bool,
    },
    /// Update download progress.
    DownloadProgress {
        version: String,
        downloaded: u64,
        total: Option<u64>,
        speed: f64,
        progress_pct: f64,
    },
    /// Download completed.
    DownloadComplete {
        version: String,
        size: u64,
        checksum_verified: bool,
    },
    /// Install phase of update.
    InstallProgress {
        version: String,
        stage: String,
        progress_pct: f64,
        message: String,
    },
    /// Update completed successfully.
    UpdateComplete {
        version: String,
        installed_at: String,
    },
    /// Update failed.
    UpdateFailed {
        version: String,
        error: String,
        can_rollback: bool,
    },
    /// Rollback completed.
    RollbackComplete {
        version: String,
        entries_restored: usize,
    },
    /// Self-healing check completed.
    HealthCheckComplete {
        healthy: usize,
        issues: usize,
        repairable: usize,
    },
    /// Extension update available.
    ExtensionUpdateAvailable {
        name: String,
        current_version: String,
        new_version: String,
    },
}

impl UpdateLifecycleEvent {
    pub const CHANNEL: &'static str = "update-lifecycle";
}

impl BootstrapEvent {
    /// Tauri event name. Single channel for all bootstrap events; the
    /// `type` tag tells the renderer how to interpret the payload.
    pub const CHANNEL: &'static str = "bootstrap";
}

// ---------------------------------------------------------------------------
// Phase 10 — Marketplace lifecycle events
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum MarketplaceEvent {
    /// A marketplace package install started.
    InstallStarted {
        package_id: String,
        name: String,
        version: String,
    },
    /// Install progress.
    InstallProgress {
        package_id: String,
        name: String,
        progress_pct: f64,
        message: String,
    },
    /// Install completed.
    InstallComplete {
        package_id: String,
        name: String,
        version: String,
        success: bool,
    },
    /// Uninstall completed.
    UninstallComplete {
        package_id: String,
        name: String,
        success: bool,
    },
    /// Update available for an installed package.
    UpdateAvailable {
        package_id: String,
        name: String,
        current_version: String,
        new_version: String,
    },
    /// Update progress.
    UpdateProgress {
        package_id: String,
        name: String,
        progress_pct: f64,
        message: String,
    },
    /// Update completed.
    UpdateComplete {
        package_id: String,
        name: String,
        old_version: String,
        new_version: String,
        success: bool,
    },
    /// Package enabled/disabled.
    Toggle {
        package_id: String,
        name: String,
        enabled: bool,
    },
    /// Permission change.
    PermissionChanged {
        package_id: String,
        permission: String,
        granted: bool,
    },
    /// Download recorded.
    DownloadRecorded {
        package_id: String,
        total_downloads: u64,
    },
    /// Review submitted.
    ReviewSubmitted {
        package_id: String,
        rating: u8,
    },
    /// Offline bundle export/import.
    OfflineBundleExported {
        path: String,
        package_count: usize,
    },
    OfflineBundleImported {
        path: String,
        package_count: usize,
    },
    /// Package published by developer.
    PackagePublished {
        package_id: String,
        name: String,
        version: String,
    },
}

impl MarketplaceEvent {
    pub const CHANNEL: &'static str = "marketplace";
}

// ---------------------------------------------------------------------------
// Phase 11 — Team Collaboration & Enterprise events
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum TeamEvent {
    OrganizationCreated { org_id: String, name: String },
    OrganizationUpdated { org_id: String, name: String },
    OrganizationDeleted { org_id: String },
    MemberJoined { org_id: String, user_id: String, user_name: String },
    MemberRemoved { org_id: String, user_id: String },
    MemberSuspended { org_id: String, user_id: String },
    MemberReactivated { org_id: String, user_id: String },
    RoleChanged { org_id: String, user_id: String, old_role: String, new_role: String },
    OwnershipTransferred { org_id: String, new_owner_id: String },
    TeamCreated { org_id: String, team_id: String, name: String },
    TeamDeleted { org_id: String, team_id: String },
    ProjectCreated { org_id: String, project_id: String, name: String },
    ProjectArchived { org_id: String, project_id: String },
    TaskCreated { org_id: String, task_id: String, title: String },
    TaskUpdated { org_id: String, task_id: String, status: String },
    TaskAssigned { org_id: String, task_id: String, assignee_id: String },
    InvitationSent { org_id: String, invitation_id: String, email: Option<String> },
    InvitationAccepted { org_id: String, invitation_id: String },
    InvitationRevoked { org_id: String, invitation_id: String },
    KnowledgeShared { org_id: String, knowledge_id: String, title: String },
    SessionStarted { org_id: String, session_id: String, session_type: String },
    PresenceChanged { org_id: String, user_id: String, status: String },
    NotificationSent { org_id: String, notification_id: String, recipient_id: String, ntype: String },
    AuditEvent { org_id: String, entry_id: String, action: String, user_id: String },
    PolicyCreated { org_id: String, policy_id: String, name: String },
    PolicyToggled { org_id: String, policy_id: String, enabled: bool },
    SecuritySettingChanged { org_id: String, setting: String },
    DeviceRegistered { org_id: String, device_id: String, device_name: String },
    DeviceRemoved { org_id: String, device_id: String },
}

impl TeamEvent {
    pub const CHANNEL: &'static str = "team";
}

// ---------------------------------------------------------------------------
// Phase 12 — Universal Communication Hub events
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum HubEvent {
    ConnectorInstalled { instance_id: String, definition_id: String, name: String },
    ConnectorRemoved { instance_id: String, name: String },
    ConnectorEnabled { instance_id: String, name: String },
    ConnectorDisabled { instance_id: String, name: String },
    ConnectorReconnected { instance_id: String, name: String },
    ConnectorDisconnected { instance_id: String, name: String, error: Option<String> },
    ConnectorError { instance_id: String, name: String, error: String },
    ConnectorHealthChanged { instance_id: String, name: String, status: String, latency_ms: u64 },
    WorkflowCreated { workflow_id: String, name: String },
    WorkflowExecuted { workflow_id: String, name: String, success: bool, duration_ms: u64 },
    WorkflowFailed { workflow_id: String, name: String, error: String },
    MessageRouted { route_id: String, from_connector: String, to_connector: String },
    InboxMessage { message_id: String, connector_id: String, sender: String, preview: String },
    InboxUpdated { message_id: String, action: String },
    AiSummary { message_id: String, summary: String },
    AutomationTriggered { workflow_id: String, trigger_source: String },
    ScheduleTriggered { workflow_id: String, schedule: String },
    WebhookReceived { path: String, method: String },
}

impl HubEvent {
    pub const CHANNEL: &'static str = "hub";
}
