use crate::marketplace_package::{MarketplacePackage, PackageType};
use crate::marketplace_store::{self, InstallResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowConfig {
    pub workflow_id: String,
    pub enabled: bool,
    pub trigger: WorkflowTrigger,
    pub schedule: Option<String>,
    pub settings: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WorkflowTrigger {
    Manual,
    Scheduled,
    Event,
    Webhook,
}

impl Default for WorkflowTrigger {
    fn default() -> Self {
        WorkflowTrigger::Manual
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStatus {
    pub workflow_id: String,
    pub name: String,
    pub enabled: bool,
    pub version: String,
    pub last_run: Option<String>,
    pub next_run: Option<String>,
    pub run_count: u64,
    pub config: WorkflowConfig,
}

fn workflow_config_dir() -> PathBuf {
    crate::marketplace_package::installed_packages_dir()
        .join("workflows")
        .join("configs")
}

fn workflow_config_path(workflow_id: &str) -> PathBuf {
    workflow_config_dir().join(format!("{workflow_id}.json"))
}

pub fn load_workflow_config(workflow_id: &str) -> WorkflowConfig {
    let path = workflow_config_path(workflow_id);
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_else(|| WorkflowConfig {
            workflow_id: workflow_id.to_string(),
            enabled: true,
            trigger: WorkflowTrigger::Manual,
            schedule: None,
            settings: HashMap::new(),
        })
}

pub fn save_workflow_config(config: &WorkflowConfig) -> Result<(), String> {
    let path = workflow_config_path(&config.workflow_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(config).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn list_workflows() -> Vec<MarketplacePackage> {
    marketplace_store::list_installed_by_type(PackageType::Workflow)
}

pub fn list_all_catalog_workflows() -> Vec<crate::marketplace_catalog::CatalogEntry> {
    crate::marketplace_catalog::packages_by_type(PackageType::Workflow)
}

pub fn get_workflow_statuses() -> Vec<WorkflowStatus> {
    let installed = list_workflows();
    installed
        .into_iter()
        .map(|pkg| {
            let config = load_workflow_config(&pkg.id);
            WorkflowStatus {
                workflow_id: pkg.id.clone(),
                name: pkg.display_name.clone(),
                enabled: config.enabled,
                version: pkg.version.clone(),
                last_run: None,
                next_run: None,
                run_count: 0,
                config,
            }
        })
        .collect()
}

#[tauri::command]
pub async fn workflow_install(package_id: String) -> Result<InstallResult, String> {
    let catalog = crate::marketplace_catalog::get_catalog();
    let entry = catalog
        .into_iter()
        .find(|e| e.package.id == package_id && e.package.package_type == PackageType::Workflow)
        .ok_or_else(|| format!("Workflow not found: {package_id}"))?;
    marketplace_store::install_package(&entry.package).await
}

#[tauri::command]
pub async fn workflow_uninstall(package_id: String) -> Result<InstallResult, String> {
    marketplace_store::uninstall_package(&package_id).await
}

#[tauri::command]
pub async fn workflow_get_config(workflow_id: String) -> Result<WorkflowConfig, String> {
    Ok(load_workflow_config(&workflow_id))
}

#[tauri::command]
pub async fn workflow_set_config(config: WorkflowConfig) -> Result<(), String> {
    save_workflow_config(&config)
}

#[tauri::command]
pub async fn workflow_list_installed() -> Result<Vec<MarketplacePackage>, String> {
    Ok(list_workflows())
}

#[tauri::command]
pub async fn workflow_list_statuses() -> Result<Vec<WorkflowStatus>, String> {
    Ok(get_workflow_statuses())
}

#[tauri::command]
pub async fn workflow_run(workflow_id: String) -> Result<(), String> {
    marketplace_store::enable_package(&workflow_id)
}

#[tauri::command]
pub async fn workflow_stop(workflow_id: String) -> Result<(), String> {
    marketplace_store::disable_package(&workflow_id)
}

#[tauri::command]
pub async fn workflow_enable(workflow_id: String) -> Result<(), String> {
    marketplace_store::enable_package(&workflow_id)
}

#[tauri::command]
pub async fn workflow_disable(workflow_id: String) -> Result<(), String> {
    marketplace_store::disable_package(&workflow_id)
}
