use crate::marketplace_package::{MarketplacePackage, PackageType};
use crate::marketplace_store::{self, InstallResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThemeConfig {
    pub theme_id: String,
    pub theme_type: ThemeType,
    pub enabled: bool,
    pub is_active: bool,
    pub settings: HashMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ThemeType {
    Dark,
    Light,
    IconPack,
    Font,
    ColorScheme,
    Animation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThemeStatus {
    pub theme_id: String,
    pub name: String,
    pub theme_type: ThemeType,
    pub enabled: bool,
    pub is_active: bool,
    pub version: String,
    pub config: ThemeConfig,
}

fn theme_config_dir() -> PathBuf {
    crate::marketplace_package::installed_packages_dir()
        .join("themes")
        .join("configs")
}

fn theme_config_path(theme_id: &str) -> PathBuf {
    theme_config_dir().join(format!("{theme_id}.json"))
}

fn active_theme_path() -> PathBuf {
    crate::marketplace_package::installed_packages_dir()
        .join("themes")
        .join("active.json")
}

pub fn load_theme_config(theme_id: &str) -> ThemeConfig {
    let path = theme_config_path(theme_id);
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_else(|| {
            let ttype = if theme_id.contains("icon") {
                ThemeType::IconPack
            } else if theme_id.contains("font") {
                ThemeType::Font
            } else if theme_id.contains("color") || theme_id.contains("scheme") {
                ThemeType::ColorScheme
            } else if theme_id.contains("anim") {
                ThemeType::Animation
            } else if theme_id.contains("light") || theme_id.contains("day") {
                ThemeType::Light
            } else {
                ThemeType::Dark
            };
            ThemeConfig {
                theme_id: theme_id.to_string(),
                theme_type: ttype,
                enabled: true,
                is_active: false,
                settings: HashMap::new(),
            }
        })
}

pub fn save_theme_config(config: &ThemeConfig) -> Result<(), String> {
    let path = theme_config_path(&config.theme_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(config).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn get_active_theme_id() -> Option<String> {
    let path = active_theme_path();
    if !path.exists() {
        return None;
    }
    std::fs::read_to_string(&path).ok().map(|s| s.trim().to_string())
}

pub fn set_active_theme(theme_id: &str) -> Result<(), String> {
    let path = active_theme_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create themes dir: {e}"))?;
    }
    std::fs::write(&path, theme_id).map_err(|e| format!("Write active theme: {e}"))?;

    let mut config = load_theme_config(theme_id);
    config.is_active = true;
    save_theme_config(&config)?;

    Ok(())
}

pub fn list_themes_by_type(theme_type: ThemeType) -> Vec<MarketplacePackage> {
    marketplace_store::list_installed_by_type(PackageType::Theme)
        .into_iter()
        .filter(|p| {
            let config = load_theme_config(&p.id);
            config.theme_type == theme_type
        })
        .collect()
}

pub fn get_theme_statuses() -> Vec<ThemeStatus> {
    let active_id = get_active_theme_id();
    let installed = marketplace_store::list_installed_by_type(PackageType::Theme);
    installed
        .into_iter()
        .map(|pkg| {
            let config = load_theme_config(&pkg.id);
            ThemeStatus {
                theme_id: pkg.id.clone(),
                name: pkg.display_name.clone(),
                theme_type: config.theme_type.clone(),
                enabled: config.enabled,
                is_active: Some(&pkg.id) == active_id.as_ref(),
                version: pkg.version.clone(),
                config,
            }
        })
        .collect()
}

#[tauri::command]
pub async fn theme_install(package_id: String) -> Result<InstallResult, String> {
    let catalog = crate::marketplace_catalog::get_catalog();
    let entry = catalog
        .into_iter()
        .find(|e| e.package.id == package_id && e.package.package_type == PackageType::Theme)
        .ok_or_else(|| format!("Theme not found: {package_id}"))?;
    marketplace_store::install_package(&entry.package).await
}

#[tauri::command]
pub async fn theme_uninstall(package_id: String) -> Result<InstallResult, String> {
    marketplace_store::uninstall_package(&package_id).await
}

#[tauri::command]
pub async fn theme_get_config(theme_id: String) -> Result<ThemeConfig, String> {
    Ok(load_theme_config(&theme_id))
}

#[tauri::command]
pub async fn theme_set_config(config: ThemeConfig) -> Result<(), String> {
    save_theme_config(&config)
}

#[tauri::command]
pub async fn theme_list_installed() -> Result<Vec<MarketplacePackage>, String> {
    Ok(marketplace_store::list_installed_by_type(PackageType::Theme))
}

#[tauri::command]
pub async fn theme_list_statuses() -> Result<Vec<ThemeStatus>, String> {
    Ok(get_theme_statuses())
}

#[tauri::command]
pub async fn theme_apply(theme_id: String) -> Result<(), String> {
    set_active_theme(&theme_id)
}

#[tauri::command]
pub async fn theme_get_active() -> Result<Option<String>, String> {
    Ok(get_active_theme_id())
}

#[tauri::command]
pub async fn theme_enable(theme_id: String) -> Result<(), String> {
    marketplace_store::enable_package(&theme_id)
}

#[tauri::command]
pub async fn theme_disable(theme_id: String) -> Result<(), String> {
    marketplace_store::disable_package(&theme_id)
}
