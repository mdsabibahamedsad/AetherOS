use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Notification {
    pub id: String,
    pub org_id: String,
    pub recipient_id: String,
    pub notification_type: NotificationType,
    pub title: String,
    pub body: String,
    pub resource_id: Option<String>,
    pub sender_id: Option<String>,
    pub is_read: bool,
    pub created_at: String,
    pub read_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NotificationType {
    Invitation,
    Mention,
    Assignment,
    TaskUpdate,
    ProjectUpdate,
    UpdateAvailable,
    MarketplaceChange,
    AutomationEvent,
    AiResponse,
    SecurityAlert,
    MemberJoined,
    RoleChanged,
    PolicyViolation,
    System,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn notifications_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("notifications.json")
}

fn load_json<T: serde::de::DeserializeOwned>(path: &PathBuf) -> Vec<T> {
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

fn save_json<T: serde::Serialize>(path: &PathBuf, data: &[T]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(data).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("notif_{:x}", nanos)
}

fn iso_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let d = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = d.as_secs();
    let millis = d.subsec_millis();
    let days = secs / 86400;
    let time_secs = secs % 86400;
    let hours = time_secs / 3600;
    let minutes = (time_secs % 3600) / 60;
    let seconds = time_secs % 60;
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:03}Z",
        1970 + (days as f64 / 365.25) as u64,
        1 + ((days % 365) / 30),
        1 + (days % 30),
        hours,
        minutes,
        seconds,
        millis
    )
}

pub fn send_notification(
    org_id: &str,
    recipient_id: &str,
    ntype: NotificationType,
    title: &str,
    body: &str,
    resource_id: Option<&str>,
    sender_id: Option<&str>,
) -> Result<Notification, String> {
    let mut notifs = load_json::<Notification>(&notifications_path(org_id));
    let id = generate_id();
    let now = iso_now();
    let notif = Notification {
        id: id.clone(),
        org_id: org_id.to_string(),
        recipient_id: recipient_id.to_string(),
        notification_type: ntype,
        title: title.to_string(),
        body: body.to_string(),
        resource_id: resource_id.map(|s| s.to_string()),
        sender_id: sender_id.map(|s| s.to_string()),
        is_read: false,
        created_at: now,
        read_at: None,
    };
    notifs.push(notif.clone());
    if notifs.len() > 500 {
        notifs.drain(0..(notifs.len() - 500));
    }
    save_json(&notifications_path(org_id), &notifs)?;
    Ok(notif)
}

pub fn get_notifications(org_id: &str, user_id: &str) -> Vec<Notification> {
    let all: Vec<Notification> = load_json(&notifications_path(org_id));
    let mut notifs: Vec<Notification> = all
        .into_iter()
        .filter(|n| n.recipient_id == user_id)
        .collect();
    notifs.reverse();
    notifs
}

pub fn get_unread_count(org_id: &str, user_id: &str) -> u32 {
    load_json::<Notification>(&notifications_path(org_id))
        .into_iter()
        .filter(|n| n.recipient_id == user_id && !n.is_read)
        .count() as u32
}

pub fn mark_as_read(org_id: &str, notification_id: &str) -> Result<(), String> {
    let mut notifs = load_json::<Notification>(&notifications_path(org_id));
    let notif = notifs.iter_mut().find(|n| n.id == notification_id)
        .ok_or_else(|| format!("Notification not found: {notification_id}"))?;
    notif.is_read = true;
    notif.read_at = Some(iso_now());
    save_json(&notifications_path(org_id), &notifs)
}

pub fn mark_all_as_read(org_id: &str, user_id: &str) -> Result<(), String> {
    let mut notifs = load_json::<Notification>(&notifications_path(org_id));
    let now = iso_now();
    for notif in notifs.iter_mut() {
        if notif.recipient_id == user_id {
            notif.is_read = true;
            notif.read_at = Some(now.clone());
        }
    }
    save_json(&notifications_path(org_id), &notifs)
}

pub fn delete_notification(org_id: &str, notification_id: &str) -> Result<(), String> {
    let mut notifs = load_json::<Notification>(&notifications_path(org_id));
    let pos = notifs.iter().position(|n| n.id == notification_id)
        .ok_or_else(|| format!("Notification not found: {notification_id}"))?;
    notifs.remove(pos);
    save_json(&notifications_path(org_id), &notifs)
}

#[tauri::command]
pub async fn notif_send(
    org_id: String, recipient_id: String, notification_type: String,
    title: String, body: String, resource_id: Option<String>, sender_id: Option<String>,
) -> Result<Notification, String> {
    let ntype = match notification_type.as_str() {
        "invitation" => NotificationType::Invitation,
        "mention" => NotificationType::Mention,
        "assignment" => NotificationType::Assignment,
        "task_update" => NotificationType::TaskUpdate,
        "project_update" => NotificationType::ProjectUpdate,
        "update_available" => NotificationType::UpdateAvailable,
        "marketplace_change" => NotificationType::MarketplaceChange,
        "automation_event" => NotificationType::AutomationEvent,
        "ai_response" => NotificationType::AiResponse,
        "security_alert" => NotificationType::SecurityAlert,
        "member_joined" => NotificationType::MemberJoined,
        "role_changed" => NotificationType::RoleChanged,
        "policy_violation" => NotificationType::PolicyViolation,
        _ => NotificationType::System,
    };
    send_notification(&org_id, &recipient_id, ntype, &title, &body, resource_id.as_deref(), sender_id.as_deref())
}

#[tauri::command]
pub async fn notif_list(org_id: String, user_id: String) -> Result<Vec<Notification>, String> {
    Ok(get_notifications(&org_id, &user_id))
}

#[tauri::command]
pub async fn notif_unread_count(org_id: String, user_id: String) -> Result<u32, String> {
    Ok(get_unread_count(&org_id, &user_id))
}

#[tauri::command]
pub async fn notif_mark_read(org_id: String, notification_id: String) -> Result<(), String> {
    mark_as_read(&org_id, &notification_id)
}

#[tauri::command]
pub async fn notif_mark_all_read(org_id: String, user_id: String) -> Result<(), String> {
    mark_all_as_read(&org_id, &user_id)
}

#[tauri::command]
pub async fn notif_delete(org_id: String, notification_id: String) -> Result<(), String> {
    delete_notification(&org_id, &notification_id)
}
