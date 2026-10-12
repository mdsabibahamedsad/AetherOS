use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// AetherOS is a self-contained application. The installer bundles everything
/// needed within the installer executable. No GitHub API calls are made
/// during installation or updates. This module is preserved for API compatibility
/// but returns static/simple responses.

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ReleaseChannel {
    Stable,
    Beta,
    Nightly,
    Specific(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReleaseAsset {
    pub version: String,
    pub url: String,
    pub filename: String,
    pub size: u64,
    pub sha256: Option<String>,
    pub channel: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReleaseInfo {
    pub version: String,
    pub channel: String,
    pub published_at: String,
    pub body: String,
    pub assets: Vec<ReleaseAsset>,
}

/// Self-contained installer: returns a static release indicating the app
/// is already bundled and no download is needed.
pub async fn fetch_release_info(_channel: &ReleaseChannel) -> Result<ReleaseInfo, String> {
    Ok(ReleaseInfo {
        version: env!("CARGO_PKG_VERSION").to_string(),
        channel: "self-contained".to_string(),
        published_at: String::new(),
        body: "AetherOS self-contained installer. All files are bundled in the installer executable.".to_string(),
        assets: vec![],
    })
}

pub fn package_download_dir() -> PathBuf {
    crate::paths::aetheros_home().join("bootstrap-cache").join("packages")
}

pub fn package_path(version: &str) -> PathBuf {
    package_download_dir().join(format!("AetherOS-{version}.zip"))
}

pub fn extract_temp_dir(version: &str) -> PathBuf {
    crate::paths::aetheros_home()
        .join("bootstrap-cache")
        .join(format!("extract-{version}"))
}

#[tauri::command]
pub async fn fetch_release_info_command(
    _channel: Option<String>,
    _version: Option<String>,
) -> Result<ReleaseInfo, String> {
    fetch_release_info(&ReleaseChannel::Stable).await
}
