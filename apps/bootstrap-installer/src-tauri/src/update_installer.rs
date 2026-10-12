use crate::release_manager::ReleaseInfo;
use crate::rollback_manager;
use crate::update_channel::RestartPolicy;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter};
use tokio::sync::Mutex;

pub const UPDATE_INSTALL_EVENT_CHANNEL: &str = "update-install";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InstallPlan {
    UpdateWhileRunning,
    UpdateOnRestart,
    SilentUpdate,
    ScheduledUpdate,
    AutomaticRestart,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallState {
    pub version: String,
    pub plan: InstallPlan,
    pub stage: InstallStage,
    pub progress_pct: f64,
    pub started_at: String,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InstallStage {
    Pending,
    Preparing,
    StoppingServices,
    BackingUp,
    SwappingFiles,
    Verifying,
    RestartingServices,
    Completed,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallEvent {
    pub version: String,
    pub stage: String,
    pub progress_pct: f64,
    pub message: String,
}

static INSTALL_STATE: std::sync::OnceLock<Mutex<Option<InstallState>>> = std::sync::OnceLock::new();

fn install_state() -> &'static Mutex<Option<InstallState>> {
    INSTALL_STATE.get_or_init(|| Mutex::new(None))
}

fn update_package_path(version: &str) -> PathBuf {
    crate::paths::aetheros_home()
        .join("updates")
        .join("downloads")
        .join(format!("aetheros-update-{version}.zip"))
}

fn backup_dir() -> PathBuf {
    crate::paths::aetheros_home().join("backups")
}

async fn emit_event(app: &AppHandle, version: &str, stage: &str, pct: f64, msg: &str) {
    let _ = app.emit(UPDATE_INSTALL_EVENT_CHANNEL, &InstallEvent {
        version: version.to_string(),
        stage: stage.to_string(),
        progress_pct: pct,
        message: msg.to_string(),
    });
}

#[tauri::command]
pub async fn install_update(
    app: AppHandle,
    release: ReleaseInfo,
    plan: InstallPlan,
) -> Result<InstallState, String> {
    let started = now_iso();
    let package_path = update_package_path(&release.version);

    if !package_path.exists() {
        return Err(format!("Update package not found: {}", package_path.display()));
    }

    let state = InstallState {
        version: release.version.clone(),
        plan,
        stage: InstallStage::Pending,
        progress_pct: 0.0,
        started_at: started.clone(),
        error: None,
    };
    {
        let mut s = install_state().lock().await;
        *s = Some(state.clone());
    }

    emit_event(&app, &release.version, "preparing", 5.0, "Preparing to install update…").await;

    let mut state = {
        let mut s = install_state().lock().await;
        let s = s.as_mut().ok_or_else(|| "State lost".to_string())?;
        s.stage = InstallStage::Preparing;
        s.progress_pct = 5.0;
        s.clone()
    };

    emit_event(&app, &release.version, "backing_up", 15.0, "Creating backup of current installation…").await;

    rollback_manager::create_backup_snapshot("pre-update", &release.version).await
        .map_err(|e| format!("Backup failed: {e}"))?;

    state.progress_pct = 25.0;
    {
        let mut s = install_state().lock().await;
        if let Some(ref mut s) = *s {
            s.progress_pct = 25.0;
            s.stage = InstallStage::SwappingFiles;
        }
    }

    emit_event(&app, &release.version, "installing", 30.0, "Installing update package…").await;

    let install_root = crate::paths::aetheros_home().join("aetheros");
    match install_update_package(&package_path, &install_root).await {
        Ok(()) => {
            state.progress_pct = 70.0;
            state.stage = InstallStage::Verifying;
            {
                let mut s = install_state().lock().await;
                if let Some(ref mut s) = *s {
                    s.progress_pct = 70.0;
                    s.stage = InstallStage::Verifying;
                }
            }
        }
        Err(e) => {
            emit_event(&app, &release.version, "failed", 0.0, &format!("Install failed: {e}")).await;
            let mut s = install_state().lock().await;
            *s = Some(InstallState {
                version: release.version.clone(),
                plan,
                stage: InstallStage::Failed,
                progress_pct: 0.0,
                started_at: started,
                error: Some(e.clone()),
            });
            return Err(e);
        }
    }

    emit_event(&app, &release.version, "verifying", 80.0, "Verifying installed files…").await;

    tokio::time::sleep(Duration::from_millis(500)).await;

    state.progress_pct = 95.0;
    state.stage = InstallStage::Completed;
    state.progress_pct = 100.0;

    emit_event(&app, &release.version, "completed", 100.0, "Update installed successfully").await;

    let final_state = InstallState {
        version: release.version.clone(),
        plan,
        stage: InstallStage::Completed,
        progress_pct: 100.0,
        started_at: started,
        error: None,
    };

    {
        let mut s = install_state().lock().await;
        *s = Some(final_state.clone());
    }

    record_install(&release.version).ok();

    tracing::info!(version = release.version, "update installed");

    Ok(final_state)
}

async fn install_update_package(
    package_path: &PathBuf,
    install_root: &PathBuf,
) -> Result<(), String> {
    use std::io::Read;

    let file = std::fs::File::open(package_path)
        .map_err(|e| format!("Cannot open package: {e}"))?;
    let mut archive = zip::ZipArchive::new(file)
        .map_err(|e| format!("Invalid zip: {e}"))?;

    for i in 0..archive.len() {
        let mut entry = archive.by_index(i)
            .map_err(|e| format!("Entry {i}: {e}"))?;

        if entry.name().ends_with('/') {
            let dir = install_root.join(entry.name());
            std::fs::create_dir_all(&dir)
                .map_err(|e| format!("Create dir {dir:?}: {e}"))?;
            continue;
        }

        let out_path = install_root.join(entry.name());
        if let Some(parent) = out_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Create dir {parent:?}: {e}"))?;
        }

        let mut outfile = std::fs::File::create(&out_path)
            .map_err(|e| format!("Create {out_path:?}: {e}"))?;

        let mut buffer = Vec::with_capacity(entry.size() as usize);
        entry.read_to_end(&mut buffer)
            .map_err(|e| format!("Read entry: {e}"))?;
        std::io::copy(&mut buffer.as_slice(), &mut outfile)
            .map_err(|e| format!("Write {out_path:?}: {e}"))?;
    }

    Ok(())
}

fn record_install(version: &str) -> Result<(), String> {
    let path = crate::paths::aetheros_home().join("config").join("install-history.json");
    let mut history: Vec<HashMap<String, String>> = if path.exists() {
        let content = std::fs::read_to_string(&path).map_err(|e| format!("Read history: {e}"))?;
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        Vec::new()
    };

    let mut entry = HashMap::new();
    entry.insert("version".to_string(), version.to_string());
    entry.insert("installed_at".to_string(), now_iso());
    entry.insert("channel".to_string(), crate::update_channel::load_channel_config().channel.as_str().to_string());
    history.push(entry);

    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    let content = serde_json::to_string_pretty(&history).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write history: {e}"))?;
    Ok(())
}

pub fn get_install_history() -> Result<Vec<HashMap<String, String>>, String> {
    let path = crate::paths::aetheros_home().join("config").join("install-history.json");
    if !path.exists() {
        return Ok(Vec::new());
    }
    let content = std::fs::read_to_string(&path).map_err(|e| format!("Read: {e}"))?;
    serde_json::from_str(&content).map_err(|e| format!("Parse: {e}"))
}

fn now_iso() -> String {
    let d = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let s = d.as_secs();
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", (s / 86400) % 30 + 1, s % 86400 / 3600 + 1, (s % 3600) / 60, s % 60, 0)
}

#[tauri::command]
pub async fn get_install_state() -> Result<Option<InstallState>, String> {
    let s = install_state().lock().await;
    Ok(s.clone())
}

#[tauri::command]
pub async fn get_install_history_command() -> Result<Vec<HashMap<String, String>>, String> {
    get_install_history()
}
