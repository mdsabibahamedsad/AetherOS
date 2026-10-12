use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum UninstallScope {
    /// Remove application files only, keep user data
    ApplicationOnly,
    /// Remove everything including user data
    Full,
    /// Remove application + cache, keep user data
    KeepData,
    /// Remove everything + logs
    Complete,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UninstallPlan {
    pub items: Vec<UninstallItem>,
    pub total_size: u64,
    pub can_undo: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UninstallItem {
    pub path: String,
    pub description: String,
    pub size: u64,
    pub will_remove: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UninstallResult {
    pub success: bool,
    pub items_removed: usize,
    pub items_failed: usize,
    pub total_freed: u64,
    pub errors: Vec<String>,
}

fn aetheros_home() -> PathBuf {
    crate::paths::aetheros_home()
}

fn app_dir() -> PathBuf {
    crate::installer::install_root()
}

pub fn build_uninstall_plan(scope: UninstallScope) -> UninstallPlan {
    let mut items = Vec::new();
    let aet = aetheros_home();
    let app = app_dir();

    match scope {
        UninstallScope::ApplicationOnly => {
            items.push(item(&app, "AetherOS Application", true));
            items.push(item(&aet.join("config"), "Configuration", false));
            items.push(item(&aet.join("cache"), "Cache", false));
            items.push(item(&aet.join("logs"), "Logs", false));
        }
        UninstallScope::Full => {
            items.push(item(&app, "AetherOS Application", true));
            items.push(item(&aet.join("config"), "Configuration", true));
            items.push(item(&aet.join("cache"), "Cache", true));
            items.push(item(&aet.join("logs"), "Logs", true));
            items.push(item(&aet.join("data"), "User Data", true));
            items.push(item(&aet.join("profiles"), "Profiles", true));
            items.push(item(&aet.join("knowledge"), "Knowledge Store", true));
            items.push(item(&aet.join("projects"), "Projects", true));
            items.push(item(&aet.join("extensions"), "Extensions", true));
            items.push(item(&aet.join("tmp"), "Temporary Files", true));
        }
        UninstallScope::KeepData => {
            items.push(item(&app, "AetherOS Application", true));
            items.push(item(&aet.join("config"), "Configuration", true));
            items.push(item(&aet.join("cache"), "Cache", true));
            items.push(item(&aet.join("logs"), "Logs", true));
            items.push(item(&aet.join("tmp"), "Temporary Files", true));
            // Keep data, profiles, knowledge, projects, extensions
            items.push(item(&aet.join("data"), "User Data (kept)", false));
            items.push(item(&aet.join("profiles"), "Profiles (kept)", false));
        }
        UninstallScope::Complete => {
            items.push(item(&app, "AetherOS Application", true));
            items.push(item(&aet.join("config"), "Configuration", true));
            items.push(item(&aet.join("cache"), "Cache", true));
            items.push(item(&aet.join("logs"), "Logs", true));
            items.push(item(&aet.join("data"), "User Data", true));
            items.push(item(&aet.join("profiles"), "Profiles", true));
            items.push(item(&aet.join("knowledge"), "Knowledge Store", true));
            items.push(item(&aet.join("projects"), "Projects", true));
            items.push(item(&aet.join("extensions"), "Extensions", true));
            items.push(item(&aet.join("models"), "Models", true));
            items.push(item(&aet.join("tmp"), "Temporary Files", true));
            items.push(item(&aet.join("bootstrap-cache"), "Bootstrap Cache", true));
        }
    }

    let total = items.iter().filter(|i| i.will_remove).map(|i| i.size).sum();
    UninstallPlan { items, total_size: total, can_undo: true }
}

fn item(path: &PathBuf, description: &str, will_remove: bool) -> UninstallItem {
    let size = if path.exists() { dir_size(path) } else { 0 };
    UninstallItem {
        path: path.to_string_lossy().to_string(),
        description: description.to_string(),
        size,
        will_remove,
    }
}

fn dir_size(path: &PathBuf) -> u64 {
    let mut total = 0u64;
    if path.is_dir() {
        if let Ok(entries) = std::fs::read_dir(path) {
            for entry in entries.flatten() {
                let p = entry.path();
                if p.is_dir() {
                    total += dir_size(&p);
                } else if let Ok(meta) = entry.metadata() {
                    total += meta.len();
                }
            }
        }
    } else if path.is_file() {
        if let Ok(meta) = std::fs::metadata(path) {
            total = meta.len();
        }
    }
    total
}

pub async fn execute_uninstall(scope: UninstallScope) -> UninstallResult {
    let plan = build_uninstall_plan(scope);
    let mut removed = 0usize;
    let mut failed = 0usize;
    let mut freed = 0u64;
    let mut errors = Vec::new();

    for item in &plan.items {
        if !item.will_remove {
            continue;
        }
        let path = PathBuf::from(&item.path);
        if !path.exists() {
            continue;
        }

        let result = if path.is_dir() {
            std::fs::remove_dir_all(&path)
        } else {
            std::fs::remove_file(&path)
        };

        match result {
            Ok(()) => {
                removed += 1;
                freed += item.size;
                tracing::info!(path = %item.path, "uninstalled");
            }
            Err(e) => {
                failed += 1;
                errors.push(format!("Failed to remove {}: {e}", item.path));
                tracing::warn!(path = %item.path, error = %e, "uninstall failed");
            }
        }
    }

    let success = failed == 0;
    UninstallResult { success, items_removed: removed, items_failed: failed, total_freed: freed, errors }
}

#[tauri::command]
pub async fn get_uninstall_plan(scope: UninstallScope) -> Result<UninstallPlan, String> {
    Ok(build_uninstall_plan(scope))
}

#[tauri::command]
pub async fn run_uninstall(scope: UninstallScope) -> Result<UninstallResult, String> {
    let result = execute_uninstall(scope).await;
    Ok(result)
}
