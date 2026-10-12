use crate::marketplace_package::{self, MarketplacePackage, PackageType};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallResult {
    pub success: bool,
    pub package_id: String,
    pub name: String,
    pub version: String,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateResult {
    pub success: bool,
    pub package_id: String,
    pub old_version: String,
    pub new_version: String,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageState {
    pub package_id: String,
    pub installed: bool,
    pub enabled: bool,
    pub version: String,
    pub install_path: String,
}

fn package_install_dir(pkg: &MarketplacePackage) -> PathBuf {
    let base = marketplace_package::installed_packages_dir();
    base.join(pkg.package_type.as_str()).join(&pkg.id)
}

impl PackageType {
    fn as_str(&self) -> &'static str {
        match self {
            PackageType::Extension => "extensions",
            PackageType::Agent => "agents",
            PackageType::Skill => "skills",
            PackageType::Template => "templates",
            PackageType::Theme => "themes",
            PackageType::Workflow => "workflows",
            PackageType::AutomationPack => "automation-packs",
            PackageType::McpServer => "mcp",
            PackageType::AiTool => "ai-tools",
            PackageType::Widget => "widgets",
            PackageType::CommunityPackage => "community",
            PackageType::OfficialPackage => "official",
            PackageType::IconPack => "icon-packs",
            PackageType::Font => "fonts",
            PackageType::ColorScheme => "color-schemes",
            PackageType::Animation => "animations",
            PackageType::Connector => "connectors",
        }
    }
}

pub fn get_package_state(package_id: &str) -> Option<PackageState> {
    let installed = marketplace_package::load_installed_packages();
    installed.into_iter().find(|p| p.id == package_id).map(|p| {
        let path = package_install_dir(&p);
        PackageState {
            package_id: p.id.clone(),
            installed: path.exists(),
            enabled: true,
            version: p.version.clone(),
            install_path: path.to_string_lossy().to_string(),
        }
    })
}

pub fn list_installed() -> Vec<MarketplacePackage> {
    marketplace_package::load_installed_packages()
}

pub fn list_installed_by_type(package_type: PackageType) -> Vec<MarketplacePackage> {
    marketplace_package::load_installed_packages()
        .into_iter()
        .filter(|p| p.package_type == package_type)
        .collect()
}

pub async fn install_package(pkg: &MarketplacePackage) -> Result<InstallResult, String> {
    let installed = marketplace_package::load_installed_packages();

    if installed.iter().any(|p| p.id == pkg.id) {
        return Ok(InstallResult {
            success: false,
            package_id: pkg.id.clone(),
            name: pkg.name.clone(),
            version: pkg.version.clone(),
            message: "Already installed".to_string(),
        });
    }

    let install_dir = package_install_dir(pkg);
    std::fs::create_dir_all(&install_dir).map_err(|e| format!("Create dir: {e}"))?;

    if let Some(ref script) = pkg.install_script {
        run_install_script(script, &install_dir)?;
    }

    if pkg.package_type == PackageType::Connector {
        if let Some(ref def) = pkg.connector_definition {
            crate::connector_manager::register_custom_definition(def.clone())?;
            tracing::info!(id = def.id, name = def.name, "connector definition registered from marketplace");
        }
    }

    let mut all = installed;
    all.push(pkg.clone());
    marketplace_package::save_installed_packages(&all)?;

    tracing::info!(id = pkg.id, name = pkg.name, "marketplace package installed");

    Ok(InstallResult {
        success: true,
        package_id: pkg.id.clone(),
        name: pkg.name.clone(),
        version: pkg.version.clone(),
        message: format!("{} installed successfully", pkg.display_name),
    })
}

pub async fn uninstall_package(package_id: &str) -> Result<InstallResult, String> {
    let mut installed = marketplace_package::load_installed_packages();
    let idx = installed.iter().position(|p| p.id == package_id)
        .ok_or_else(|| format!("Package not installed: {package_id}"))?;
    let pkg = &installed[idx];

    if let Some(ref script) = pkg.uninstall_script {
        run_install_script(script, &package_install_dir(pkg))?;
    }

    let install_dir = package_install_dir(pkg);
    if install_dir.exists() {
        std::fs::remove_dir_all(&install_dir).map_err(|e| format!("Remove dir: {e}"))?;
    }

    let pkg = installed.remove(idx);
    marketplace_package::save_installed_packages(&installed)?;

    if pkg.package_type == PackageType::Connector {
        let def_id = pkg.connector_definition.as_ref().map(|d| d.id.clone())
            .unwrap_or_else(|| pkg.id.clone());
        let _ = crate::connector_manager::unregister_custom_definition(&def_id);
        tracing::info!(id = def_id, "connector definition unregistered from marketplace");
    }

    tracing::info!(id = package_id, "marketplace package uninstalled");

    Ok(InstallResult {
        success: true,
        package_id: pkg.id.clone(),
        name: pkg.name.clone(),
        version: pkg.version.clone(),
        message: format!("{} uninstalled", pkg.display_name),
    })
}

pub async fn check_for_updates() -> Vec<UpdateResult> {
    let installed = marketplace_package::load_installed_packages();
    let catalog = crate::marketplace_catalog::get_catalog();
    let mut results = Vec::new();

    for installed_pkg in &installed {
        if let Some(catalog_entry) = catalog.iter().find(|e| e.package.id == installed_pkg.id) {
            if catalog_entry.package.version != installed_pkg.version {
                results.push(UpdateResult {
                    success: true,
                    package_id: installed_pkg.id.clone(),
                    old_version: installed_pkg.version.clone(),
                    new_version: catalog_entry.package.version.clone(),
                    message: format!("Update available: {} -> {}", installed_pkg.version, catalog_entry.package.version),
                });
            }
        }
    }

    results
}

pub async fn update_package(package_id: &str) -> Result<UpdateResult, String> {
    let catalog = crate::marketplace_catalog::get_catalog();
    let catalog_entry = catalog.into_iter()
        .find(|e| e.package.id == package_id)
        .ok_or_else(|| format!("Package not found in catalog: {package_id}"))?;

    let mut installed = marketplace_package::load_installed_packages();
    let idx = installed.iter().position(|p| p.id == package_id)
        .ok_or_else(|| format!("Package not installed: {package_id}"))?;
    let old_version = installed[idx].version.clone();

    let install_dir = package_install_dir(&catalog_entry.package);
    std::fs::create_dir_all(&install_dir).map_err(|e| format!("Create dir: {e}"))?;

    installed[idx] = catalog_entry.package.clone();
    marketplace_package::save_installed_packages(&installed)?;

    tracing::info!(id = package_id, "marketplace package updated");

    Ok(UpdateResult {
        success: true,
        package_id: package_id.to_string(),
        old_version,
        new_version: catalog_entry.package.version.clone(),
        message: format!("Updated to {}", catalog_entry.package.version),
    })
}

pub fn disable_package(package_id: &str) -> Result<(), String> {
    let path = marketplace_package::installed_packages_dir()
        .join("disabled")
        .join(package_id);
    let src = marketplace_package::installed_packages_dir().join(package_id);
    if src.exists() {
        std::fs::create_dir_all(path.parent().ok_or("No parent")?)
            .map_err(|e| format!("Create disabled dir: {e}"))?;
        std::fs::rename(&src, &path).map_err(|e| format!("Disable: {e}"))?;
    }
    Ok(())
}

pub fn enable_package(package_id: &str) -> Result<(), String> {
    let path = marketplace_package::installed_packages_dir()
        .join("disabled")
        .join(package_id);
    let dst = marketplace_package::installed_packages_dir().join(package_id);
    if path.exists() {
        std::fs::rename(&path, &dst).map_err(|e| format!("Enable: {e}"))?;
    }
    Ok(())
}

fn run_install_script(script: &str, _dir: &PathBuf) -> Result<(), String> {
    tracing::info!("install script placeholder: {}", &script[..script.len().min(100)]);
    Ok(())
}

#[tauri::command]
pub async fn marketplace_install(package_id: String) -> Result<InstallResult, String> {
    let catalog = crate::marketplace_catalog::get_catalog();
    let entry = catalog.into_iter()
        .find(|e| e.package.id == package_id)
        .ok_or_else(|| format!("Package not found: {package_id}"))?;
    install_package(&entry.package).await
}

#[tauri::command]
pub async fn marketplace_uninstall(package_id: String) -> Result<InstallResult, String> {
    uninstall_package(&package_id).await
}

#[tauri::command]
pub async fn marketplace_update(package_id: String) -> Result<UpdateResult, String> {
    update_package(&package_id).await
}

#[tauri::command]
pub async fn marketplace_check_updates() -> Result<Vec<UpdateResult>, String> {
    Ok(check_for_updates().await)
}

#[tauri::command]
pub async fn marketplace_list_installed() -> Result<Vec<MarketplacePackage>, String> {
    Ok(list_installed())
}

#[tauri::command]
pub async fn marketplace_get_state(package_id: String) -> Result<Option<PackageState>, String> {
    Ok(get_package_state(&package_id))
}

#[tauri::command]
pub async fn marketplace_disable(package_id: String) -> Result<(), String> {
    disable_package(&package_id)
}

#[tauri::command]
pub async fn marketplace_enable(package_id: String) -> Result<(), String> {
    enable_package(&package_id)
}
