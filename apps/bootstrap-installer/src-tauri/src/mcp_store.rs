use crate::marketplace_package::{MarketplacePackage, PackageType};
use crate::marketplace_store::{self, InstallResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpServerConfig {
    pub server_id: String,
    pub enabled: bool,
    pub auto_start: bool,
    pub transport: McpTransport,
    pub command: Option<String>,
    pub args: Vec<String>,
    pub env: HashMap<String, String>,
    pub settings: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum McpTransport {
    Stdio,
    Sse,
    StreamableHttp,
}

impl Default for McpTransport {
    fn default() -> Self {
        McpTransport::Stdio
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpServerStatus {
    pub server_id: String,
    pub name: String,
    pub running: bool,
    pub enabled: bool,
    pub version: String,
    pub transport: McpTransport,
    pub connected: bool,
    pub last_active: Option<String>,
    pub config: McpServerConfig,
}

fn mcp_config_dir() -> PathBuf {
    crate::marketplace_package::installed_packages_dir()
        .join("mcp")
        .join("configs")
}

fn mcp_config_path(server_id: &str) -> PathBuf {
    mcp_config_dir().join(format!("{server_id}.json"))
}

pub fn load_mcp_config(server_id: &str) -> McpServerConfig {
    let path = mcp_config_path(server_id);
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_else(|| McpServerConfig {
            server_id: server_id.to_string(),
            enabled: true,
            auto_start: false,
            transport: McpTransport::Stdio,
            command: None,
            args: Vec::new(),
            env: HashMap::new(),
            settings: HashMap::new(),
        })
}

pub fn save_mcp_config(config: &McpServerConfig) -> Result<(), String> {
    let path = mcp_config_path(&config.server_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(config).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn list_mcp_servers() -> Vec<MarketplacePackage> {
    marketplace_store::list_installed_by_type(PackageType::McpServer)
}

pub fn list_all_catalog_mcp() -> Vec<crate::marketplace_catalog::CatalogEntry> {
    crate::marketplace_catalog::packages_by_type(PackageType::McpServer)
}

pub fn get_mcp_statuses() -> Vec<McpServerStatus> {
    let installed = list_mcp_servers();
    installed
        .into_iter()
        .map(|pkg| {
            let config = load_mcp_config(&pkg.id);
            McpServerStatus {
                server_id: pkg.id.clone(),
                name: pkg.display_name.clone(),
                running: false,
                enabled: config.enabled,
                version: pkg.version.clone(),
                transport: config.transport.clone(),
                connected: false,
                last_active: None,
                config,
            }
        })
        .collect()
}

#[tauri::command]
pub async fn mcp_install(package_id: String) -> Result<InstallResult, String> {
    let catalog = crate::marketplace_catalog::get_catalog();
    let entry = catalog
        .into_iter()
        .find(|e| e.package.id == package_id && e.package.package_type == PackageType::McpServer)
        .ok_or_else(|| format!("MCP server not found: {package_id}"))?;
    marketplace_store::install_package(&entry.package).await
}

#[tauri::command]
pub async fn mcp_uninstall(package_id: String) -> Result<InstallResult, String> {
    marketplace_store::uninstall_package(&package_id).await
}

#[tauri::command]
pub async fn mcp_get_config(server_id: String) -> Result<McpServerConfig, String> {
    Ok(load_mcp_config(&server_id))
}

#[tauri::command]
pub async fn mcp_set_config(config: McpServerConfig) -> Result<(), String> {
    save_mcp_config(&config)
}

#[tauri::command]
pub async fn mcp_list_installed() -> Result<Vec<MarketplacePackage>, String> {
    Ok(list_mcp_servers())
}

#[tauri::command]
pub async fn mcp_list_statuses() -> Result<Vec<McpServerStatus>, String> {
    Ok(get_mcp_statuses())
}

#[tauri::command]
pub async fn mcp_start(server_id: String) -> Result<(), String> {
    marketplace_store::enable_package(&server_id)
}

#[tauri::command]
pub async fn mcp_stop(server_id: String) -> Result<(), String> {
    marketplace_store::disable_package(&server_id)
}

#[tauri::command]
pub async fn mcp_enable(server_id: String) -> Result<(), String> {
    marketplace_store::enable_package(&server_id)
}

#[tauri::command]
pub async fn mcp_disable(server_id: String) -> Result<(), String> {
    marketplace_store::disable_package(&server_id)
}
