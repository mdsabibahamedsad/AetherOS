use crate::connector_manager::ConnectorDefinition;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketplacePackage {
    pub id: String,
    pub name: String,
    pub display_name: String,
    pub description: String,
    pub package_type: PackageType,
    pub version: String,
    pub author: PackageAuthor,
    pub license: String,
    pub tags: Vec<String>,
    pub categories: Vec<String>,
    pub dependencies: Vec<PackageDependency>,
    pub permissions: Vec<PackagePermission>,
    pub compatibility: PackageCompatibility,
    pub checksum: String,
    pub signature: Option<String>,
    pub size_bytes: u64,
    pub download_url: String,
    pub icon_url: Option<String>,
    pub screenshots: Vec<String>,
    pub readme: Option<String>,
    pub changelog: Option<String>,
    pub install_script: Option<String>,
    pub uninstall_script: Option<String>,
    pub min_app_version: String,
    pub max_app_version: Option<String>,
    pub created_at: String,
    pub updated_at: String,
    pub verified: bool,
    pub is_official: bool,
    pub is_open_source: bool,
    pub connector_definition: Option<ConnectorDefinition>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PackageType {
    Extension,
    Agent,
    Skill,
    Template,
    Theme,
    Workflow,
    AutomationPack,
    McpServer,
    AiTool,
    Widget,
    CommunityPackage,
    OfficialPackage,
    IconPack,
    Font,
    ColorScheme,
    Animation,
    Connector,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageAuthor {
    pub name: String,
    pub email: Option<String>,
    pub website: Option<String>,
    pub github: Option<String>,
    pub is_verified: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageDependency {
    pub id: String,
    pub name: String,
    pub version_req: String,
    pub optional: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackagePermission {
    pub permission: String,
    pub description: String,
    pub required: bool,
    pub granted: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageCompatibility {
    pub os: Vec<String>,
    pub arch: Vec<String>,
    pub app_version: String,
    pub min_ram_mb: Option<u64>,
    pub min_disk_mb: Option<u64>,
}

pub fn marketplace_dir() -> PathBuf {
    crate::paths::aetheros_home().join("marketplace")
}

pub fn installed_packages_dir() -> PathBuf {
    marketplace_dir().join("installed")
}

pub fn package_cache_dir() -> PathBuf {
    marketplace_dir().join("cache")
}

pub fn package_registry_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("marketplace-registry.json")
}

pub fn load_installed_packages() -> Vec<MarketplacePackage> {
    let path = package_registry_path();
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

pub fn save_installed_packages(packages: &[MarketplacePackage]) -> Result<(), String> {
    let path = package_registry_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(packages).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}
