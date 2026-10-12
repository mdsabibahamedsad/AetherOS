use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{AppHandle, Emitter, State};

use crate::AppState;

pub const RUNTIME_EVENT_CHANNEL: &str = "runtime";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeKind {
    Git,
    Python,
    Node,
    Rust,
    VcRedist,
    WebView2,
    Pwsh7,
}

impl RuntimeKind {
    pub fn label(&self) -> &'static str {
        match self {
            RuntimeKind::Git => "Git",
            RuntimeKind::Python => "Python 3",
            RuntimeKind::Node => "Node.js LTS",
            RuntimeKind::Rust => "Rust Toolchain",
            RuntimeKind::VcRedist => "Visual C++ Redistributable",
            RuntimeKind::WebView2 => "Microsoft Edge WebView2",
            RuntimeKind::Pwsh7 => "PowerShell 7",
        }
    }

    pub fn install_order() -> &'static [RuntimeKind] {
        &[
            RuntimeKind::VcRedist,
            RuntimeKind::WebView2,
            RuntimeKind::Git,
            RuntimeKind::Python,
            RuntimeKind::Node,
            RuntimeKind::Rust,
        ]
    }

    pub fn is_optional(&self) -> bool {
        match self {
            RuntimeKind::Pwsh7 => true,
            _ => false,
        }
    }

    pub fn is_windows_only(&self) -> bool {
        match self {
            RuntimeKind::VcRedist | RuntimeKind::WebView2 => true,
            _ => false,
        }
    }

    pub fn is_bundled(&self) -> bool {
        match self {
            RuntimeKind::Git | RuntimeKind::Rust | RuntimeKind::Pwsh7 => false,
            _ => true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeInfo {
    pub kind: RuntimeKind,
    pub label: String,
    pub status: RuntimeStatus,
    pub installed_version: Option<String>,
    pub required_version: Option<String>,
    pub install_path: Option<String>,
    pub architecture: Option<String>,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeStatus {
    Detecting,
    Missing,
    Compatible,
    WrongVersion,
    Broken,
    Downloading,
    Installing,
    Updating,
    Repairing,
    Completed,
    Failed,
    Skipped,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeEvent {
    pub kind: RuntimeKind,
    pub status: RuntimeStatus,
    pub progress: Option<f64>,
    pub message: Option<String>,
    pub version: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeCheckResult {
    pub runtimes: Vec<RuntimeInfo>,
    pub all_compatible: bool,
    pub missing_count: usize,
    pub broken_count: usize,
}

pub struct RuntimeManagerState {
    pub runtimes: Vec<RuntimeInfo>,
    pub running: bool,
}

fn emit_runtime_event(app: &AppHandle, event: RuntimeEvent) {
    tracing::info!(
        kind = ?event.kind,
        status = ?event.status,
        progress = ?event.progress,
        "runtime event"
    );
    let _ = app.emit(RUNTIME_EVENT_CHANNEL, &event);
}

fn check_cmd(cmd: &str, arg: &str) -> Option<String> {
    let output = std::process::Command::new(cmd)
        .arg(arg)
        .output()
        .ok()?;
    if output.status.success() {
        Some(String::from_utf8_lossy(&output.stdout).trim().to_string())
    } else {
        None
    }
}

fn check_cmd_where(exe: &str) -> Option<String> {
    #[cfg(windows)]
    {
        let output = std::process::Command::new("where")
            .arg(exe)
            .output()
            .ok()?;
        if output.status.success() {
            let path = String::from_utf8_lossy(&output.stdout).lines().next()?.to_string();
            return Some(path);
        }
        None
    }
    #[cfg(not(windows))]
    {
        let output = std::process::Command::new("which")
            .arg(exe)
            .output()
            .ok()?;
        if output.status.success() {
            let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
            return Some(path);
        }
        None
    }
}

fn detect_git() -> RuntimeInfo {
    let path = check_cmd_where("git");
    let version = check_cmd("git", "--version");
    let installed = version.is_some();
    RuntimeInfo {
        kind: RuntimeKind::Git,
        label: "Git".to_string(),
        status: if installed { RuntimeStatus::Compatible } else { RuntimeStatus::Missing },
        installed_version: version,
        required_version: Some("2.x".to_string()),
        install_path: path,
        architecture: None,
        errors: Vec::new(),
    }
}

fn detect_python() -> RuntimeInfo {
    let path = check_cmd_where("python");
    let version = check_cmd("python", "--version");
    let installed = version.is_some();
    RuntimeInfo {
        kind: RuntimeKind::Python,
        label: "Python 3".to_string(),
        status: if installed { RuntimeStatus::Compatible } else { RuntimeStatus::Missing },
        installed_version: version,
        required_version: Some("3.10+".to_string()),
        install_path: path,
        architecture: None,
        errors: Vec::new(),
    }
}

fn detect_node() -> RuntimeInfo {
    let path = check_cmd_where("node");
    let version = check_cmd("node", "--version");
    let installed = version.is_some();
    RuntimeInfo {
        kind: RuntimeKind::Node,
        label: "Node.js LTS".to_string(),
        status: if installed { RuntimeStatus::Compatible } else { RuntimeStatus::Missing },
        installed_version: version,
        required_version: Some("18+ LTS".to_string()),
        install_path: path,
        architecture: None,
        errors: Vec::new(),
    }
}

fn detect_rust() -> RuntimeInfo {
    let path = check_cmd_where("rustc");
    let version = check_cmd("rustc", "--version");
    let cargo = check_cmd("cargo", "--version");
    let installed = version.is_some() && cargo.is_some();
    let errors = if version.is_some() && cargo.is_none() {
        vec!["cargo not found on PATH".to_string()]
    } else {
        Vec::new()
    };
    RuntimeInfo {
        kind: RuntimeKind::Rust,
        label: "Rust Toolchain".to_string(),
        status: if installed { RuntimeStatus::Compatible } else { RuntimeStatus::Missing },
        installed_version: version.clone(),
        required_version: Some("1.70+".to_string()),
        install_path: path,
        architecture: None,
        errors,
    }
}

#[cfg(windows)]
fn detect_vcredist() -> RuntimeInfo {
    use windows_sys::Win32::Foundation::ERROR_SUCCESS;
    use windows_sys::Win32::System::Registry::*;
    use std::os::windows::ffi::OsStrExt;

    let keys = &[
        r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64",
        r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\X64",
    ];

    for key_path in keys {
        let wide: Vec<u16> = std::ffi::OsStr::new(key_path)
            .encode_wide()
            .chain(std::iter::once(0))
            .collect();

        let mut hkey: HKEY = std::ptr::null_mut();
        let result = unsafe {
            RegOpenKeyExW(
                HKEY_LOCAL_MACHINE,
                wide.as_ptr(),
                0,
                KEY_READ,
                &mut hkey,
            )
        };

        if result == ERROR_SUCCESS {
            let mut installed_val: u32 = 0;
            let mut size = std::mem::size_of::<u32>() as u32;
            let installed_name: Vec<u16> = std::ffi::OsStr::new("Installed")
                .encode_wide()
                .chain(std::iter::once(0))
                .collect();

            let query_result = unsafe {
                RegQueryValueExW(
                    hkey,
                    installed_name.as_ptr(),
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    &mut installed_val as *mut u32 as *mut u8,
                    &mut size,
                )
            };

            let mut version_buf = [0u16; 128];
            let mut version_size = (version_buf.len() * 2) as u32;
            let version_name: Vec<u16> = std::ffi::OsStr::new("Version")
                .encode_wide()
                .chain(std::iter::once(0))
                .collect();

            let version_result = unsafe {
                RegQueryValueExW(
                    hkey,
                    version_name.as_ptr(),
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    &mut version_buf as *mut [u16; 128] as *mut u8,
                    &mut version_size,
                )
            };

            unsafe { let _ = RegCloseKey(hkey); };

            if query_result == ERROR_SUCCESS && installed_val == 1 {
                let version_str = if version_result == ERROR_SUCCESS {
                    Some(
                        String::from_utf16_lossy(&version_buf[..version_size as usize / 2])
                            .trim_matches('\0')
                            .to_string(),
                    )
                } else {
                    None
                };

                return RuntimeInfo {
                    kind: RuntimeKind::VcRedist,
                    label: "Visual C++ Redistributable".to_string(),
                    status: RuntimeStatus::Compatible,
                    installed_version: version_str,
                    required_version: Some("14.x".to_string()),
                    install_path: Some("Registry::HKLM/VC/Runtimes/X64".to_string()),
                    architecture: Some("x64".to_string()),
                    errors: Vec::new(),
                };
            }
        }
    }

    RuntimeInfo {
        kind: RuntimeKind::VcRedist,
        label: "Visual C++ Redistributable".to_string(),
        status: RuntimeStatus::Missing,
        installed_version: None,
        required_version: Some("14.x".to_string()),
        install_path: None,
        architecture: None,
        errors: Vec::new(),
    }
}

#[cfg(not(windows))]
fn detect_vcredist() -> RuntimeInfo {
    RuntimeInfo {
        kind: RuntimeKind::VcRedist,
        label: "Visual C++ Redistributable".to_string(),
        status: RuntimeStatus::Skipped,
        installed_version: None,
        required_version: None,
        install_path: None,
        architecture: None,
        errors: Vec::new(),
    }
}

#[cfg(windows)]
fn detect_webview2() -> RuntimeInfo {
    use windows_sys::Win32::Foundation::ERROR_SUCCESS;
    use windows_sys::Win32::System::Registry::*;
    use std::os::windows::ffi::OsStrExt;

    let keys = &[
        r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    ];

    for key_path in keys {
        let wide: Vec<u16> = std::ffi::OsStr::new(key_path)
            .encode_wide()
            .chain(std::iter::once(0))
            .collect();

        let mut hkey: HKEY = std::ptr::null_mut();
        let result = unsafe {
            RegOpenKeyExW(
                HKEY_LOCAL_MACHINE,
                wide.as_ptr(),
                0,
                KEY_READ,
                &mut hkey,
            )
        };

        if result == ERROR_SUCCESS {
            let mut version_buf = [0u16; 128];
            let mut version_size = (version_buf.len() * 2) as u32;
            let pv_name: Vec<u16> = std::ffi::OsStr::new("pv")
                .encode_wide()
                .chain(std::iter::once(0))
                .collect();

            let version_result = unsafe {
                RegQueryValueExW(
                    hkey,
                    pv_name.as_ptr(),
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    &mut version_buf as *mut [u16; 128] as *mut u8,
                    &mut version_size,
                )
            };

            unsafe { let _ = RegCloseKey(hkey); };

            if version_result == ERROR_SUCCESS {
                let version = String::from_utf16_lossy(&version_buf[..version_size as usize / 2])
                    .trim_matches('\0')
                    .to_string();
                return RuntimeInfo {
                    kind: RuntimeKind::WebView2,
                    label: "Microsoft Edge WebView2".to_string(),
                    status: RuntimeStatus::Compatible,
                    installed_version: Some(version),
                    required_version: Some("Evergreen".to_string()),
                    install_path: None,
                    architecture: None,
                    errors: Vec::new(),
                };
            }
        }
    }

    RuntimeInfo {
        kind: RuntimeKind::WebView2,
        label: "Microsoft Edge WebView2".to_string(),
        status: RuntimeStatus::Missing,
        installed_version: None,
        required_version: Some("Evergreen".to_string()),
        install_path: None,
        architecture: None,
        errors: Vec::new(),
    }
}

#[cfg(not(windows))]
fn detect_webview2() -> RuntimeInfo {
    RuntimeInfo {
        kind: RuntimeKind::WebView2,
        label: "Microsoft Edge WebView2".to_string(),
        status: RuntimeStatus::Skipped,
        installed_version: None,
        required_version: None,
        install_path: None,
        architecture: None,
        errors: Vec::new(),
    }
}

fn detect_pwsh7() -> RuntimeInfo {
    let path = check_cmd_where("pwsh");
    let version = check_cmd("pwsh", "--version");
    let installed = version.is_some();
    RuntimeInfo {
        kind: RuntimeKind::Pwsh7,
        label: "PowerShell 7".to_string(),
        status: if installed { RuntimeStatus::Compatible } else { RuntimeStatus::Missing },
        installed_version: version,
        required_version: Some("7.x".to_string()),
        install_path: path,
        architecture: None,
        errors: Vec::new(),
    }
}

fn detect_runtime(kind: RuntimeKind) -> RuntimeInfo {
    match kind {
        RuntimeKind::Git => detect_git(),
        RuntimeKind::Python => detect_python(),
        RuntimeKind::Node => detect_node(),
        RuntimeKind::Rust => detect_rust(),
        RuntimeKind::VcRedist => detect_vcredist(),
        RuntimeKind::WebView2 => detect_webview2(),
        RuntimeKind::Pwsh7 => detect_pwsh7(),
    }
}

#[tauri::command]
pub async fn detect_runtimes() -> Result<RuntimeCheckResult, String> {
    let kinds = RuntimeKind::install_order();
    let mut runtimes = Vec::new();

    for kind in kinds {
        let info = detect_runtime(*kind);
        tracing::info!(label = %info.label, status = ?info.status, "runtime detected");
        runtimes.push(info);
    }

    let all_compatible = runtimes.iter().all(|r| {
        r.status == RuntimeStatus::Compatible || r.status == RuntimeStatus::Skipped
    });
    let missing_count = runtimes.iter().filter(|r| r.status == RuntimeStatus::Missing).count();
    let broken_count = runtimes.iter().filter(|r| r.status == RuntimeStatus::Broken).count();

    Ok(RuntimeCheckResult {
        runtimes,
        all_compatible,
        missing_count,
        broken_count,
    })
}

#[tauri::command]
pub async fn install_runtimes(
    app: AppHandle,
    state: State<'_, Arc<AppState>>,
) -> Result<(), String> {
    {
        let mut guard = state.runtime_manager.lock().await;
        if guard.running {
            return Err("Runtime installation is already in progress".to_string());
        }
        guard.running = true;
    }

    let kinds = RuntimeKind::install_order();

    for kind in kinds {
        let info = detect_runtime(*kind);
        if info.status == RuntimeStatus::Compatible || info.status == RuntimeStatus::Skipped {
            emit_runtime_event(&app, RuntimeEvent {
                kind: *kind,
                status: RuntimeStatus::Skipped,
                progress: Some(1.0),
                message: Some(format!("{} already installed", kind.label())),
                version: info.installed_version.clone(),
            });
            continue;
        }

        if kind.is_bundled() {
            emit_runtime_event(&app, RuntimeEvent {
                kind: *kind,
                status: RuntimeStatus::Skipped,
                progress: Some(1.0),
                message: Some(format!("{} is bundled with AetherOS — reinstall using the official installer", kind.label())),
                version: None,
            });
        } else {
            emit_runtime_event(&app, RuntimeEvent {
                kind: *kind,
                status: RuntimeStatus::Skipped,
                progress: Some(1.0),
                message: Some(format!("{} is a system dependency — install it manually", kind.label())),
                version: None,
            });
        }
    }

    {
        let mut guard = state.runtime_manager.lock().await;
        guard.running = false;
    }

    Ok(())
}

#[tauri::command]
pub async fn get_runtime_status(
    state: State<'_, Arc<AppState>>,
) -> Result<Vec<RuntimeInfo>, String> {
    let guard = state.runtime_manager.lock().await;
    Ok(guard.runtimes.clone())
}
