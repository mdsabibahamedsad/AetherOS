use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateNotification {
    pub id: String,
    pub notification_type: NotificationType,
    pub title: String,
    pub message: String,
    pub severity: NotificationSeverity,
    pub action_required: bool,
    pub timestamp: String,
    pub dismissed: bool,
    pub metadata: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NotificationType {
    NewVersionAvailable,
    DownloadingUpdate,
    DownloadComplete,
    VerifyingUpdate,
    InstallingUpdate,
    UpdateComplete,
    RestartRequired,
    Restarting,
    RollbackAvailable,
    RollbackComplete,
    UpdateFailed,
    SecurityPatchAvailable,
    HealthIssueDetected,
    RepairCompleted,
    ExtensionUpdateAvailable,
    ExtensionUpdated,
    ModelUpdateAvailable,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NotificationSeverity {
    Info,
    Warning,
    Critical,
}

use std::sync::atomic::AtomicU64;

static NEXT_NOTIFICATION_ID: AtomicU64 = AtomicU64::new(1);
static NOTIFICATIONS: std::sync::OnceLock<tokio::sync::Mutex<Vec<UpdateNotification>>> =
    std::sync::OnceLock::new();

fn notifications() -> &'static tokio::sync::Mutex<Vec<UpdateNotification>> {
    NOTIFICATIONS.get_or_init(|| tokio::sync::Mutex::new(Vec::new()))
}

pub async fn create_notification(
    ntype: NotificationType,
    title: &str,
    message: &str,
    severity: NotificationSeverity,
    action_required: bool,
    metadata: Option<serde_json::Value>,
) -> UpdateNotification {
    let id = NEXT_NOTIFICATION_ID
        .fetch_add(1, std::sync::atomic::Ordering::SeqCst)
        .to_string();

    let notification = UpdateNotification {
        id,
        notification_type: ntype,
        title: title.to_string(),
        message: message.to_string(),
        severity,
        action_required,
        timestamp: now_iso(),
        dismissed: false,
        metadata,
    };

    {
        let mut n = notifications().lock().await;
        n.push(notification.clone());
    }

    notification
}

#[tauri::command]
pub async fn send_update_notification(
    notification_type: String,
    title: String,
    message: String,
    severity: String,
) -> Result<UpdateNotification, String> {
    let ntype = match notification_type.as_str() {
        "new_version" => NotificationType::NewVersionAvailable,
        "downloading" => NotificationType::DownloadingUpdate,
        "download_complete" => NotificationType::DownloadComplete,
        "installing" => NotificationType::InstallingUpdate,
        "update_complete" => NotificationType::UpdateComplete,
        "restart_required" => NotificationType::RestartRequired,
        "update_failed" => NotificationType::UpdateFailed,
        "security_patch" => NotificationType::SecurityPatchAvailable,
        "health_issue" => NotificationType::HealthIssueDetected,
        "repair_complete" => NotificationType::RepairCompleted,
        "ext_update" => NotificationType::ExtensionUpdateAvailable,
        _ => NotificationType::NewVersionAvailable,
    };

    let sev = match severity.as_str() {
        "warning" => NotificationSeverity::Warning,
        "critical" => NotificationSeverity::Critical,
        _ => NotificationSeverity::Info,
    };

    Ok(create_notification(ntype, &title, &message, sev, false, None).await)
}

#[tauri::command]
pub async fn get_notifications(
    include_dismissed: Option<bool>,
) -> Result<Vec<UpdateNotification>, String> {
    let n = notifications().lock().await;
    if include_dismissed.unwrap_or(false) {
        Ok(n.clone())
    } else {
        Ok(n.iter().filter(|n| !n.dismissed).cloned().collect())
    }
}

#[tauri::command]
pub async fn dismiss_notification(id: String) -> Result<(), String> {
    let mut n = notifications().lock().await;
    if let Some(notif) = n.iter_mut().find(|n| n.id == id) {
        notif.dismissed = true;
        Ok(())
    } else {
        Err(format!("Notification not found: {id}"))
    }
}

#[tauri::command]
pub async fn clear_all_notifications() -> Result<(), String> {
    let mut n = notifications().lock().await;
    n.clear();
    Ok(())
}

fn now_iso() -> String {
    let d = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let s = d.as_secs();
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", (s / 86400) % 30 + 1, s % 86400 / 3600 + 1, (s % 3600) / 60, s % 60, 0)
}
