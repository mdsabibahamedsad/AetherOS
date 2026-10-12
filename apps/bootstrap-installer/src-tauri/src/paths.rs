//! Filesystem paths + logging setup.
//!
//! Mirrors `aetheros_constants.get_aetheros_home()` from the Python CLI:
//!   Windows: %LOCALAPPDATA%\aetheros
//!   macOS:   ~/.aetheros
//!   Linux:   ~/.aetheros  (override via $AETHEROS_HOME)
//!
//! NOTE (macOS): Python's get_aetheros_home(), scripts/install.sh, and the
//! Electron desktop's resolveAetherosHome() ALL use ~/.aetheros on macOS — there
//! is no ~/Library/Application Support branch anywhere else. An earlier
//! version of this file used Application Support, which drifted from every
//! other component: the installer wrote the install to one dir and the
//! desktop looked for it in another, so first launch never found the backend.
//!
//! IMPORTANT: this must match exactly. Drift here means install.ps1
//! writes to one place and the installer reads from another, breaking
//! the bootstrap-complete check.

use std::path::{Path, PathBuf};
#[cfg(target_os = "macos")]
use std::process::Command;
use tracing_appender::non_blocking::WorkerGuard;

/// Returns the canonical Aetheros home directory, respecting $AETHEROS_HOME if set.
pub fn aetheros_home() -> PathBuf {
    if let Ok(override_path) = std::env::var("AETHEROS_HOME") {
        if !override_path.trim().is_empty() {
            return PathBuf::from(override_path);
        }
    }

    #[cfg(target_os = "windows")]
    {
        // %LOCALAPPDATA%\aetheros — matches scripts/install.ps1's $AetherosHome.
        if let Some(local_app_data) = dirs::data_local_dir() {
            return local_app_data.join("aetheros");
        }
    }

    // macOS + Linux + fallback: ~/.aetheros (matches Python get_aetheros_home(),
    // install.sh, and the Electron desktop's resolveAetherosHome()).
    if let Some(home) = dirs::home_dir() {
        return home.join(".aetheros");
    }

    // Last resort — current dir, almost certainly wrong but at least
    // doesn't panic.
    PathBuf::from(".aetheros")
}

pub fn log_dir() -> PathBuf {
    aetheros_home().join("logs")
}

pub fn log_path() -> PathBuf {
    log_dir().join("bootstrap-installer.log")
}

pub fn bootstrap_cache_dir() -> PathBuf {
    aetheros_home().join("bootstrap-cache")
}

/// Path to the bundled application archive within the installer's resources.
/// In a self-contained installation, all application files are bundled inside
/// the installer executable and extracted at install time. This is the path
/// where the archive is expected to be found.
pub fn bundled_app_archive() -> PathBuf {
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));
    // The archive is expected to be bundled alongside the installer,
    // or embedded in the installer's resource directory.
    let archive_name = "aetheros-bundle.zip";
    let adjacent = exe_dir.join(archive_name);
    if adjacent.exists() {
        return adjacent;
    }
    // Fallback: check the Tauri resources directory
    if let Ok(manifest_dir) = std::env::var("CARGO_MANIFEST_DIR") {
        let resource = PathBuf::from(manifest_dir).join("resources").join(archive_name);
        if resource.exists() {
            return resource;
        }
    }
    aetheros_home().join("cache").join(archive_name)
}

/// Stable location the installer copies itself to after a successful install.
/// The desktop app re-invokes this with `--update`, and the start-menu /
/// desktop shortcuts can point users back to it. Lives directly under
/// AETHEROS_HOME so it survives repo checkout deletion (unlike anything under
/// aetheros/).
///
/// On Windows this is `%LOCALAPPDATA%\aetheros\aetheros-setup.exe`; on other
/// platforms the extension differs but the directory is the same.
pub fn installer_dest() -> PathBuf {
    let name = if cfg!(target_os = "windows") {
        "aetheros-setup.exe"
    } else {
        "aetheros-setup"
    };
    aetheros_home().join(name)
}

/// Copy the currently-running installer binary to `installer_dest()` so it's
/// available for future `--update` runs and shortcut launches.
///
/// No-ops (returns Ok) when the running exe is ALREADY the destination — which
/// is exactly the case during an `--update` run (the desktop launched us FROM
/// that path), where copying onto ourselves would be a Windows sharing
/// violation. Best-effort: a failure here must not fail the install, so the
/// caller logs and continues.
pub fn copy_self_to_aetheros_home() -> std::io::Result<()> {
    let src = std::env::current_exe()?;
    let dest = installer_dest();

    // Skip if we're already running from the destination (update re-invocation
    // or a prior copy). canonicalize both so symlinks / 8.3 short paths / case
    // differences don't trick us into a self-copy.
    let same = match (src.canonicalize(), dest.canonicalize()) {
        (Ok(a), Ok(b)) => a == b,
        _ => src == dest,
    };
    if same {
        tracing::info!(?dest, "installer already at destination; skipping self-copy");
        return Ok(());
    }

    if let Some(parent) = dest.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::copy(&src, &dest)?;
    repair_macos_installer_helper(&dest);
    tracing::info!(?src, ?dest, "copied installer to AETHEROS_HOME");
    Ok(())
}

#[cfg(target_os = "macos")]
fn repair_macos_installer_helper(path: &Path) {
    let _ = Command::new("/usr/bin/xattr")
        .args(["-cr"])
        .arg(path)
        .status();

    let verify = Command::new("/usr/bin/codesign")
        .arg("--verify")
        .arg(path)
        .status();

    if !matches!(verify, Ok(status) if status.success()) {
        let _ = Command::new("/usr/bin/codesign")
            .args(["--force", "--sign", "-"])
            .arg(path)
            .status();
    }
}

#[cfg(not(target_os = "macos"))]
fn repair_macos_installer_helper(_path: &Path) {}

/// Where install.ps1 writes the bootstrap-complete marker (existence-only file
/// the Electron app also checks). Per main.cjs:
///   const BOOTSTRAP_COMPLETE_MARKER = path.join(ACTIVE_AETHEROS_ROOT, '.aetheros-bootstrap-complete')
/// We don't always know ACTIVE_AETHEROS_ROOT until install.ps1 reports it, so
/// this is a probe helper, not a definitive path.
pub fn likely_bootstrap_marker(install_root: &Path) -> PathBuf {
    install_root.join(".aetheros-bootstrap-complete")
}

/// Initializes tracing to bootstrap-installer.log under AETHEROS_HOME/logs/.
/// Returns a guard that flushes the appender on drop — keep it alive for
/// the lifetime of the process.
pub fn init_logging() -> Option<WorkerGuard> {
    let dir = log_dir();
    if let Err(err) = std::fs::create_dir_all(&dir) {
        // No log dir → log to stderr only. Don't panic; the installer
        // should still be usable on an exotic filesystem.
        eprintln!("[aetheros-setup] could not create log dir {dir:?}: {err}");
        return None;
    }

    let file_appender = tracing_appender::rolling::never(&dir, "bootstrap-installer.log");
    let (non_blocking, guard) = tracing_appender::non_blocking(file_appender);

    let env_filter = tracing_subscriber::EnvFilter::try_from_env("AETHEROS_BOOTSTRAP_LOG")
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info"));

    tracing_subscriber::fmt()
        .with_env_filter(env_filter)
        .with_writer(non_blocking)
        .with_ansi(false)
        .with_target(true)
        .init();

    Some(guard)
}

// ---------------------------------------------------------------------------
// Tauri commands
// ---------------------------------------------------------------------------

#[tauri::command]
pub fn get_log_path() -> String {
    log_path().to_string_lossy().into_owned()
}

#[tauri::command]
pub fn get_aetheros_home() -> String {
    aetheros_home().to_string_lossy().into_owned()
}

#[tauri::command]
pub fn open_log_dir(app: tauri::AppHandle) -> Result<(), String> {
    use tauri_plugin_opener::OpenerExt;
    let path = log_dir();
    app.opener()
        .open_path(path.to_string_lossy(), None::<&str>)
        .map_err(|e| e.to_string())
}
