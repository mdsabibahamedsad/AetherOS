use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FirstRunStatus {
    pub is_first_run: bool,
    pub has_bootstrap_marker: bool,
    pub has_config: bool,
    pub has_profile: bool,
    pub has_ai_settings: bool,
    pub has_wizard_complete: bool,
    pub has_workspace: bool,
}

fn wizard_complete_marker() -> PathBuf {
    crate::paths::aetheros_home().join("config").join(".setup-wizard-complete")
}

fn check_bootstrap_marker() -> bool {
    let marker = crate::installer::bootstrap_complete_marker();
    marker.exists()
}

fn check_config() -> bool {
    let config = crate::paths::aetheros_home().join("config").join("config.yaml");
    config.exists()
}

fn check_profile() -> bool {
    let profile = crate::paths::aetheros_home()
        .join("profiles")
        .join("default")
        .join("profile.yaml");
    profile.exists()
}

fn check_ai_settings() -> bool {
    let providers = crate::paths::aetheros_home()
        .join("config")
        .join("ai-providers.json");
    providers.exists()
}

fn check_wizard_complete() -> bool {
    wizard_complete_marker().exists()
}

fn check_workspace() -> bool {
    let home = crate::paths::aetheros_home();
    home.join("knowledge").exists() || home.join("projects").exists()
}

pub fn detect_first_run() -> FirstRunStatus {
    let has_bootstrap = check_bootstrap_marker();
    let has_cfg = check_config();
    let has_prof = check_profile();

    FirstRunStatus {
        is_first_run: !(has_bootstrap && has_cfg && has_prof && check_wizard_complete()),
        has_bootstrap_marker: has_bootstrap,
        has_config: has_cfg,
        has_profile: has_prof,
        has_ai_settings: check_ai_settings(),
        has_wizard_complete: check_wizard_complete(),
        has_workspace: check_workspace(),
    }
}

pub fn mark_wizard_complete() -> Result<(), String> {
    let path = wizard_complete_marker();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create config dir: {e}"))?;
    }
    let content = serde_json::json!({
        "completed_at": now_iso(),
        "version": env!("CARGO_PKG_VERSION"),
    });
    std::fs::write(&path, serde_json::to_string_pretty(&content).unwrap())
        .map_err(|e| format!("Cannot write wizard marker: {e}"))?;
    tracing::info!("setup wizard marked complete");
    Ok(())
}

pub fn reset_wizard() -> Result<(), String> {
    let path = wizard_complete_marker();
    if path.exists() {
        std::fs::remove_file(&path).map_err(|e| format!("Cannot remove wizard marker: {e}"))?;
    }
    Ok(())
}

fn now_iso() -> String {
    let duration = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = duration.as_secs();
    let days = secs / 86400;
    let hours = (secs % 86400) / 3600;
    let minutes = (secs % 3600) / 60;
    let seconds = secs % 60;
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", days / 30 + 1, days % 30 + 1, hours, minutes, seconds)
}

#[tauri::command]
pub async fn check_first_run() -> Result<FirstRunStatus, String> {
    Ok(detect_first_run())
}

#[tauri::command]
pub async fn complete_setup_wizard() -> Result<(), String> {
    mark_wizard_complete()
}

#[tauri::command]
pub async fn reset_setup_wizard() -> Result<(), String> {
    reset_wizard()
}
