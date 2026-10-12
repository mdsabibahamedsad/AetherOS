use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Emitter};

pub const INSTALL_EVENT_CHANNEL: &str = "install";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallProgress {
    pub phase: String,
    pub detail: String,
    pub percent: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallResult {
    pub success: bool,
    pub install_root: String,
    pub version: Option<String>,
    pub errors: Vec<String>,
}

pub const INSTALLED_APP_DIR: &str = "aetheros";

pub fn install_root() -> PathBuf {
    crate::paths::aetheros_home().join(INSTALLED_APP_DIR)
}

pub fn bootstrap_complete_marker() -> PathBuf {
    install_root().join(".aetheros-bootstrap-complete")
}

pub async fn create_directory_structure(aetheros_home: &Path, app: Option<&AppHandle>) -> Result<(), String> {
    let dirs = [
        aetheros_home.join("logs"),
        aetheros_home.join("data"),
        aetheros_home.join("config"),
        aetheros_home.join("cache"),
        aetheros_home.join("profiles"),
        aetheros_home.join(INSTALLED_APP_DIR),
        aetheros_home.join("tmp"),
    ];

    let total = dirs.len();
    for (i, dir) in dirs.iter().enumerate() {
        std::fs::create_dir_all(dir)
            .map_err(|e| format!("Failed to create directory {}: {e}", dir.display()))?;

        if let Some(_app) = app {
            emit_progress(
                _app,
                "directories",
                &format!("Created {}", dir.file_name().unwrap_or_default().to_string_lossy()),
                (i + 1) as f64 / total as f64 * 100.0,
            );
        }
    }

    tracing::info!(?dirs, "directory structure created");
    Ok(())
}

pub async fn copy_installed_files(
    extract_dir: &Path,
    dest_dir: &Path,
    app: Option<&AppHandle>,
) -> Result<u64, String> {
    if !extract_dir.exists() {
        return Err(format!(
            "Extraction directory does not exist: {}",
            extract_dir.display()
        ));
    }

    if !dest_dir.exists() {
        std::fs::create_dir_all(dest_dir)
            .map_err(|e| format!("Failed to create destination {}: {e}", dest_dir.display()))?;
    }

    let mut total_files = 0u64;
    let entries = collect_entries(extract_dir);
    let total = entries.len();

    for (i, (relative, is_dir)) in entries.iter().enumerate() {
        let target = dest_dir.join(relative);
        let source = extract_dir.join(relative);

        if *is_dir {
            let _ = std::fs::create_dir_all(&target);
        } else {
            if let Some(parent) = target.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            match std::fs::copy(&source, &target) {
                Ok(_) => {
                    total_files += 1;
                }
                Err(e) => {
                    return Err(format!(
                        "Failed to copy {} to {}: {e}",
                        source.display(),
                        target.display()
                    ));
                }
            }
        }

        if let Some(_app) = app {
            if i % 20 == 0 || i == total - 1 {
                emit_progress(
                    _app,
                    "install_files",
                    &relative.to_string_lossy(),
                    (i + 1) as f64 / total as f64 * 100.0,
                );
            }
        }
    }

    tracing::info!(
        files = total_files,
        from = %extract_dir.display(),
        to = %dest_dir.display(),
        "file copy complete"
    );

    Ok(total_files)
}

fn collect_entries(dir: &Path) -> Vec<(PathBuf, bool)> {
    let mut entries = Vec::new();
    let base = dir.to_path_buf();
    collect_entries_recursive(dir, &base, &mut entries);
    entries
}

fn collect_entries_recursive(
    dir: &Path,
    base: &Path,
    entries: &mut Vec<(PathBuf, bool)>,
) {
    if let Ok(reader) = std::fs::read_dir(dir) {
        for entry in reader.flatten() {
            let path = entry.path();
            let is_dir = path.is_dir();
            let relative = path
                .strip_prefix(base)
                .unwrap_or(&path)
                .to_path_buf();
            if !relative.as_os_str().is_empty() {
                entries.push((relative, is_dir));
            }
            if is_dir {
                collect_entries_recursive(&path, base, entries);
            }
        }
    }
}

pub async fn create_default_config(aetheros_home: &Path) -> Result<(), String> {
    let config_dir = aetheros_home.join("config");
    let config_path = config_dir.join("config.yaml");

    if config_path.exists() {
        return Ok(());
    }

    std::fs::create_dir_all(&config_dir)
        .map_err(|e| format!("Failed to create config directory: {e}"))?;

    let config_content = r##"# Aetheros Configuration
# Created by Aetheros Setup

model:
  provider: ""
  model: ""

agent:
  max_iterations: 90

terminal:
  shell: ""

display:
  skin: "default"

logging:
  level: "info"
"##;

    std::fs::write(&config_path, config_content)

        .map_err(|e| format!("Failed to write default config: {e}"))?;

    Ok(())
}

pub async fn create_user_profile(aetheros_home: &Path) -> Result<(), String> {
    let profiles_dir = aetheros_home.join("profiles");
    let default_profile = profiles_dir.join("default");

    if default_profile.exists() {
        return Ok(());
    }

    std::fs::create_dir_all(&default_profile)
        .map_err(|e| format!("Failed to create default profile: {e}"))?;

    let profile_config = format!(
        r##"profile:
  name: "default"
  created_at: {}
  version: "{}"
"##,
        chrono_now(),
        env!("CARGO_PKG_VERSION")
    );

    std::fs::write(default_profile.join("profile.yaml"), &profile_config)
        .map_err(|e| format!("Failed to write profile config: {e}"))?;

    Ok(())
}

pub async fn write_bootstrap_marker(_aetheros_home: &Path, version: &str) -> Result<(), String> {
    let marker = bootstrap_complete_marker();
    if let Some(parent) = marker.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create marker directory: {e}"))?;
    }

    let content = serde_json::json!({
        "version": version,
        "installed_at": chrono_now(),
        "installer_version": env!("CARGO_PKG_VERSION"),
    });

    std::fs::write(&marker, serde_json::to_string_pretty(&content).unwrap())
        .map_err(|e| format!("Failed to write bootstrap marker: {e}"))?;

    tracing::info!(
        ?marker,
        version,
        "bootstrap complete marker written"
    );

    Ok(())
}

pub async fn create_workspace_dirs(aetheros_home: &Path) -> Result<(), String> {
    let dirs = [
        aetheros_home.join("knowledge"),
        aetheros_home.join("projects"),
        aetheros_home.join("extensions"),
    ];

    for dir in &dirs {
        std::fs::create_dir_all(dir)
            .map_err(|e| format!("Failed to create workspace directory {}: {e}", dir.display()))?;
    }

    Ok(())
}

fn emit_progress(app: &AppHandle, phase: &str, detail: &str, percent: f64) {
    let _ = app.emit(
        "install",
        &InstallProgress {
            phase: phase.to_string(),
            detail: detail.to_string(),
            percent,
        },
    );
}

fn chrono_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    duration.as_secs().to_string()
}
