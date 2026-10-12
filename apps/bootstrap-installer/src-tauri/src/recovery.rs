use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecoveryCheckpoint {
    pub stage: String,
    pub timestamp: String,
    pub data: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecoveryState {
    pub interrupted: bool,
    pub last_stage: Option<String>,
    pub checkpoints: Vec<RecoveryCheckpoint>,
    pub can_resume: bool,
    pub install_root: Option<String>,
}

fn recovery_file_path() -> PathBuf {
    crate::paths::aetheros_home().join(".install-recovery.json")
}

fn bootstrap_complete_marker() -> PathBuf {
    crate::installer::bootstrap_complete_marker()
}

#[tauri::command]
pub async fn check_recovery_status() -> Result<RecoveryState, String> {
    let recovery_path = recovery_file_path();
    let marker_path = bootstrap_complete_marker();

    let interrupted = recovery_path.exists() && !marker_path.exists();

    if !interrupted {
        return Ok(RecoveryState {
            interrupted: false,
            last_stage: None,
            checkpoints: Vec::new(),
            can_resume: false,
            install_root: None,
        });
    }

    let content = std::fs::read_to_string(&recovery_path)
        .map_err(|e| format!("Failed to read recovery state: {e}"))?;

    let state: RecoveryState = serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse recovery state: {e}"))?;

    Ok(RecoveryState {
        can_resume: state.last_stage.is_some(),
        ..state
    })
}

#[tauri::command]
pub async fn clear_recovery_state() -> Result<(), String> {
    let path = recovery_file_path();
    if path.exists() {
        std::fs::remove_file(&path)
            .map_err(|e| format!("Failed to clear recovery state: {e}"))?;
    }
    Ok(())
}

#[tauri::command]
pub async fn check_existing_install() -> Result<bool, String> {
    let marker = bootstrap_complete_marker();
    Ok(marker.exists())
}
