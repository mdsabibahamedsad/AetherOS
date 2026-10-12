use crate::marketplace_package::{MarketplacePackage, PackageType};
use crate::marketplace_store::{self, InstallResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtensionConfig {
    pub extension_id: String,
    pub enabled: bool,
    pub auto_update: bool,
    pub settings: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtensionStatus {
    pub extension_id: String,
    pub name: String,
    pub enabled: bool,
    pub version: String,
    pub has_update: bool,
    pub config: ExtensionConfig,
}

fn extension_config_dir() -> PathBuf {
    crate::marketplace_package::installed_packages_dir()
        .join("extensions")
        .join("configs")
}

fn extension_config_path(extension_id: &str) -> PathBuf {
    extension_config_dir().join(format!("{extension_id}.json"))
}

pub fn load_extension_config(extension_id: &str) -> ExtensionConfig {
    let path = extension_config_path(extension_id);
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_else(|| ExtensionConfig {
            extension_id: extension_id.to_string(),
            enabled: true,
            auto_update: true,
            settings: HashMap::new(),
        })
}

pub fn save_extension_config(config: &ExtensionConfig) -> Result<(), String> {
    let path = extension_config_path(&config.extension_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(config).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn list_extensions() -> Vec<MarketplacePackage> {
    marketplace_store::list_installed_by_type(PackageType::Extension)
}

pub fn list_all_catalog_extensions() -> Vec<crate::marketplace_catalog::CatalogEntry> {
    crate::marketplace_catalog::packages_by_type(PackageType::Extension)
}

pub fn get_extension_statuses() -> Vec<ExtensionStatus> {
    let installed = list_extensions();
    installed
        .into_iter()
        .map(|pkg| {
            let config = load_extension_config(&pkg.id);
            ExtensionStatus {
                extension_id: pkg.id.clone(),
                name: pkg.display_name.clone(),
                enabled: config.enabled,
                version: pkg.version.clone(),
                has_update: false,
                config,
            }
        })
        .collect()
}

#[tauri::command]
pub async fn extension_install(package_id: String) -> Result<InstallResult, String> {
    let catalog = crate::marketplace_catalog::get_catalog();
    let entry = catalog
        .into_iter()
        .find(|e| e.package.id == package_id && e.package.package_type == PackageType::Extension)
        .ok_or_else(|| format!("Extension not found: {package_id}"))?;
    marketplace_store::install_package(&entry.package).await
}

#[tauri::command]
pub async fn extension_uninstall(package_id: String) -> Result<InstallResult, String> {
    marketplace_store::uninstall_package(&package_id).await
}

#[tauri::command]
pub async fn extension_get_config(extension_id: String) -> Result<ExtensionConfig, String> {
    Ok(load_extension_config(&extension_id))
}

#[tauri::command]
pub async fn extension_set_config(config: ExtensionConfig) -> Result<(), String> {
    save_extension_config(&config)
}

#[tauri::command]
pub async fn extension_list_installed() -> Result<Vec<MarketplacePackage>, String> {
    Ok(list_extensions())
}

#[tauri::command]
pub async fn extension_list_statuses() -> Result<Vec<ExtensionStatus>, String> {
    Ok(get_extension_statuses())
}

#[tauri::command]
pub async fn extension_enable(extension_id: String) -> Result<(), String> {
    marketplace_store::enable_package(&extension_id)
}

#[tauri::command]
pub async fn extension_disable(extension_id: String) -> Result<(), String> {
    marketplace_store::disable_package(&extension_id)
}
