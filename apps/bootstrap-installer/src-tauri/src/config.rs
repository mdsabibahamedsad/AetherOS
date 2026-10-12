use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Arc;
use tauri::State;

use crate::AppState;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallConfig {
    pub install_location: String,
    pub create_shortcuts: bool,
    pub install_desktop_app: bool,
    pub install_cli: bool,
    pub auto_launch: bool,
}

impl Default for InstallConfig {
    fn default() -> Self {
        Self {
            install_location: default_install_location(),
            create_shortcuts: true,
            install_desktop_app: true,
            install_cli: true,
            auto_launch: true,
        }
    }
}

fn default_install_location() -> String {
    crate::paths::aetheros_home()
        .join("aetheros")
        .to_string_lossy()
        .into_owned()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallConfigState {
    pub config: InstallConfig,
}

impl InstallConfigState {
    pub fn new() -> Self {
        Self {
            config: InstallConfig::default(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocationCheck {
    pub valid: bool,
    pub writable: bool,
    pub exists: bool,
    pub free_space: Option<String>,
    pub message: String,
}

#[tauri::command]
pub async fn get_install_config(
    state: State<'_, Arc<AppState>>,
) -> Result<InstallConfig, String> {
    let guard = state.config.lock().await;
    Ok(guard.config.clone())
}

#[tauri::command]
pub async fn set_install_location(
    state: State<'_, Arc<AppState>>,
    location: String,
) -> Result<(), String> {
    let mut guard = state.config.lock().await;
    guard.config.install_location = location;
    Ok(())
}

#[tauri::command]
pub async fn set_components(
    state: State<'_, Arc<AppState>>,
    desktop_app: bool,
    cli: bool,
    shortcuts: bool,
    auto_launch: bool,
) -> Result<(), String> {
    let mut guard = state.config.lock().await;
    guard.config.install_desktop_app = desktop_app;
    guard.config.install_cli = cli;
    guard.config.create_shortcuts = shortcuts;
    guard.config.auto_launch = auto_launch;
    Ok(())
}

#[tauri::command]
pub async fn validate_install_location(location: String) -> Result<LocationCheck, String> {
    let path = PathBuf::from(&location);

    let exists = path.exists();

    let writable = if exists {
        std::fs::metadata(&path)
            .map(|m| !m.permissions().readonly())
            .unwrap_or(false)
    } else if let Some(parent) = path.parent() {
        let test_file = parent.join(".aetheros-write-test");
        match std::fs::write(&test_file, "") {
            Ok(_) => {
                let _ = std::fs::remove_file(&test_file);
                true
            }
            Err(_) => false,
        }
    } else {
        false
    };

    let free_space = None;

    let valid = writable;
    let message = if valid {
        "Location is valid and writable".to_string()
    } else if exists {
        "Location exists but is not writable".to_string()
    } else {
        "Parent directory does not exist or is not writable".to_string()
    };

    Ok(LocationCheck {
        valid,
        writable,
        exists,
        free_space,
        message,
    })
}
