use serde::{Deserialize, Serialize};

use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnterprisePolicy {
    pub id: String,
    pub org_id: String,
    pub policy_type: PolicyType,
    pub name: String,
    pub description: String,
    pub enabled: bool,
    pub config: serde_json::Value,
    pub created_at: String,
    pub updated_at: String,
    pub created_by: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PolicyType {
    ApprovedAiProviders,
    ApprovedModels,
    ApprovedExtensions,
    ApprovedMcpServers,
    StorageLimit,
    DownloadLimit,
    SecurityPolicy,
    PasswordPolicy,
    UpdatePolicy,
    SessionPolicy,
    DataRetention,
    NetworkAccess,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecuritySettings {
    pub two_factor_required: bool,
    pub two_factor_methods: Vec<String>,
    pub session_timeout_minutes: u32,
    pub max_concurrent_sessions: u32,
    pub max_login_attempts: u32,
    pub login_lockout_minutes: u32,
    pub password_min_length: u32,
    pub password_require_special: bool,
    pub password_require_numbers: bool,
    pub password_require_uppercase: bool,
    pub password_expiry_days: u32,
    pub ip_whitelist_enabled: bool,
    pub ip_whitelist: Vec<String>,
    pub mfa_enforcement: MfaEnforcement,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MfaEnforcement {
    Disabled,
    Optional,
    RequiredForAdmin,
    RequiredForAll,
}

impl Default for SecuritySettings {
    fn default() -> Self {
        Self {
            two_factor_required: false,
            two_factor_methods: vec!["totp".into(), "email".into()],
            session_timeout_minutes: 480,
            max_concurrent_sessions: 5,
            max_login_attempts: 5,
            login_lockout_minutes: 30,
            password_min_length: 8,
            password_require_special: true,
            password_require_numbers: true,
            password_require_uppercase: true,
            password_expiry_days: 90,
            ip_whitelist_enabled: false,
            ip_whitelist: Vec::new(),
            mfa_enforcement: MfaEnforcement::Optional,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceInfo {
    pub device_id: String,
    pub user_id: String,
    pub device_name: String,
    pub device_type: String,
    pub os: String,
    pub browser: Option<String>,
    pub trusted: bool,
    pub last_ip: String,
    pub last_active_at: String,
    pub created_at: String,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn policies_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("policies.json")
}

fn security_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("security.json")
}

fn devices_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("devices.json")
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
    format!("pol_{:x}", nanos)
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

pub fn create_policy(
    org_id: &str,
    policy_type: PolicyType,
    name: &str,
    description: &str,
    config: serde_json::Value,
    created_by: &str,
) -> Result<EnterprisePolicy, String> {
    let mut policies = load_json::<EnterprisePolicy>(&policies_path(org_id));
    let id = generate_id();
    let now = iso_now();
    let policy = EnterprisePolicy {
        id: id.clone(),
        org_id: org_id.to_string(),
        policy_type,
        name: name.to_string(),
        description: description.to_string(),
        enabled: true,
        config,
        created_at: now.clone(),
        updated_at: now,
        created_by: created_by.to_string(),
    };
    policies.push(policy.clone());
    save_json(&policies_path(org_id), &policies)?;
    Ok(policy)
}

pub fn list_policies(org_id: &str) -> Vec<EnterprisePolicy> {
    load_json(&policies_path(org_id))
}

pub fn toggle_policy(org_id: &str, policy_id: &str, enabled: bool) -> Result<EnterprisePolicy, String> {
    let mut policies = load_json::<EnterprisePolicy>(&policies_path(org_id));
    let policy = policies.iter_mut().find(|p| p.id == policy_id)
        .ok_or_else(|| format!("Policy not found: {policy_id}"))?;
    policy.enabled = enabled;
    policy.updated_at = iso_now();
    let result = policy.clone();
    save_json(&policies_path(org_id), &policies)?;
    Ok(result)
}

pub fn delete_policy(org_id: &str, policy_id: &str) -> Result<(), String> {
    let mut policies = load_json::<EnterprisePolicy>(&policies_path(org_id));
    let pos = policies.iter().position(|p| p.id == policy_id)
        .ok_or_else(|| format!("Policy not found: {policy_id}"))?;
    policies.remove(pos);
    save_json(&policies_path(org_id), &policies)
}

pub fn check_policy_allows(org_id: &str, resource: &str, value: &str) -> bool {
    let policies = load_json::<EnterprisePolicy>(&policies_path(org_id));
    for policy in &policies {
        if !policy.enabled {
            continue;
        }
        let allowed = match policy.policy_type {
            PolicyType::ApprovedAiProviders => {
                if resource == "ai_provider" {
                    policy.config["providers"]
                        .as_array()
                        .map(|arr| arr.iter().any(|v| v.as_str() == Some(value)))
                        .unwrap_or(true)
                } else {
                    true
                }
            }
            PolicyType::ApprovedModels => {
                if resource == "model" {
                    policy.config["models"]
                        .as_array()
                        .map(|arr| arr.iter().any(|v| v.as_str() == Some(value)))
                        .unwrap_or(true)
                } else {
                    true
                }
            }
            PolicyType::ApprovedExtensions => {
                if resource == "extension" {
                    policy.config["extensions"]
                        .as_array()
                        .map(|arr| arr.iter().any(|v| v.as_str() == Some(value)))
                        .unwrap_or(true)
                } else {
                    true
                }
            }
            PolicyType::ApprovedMcpServers => {
                if resource == "mcp_server" {
                    policy.config["servers"]
                        .as_array()
                        .map(|arr| arr.iter().any(|v| v.as_str() == Some(value)))
                        .unwrap_or(true)
                } else {
                    true
                }
            }
            _ => true,
        };
        if !allowed {
            return false;
        }
    }
    true
}

pub fn load_security_settings(org_id: &str) -> SecuritySettings {
    let path = security_path(org_id);
    if !path.exists() {
        return SecuritySettings::default();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

pub fn save_security_settings(org_id: &str, settings: &SecuritySettings) -> Result<(), String> {
    let path = security_path(org_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(settings).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn register_device(
    org_id: &str,
    user_id: &str,
    device_name: &str,
    device_type: &str,
    os: &str,
    browser: Option<&str>,
    ip: &str,
) -> Result<DeviceInfo, String> {
    let mut devices = load_json::<DeviceInfo>(&devices_path(org_id));
    let now = iso_now();
    if let Some(dev) = devices.iter_mut().find(|d| d.device_id == format!("{user_id}_{device_name}")) {
        dev.last_active_at = now.clone();
        dev.last_ip = ip.to_string();
        return Ok(dev.clone());
    }
    let device = DeviceInfo {
        device_id: format!("{user_id}_{device_name}"),
        user_id: user_id.to_string(),
        device_name: device_name.to_string(),
        device_type: device_type.to_string(),
        os: os.to_string(),
        browser: browser.map(|s| s.to_string()),
        trusted: false,
        last_ip: ip.to_string(),
        last_active_at: now.clone(),
        created_at: now,
    };
    devices.push(device.clone());
    save_json(&devices_path(org_id), &devices)?;
    Ok(device)
}

pub fn list_devices(org_id: &str, user_id: &str) -> Vec<DeviceInfo> {
    load_json::<DeviceInfo>(&devices_path(org_id))
        .into_iter()
        .filter(|d| d.user_id == user_id)
        .collect()
}

pub fn trust_device(org_id: &str, device_id: &str) -> Result<(), String> {
    let mut devices = load_json::<DeviceInfo>(&devices_path(org_id));
    let device = devices.iter_mut().find(|d| d.device_id == device_id)
        .ok_or_else(|| format!("Device not found: {device_id}"))?;
    device.trusted = true;
    save_json(&devices_path(org_id), &devices)
}

pub fn remove_device(org_id: &str, device_id: &str) -> Result<(), String> {
    let mut devices = load_json::<DeviceInfo>(&devices_path(org_id));
    let pos = devices.iter().position(|d| d.device_id == device_id)
        .ok_or_else(|| format!("Device not found: {device_id}"))?;
    devices.remove(pos);
    save_json(&devices_path(org_id), &devices)
}

#[tauri::command]
pub async fn policy_create(
    org_id: String, policy_type: String, name: String, description: String,
    config: serde_json::Value, created_by: String,
) -> Result<EnterprisePolicy, String> {
    let ptype = match policy_type.as_str() {
        "approved_ai_providers" => PolicyType::ApprovedAiProviders,
        "approved_models" => PolicyType::ApprovedModels,
        "approved_extensions" => PolicyType::ApprovedExtensions,
        "approved_mcp_servers" => PolicyType::ApprovedMcpServers,
        "storage_limit" => PolicyType::StorageLimit,
        "download_limit" => PolicyType::DownloadLimit,
        "security_policy" => PolicyType::SecurityPolicy,
        "password_policy" => PolicyType::PasswordPolicy,
        "update_policy" => PolicyType::UpdatePolicy,
        "session_policy" => PolicyType::SessionPolicy,
        "data_retention" => PolicyType::DataRetention,
        "network_access" => PolicyType::NetworkAccess,
        _ => return Err("Invalid policy type".to_string()),
    };
    create_policy(&org_id, ptype, &name, &description, config, &created_by)
}

#[tauri::command]
pub async fn policy_list(org_id: String) -> Result<Vec<EnterprisePolicy>, String> {
    Ok(list_policies(&org_id))
}

#[tauri::command]
pub async fn policy_toggle(org_id: String, policy_id: String, enabled: bool) -> Result<EnterprisePolicy, String> {
    toggle_policy(&org_id, &policy_id, enabled)
}

#[tauri::command]
pub async fn policy_delete(org_id: String, policy_id: String) -> Result<(), String> {
    delete_policy(&org_id, &policy_id)
}

#[tauri::command]
pub async fn policy_check_allows(org_id: String, resource: String, value: String) -> Result<bool, String> {
    Ok(check_policy_allows(&org_id, &resource, &value))
}

#[tauri::command]
pub async fn security_get_settings(org_id: String) -> Result<SecuritySettings, String> {
    Ok(load_security_settings(&org_id))
}

#[tauri::command]
pub async fn security_save_settings(org_id: String, settings: SecuritySettings) -> Result<(), String> {
    save_security_settings(&org_id, &settings)
}

#[tauri::command]
pub async fn device_register(
    org_id: String, user_id: String, device_name: String, device_type: String,
    os: String, browser: Option<String>, ip: String,
) -> Result<DeviceInfo, String> {
    register_device(&org_id, &user_id, &device_name, &device_type, &os, browser.as_deref(), &ip)
}

#[tauri::command]
pub async fn device_list(org_id: String, user_id: String) -> Result<Vec<DeviceInfo>, String> {
    Ok(list_devices(&org_id, &user_id))
}

#[tauri::command]
pub async fn device_trust(org_id: String, device_id: String) -> Result<(), String> {
    trust_device(&org_id, &device_id)
}

#[tauri::command]
pub async fn device_remove(org_id: String, device_id: String) -> Result<(), String> {
    remove_device(&org_id, &device_id)
}
