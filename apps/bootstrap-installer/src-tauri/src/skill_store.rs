use crate::marketplace_package::{MarketplacePackage, PackageType};
use crate::marketplace_store::{self, InstallResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillConfig {
    pub skill_id: String,
    pub enabled: bool,
    pub auto_load: bool,
    pub priority: u32,
    pub settings: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillStatus {
    pub skill_id: String,
    pub name: String,
    pub enabled: bool,
    pub active: bool,
    pub version: String,
    pub config: SkillConfig,
}

fn skill_config_dir() -> PathBuf {
    crate::marketplace_package::installed_packages_dir()
        .join("skills")
        .join("configs")
}

fn skill_config_path(skill_id: &str) -> PathBuf {
    skill_config_dir().join(format!("{skill_id}.json"))
}

pub fn load_skill_config(skill_id: &str) -> SkillConfig {
    let path = skill_config_path(skill_id);
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_else(|| SkillConfig {
            skill_id: skill_id.to_string(),
            enabled: true,
            auto_load: true,
            priority: 0,
            settings: HashMap::new(),
        })
}

pub fn save_skill_config(config: &SkillConfig) -> Result<(), String> {
    let path = skill_config_path(&config.skill_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(config).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn list_skills() -> Vec<MarketplacePackage> {
    marketplace_store::list_installed_by_type(PackageType::Skill)
}

pub fn list_all_catalog_skills() -> Vec<crate::marketplace_catalog::CatalogEntry> {
    crate::marketplace_catalog::packages_by_type(PackageType::Skill)
}

pub fn get_skill_statuses() -> Vec<SkillStatus> {
    let installed = list_skills();
    installed
        .into_iter()
        .map(|pkg| {
            let config = load_skill_config(&pkg.id);
            SkillStatus {
                skill_id: pkg.id.clone(),
                name: pkg.display_name.clone(),
                enabled: config.enabled,
                active: config.enabled && config.auto_load,
                version: pkg.version.clone(),
                config,
            }
        })
        .collect()
}

pub fn activate_skill(skill_id: &str) -> Result<(), String> {
    let mut config = load_skill_config(skill_id);
    config.enabled = true;
    save_skill_config(&config)
}

pub fn deactivate_skill(skill_id: &str) -> Result<(), String> {
    let mut config = load_skill_config(skill_id);
    config.enabled = false;
    save_skill_config(&config)
}

#[tauri::command]
pub async fn skill_install(package_id: String) -> Result<InstallResult, String> {
    let catalog = crate::marketplace_catalog::get_catalog();
    let entry = catalog
        .into_iter()
        .find(|e| e.package.id == package_id && e.package.package_type == PackageType::Skill)
        .ok_or_else(|| format!("Skill not found: {package_id}"))?;
    marketplace_store::install_package(&entry.package).await
}

#[tauri::command]
pub async fn skill_uninstall(package_id: String) -> Result<InstallResult, String> {
    marketplace_store::uninstall_package(&package_id).await
}

#[tauri::command]
pub async fn skill_get_config(skill_id: String) -> Result<SkillConfig, String> {
    Ok(load_skill_config(&skill_id))
}

#[tauri::command]
pub async fn skill_set_config(config: SkillConfig) -> Result<(), String> {
    save_skill_config(&config)
}

#[tauri::command]
pub async fn skill_list_installed() -> Result<Vec<MarketplacePackage>, String> {
    Ok(list_skills())
}

#[tauri::command]
pub async fn skill_list_statuses() -> Result<Vec<SkillStatus>, String> {
    Ok(get_skill_statuses())
}

#[tauri::command]
pub async fn skill_activate(skill_id: String) -> Result<(), String> {
    activate_skill(&skill_id)
}

#[tauri::command]
pub async fn skill_deactivate(skill_id: String) -> Result<(), String> {
    deactivate_skill(&skill_id)
}

#[tauri::command]
pub async fn skill_enable(skill_id: String) -> Result<(), String> {
    marketplace_store::enable_package(&skill_id)
}

#[tauri::command]
pub async fn skill_disable(skill_id: String) -> Result<(), String> {
    marketplace_store::disable_package(&skill_id)
}
