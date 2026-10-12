use serde::Serialize;
use std::process::Command;

#[derive(Debug, Clone, Serialize)]
pub struct PathCheck {
    pub name: String,
    pub executable: String,
    pub found: bool,
    pub path: Option<String>,
    pub version: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct PathCheckResult {
    pub checks: Vec<PathCheck>,
    pub all_found: bool,
    pub system_path: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct PathEntryResult {
    pub added: bool,
    pub path: String,
    pub message: String,
}

fn get_system_path() -> String {
    std::env::var("PATH").unwrap_or_default()
}

#[cfg(windows)]
fn check_path_for_exe(name: &str, exe: &str) -> PathCheck {
    let output = Command::new("where")
        .arg(exe)
        .output();

    match output {
        Ok(out) if out.status.success() => {
            let path = String::from_utf8_lossy(&out.stdout)
                .lines()
                .next()
                .map(|s| s.to_string());

            let version = get_exe_version(&path.as_deref().unwrap_or(""));

            PathCheck {
                name: name.to_string(),
                executable: exe.to_string(),
                found: true,
                path,
                version,
            }
        }
        _ => PathCheck {
            name: name.to_string(),
            executable: exe.to_string(),
            found: false,
            path: None,
            version: None,
        },
    }
}

#[cfg(not(windows))]
fn check_path_for_exe(name: &str, exe: &str) -> PathCheck {
    let output = Command::new("which")
        .arg(exe)
        .output();

    match output {
        Ok(out) if out.status.success() => {
            let path = String::from_utf8_lossy(&out.stdout)
                .trim()
                .to_string();
            let version = get_exe_version(&path);
            PathCheck {
                name: name.to_string(),
                executable: exe.to_string(),
                found: true,
                path: Some(path),
                version,
            }
        }
        _ => PathCheck {
            name: name.to_string(),
            executable: exe.to_string(),
            found: false,
            path: None,
            version: None,
        },
    }
}

fn get_exe_version(exe: &str) -> Option<String> {
    let version_flags = ["--version", "-v", "version"];
    for flag in &version_flags {
        if let Ok(out) = Command::new(exe).arg(flag).output() {
            if out.status.success() {
                let ver = String::from_utf8_lossy(&out.stdout).trim().to_string();
                if !ver.is_empty() {
                    return Some(ver);
                }
            }
        }
    }
    None
}

fn check_exe_on_path(name: &str, exe: &str) -> PathCheck {
    check_path_for_exe(name, exe)
}

#[tauri::command]
pub async fn check_runtime_paths() -> Result<PathCheckResult, String> {
    let checks = vec![
        check_exe_on_path("Git", "git"),
        check_exe_on_path("Python", "python"),
        check_exe_on_path("Node.js", "node"),
        check_exe_on_path("npm", "npm"),
        check_exe_on_path("Rust compiler", "rustc"),
        check_exe_on_path("Cargo", "cargo"),
        check_exe_on_path("PowerShell 7", "pwsh"),
    ];

    let all_found = checks.iter().all(|c| c.found);

    Ok(PathCheckResult {
        checks,
        all_found,
        system_path: get_system_path(),
    })
}

#[cfg(windows)]
fn persistent_path_entry(target: &str) -> Option<PathEntryResult> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Foundation::ERROR_SUCCESS;
    use windows_sys::Win32::System::Registry::*;

    let key_path = "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment";
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
            KEY_READ | KEY_WRITE,
            &mut hkey,
        )
    };

    if result != ERROR_SUCCESS {
        return Some(PathEntryResult {
            added: false,
            path: target.to_string(),
            message: "Failed to open registry key — need administrator privileges".to_string(),
        });
    }

    let value_name: Vec<u16> = std::ffi::OsStr::new("PATH")
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    let mut value_size: u32 = 0;
    let query_result = unsafe {
        RegQueryValueExW(
            hkey,
            value_name.as_ptr(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            &mut value_size,
        )
    };

    let current_path = if query_result == ERROR_SUCCESS && value_size > 0 {
        let mut buf: Vec<u16> = vec![0; (value_size / 2 + 1) as usize];
        let mut actual_size = value_size;
        let read_result = unsafe {
            RegQueryValueExW(
                hkey,
                value_name.as_ptr(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                buf.as_mut_ptr() as *mut u8,
                &mut actual_size,
            )
        };
        if read_result == ERROR_SUCCESS {
            Some(String::from_utf16_lossy(&buf[..actual_size as usize / 2]))
        } else {
            None
        }
    } else {
        None
    };

    let path = current_path.as_deref().unwrap_or("");
    if path.contains(target) {
        unsafe { let _ = RegCloseKey(hkey); };
        return Some(PathEntryResult {
            added: true,
            path: target.to_string(),
            message: "Already in PATH".to_string(),
        });
    }

    let separator = if path.is_empty() { "" } else { ";" };
    let new_path = format!("{}{}{}", path, separator, target);
    let new_path_wide: Vec<u16> = std::ffi::OsStr::new(&new_path)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    let set_result = unsafe {
        RegSetValueExW(
            hkey,
            value_name.as_ptr(),
            0,
            REG_EXPAND_SZ,
            new_path_wide.as_ptr() as *const u8,
            (new_path_wide.len() * 2) as u32,
        )
    };

    unsafe { let _ = RegCloseKey(hkey); };

    if set_result == ERROR_SUCCESS {
        let _ = refresh_environment();
        Some(PathEntryResult {
            added: true,
            path: target.to_string(),
            message: format!("Added to system PATH: {target}"),
        })
    } else {
        Some(PathEntryResult {
            added: false,
            path: target.to_string(),
            message: "Failed to write to registry — need administrator privileges".to_string(),
        })
    }
}

#[cfg(not(windows))]
fn persistent_path_entry(target: &str) -> Option<PathEntryResult> {
    None
}

#[cfg(windows)]
fn refresh_environment() -> std::io::Result<()> {
    use windows_sys::Win32::UI::WindowsAndMessaging::*;
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;

    let broadcast: Vec<u16> = OsStr::new("Environment")
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    unsafe {
        SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            broadcast.as_ptr() as isize,
            SMTO_ABORTIFHUNG,
            5000,
            std::ptr::null_mut(),
        );
    }
    Ok(())
}

#[cfg(not(windows))]
fn refresh_environment() -> std::io::Result<()> {
    Ok(())
}

#[tauri::command]
pub async fn add_to_system_path(target_path: String) -> Result<PathEntryResult, String> {
    if let Some(result) = persistent_path_entry(&target_path) {
        Ok(result)
    } else {
        Ok(PathEntryResult {
            added: false,
            path: target_path,
            message: "PATH management not supported on this platform".to_string(),
        })
    }
}

#[tauri::command]
pub async fn refresh_system_environment() -> Result<(), String> {
    refresh_environment().map_err(|e| format!("Failed to refresh environment: {e}"))
}
