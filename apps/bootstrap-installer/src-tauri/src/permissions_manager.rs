use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Permission {
    Notifications,
    AutoUpdate,
    BackgroundService,
    Startup,
    CrashReports,
    Analytics,
}

impl Permission {
    pub fn all() -> &'static [Permission] {
        &[
            Permission::Notifications,
            Permission::AutoUpdate,
            Permission::BackgroundService,
            Permission::Startup,
            Permission::CrashReports,
            Permission::Analytics,
        ]
    }

    pub fn label(&self) -> &'static str {
        match self {
            Permission::Notifications => "Notifications",
            Permission::AutoUpdate => "Auto Update",
            Permission::BackgroundService => "Background Service",
            Permission::Startup => "Launch on Startup",
            Permission::CrashReports => "Crash Reports",
            Permission::Analytics => "Analytics (Optional)",
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            Permission::Notifications => "Show desktop notifications for events and updates",
            Permission::AutoUpdate => "Automatically download and install updates",
            Permission::BackgroundService => "Keep AetherOS running in the background",
            Permission::Startup => "Launch AetherOS when you start your computer",
            Permission::CrashReports => "Send anonymous crash reports to help improve AetherOS",
            Permission::Analytics => "Help us improve by sharing anonymous usage data",
        }
    }

    pub fn default_enabled(&self) -> bool {
        matches!(self, Permission::Notifications | Permission::AutoUpdate | Permission::BackgroundService | Permission::CrashReports)
    }

    pub fn optional(&self) -> bool {
        matches!(self, Permission::Analytics)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionState {
    pub notifications: bool,
    pub auto_update: bool,
    pub background_service: bool,
    pub startup: bool,
    pub crash_reports: bool,
    pub analytics: bool,
}

impl Default for PermissionState {
    fn default() -> Self {
        Self {
            notifications: true,
            auto_update: true,
            background_service: true,
            startup: false,
            crash_reports: true,
            analytics: false,
        }
    }
}

impl PermissionState {
    pub fn to_map(&self) -> Vec<PermissionEntry> {
        vec![
            PermissionEntry { permission: Permission::Notifications, enabled: self.notifications },
            PermissionEntry { permission: Permission::AutoUpdate, enabled: self.auto_update },
            PermissionEntry { permission: Permission::BackgroundService, enabled: self.background_service },
            PermissionEntry { permission: Permission::Startup, enabled: self.startup },
            PermissionEntry { permission: Permission::CrashReports, enabled: self.crash_reports },
            PermissionEntry { permission: Permission::Analytics, enabled: self.analytics },
        ]
    }

    pub fn from_map(entries: &[PermissionEntry]) -> Self {
        let mut state = Self::default();
        for entry in entries {
            match entry.permission {
                Permission::Notifications => state.notifications = entry.enabled,
                Permission::AutoUpdate => state.auto_update = entry.enabled,
                Permission::BackgroundService => state.background_service = entry.enabled,
                Permission::Startup => state.startup = entry.enabled,
                Permission::CrashReports => state.crash_reports = entry.enabled,
                Permission::Analytics => state.analytics = entry.enabled,
            }
        }
        state
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionEntry {
    pub permission: Permission,
    pub enabled: bool,
}

fn permissions_config_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("permissions.json")
}

pub fn save_permissions(state: &PermissionState) -> Result<(), String> {
    let path = permissions_config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(state)
        .map_err(|e| format!("Serialize error: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write error: {e}"))?;
    tracing::info!("permissions saved");
    Ok(())
}

pub fn load_permissions() -> Result<PermissionState, String> {
    let path = permissions_config_path();
    if !path.exists() {
        return Ok(PermissionState::default());
    }
    let content = std::fs::read_to_string(&path).map_err(|e| format!("Read error: {e}"))?;
    serde_json::from_str(&content).map_err(|e| format!("Parse error: {e}"))
}

#[tauri::command]
pub async fn get_permission_definitions() -> Result<Vec<serde_json::Value>, String> {
    let perms: Vec<serde_json::Value> = Permission::all()
        .iter()
        .map(|p| {
            serde_json::json!({
                "id": p,
                "label": p.label(),
                "description": p.description(),
                "default": p.default_enabled(),
                "optional": p.optional(),
            })
        })
        .collect();
    Ok(perms)
}

#[tauri::command]
pub async fn get_current_permissions() -> Result<PermissionState, String> {
    load_permissions()
}

#[tauri::command]
pub async fn save_permission_state(state: PermissionState) -> Result<(), String> {
    save_permissions(&state)
}
