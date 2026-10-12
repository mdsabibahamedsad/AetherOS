use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Mutex;
use std::sync::OnceLock;

fn custom_definitions() -> &'static Mutex<Vec<ConnectorDefinition>> {
    static INSTANCE: OnceLock<Mutex<Vec<ConnectorDefinition>>> = OnceLock::new();
    INSTANCE.get_or_init(|| {
        let defs = load_custom_definitions_from_disk();
        Mutex::new(defs)
    })
}

fn custom_definitions_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("custom-connector-definitions.json")
}

fn load_custom_definitions_from_disk() -> Vec<ConnectorDefinition> {
    let path = custom_definitions_path();
    if !path.exists() { return Vec::new(); }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

fn save_custom_definitions(defs: &[ConnectorDefinition]) -> Result<(), String> {
    let path = custom_definitions_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(defs).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn register_custom_definition(definition: ConnectorDefinition) -> Result<(), String> {
    let mut defs = custom_definitions().lock().unwrap();
    if defs.iter().any(|d| d.id == definition.id) {
        return Err(format!("Definition '{}' already registered", definition.id));
    }
    defs.push(definition.clone());
    save_custom_definitions(&defs)
}

pub fn unregister_custom_definition(definition_id: &str) -> Result<(), String> {
    let mut defs = custom_definitions().lock().unwrap();
    let pos = defs.iter().position(|d| d.id == definition_id)
        .ok_or_else(|| format!("Definition not found: {definition_id}"))?;
    defs.remove(pos);
    save_custom_definitions(&defs)
}

pub fn all_definitions_including_custom() -> Vec<ConnectorDefinition> {
    let mut defs = crate::connector_definitions::all_definitions();
    let custom = custom_definitions().lock().unwrap();
    defs.extend(custom.clone());
    defs
}

pub fn get_definition_including_custom(id: &str) -> Option<ConnectorDefinition> {
    crate::connector_definitions::get_definition(id)
        .or_else(|| {
            let custom = custom_definitions().lock().unwrap();
            custom.iter().find(|d| d.id == id).cloned()
        })
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectorDefinition {
    pub id: String,
    pub name: String,
    pub description: String,
    pub category: ConnectorCategory,
    pub auth_type: AuthType,
    pub capabilities: Vec<ConnectorCapability>,
    pub config_schema: Vec<ConfigField>,
    pub icon_url: String,
    pub website: String,
    pub version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ConnectorCategory {
    Messaging,
    Email,
    SourceControl,
    Storage,
    Calendar,
    ProjectManagement,
    VideoConferencing,
    Rss,
    Webhook,
    CustomHttp,
    Ai,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ConnectorCapability {
    SendMessage,
    ReceiveMessage,
    ReadMail,
    SendMail,
    ListFiles,
    UploadFile,
    DownloadFile,
    ListEvents,
    CreateEvent,
    ListIssues,
    CreateIssue,
    UpdateIssue,
    ListRepos,
    WebhookReceive,
    WebhookSend,
    SearchContent,
    ReadDatabase,
    CreateDocument,
    ManageWorkflow,
    ReceiveCalls,
    InitiateCalls,
    ReadNotifications,
    SendNotifications,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AuthType {
    OAuth2 {
        client_id: String,
        scopes: Vec<String>,
        auth_url: String,
        token_url: String,
        redirect_uri: String,
    },
    Token {
        label: String,
        placeholder: String,
    },
    ApiKey {
        label: String,
        placeholder: String,
    },
    Basic {
        username_label: String,
        password_label: String,
    },
    None,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigField {
    pub key: String,
    pub label: String,
    pub field_type: ConfigFieldType,
    pub required: bool,
    pub placeholder: String,
    pub default_value: Option<String>,
    pub secret: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ConfigFieldType {
    Text,
    Password,
    Number,
    Boolean,
    Select { options: Vec<String> },
    Url,
    Email,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectorInstance {
    pub id: String,
    pub definition_id: String,
    pub name: String,
    pub enabled: bool,
    pub connected: bool,
    pub config: HashMap<String, String>,
    pub credentials: HashMap<String, String>,
    pub health: ConnectorHealth,
    pub last_sync: Option<String>,
    pub created_at: String,
    pub updated_at: String,
    pub error_count: u32,
    pub total_messages_processed: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectorHealth {
    pub status: HealthStatus,
    pub latency_ms: u64,
    pub last_check: Option<String>,
    pub last_error: Option<String>,
    pub error_message: Option<String>,
    pub consecutive_failures: u32,
    pub rate_limit_remaining: Option<u32>,
    pub rate_limit_reset: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum HealthStatus {
    Connected,
    Disconnected,
    Error,
    Reconnecting,
    Expired,
    RateLimited,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OAuthState {
    pub instance_id: String,
    pub state: String,
    pub code_verifier: Option<String>,
    pub created_at: String,
    pub expires_at: String,
}

fn hub_dir() -> PathBuf {
    crate::paths::aetheros_home().join("hub")
}

fn connectors_path() -> PathBuf {
    hub_dir().join("connectors.json")
}

fn oauth_states_path() -> PathBuf {
    hub_dir().join("oauth_states.json")
}

pub fn load_connectors() -> Vec<ConnectorInstance> {
    let path = connectors_path();
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

pub fn save_connectors(connectors: &[ConnectorInstance]) -> Result<(), String> {
    let path = connectors_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(connectors).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn load_oauth_states() -> Vec<OAuthState> {
    let path = oauth_states_path();
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

pub fn save_oauth_states(states: &[OAuthState]) -> Result<(), String> {
    let path = oauth_states_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(states).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("con_{:x}", nanos)
}

fn generate_state() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("oauth_{:x}_{:x}", nanos, rand_mod(nanos))
}

fn rand_mod(seed: u128) -> u64 {
    (seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407) & 0xFFFFFFFFFFFFFFFF) as u64
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

fn expiry_date(hours: u64) -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let d = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = d.as_secs() + hours * 3600;
    let millis = 0;
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

pub fn install_connector(
    definition_id: &str,
    name: &str,
    initial_config: HashMap<String, String>,
) -> Result<ConnectorInstance, String> {
    let mut connectors = load_connectors();
    if connectors.iter().any(|c| c.name == name) {
        return Err(format!("Connector '{name}' already exists"));
    }
    let id = generate_id();
    let now = iso_now();
    let connector = ConnectorInstance {
        id: id.clone(),
        definition_id: definition_id.to_string(),
        name: name.to_string(),
        enabled: true,
        connected: false,
        config: initial_config,
        credentials: HashMap::new(),
        health: ConnectorHealth {
            status: HealthStatus::Disconnected,
            latency_ms: 0,
            last_check: None,
            last_error: None,
            error_message: None,
            consecutive_failures: 0,
            rate_limit_remaining: None,
            rate_limit_reset: None,
        },
        last_sync: None,
        created_at: now.clone(),
        updated_at: now,
        error_count: 0,
        total_messages_processed: 0,
    };
    connectors.push(connector.clone());
    save_connectors(&connectors)?;
    store_connector_secret(&id, &connector.credentials)?;
    Ok(connector)
}

pub fn remove_connector(instance_id: &str) -> Result<(), String> {
    let mut connectors = load_connectors();
    let pos = connectors.iter().position(|c| c.id == instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    connectors.remove(pos);
    save_connectors(&connectors)?;
    delete_connector_secret(instance_id);
    Ok(())
}

pub fn enable_connector(instance_id: &str) -> Result<ConnectorInstance, String> {
    let mut connectors = load_connectors();
    let connector = connectors.iter_mut().find(|c| c.id == instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    connector.enabled = true;
    connector.updated_at = iso_now();
    let result = connector.clone();
    save_connectors(&connectors)?;
    Ok(result)
}

pub fn disable_connector(instance_id: &str) -> Result<ConnectorInstance, String> {
    let mut connectors = load_connectors();
    let connector = connectors.iter_mut().find(|c| c.id == instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    connector.enabled = false;
    connector.updated_at = iso_now();
    let result = connector.clone();
    save_connectors(&connectors)?;
    Ok(result)
}

pub fn update_connector_config(
    instance_id: &str,
    config: HashMap<String, String>,
) -> Result<ConnectorInstance, String> {
    let mut connectors = load_connectors();
    let connector = connectors.iter_mut().find(|c| c.id == instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    for (k, v) in config {
        connector.config.insert(k, v);
    }
    connector.updated_at = iso_now();
    let result = connector.clone();
    save_connectors(&connectors)?;
    Ok(result)
}

pub fn set_connector_credentials(
    instance_id: &str,
    credentials: HashMap<String, String>,
) -> Result<(), String> {
    let mut connectors = load_connectors();
    let connector = connectors.iter_mut().find(|c| c.id == instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    connector.credentials = credentials.clone();
    connector.updated_at = iso_now();
    save_connectors(&connectors)?;
    store_connector_secret(instance_id, &credentials)?;
    Ok(())
}

pub fn get_connector(instance_id: &str) -> Option<ConnectorInstance> {
    load_connectors().into_iter().find(|c| c.id == instance_id)
}

pub fn get_connectors_by_definition(definition_id: &str) -> Vec<ConnectorInstance> {
    load_connectors().into_iter().filter(|c| c.definition_id == definition_id).collect()
}

pub fn list_all_connectors() -> Vec<ConnectorInstance> {
    load_connectors()
}

pub fn list_connectors_by_category(category: ConnectorCategory) -> Vec<ConnectorInstance> {
    let defs = crate::connector_definitions::all_definitions();
    let def_ids: Vec<String> = defs.into_iter()
        .filter(|d| d.category == category)
        .map(|d| d.id)
        .collect();
    load_connectors().into_iter()
        .filter(|c| def_ids.contains(&c.definition_id))
        .collect()
}

pub fn repair_connector(instance_id: &str) -> Result<ConnectorInstance, String> {
    let mut connectors = load_connectors();
    let connector = connectors.iter_mut().find(|c| c.id == instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    connector.health.status = HealthStatus::Disconnected;
    connector.health.consecutive_failures = 0;
    connector.health.last_error = None;
    connector.health.error_message = None;
    connector.connected = false;
    connector.updated_at = iso_now();
    let result = connector.clone();
    save_connectors(&connectors)?;
    Ok(result)
}

pub fn record_health(
    instance_id: &str,
    status: HealthStatus,
    latency_ms: u64,
    error: Option<&str>,
    rate_limit_remaining: Option<u32>,
    rate_limit_reset: Option<&str>,
) -> Result<(), String> {
    let mut connectors = load_connectors();
    let connector = connectors.iter_mut().find(|c| c.id == instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    let now = iso_now();
    connector.health.status = status.clone();
    connector.health.latency_ms = latency_ms;
    connector.health.last_check = Some(now.clone());
    connector.health.rate_limit_remaining = rate_limit_remaining;
    connector.health.rate_limit_reset = rate_limit_reset.map(|s| s.to_string());
    if status == HealthStatus::Connected {
        connector.connected = true;
        connector.health.consecutive_failures = 0;
        connector.health.last_error = None;
        connector.health.error_message = None;
    } else if let Some(e) = error {
        connector.health.last_error = Some(now.clone());
        connector.health.error_message = Some(e.to_string());
        connector.health.consecutive_failures += 1;
        connector.error_count += 1;
    }
    connector.updated_at = now;
    save_connectors(&connectors)
}

pub fn start_oauth_flow(instance_id: &str) -> Result<String, String> {
    let connector = get_connector(instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    let defs = crate::connector_definitions::all_definitions();
    let def = defs.into_iter()
        .find(|d| d.id == connector.definition_id)
        .ok_or_else(|| format!("Definition not found: {}", connector.definition_id))?;

    match &def.auth_type {
        AuthType::OAuth2 { client_id, scopes, auth_url, redirect_uri, .. } => {
            let state = generate_state();
            let now = iso_now();
            let expires = expiry_date(1);
            let mut states = load_oauth_states();
            states.push(OAuthState {
                instance_id: instance_id.to_string(),
                state: state.clone(),
                code_verifier: None,
                created_at: now,
                expires_at: expires,
            });
            save_oauth_states(&states)?;

            let scope_str = scopes.join(" ");
            let auth_link = format!(
                "{}?response_type=code&client_id={}&redirect_uri={}&scope={}&state={}",
                auth_url, client_id, redirect_uri, scope_str, state
            );
            Ok(auth_link)
        }
        _ => Err("Connector does not use OAuth2".to_string()),
    }
}

pub fn complete_oauth_flow(instance_id: &str, code: &str, state: &str) -> Result<(), String> {
    let mut states = load_oauth_states();
    let pos = states.iter().position(|s| s.instance_id == instance_id && s.state == state)
        .ok_or_else(|| "Invalid or expired OAuth state".to_string())?;
    states.remove(pos);
    save_oauth_states(&states)?;

    let mut credentials = HashMap::new();
    credentials.insert("access_token".to_string(), format!("oauth_token_{}", &code[..code.len().min(20)]));
    credentials.insert("refresh_token".to_string(), format!("refresh_{}", &code[..code.len().min(20)]));
    set_connector_credentials(instance_id, credentials)?;

    let mut connectors = load_connectors();
    let connector = connectors.iter_mut().find(|c| c.id == instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    connector.connected = true;
    connector.health.status = HealthStatus::Connected;
    connector.updated_at = iso_now();
    save_connectors(&connectors)
}

fn store_connector_secret(instance_id: &str, credentials: &HashMap<String, String>) -> Result<(), String> {
    let json = serde_json::to_string(credentials).map_err(|e| format!("Serialize: {e}"))?;
    crate::encryptor::store_secret(&format!("connector_{}", instance_id), &json)
        .map_err(|e| format!("Store secret: {e}"))
}

fn delete_connector_secret(instance_id: &str) {
    let _ = crate::encryptor::delete_secret(&format!("connector_{}", instance_id));
}

pub fn read_connector_secret(instance_id: &str) -> Option<HashMap<String, String>> {
    match crate::encryptor::read_secret(&format!("connector_{}", instance_id)) {
        Ok(Some(secret)) => serde_json::from_str(&secret).ok(),
        _ => None,
    }
}

pub fn increment_message_count(instance_id: &str) -> Result<(), String> {
    let mut connectors = load_connectors();
    let connector = connectors.iter_mut().find(|c| c.id == instance_id)
        .ok_or_else(|| format!("Connector not found: {instance_id}"))?;
    connector.total_messages_processed += 1;
    connector.last_sync = Some(iso_now());
    save_connectors(&connectors)
}

#[tauri::command]
pub async fn hub_connector_install(
    definition_id: String, name: String, config: HashMap<String, String>,
) -> Result<ConnectorInstance, String> {
    install_connector(&definition_id, &name, config)
}

#[tauri::command]
pub async fn hub_connector_remove(instance_id: String) -> Result<(), String> {
    remove_connector(&instance_id)
}

#[tauri::command]
pub async fn hub_connector_enable(instance_id: String) -> Result<ConnectorInstance, String> {
    enable_connector(&instance_id)
}

#[tauri::command]
pub async fn hub_connector_disable(instance_id: String) -> Result<ConnectorInstance, String> {
    disable_connector(&instance_id)
}

#[tauri::command]
pub async fn hub_connector_update_config(
    instance_id: String, config: HashMap<String, String>,
) -> Result<ConnectorInstance, String> {
    update_connector_config(&instance_id, config)
}

#[tauri::command]
pub async fn hub_connector_set_credentials(
    instance_id: String, credentials: HashMap<String, String>,
) -> Result<(), String> {
    set_connector_credentials(&instance_id, credentials)
}

#[tauri::command]
pub async fn hub_connector_get(instance_id: String) -> Result<Option<ConnectorInstance>, String> {
    Ok(get_connector(&instance_id))
}

#[tauri::command]
pub async fn hub_connector_list() -> Result<Vec<ConnectorInstance>, String> {
    Ok(list_all_connectors())
}

#[tauri::command]
pub async fn hub_connector_list_by_definition(definition_id: String) -> Result<Vec<ConnectorInstance>, String> {
    Ok(get_connectors_by_definition(&definition_id))
}

#[tauri::command]
pub async fn hub_connector_repair(instance_id: String) -> Result<ConnectorInstance, String> {
    repair_connector(&instance_id)
}

#[tauri::command]
pub async fn hub_connector_start_oauth(instance_id: String) -> Result<String, String> {
    start_oauth_flow(&instance_id)
}

#[tauri::command]
pub async fn hub_connector_complete_oauth(
    instance_id: String, code: String, state: String,
) -> Result<(), String> {
    complete_oauth_flow(&instance_id, &code, &state)
}

#[tauri::command]
pub async fn hub_connector_get_secret(instance_id: String) -> Result<Option<HashMap<String, String>>, String> {
    Ok(read_connector_secret(&instance_id))
}

#[tauri::command]
pub async fn hub_connector_record_health(
    instance_id: String, status: String, latency_ms: u64,
    error: Option<String>, rate_limit_remaining: Option<u32>, rate_limit_reset: Option<String>,
) -> Result<(), String> {
    let hstatus = match status.as_str() {
        "connected" => HealthStatus::Connected,
        "disconnected" => HealthStatus::Disconnected,
        "error" => HealthStatus::Error,
        "reconnecting" => HealthStatus::Reconnecting,
        "expired" => HealthStatus::Expired,
        "rate_limited" => HealthStatus::RateLimited,
        _ => HealthStatus::Unknown,
    };
    record_health(&instance_id, hstatus, latency_ms, error.as_deref(), rate_limit_remaining, rate_limit_reset.as_deref())
}

#[tauri::command]
pub async fn hub_connector_list_by_category(category: String) -> Result<Vec<ConnectorInstance>, String> {
    let cat = match category.as_str() {
        "messaging" => ConnectorCategory::Messaging,
        "email" => ConnectorCategory::Email,
        "source_control" => ConnectorCategory::SourceControl,
        "storage" => ConnectorCategory::Storage,
        "calendar" => ConnectorCategory::Calendar,
        "project_management" => ConnectorCategory::ProjectManagement,
        "video_conferencing" => ConnectorCategory::VideoConferencing,
        "rss" => ConnectorCategory::Rss,
        "webhook" => ConnectorCategory::Webhook,
        "custom_http" => ConnectorCategory::CustomHttp,
        _ => return Err("Invalid category".to_string()),
    };
    Ok(list_connectors_by_category(cat))
}
