use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum UpdateChannel {
    Stable,
    Beta,
    Nightly,
    Development,
    Enterprise,
}

impl UpdateChannel {
    pub fn as_str(&self) -> &'static str {
        match self {
            UpdateChannel::Stable => "stable",
            UpdateChannel::Beta => "beta",
            UpdateChannel::Nightly => "nightly",
            UpdateChannel::Development => "development",
            UpdateChannel::Enterprise => "enterprise",
        }
    }

    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "beta" => UpdateChannel::Beta,
            "nightly" => UpdateChannel::Nightly,
            "development" | "dev" => UpdateChannel::Development,
            "enterprise" => UpdateChannel::Enterprise,
            _ => UpdateChannel::Stable,
        }
    }

    pub fn update_interval_minutes(&self) -> u64 {
        match self {
            UpdateChannel::Stable => 1440,
            UpdateChannel::Beta => 360,
            UpdateChannel::Nightly => 60,
            UpdateChannel::Development => 30,
            UpdateChannel::Enterprise => 1440,
        }
    }

    pub fn accepts_prerelease(&self) -> bool {
        matches!(self, UpdateChannel::Nightly | UpdateChannel::Development)
    }

    pub fn description(&self) -> &'static str {
        match self {
            UpdateChannel::Stable => "Stable — thoroughly tested releases",
            UpdateChannel::Beta => "Beta — pre-release features with testing",
            UpdateChannel::Nightly => "Nightly — latest builds, may be unstable",
            UpdateChannel::Development => "Development — bleeding-edge for contributors",
            UpdateChannel::Enterprise => "Enterprise — managed rollouts with policy controls",
        }
    }
}

impl Default for UpdateChannel {
    fn default() -> Self {
        UpdateChannel::Stable
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateChannelConfig {
    pub channel: UpdateChannel,
    pub auto_update: bool,
    pub notify_only: bool,
    pub bandwidth_limit_kbps: Option<u64>,
    pub scheduled_time: Option<String>,
    pub restart_policy: RestartPolicy,
    pub include_prerelease: bool,
    pub allow_downgrade: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RestartPolicy {
    Always,
    Sometime,
    Never,
}

impl Default for UpdateChannelConfig {
    fn default() -> Self {
        Self {
            channel: UpdateChannel::Stable,
            auto_update: true,
            notify_only: false,
            bandwidth_limit_kbps: None,
            scheduled_time: None,
            restart_policy: RestartPolicy::Sometime,
            include_prerelease: false,
            allow_downgrade: false,
        }
    }
}

fn config_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("update-channel.json")
}

pub fn load_channel_config() -> UpdateChannelConfig {
    let path = config_path();
    if path.exists() {
        if let Ok(content) = std::fs::read_to_string(&path) {
            if let Ok(config) = serde_json::from_str(&content) {
                return config;
            }
        }
    }
    UpdateChannelConfig::default()
}

pub fn save_channel_config(config: &UpdateChannelConfig) -> Result<(), String> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(config).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

#[tauri::command]
pub async fn get_update_channel() -> Result<UpdateChannelConfig, String> {
    Ok(load_channel_config())
}

#[tauri::command]
pub async fn set_update_channel(config: UpdateChannelConfig) -> Result<(), String> {
    save_channel_config(&config)
}

#[tauri::command]
pub async fn get_available_channels() -> Result<Vec<UpdateChannel>, String> {
    Ok(vec![
        UpdateChannel::Stable,
        UpdateChannel::Beta,
        UpdateChannel::Nightly,
        UpdateChannel::Development,
        UpdateChannel::Enterprise,
    ])
}
