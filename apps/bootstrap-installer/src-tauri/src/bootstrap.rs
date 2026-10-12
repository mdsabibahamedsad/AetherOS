use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, State};
use tokio::sync::{mpsc, Mutex};

use crate::events::{BootstrapEvent, LogStream, StageInfo, StageState};
use crate::install_modes::{InstallMode, InstallModeConfig};
use crate::package_format::PackageManifest;
use crate::package_manager;
use crate::{extract, installer, package, paths};
use crate::AppState;

#[derive(Debug, Deserialize)]
pub struct StartBootstrapArgs {
    pub commit: Option<String>,
    pub branch: Option<String>,
    #[serde(default = "default_true")]
    pub include_desktop: bool,
    pub aetheros_home: Option<String>,
    pub release_channel: Option<String>,
    pub release_version: Option<String>,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Serialize)]
pub struct BootstrapStatus {
    pub running: bool,
    pub completed: bool,
    pub install_root: Option<String>,
    pub last_error: Option<String>,
}

pub struct BootstrapHandle {
    pub cancel_tx: mpsc::Sender<()>,
    pub started_at: Instant,
    pub status: BootstrapStatus,
}

#[tauri::command]
pub async fn start_bootstrap(
    app: AppHandle,
    state: State<'_, Arc<AppState>>,
    args: StartBootstrapArgs,
) -> Result<(), String> {
    let mut guard = state.bootstrap.lock().await;
    if let Some(h) = guard.as_ref() {
        if h.status.running {
            return Err("Bootstrap is already running".into());
        }
    }

    let (cancel_tx, cancel_rx) = mpsc::channel::<()>(1);
    let handle = BootstrapHandle {
        cancel_tx,
        started_at: Instant::now(),
        status: BootstrapStatus {
            running: true,
            completed: false,
            install_root: None,
            last_error: None,
        },
    };
    *guard = Some(handle);
    drop(guard);

    let app_for_task = app.clone();
    let state_for_task = state.inner().clone();
    let cancel_rx = Arc::new(Mutex::new(Some(cancel_rx)));

    tokio::spawn(async move {
        let result = run_self_contained_bootstrap(app_for_task.clone(), args, cancel_rx).await;

        let mut guard = state_for_task.bootstrap.lock().await;
        if let Some(h) = guard.as_mut() {
            h.status.running = false;
            match &result {
                Ok(install_root) => {
                    h.status.completed = true;
                    h.status.install_root = Some(install_root.clone());
                    h.status.last_error = None;
                }
                Err(err) => {
                    h.status.completed = false;
                    h.status.last_error = Some(err.to_string());
                }
            }
        }
    });

    Ok(())
}

#[tauri::command]
pub async fn cancel_bootstrap(state: State<'_, Arc<AppState>>) -> Result<(), String> {
    let guard = state.bootstrap.lock().await;
    if let Some(h) = guard.as_ref() {
        let _ = h.cancel_tx.try_send(());
    }
    Ok(())
}

#[tauri::command]
pub async fn get_bootstrap_status(
    state: State<'_, Arc<AppState>>,
) -> Result<BootstrapStatus, String> {
    let guard = state.bootstrap.lock().await;
    Ok(match guard.as_ref() {
        Some(h) => BootstrapStatus {
            running: h.status.running,
            completed: h.status.completed,
            install_root: h.status.install_root.clone(),
            last_error: h.status.last_error.clone(),
        },
        None => BootstrapStatus {
            running: false,
            completed: false,
            install_root: None,
            last_error: None,
        },
    })
}

#[tauri::command]
pub async fn launch_aetheros_desktop(
    app: AppHandle,
    install_root: String,
) -> Result<(), String> {
    let install_root = PathBuf::from(&install_root);
    let exe_path = resolve_aetheros_desktop_exe(&install_root).ok_or_else(|| {
        format!(
            "Couldn't find AetherOS desktop at {}. The installation may be incomplete. \
             Run the installer again to repair.",
            install_root.join("apps").join("desktop").join("release").display()
        )
    })?;

    tracing::info!(?exe_path, "launching AetherOS desktop");

    let mut cmd = desktop_launch_command(&exe_path, &install_root);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0000_0008);
    }

    cmd.spawn().map_err(|e| {
        format!("failed to launch {}: {e}", exe_path.display())
    })?;

    tokio::time::sleep(std::time::Duration::from_millis(150)).await;
    app.exit(0);
    Ok(())
}

pub(crate) fn resolve_aetheros_desktop_exe(install_root: &std::path::Path) -> Option<PathBuf> {
    let release_dir = install_root.join("apps").join("desktop").join("release");
    let candidates: &[(&str, &str)] = if cfg!(target_os = "windows") {
        &[
            ("win-unpacked", "Aetheros.exe"),
            ("win-arm64-unpacked", "Aetheros.exe"),
        ]
    } else if cfg!(target_os = "macos") {
        &[
            ("mac/Aetheros.app/Contents/MacOS", "Aetheros"),
            ("mac-arm64/Aetheros.app/Contents/MacOS", "Aetheros"),
        ]
    } else {
        &[("linux-unpacked", "aetheros")]
    };
    for (subdir, exe) in candidates {
        let p = release_dir.join(subdir).join(exe);
        if p.exists() {
            return Some(p);
        }
    }
    None
}

pub(crate) fn resolve_aetheros_desktop_app(install_root: &std::path::Path) -> Option<PathBuf> {
    let exe = resolve_aetheros_desktop_exe(install_root)?;
    #[cfg(target_os = "macos")]
    {
        let app = exe.parent()?.parent()?.parent()?.to_path_buf();
        if app.extension().and_then(|e| e.to_str()) == Some("app") && app.is_dir() {
            return Some(app);
        }
    }
    #[cfg(not(target_os = "macos"))]
    {
        return Some(exe);
    }
    #[allow(unreachable_code)]
    None
}

pub(crate) fn aetheros_is_installed(install_root: &std::path::Path) -> bool {
    installer::bootstrap_complete_marker().exists()
        && resolve_aetheros_desktop_exe(install_root).is_some()
}

pub(crate) fn spawn_installed_desktop(install_root: &std::path::Path) -> std::io::Result<()> {
    let exe = resolve_aetheros_desktop_exe(install_root).ok_or_else(|| {
        std::io::Error::new(std::io::ErrorKind::NotFound, "no built AetherOS desktop app")
    })?;
    let mut cmd = desktop_launch_command_std(&exe, install_root);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0000_0008);
    }
    cmd.spawn().map(|_child| ())
}

#[cfg(target_os = "macos")]
pub(crate) fn open_macos_app_detached(app_bundle: &std::path::Path) -> std::io::Result<()> {
    let mut cmd = std::process::Command::new("/usr/bin/open");
    cmd.arg(app_bundle);
    cmd.current_dir(crate::paths::aetheros_home());
    cmd.spawn().map(|_child| ())
}

#[cfg(target_os = "macos")]
fn app_bundle_for_exe(exe: &std::path::Path) -> Option<PathBuf> {
    let app = exe.parent()?.parent()?.parent()?.to_path_buf();
    if app.extension().and_then(|e| e.to_str()) == Some("app") && app.is_dir() {
        Some(app)
    } else {
        None
    }
}

fn desktop_launch_command(
    exe_path: &std::path::Path,
    install_root: &std::path::Path,
) -> tokio::process::Command {
    #[cfg(target_os = "macos")]
    {
        if let Some(app_bundle) = app_bundle_for_exe(exe_path) {
            let mut cmd = tokio::process::Command::new("/usr/bin/open");
            cmd.arg(app_bundle);
            cmd.current_dir(crate::paths::aetheros_home());
            return cmd;
        }
    }
    let mut cmd = tokio::process::Command::new(exe_path);
    cmd.current_dir(exe_path.parent().unwrap_or(install_root));
    cmd
}

fn desktop_launch_command_std(
    exe_path: &std::path::Path,
    install_root: &std::path::Path,
) -> std::process::Command {
    #[cfg(target_os = "macos")]
    {
        if let Some(app_bundle) = app_bundle_for_exe(exe_path) {
            let mut cmd = std::process::Command::new("/usr/bin/open");
            cmd.arg(app_bundle);
            cmd.current_dir(crate::paths::aetheros_home());
            return cmd;
        }
    }
    let mut cmd = std::process::Command::new(exe_path);
    cmd.current_dir(exe_path.parent().unwrap_or(install_root));
    cmd
}

/// Self-contained bootstrap that installs AetherOS from bundled resources.
/// No network access, no GitHub API calls, no repository cloning.
/// The installer executable contains everything needed to install AetherOS.
pub async fn run_package_bootstrap(
    app: AppHandle,
    mode: InstallMode,
    packages: Vec<PackageManifest>,
    offline_bundle_path: Option<String>,
) -> Result<String> {
    let install_root = installer::install_root();
    let mode_config = InstallModeConfig::for_mode(mode);

    let stages = vec![
        StageInfo {
            name: "resolve_packages".to_string(),
            title: "Resolving packages".to_string(),
            category: "install".to_string(),
            needs_user_input: false,
        },
        StageInfo {
            name: "install_packages".to_string(),
            title: "Installing AetherOS".to_string(),
            category: "install".to_string(),
            needs_user_input: false,
        },
        StageInfo {
            name: "configure".to_string(),
            title: "Configuring AetherOS".to_string(),
            category: "install".to_string(),
            needs_user_input: false,
        },
        StageInfo {
            name: "shortcuts".to_string(),
            title: "Creating shortcuts".to_string(),
            category: "install".to_string(),
            needs_user_input: false,
        },
    ];

    emit_event(&app, BootstrapEvent::Manifest {
        stages: stages.clone(),
        protocol_version: Some(2),
    });

    // Stage 1: Resolve packages
    run_stage(&app, &stages[0], &Arc::new(Mutex::new(None)), || async {
        tracing::info!("Resolving {} packages for {:?} mode", packages.len(), mode);
        if packages.is_empty() {
            return Err("No packages specified for installation".to_string());
        }
        Ok(())
    }).await?;

    // Stage 2: Install packages using PackageManager (from bundled resources)
    run_stage(&app, &stages[1], &Arc::new(Mutex::new(None)), || async {
        let ops: Vec<package_manager::PackageOperation> = packages
            .iter()
            .map(|m| package_manager::PackageOperation {
                manifest: m.clone(),
                status: package_manager::PackageStatus::Pending,
                download_url: None,
                local_path: None,
                size: m.size,
            })
            .collect();

        let mut pm = package_manager::PackageManager::new(install_root.clone(), mode_config.clone())
            .with_operations(ops);
        pm.resolve_operations().await?;

        let result = pm.run_installation(app.clone()).await;
        if !result.success {
            let errs = result.errors.join("; ");
            return Err(format!("Package installation failed: {errs}"));
        }
        Ok(())
    }).await?;

    // Stage 3: Configure
    run_stage(&app, &stages[2], &Arc::new(Mutex::new(None)), || async {
        let aetheros_home = crate::paths::aetheros_home();
        installer::create_default_config(&aetheros_home).await?;
        installer::create_user_profile(&aetheros_home).await?;
        installer::create_workspace_dirs(&aetheros_home).await?;
        installer::write_bootstrap_marker(&aetheros_home, "self-contained").await?;
        if let Err(err) = crate::paths::copy_self_to_aetheros_home() {
            tracing::warn!(?err, "failed to copy installer (non-fatal)");
        }
        Ok(())
    }).await?;

    // Stage 4: Create Shortcuts
    run_stage(&app, &stages[3], &Arc::new(Mutex::new(None)), || async {
        let shortcut_options = crate::shortcuts::ShortcutOptions {
            start_menu: true,
            desktop: true,
            taskbar: false,
            path_alias: false,
        };
        crate::shortcuts::create_installer_shortcuts(shortcut_options).await?;
        Ok(())
    }).await?;

    emit_event(&app, BootstrapEvent::Complete {
        install_root: install_root.to_string_lossy().into_owned(),
        marker: None,
    });

    Ok(install_root.to_string_lossy().into_owned())
}

#[tauri::command]
pub async fn start_package_bootstrap(
    app: AppHandle,
    state: State<'_, Arc<AppState>>,
    mode: InstallMode,
    packages: Vec<PackageManifest>,
    offline_bundle_path: Option<String>,
) -> Result<(), String> {
    let mut guard = state.bootstrap.lock().await;
    if let Some(h) = guard.as_ref() {
        if h.status.running {
            return Err("Bootstrap is already running".into());
        }
    }

    let (cancel_tx, _cancel_rx) = mpsc::channel::<()>(1);
    let handle = BootstrapHandle {
        cancel_tx,
        started_at: Instant::now(),
        status: BootstrapStatus {
            running: true,
            completed: false,
            install_root: None,
            last_error: None,
        },
    };
    *guard = Some(handle);
    drop(guard);

    let app_for_task = app.clone();
    let state_for_task = state.inner().clone();

    tokio::spawn(async move {
        let result = run_package_bootstrap(
            app_for_task.clone(),
            mode,
            packages,
            offline_bundle_path,
        ).await;

        let mut guard = state_for_task.bootstrap.lock().await;
        if let Some(h) = guard.as_mut() {
            h.status.running = false;
            match &result {
                Ok(install_root) => {
                    h.status.completed = true;
                    h.status.install_root = Some(install_root.clone());
                    h.status.last_error = None;
                }
                Err(err) => {
                    h.status.completed = false;
                    h.status.last_error = Some(err.to_string());
                }
            }
        }
    });

    Ok(())
}

/// Self-contained bootstrap installation from bundled resources.
/// Extracts and installs AetherOS from resources bundled within the installer.
/// No network fetch, no GitHub API, no repository cloning.
async fn run_self_contained_bootstrap(
    app: AppHandle,
    args: StartBootstrapArgs,
    cancel_rx_holder: Arc<Mutex<Option<mpsc::Receiver<()>>>>,
) -> Result<String> {
    let aetheros_home = paths::aetheros_home();
    let install_root = installer::install_root();

    let stages = vec![
        StageInfo {
            name: "extract".to_string(),
            title: "Extracting AetherOS".to_string(),
            category: "install".to_string(),
            needs_user_input: false,
        },
        StageInfo {
            name: "install".to_string(),
            title: "Installing AetherOS".to_string(),
            category: "install".to_string(),
            needs_user_input: false,
        },
        StageInfo {
            name: "configure".to_string(),
            title: "Configuring AetherOS".to_string(),
            category: "install".to_string(),
            needs_user_input: false,
        },
        StageInfo {
            name: "shortcuts".to_string(),
            title: "Creating shortcuts".to_string(),
            category: "install".to_string(),
            needs_user_input: false,
        },
    ];

    emit_event(&app, BootstrapEvent::Manifest {
        stages: stages.clone(),
        protocol_version: Some(2),
    });

    let emit_log = |line: &str| {
        emit_event(&app, BootstrapEvent::Log {
            stage: None,
            line: line.to_string(),
            stream: LogStream::Stdout,
        });
        tracing::info!(target: "bootstrap.log", "{line}");
    };

    emit_log("[bootstrap] AetherOS self-contained installer starting");
    emit_log("[bootstrap] extracting bundled application files");

    // Stage 1: Extract bundled application resources
    run_stage(&app, &stages[0], &cancel_rx_holder, || async {
        let bundle_path = paths::bundled_app_archive();
        if bundle_path.exists() {
            emit_log(&format!(
                "[bootstrap] extracting from bundled archive: {}",
                bundle_path.display()
            ));

            let extract_dir = aetheros_home.join("tmp").join("extract");
            std::fs::create_dir_all(&extract_dir)
                .map_err(|e| format!("Failed to create extract directory: {e}"))?;

            extract::extract_zip(&app, &bundle_path, &extract_dir).await?;

            let entry_count = extract::validate_extraction(&extract_dir, None)
                .map_err(|e| format!("{e}"))?;
            emit_log(&format!("[bootstrap] extracted {entry_count} entries"));

            let extracted_app = find_extracted_root(&extract_dir);

            emit_log(&format!(
                "[bootstrap] installing to {}",
                install_root.display()
            ));

            installer::copy_installed_files(&extracted_app, &install_root, Some(&app)).await?;
        } else {
            emit_log("[bootstrap] no bundled archive found; using pre-installed layout");
            emit_log("[bootstrap] creating directory structure from bundled resources");

            std::fs::create_dir_all(&install_root)
                .map_err(|e| format!("Failed to create install directory: {e}"))?;
        }

        installer::create_directory_structure(&aetheros_home, Some(&app)).await?;

        Result::<_, String>::Ok(())
    })
    .await?;

    // Stage 2: Install/Configure runtime
    run_stage(&app, &stages[1], &cancel_rx_holder, || async {
        emit_log("[bootstrap] setting up AetherOS");
        Ok(())
    })
    .await?;

    // Stage 3: Configure
    run_stage(&app, &stages[2], &cancel_rx_holder, || async {
        emit_log("[bootstrap] creating configuration");

        installer::create_default_config(&aetheros_home).await?;
        installer::create_user_profile(&aetheros_home).await?;
        installer::create_workspace_dirs(&aetheros_home).await?;
        installer::write_bootstrap_marker(&aetheros_home, "self-contained").await?;

        if let Err(err) = paths::copy_self_to_aetheros_home() {
            tracing::warn!(?err, "failed to copy installer (non-fatal)");
            emit_log(&format!("[bootstrap] warning: could not stage updater binary: {err}"));
        }

        emit_log("[bootstrap] configuration complete");
        Result::<_, String>::Ok(())
    })
    .await?;

    // Stage 4: Create Shortcuts
    run_stage(&app, &stages[3], &cancel_rx_holder, || async {
        emit_log("[bootstrap] creating desktop shortcuts");

        let shortcut_options = crate::shortcuts::ShortcutOptions {
            start_menu: true,
            desktop: true,
            taskbar: false,
            path_alias: false,
        };
        let results = crate::shortcuts::create_installer_shortcuts(shortcut_options).await?;
        for r in &results {
            let status = if r.created { "created" } else { "failed" };
            emit_log(&format!("[bootstrap] shortcut {status}: {} ({})", r.name, r.location));
        }

        Result::<_, String>::Ok(())
    })
    .await?;

    // Complete
    emit_event(&app, BootstrapEvent::Complete {
        install_root: install_root.to_string_lossy().into_owned(),
        marker: Some(serde_json::json!({
            "version": "self-contained",
            "channel": "stable",
        })),
    });

    Ok(install_root.to_string_lossy().into_owned())
}

fn find_extracted_root(extract_dir: &std::path::Path) -> PathBuf {
    if let Ok(entries) = std::fs::read_dir(extract_dir) {
        let dirs: Vec<_> = entries
            .flatten()
            .filter(|e| e.path().is_dir())
            .collect();
        if dirs.len() == 1 {
            return dirs[0].path();
        }
    }
    extract_dir.to_path_buf()
}

async fn run_stage<F, Fut>(
    app: &AppHandle,
    stage: &StageInfo,
    cancel_rx_holder: &Arc<Mutex<Option<mpsc::Receiver<()>>>>,
    f: F,
) -> Result<(), anyhow::Error>
where
    F: FnOnce() -> Fut,
    Fut: std::future::Future<Output = Result<(), String>>,
{
    run_stage_inner(app, stage, cancel_rx_holder, || async {
        f().await?;
        Ok(())
    })
    .await
    .map(|_| ())
}

async fn run_stage_with_result<T, F, Fut>(
    app: &AppHandle,
    stage: &StageInfo,
    cancel_rx_holder: &Arc<Mutex<Option<mpsc::Receiver<()>>>>,
    f: F,
) -> Result<T, anyhow::Error>
where
    F: FnOnce() -> Fut,
    Fut: std::future::Future<Output = Result<T, String>>,
    T: Send + 'static,
{
    run_stage_inner(app, stage, cancel_rx_holder, f).await
}

async fn run_stage_inner<T, F, Fut>(
    app: &AppHandle,
    stage: &StageInfo,
    cancel_rx_holder: &Arc<Mutex<Option<mpsc::Receiver<()>>>>,
    f: F,
) -> Result<T, anyhow::Error>
where
    F: FnOnce() -> Fut,
    Fut: std::future::Future<Output = Result<T, String>>,
{
    if cancellation_signalled(cancel_rx_holder).await {
        emit_event(app, BootstrapEvent::Failed {
            stage: Some(stage.name.clone()),
            error: "bootstrap cancelled by user".to_string(),
        });
        return Err(anyhow!("bootstrap cancelled by user"));
    }

    let started = Instant::now();
    emit_event(app, BootstrapEvent::Stage {
        name: stage.name.clone(),
        state: StageState::Running,
        duration_ms: None,
        result: None,
        error: None,
    });

    match f().await {
        Ok(result) => {
            let duration_ms = started.elapsed().as_millis() as u64;
            emit_event(app, BootstrapEvent::Stage {
                name: stage.name.clone(),
                state: StageState::Succeeded,
                duration_ms: Some(duration_ms),
                result: None,
                error: None,
            });
            Ok(result)
        }
        Err(err) => {
            let duration_ms = started.elapsed().as_millis() as u64;
            emit_event(app, BootstrapEvent::Stage {
                name: stage.name.clone(),
                state: StageState::Failed,
                duration_ms: Some(duration_ms),
                result: None,
                error: Some(err.clone()),
            });
            emit_event(app, BootstrapEvent::Failed {
                stage: Some(stage.name.clone()),
                error: err.clone(),
            });
            Err(anyhow!(err))
        }
    }
}

async fn cancellation_signalled(holder: &Arc<Mutex<Option<mpsc::Receiver<()>>>>) -> bool {
    let mut guard = holder.lock().await;
    if let Some(rx) = guard.as_mut() {
        rx.try_recv().is_ok()
    } else {
        false
    }
}

fn emit_event(app: &AppHandle, event: BootstrapEvent) {
    match &event {
        BootstrapEvent::Manifest { stages, .. } => {
            tracing::info!(
                stage_count = stages.len(),
                names = ?stages.iter().map(|s| s.name.as_str()).collect::<Vec<_>>(),
                "manifest received"
            );
        }
        BootstrapEvent::Stage { name, state, duration_ms, error, .. } => {
            tracing::info!(stage = %name, ?state, duration_ms = ?duration_ms, error = ?error, "stage transition");
        }
        BootstrapEvent::Complete { install_root, .. } => {
            tracing::info!(install_root = %install_root, "bootstrap complete");
        }
        BootstrapEvent::Failed { stage, error } => {
            tracing::error!(stage = ?stage, error = %error, "bootstrap FAILED");
        }
        BootstrapEvent::Log { .. } => {}
    }
    if let Err(e) = app.emit(BootstrapEvent::CHANNEL, &event) {
        tracing::warn!(?e, "failed to emit bootstrap event");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    fn unique_tmp_dir(tag: &str) -> PathBuf {
        let base = std::env::temp_dir().join(format!(
            "aetheros-bootstrap-test-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&base).unwrap();
        base
    }

    fn make_release_tree(install_root: &Path) -> PathBuf {
        let release = install_root.join("apps").join("desktop").join("release");
        if cfg!(target_os = "macos") {
            let macos_dir = release
                .join("mac-arm64")
                .join("Aetheros.app")
                .join("Contents")
                .join("MacOS");
            std::fs::create_dir_all(&macos_dir).unwrap();
            std::fs::write(macos_dir.join("Aetheros"), b"#!/bin/sh\n").unwrap();
            macos_dir.parent().unwrap().parent().unwrap().to_path_buf()
        } else if cfg!(target_os = "windows") {
            let dir = release.join("win-unpacked");
            std::fs::create_dir_all(&dir).unwrap();
            let exe = dir.join("Aetheros.exe");
            std::fs::write(&exe, b"stub").unwrap();
            exe
        } else {
            let dir = release.join("linux-unpacked");
            std::fs::create_dir_all(&dir).unwrap();
            let exe = dir.join("aetheros");
            std::fs::write(&exe, b"stub").unwrap();
            exe
        }
    }

    #[test]
    fn resolve_aetheros_desktop_app_finds_built_bundle() {
        let root = unique_tmp_dir("app-ok");
        let expected = make_release_tree(&root);
        let resolved = resolve_aetheros_desktop_app(&root)
            .expect("should resolve the freshly-built desktop app");
        #[cfg(target_os = "macos")]
        {
            assert_eq!(resolved, expected, "must resolve to the .app bundle");
            assert_eq!(
                resolved.extension().and_then(|e| e.to_str()),
                Some("app"),
                "relaunch target must be a .app bundle on macOS"
            );
        }
        #[cfg(not(target_os = "macos"))]
        {
            assert_eq!(resolved, expected);
        }
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn resolve_aetheros_desktop_app_is_none_without_a_build() {
        let root = unique_tmp_dir("app-none");
        assert!(
            resolve_aetheros_desktop_app(&root).is_none(),
            "no resolved app when nothing has been built"
        );
        let _ = std::fs::remove_dir_all(&root);
    }
}
