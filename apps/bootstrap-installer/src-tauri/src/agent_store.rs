use crate::marketplace_package::{MarketplacePackage, PackageType};
use crate::marketplace_store::{self, InstallResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    pub agent_id: String,
    pub enabled: bool,
    pub auto_start: bool,
    pub max_iterations: Option<u32>,
    pub model: Option<String>,
    pub provider: Option<String>,
    pub system_prompt: Option<String>,
    pub allowed_tools: Vec<String>,
    pub settings: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStatus {
    pub agent_id: String,
    pub name: String,
    pub running: bool,
    pub enabled: bool,
    pub version: String,
    pub last_active: Option<String>,
    pub config: AgentConfig,
}

fn agent_config_dir() -> PathBuf {
    crate::marketplace_package::installed_packages_dir()
        .join("agents")
        .join("configs")
}

fn agent_config_path(agent_id: &str) -> PathBuf {
    agent_config_dir().join(format!("{agent_id}.json"))
}

pub fn load_agent_config(agent_id: &str) -> AgentConfig {
    let path = agent_config_path(agent_id);
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_else(|| AgentConfig {
            agent_id: agent_id.to_string(),
            enabled: true,
            auto_start: false,
            max_iterations: None,
            model: None,
            provider: None,
            system_prompt: None,
            allowed_tools: Vec::new(),
            settings: HashMap::new(),
        })
}

pub fn save_agent_config(config: &AgentConfig) -> Result<(), String> {
    let path = agent_config_path(&config.agent_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(config).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn list_agents() -> Vec<MarketplacePackage> {
    marketplace_store::list_installed_by_type(PackageType::Agent)
}

pub fn list_all_catalog_agents() -> Vec<crate::marketplace_catalog::CatalogEntry> {
    crate::marketplace_catalog::packages_by_type(PackageType::Agent)
}

pub fn get_agent_statuses() -> Vec<AgentStatus> {
    let installed = list_agents();
    installed
        .into_iter()
        .map(|pkg| {
            let config = load_agent_config(&pkg.id);
            AgentStatus {
                agent_id: pkg.id.clone(),
                name: pkg.display_name.clone(),
                running: false,
                enabled: config.enabled,
                version: pkg.version.clone(),
                last_active: None,
                config,
            }
        })
        .collect()
}

#[tauri::command]
pub async fn agent_install(package_id: String) -> Result<InstallResult, String> {
    let catalog = crate::marketplace_catalog::get_catalog();
    let entry = catalog
        .into_iter()
        .find(|e| e.package.id == package_id && e.package.package_type == PackageType::Agent)
        .ok_or_else(|| format!("Agent not found: {package_id}"))?;
    marketplace_store::install_package(&entry.package).await
}

#[tauri::command]
pub async fn agent_uninstall(package_id: String) -> Result<InstallResult, String> {
    marketplace_store::uninstall_package(&package_id).await
}

#[tauri::command]
pub async fn agent_get_config(agent_id: String) -> Result<AgentConfig, String> {
    Ok(load_agent_config(&agent_id))
}

#[tauri::command]
pub async fn agent_set_config(config: AgentConfig) -> Result<(), String> {
    save_agent_config(&config)
}

#[tauri::command]
pub async fn agent_list_installed() -> Result<Vec<MarketplacePackage>, String> {
    Ok(list_agents())
}

#[tauri::command]
pub async fn agent_list_statuses() -> Result<Vec<AgentStatus>, String> {
    Ok(get_agent_statuses())
}

#[tauri::command]
pub async fn agent_enable(agent_id: String) -> Result<(), String> {
    marketplace_store::enable_package(&agent_id)
}

#[tauri::command]
pub async fn agent_disable(agent_id: String) -> Result<(), String> {
    marketplace_store::disable_package(&agent_id)
}
