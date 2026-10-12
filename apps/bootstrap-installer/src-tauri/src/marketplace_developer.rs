use crate::marketplace_package::{MarketplacePackage, PackageAuthor, PackageType};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeveloperProfile {
    pub id: String,
    pub name: String,
    pub email: String,
    pub website: Option<String>,
    pub github: Option<String>,
    pub bio: Option<String>,
    pub is_verified: bool,
    pub joined_at: String,
    pub total_packages: u32,
    pub total_downloads: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PublishRequest {
    pub package: MarketplacePackage,
    pub release_notes: Option<String>,
    pub is_prerelease: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PublishResult {
    pub success: bool,
    pub package_id: String,
    pub version: String,
    pub message: String,
    pub approval_required: bool,
}

fn developer_dir() -> PathBuf {
    crate::paths::aetheros_home().join("marketplace").join("developer")
}

fn published_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("developer-packages.json")
}

fn load_published() -> Vec<MarketplacePackage> {
    let path = published_path();
    if !path.exists() { return Vec::new(); }
    std::fs::read_to_string(&path).ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

fn save_published(packages: &[MarketplacePackage]) -> Result<(), String> {
    let path = published_path();
    if let Some(parent) = path.parent() { std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?; }
    let content = serde_json::to_string_pretty(packages).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn publish_package(request: PublishRequest) -> PublishResult {
    let mut published = load_published();

    if published.iter().any(|p| p.id == request.package.id && p.version == request.package.version) {
        return PublishResult {
            success: false,
            package_id: request.package.id.clone(),
            version: request.package.version.clone(),
            message: "This version is already published".to_string(),
            approval_required: false,
        };
    }

    let pkg_dir = developer_dir().join(&request.package.id).join(&request.package.version);
    std::fs::create_dir_all(&pkg_dir).ok();

    let meta_path = pkg_dir.join("package.json");
    if let Ok(json) = serde_json::to_string_pretty(&request.package) {
        std::fs::write(&meta_path, json).ok();
    }

    if let Some(notes) = &request.release_notes {
        std::fs::write(pkg_dir.join("RELEASE_NOTES.md"), notes).ok();
    }

    published.push(request.package.clone());
    save_published(&published).ok();

    tracing::info!(id = request.package.id, version = request.package.version, "package published");

    PublishResult {
        success: true,
        package_id: request.package.id.clone(),
        version: request.package.version.clone(),
        message: format!("{} v{} published", request.package.display_name, request.package.version),
        approval_required: !request.package.verified,
    }
}

pub fn list_developer_packages(developer_id: &str) -> Vec<MarketplacePackage> {
    load_published().into_iter().filter(|p| p.author.name == developer_id).collect()
}

pub fn create_package_version(
    id: &str,
    name: &str,
    display_name: &str,
    description: &str,
    package_type: PackageType,
    version: &str,
    author: PackageAuthor,
) -> MarketplacePackage {
    MarketplacePackage {
        id: id.to_string(),
        name: name.to_string(),
        display_name: display_name.to_string(),
        description: description.to_string(),
        package_type,
        version: version.to_string(),
        author,
        license: "MIT".to_string(),
        tags: Vec::new(),
        categories: vec!["custom".into()],
        dependencies: Vec::new(),
        permissions: Vec::new(),
        compatibility: crate::marketplace_package::PackageCompatibility {
            os: vec!["windows".into(), "macos".into(), "linux".into()],
            arch: vec!["x64".into(), "arm64".into()],
            app_version: "0.1.0".into(),
            min_ram_mb: None,
            min_disk_mb: None,
        },
        checksum: String::new(),
        signature: None,
        size_bytes: 0,
        download_url: String::new(),
        icon_url: None,
        screenshots: Vec::new(),
        readme: None,
        changelog: None,
        install_script: None,
        uninstall_script: None,
        min_app_version: "0.1.0".into(),
        max_app_version: None,
        created_at: now_iso(),
        updated_at: now_iso(),
        verified: false,
        is_official: false,
        is_open_source: true,
        connector_definition: None,
    }
}

fn now_iso() -> String {
    let d = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default();
    let s = d.as_secs();
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", (s / 86400) % 30 + 1, s % 86400 / 3600 + 1, (s % 3600) / 60, s % 60, 0)
}

#[tauri::command]
pub async fn developer_publish(request: PublishRequest) -> Result<PublishResult, String> {
    Ok(publish_package(request))
}

#[tauri::command]
pub async fn developer_list_packages(developer_id: String) -> Result<Vec<MarketplacePackage>, String> {
    Ok(list_developer_packages(&developer_id))
}

#[tauri::command]
pub async fn developer_create_package(
    id: String, name: String, display_name: String, description: String,
    package_type: String, version: String, author_name: String,
) -> Result<MarketplacePackage, String> {
    let ptype = match package_type.as_str() {
        "extension" => PackageType::Extension, "agent" => PackageType::Agent,
        "skill" => PackageType::Skill, "template" => PackageType::Template,
        "theme" => PackageType::Theme, "workflow" => PackageType::Workflow,
        "mcp_server" => PackageType::McpServer, _ => PackageType::CommunityPackage,
    };
    let author = PackageAuthor {
        name: author_name, email: None, website: None, github: None, is_verified: false,
    };
    Ok(create_package_version(&id, &name, &display_name, &description, ptype, &version, author))
}
