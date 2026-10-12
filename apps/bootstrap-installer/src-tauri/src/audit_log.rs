use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditLogEntry {
    pub id: String,
    pub org_id: String,
    pub user_id: String,
    pub user_name: String,
    pub action: String,
    pub resource_type: String,
    pub resource_id: String,
    pub resource_name: String,
    pub details: serde_json::Value,
    pub ip_address: Option<String>,
    pub user_agent: Option<String>,
    pub success: bool,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditLogSummary {
    pub total_entries: usize,
    pub by_action: std::collections::HashMap<String, usize>,
    pub by_user: std::collections::HashMap<String, usize>,
    pub by_resource: std::collections::HashMap<String, usize>,
    pub recent_entries: Vec<AuditLogEntry>,
    pub time_range_hours: u64,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn audit_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("audit_log.json")
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
    format!("audit_{:x}", nanos)
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

pub fn log_audit_entry(
    org_id: &str,
    user_id: &str,
    user_name: &str,
    action: &str,
    resource_type: &str,
    resource_id: &str,
    resource_name: &str,
    details: serde_json::Value,
    ip_address: Option<&str>,
    user_agent: Option<&str>,
    success: bool,
) -> Result<AuditLogEntry, String> {
    let mut entries = load_json::<AuditLogEntry>(&audit_path(org_id));
    let id = generate_id();
    let entry = AuditLogEntry {
        id: id.clone(),
        org_id: org_id.to_string(),
        user_id: user_id.to_string(),
        user_name: user_name.to_string(),
        action: action.to_string(),
        resource_type: resource_type.to_string(),
        resource_id: resource_id.to_string(),
        resource_name: resource_name.to_string(),
        details,
        ip_address: ip_address.map(|s| s.to_string()),
        user_agent: user_agent.map(|s| s.to_string()),
        success,
        timestamp: iso_now(),
    };
    entries.push(entry.clone());
    if entries.len() > 10000 {
        entries.drain(0..(entries.len() - 10000));
    }
    save_json(&audit_path(org_id), &entries)?;
    Ok(entry)
}

pub fn get_audit_log(org_id: &str) -> Vec<AuditLogEntry> {
    let mut entries: Vec<AuditLogEntry> = load_json(&audit_path(org_id));
    entries.reverse();
    entries
}

pub fn search_audit_log(
    org_id: &str,
    action_filter: Option<&str>,
    user_filter: Option<&str>,
    resource_filter: Option<&str>,
    limit: usize,
) -> Vec<AuditLogEntry> {
    let entries: Vec<AuditLogEntry> = load_json(&audit_path(org_id));
    let filtered = entries
        .into_iter()
        .filter(|e| {
            if let Some(action) = action_filter {
                if !e.action.contains(action) {
                    return false;
                }
            }
            if let Some(user) = user_filter {
                if e.user_id != user && !e.user_name.contains(user) {
                    return false;
                }
            }
            if let Some(resource) = resource_filter {
                if !e.resource_type.contains(resource) && !e.resource_name.contains(resource) {
                    return false;
                }
            }
            true
        })
        .collect::<Vec<_>>();
    let mut result = filtered;
    result.reverse();
    result.truncate(limit);
    result
}

pub fn get_audit_summary(org_id: &str, hours: u64) -> AuditLogSummary {
    use std::time::{SystemTime, UNIX_EPOCH};
    let entries = load_json::<AuditLogEntry>(&audit_path(org_id));
    let cutoff_secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
        - hours * 3600;

    let recent: Vec<AuditLogEntry> = entries
        .clone()
        .into_iter()
        .filter(|e| {
            let secs = parse_iso_secs_fallback(&e.timestamp);
            secs >= cutoff_secs
        })
        .collect();

    let mut by_action = std::collections::HashMap::new();
    let mut by_user = std::collections::HashMap::new();
    let mut by_resource = std::collections::HashMap::new();

    for entry in &recent {
        *by_action.entry(entry.action.clone()).or_insert(0) += 1;
        *by_user.entry(entry.user_name.clone()).or_insert(0) += 1;
        *by_resource.entry(entry.resource_type.clone()).or_insert(0) += 1;
    }

    let mut recent_entries = recent;
    recent_entries.reverse();
    recent_entries.truncate(50);

    AuditLogSummary {
        total_entries: entries.len(),
        by_action,
        by_user,
        by_resource,
        recent_entries,
        time_range_hours: hours,
    }
}

pub fn parse_iso_secs_fallback(iso: &str) -> u64 {
    if iso.len() < 20 {
        return 0;
    }
    let year: u64 = iso[0..4].parse().unwrap_or(0);
    let month: u64 = iso[5..7].parse().unwrap_or(1);
    let day: u64 = iso[8..10].parse().unwrap_or(1);
    let hour: u64 = iso[11..13].parse().unwrap_or(0);
    let min: u64 = iso[14..16].parse().unwrap_or(0);
    let sec: u64 = iso[17..19].parse().unwrap_or(0);

    let days_from_epoch = (year - 1970) * 365 + (year - 1970) / 4 + (month as u64 * 30) + day;
    days_from_epoch * 86400 + hour * 3600 + min * 60 + sec
}

#[tauri::command]
pub async fn audit_log_event(
    org_id: String, user_id: String, user_name: String, action: String,
    resource_type: String, resource_id: String, resource_name: String,
    details: serde_json::Value, ip_address: Option<String>, user_agent: Option<String>, success: bool,
) -> Result<AuditLogEntry, String> {
    log_audit_entry(&org_id, &user_id, &user_name, &action, &resource_type, &resource_id, &resource_name, details, ip_address.as_deref(), user_agent.as_deref(), success)
}

#[tauri::command]
pub async fn audit_log_list(org_id: String) -> Result<Vec<AuditLogEntry>, String> {
    Ok(get_audit_log(&org_id))
}

#[tauri::command]
pub async fn audit_log_search(
    org_id: String, action_filter: Option<String>, user_filter: Option<String>,
    resource_filter: Option<String>, limit: Option<usize>,
) -> Result<Vec<AuditLogEntry>, String> {
    Ok(search_audit_log(&org_id, action_filter.as_deref(), user_filter.as_deref(), resource_filter.as_deref(), limit.unwrap_or(100)))
}

#[tauri::command]
pub async fn audit_log_summary(org_id: String, hours: Option<u64>) -> Result<AuditLogSummary, String> {
    Ok(get_audit_summary(&org_id, hours.unwrap_or(24)))
}
