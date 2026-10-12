use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceDefinition {
    pub id: String,
    pub name: String,
    pub description: String,
    pub icon: String,
    pub category: String,
    pub auth_type: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceConnection {
    pub service_id: String,
    pub enabled: bool,
    pub connected: bool,
    pub config: HashMap<String, String>,
}

pub fn available_services() -> Vec<ServiceDefinition> {
    vec![
        ServiceDefinition {
            id: "github".into(),
            name: "GitHub".into(),
            description: "Code repositories, pull requests, issues".into(),
            icon: "github".into(),
            category: "development".into(),
            auth_type: "oauth".into(),
        },
        ServiceDefinition {
            id: "google".into(),
            name: "Google".into(),
            description: "Gmail, Calendar, Drive".into(),
            icon: "google".into(),
            category: "productivity".into(),
            auth_type: "oauth".into(),
        },
        ServiceDefinition {
            id: "gmail".into(),
            name: "Gmail".into(),
            description: "Email access and management".into(),
            icon: "mail".into(),
            category: "communication".into(),
            auth_type: "oauth".into(),
        },
        ServiceDefinition {
            id: "telegram".into(),
            name: "Telegram".into(),
            description: "Messaging bot integration".into(),
            icon: "message-circle".into(),
            category: "messaging".into(),
            auth_type: "token".into(),
        },
        ServiceDefinition {
            id: "discord".into(),
            name: "Discord".into(),
            description: "Community server bot".into(),
            icon: "message-square".into(),
            category: "messaging".into(),
            auth_type: "token".into(),
        },
        ServiceDefinition {
            id: "slack".into(),
            name: "Slack".into(),
            description: "Workspace integration".into(),
            icon: "hash".into(),
            category: "communication".into(),
            auth_type: "token".into(),
        },
        ServiceDefinition {
            id: "whatsapp".into(),
            name: "WhatsApp Business".into(),
            description: "Business messaging API".into(),
            icon: "phone".into(),
            category: "messaging".into(),
            auth_type: "token".into(),
        },
        ServiceDefinition {
            id: "microsoft".into(),
            name: "Microsoft".into(),
            description: "Office 365, Outlook, Azure".into(),
            icon: "windows".into(),
            category: "productivity".into(),
            auth_type: "oauth".into(),
        },
        ServiceDefinition {
            id: "notion".into(),
            name: "Notion".into(),
            description: "Docs, wikis, project management".into(),
            icon: "book-open".into(),
            category: "productivity".into(),
            auth_type: "token".into(),
        },
        ServiceDefinition {
            id: "linear".into(),
            name: "Linear".into(),
            description: "Issue tracking and project management".into(),
            icon: "trello".into(),
            category: "development".into(),
            auth_type: "token".into(),
        },
        ServiceDefinition {
            id: "jira".into(),
            name: "Jira".into(),
            description: "Issue and project tracking".into(),
            icon: "trello".into(),
            category: "development".into(),
            auth_type: "oauth".into(),
        },
        ServiceDefinition {
            id: "gitlab".into(),
            name: "GitLab".into(),
            description: "Self-hosted or cloud Git repositories".into(),
            icon: "git-branch".into(),
            category: "development".into(),
            auth_type: "token".into(),
        },
    ]
}

fn services_config_path() -> std::path::PathBuf {
    crate::paths::aetheros_home().join("config").join("services.json")
}

pub fn save_connections(connections: &[ServiceConnection]) -> Result<(), String> {
    let path = services_config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(connections)
        .map_err(|e| format!("Serialize error: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write error: {e}"))?;
    Ok(())
}

pub fn load_connections() -> Result<Vec<ServiceConnection>, String> {
    let path = services_config_path();
    if !path.exists() {
        return Ok(Vec::new());
    }
    let content = std::fs::read_to_string(&path).map_err(|e| format!("Read error: {e}"))?;
    serde_json::from_str(&content).map_err(|e| format!("Parse error: {e}"))
}

pub fn store_service_token(service_id: &str, token: &str) -> Result<(), String> {
    let key = format!("service_token_{}", service_id);
    crate::encryptor::store_secret(&key, token)
}

pub fn read_service_token(service_id: &str) -> Result<Option<String>, String> {
    let key = format!("service_token_{}", service_id);
    crate::encryptor::read_secret(&key)
}

#[tauri::command]
pub async fn get_available_services() -> Result<Vec<ServiceDefinition>, String> {
    Ok(available_services())
}

#[tauri::command]
pub async fn get_service_connections() -> Result<Vec<ServiceConnection>, String> {
    load_connections()
}

#[tauri::command]
pub async fn save_service_connections(connections: Vec<ServiceConnection>) -> Result<(), String> {
    save_connections(&connections)
}

#[tauri::command]
pub async fn connect_service(service_id: String, config: HashMap<String, String>) -> Result<(), String> {
    let mut connections = load_connections()?;
    if let Some(existing) = connections.iter_mut().find(|c| c.service_id == service_id) {
        existing.enabled = true;
        existing.connected = true;
        existing.config = config;
    } else {
        connections.push(ServiceConnection {
            service_id,
            enabled: true,
            connected: true,
            config,
        });
    }
    save_connections(&connections)
}

#[tauri::command]
pub async fn disconnect_service(service_id: String) -> Result<(), String> {
    let mut connections = load_connections()?;
    if let Some(existing) = connections.iter_mut().find(|c| c.service_id == service_id) {
        existing.enabled = false;
        existing.connected = false;
    }
    save_connections(&connections)
}
