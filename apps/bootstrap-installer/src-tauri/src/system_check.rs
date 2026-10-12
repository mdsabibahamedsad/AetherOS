use serde::{Deserialize, Serialize};
use std::path::Path;
use fs2::available_space;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckItem {
    pub name: String,
    pub label: String,
    pub passed: bool,
    pub warning: bool,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemCheckResult {
    pub checks: Vec<CheckItem>,
    pub all_passed: bool,
    pub has_warnings: bool,
}

impl CheckItem {
    pub fn pass(name: &str, label: &str, message: &str) -> Self {
        Self {
            name: name.to_string(),
            label: label.to_string(),
            passed: true,
            warning: false,
            message: message.to_string(),
        }
    }

    pub fn warn(name: &str, label: &str, message: &str) -> Self {
        Self {
            name: name.to_string(),
            label: label.to_string(),
            passed: true,
            warning: true,
            message: message.to_string(),
        }
    }

    pub fn fail(name: &str, label: &str, message: &str) -> Self {
        Self {
            name: name.to_string(),
            label: label.to_string(),
            passed: false,
            warning: false,
            message: message.to_string(),
        }
    }
}

#[tauri::command]
pub async fn run_system_checks() -> Result<SystemCheckResult, String> {
        let checks = vec![
        check_os(),
        check_architecture(),
        check_disk_space(),
        check_memory(),
    ];

    let all_passed = checks.iter().all(|c| c.passed);
    let has_warnings = checks.iter().any(|c| c.warning);

    tracing::info!(
        all_passed,
        has_warnings,
        check_count = checks.len(),
        "system checks complete"
    );

    Ok(SystemCheckResult {
        checks,
        all_passed,
        has_warnings,
    })
}

fn check_os() -> CheckItem {
    #[cfg(target_os = "windows")]
    {
        let version = std::env::var("OS").unwrap_or_default();
                if !version.is_empty() {
            CheckItem::pass("os", "Operating System", &format!("Windows ({version}) — supported"))
        } else {
            CheckItem::pass("os", "Operating System", "Windows — supported")
        }
    }
    #[cfg(target_os = "macos")]
    {
        match std::process::Command::new("sw_vers").arg("-productVersion").output() {
            Ok(output) => {
                let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
                CheckItem::pass("os", "Operating System", &format!("macOS {version} — supported"))
            }
            Err(_) => CheckItem::warn("os", "Operating System", "macOS — could not verify version"),
        }
    }
    #[cfg(target_os = "linux")]
    {
        CheckItem::pass("os", "Operating System", "Linux — supported")
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    {
        CheckItem::fail("os", "Operating System", "Unsupported operating system")
    }
}

fn check_architecture() -> CheckItem {
    let arch = std::env::consts::ARCH;
    match arch {
        "x86_64" | "aarch64" => {
            CheckItem::pass("arch", "System Architecture", &format!("{arch} — supported"))
        }
        other => {
            CheckItem::fail("arch", "System Architecture", &format!("{other} — not supported"))
        }
    }
}

fn check_disk_space() -> CheckItem {
    let minimum_bytes: u64 = 5 * 1024 * 1024 * 1024;

    let check_path = crate::paths::aetheros_home();

    if !check_path.exists() {
        if let Some(parent) = check_path.parent() {
            return check_disk_space_at(parent, minimum_bytes);
        }
        return CheckItem::warn("disk", "Disk Space", "Could not determine install path");
    }

    check_disk_space_at(&check_path, minimum_bytes)
}

fn check_disk_space_at(path: &Path, minimum: u64) -> CheckItem {
    match available_space(path) {
        Ok(free) => {
            let label = format_disk_size(free);
            if free >= minimum {
                CheckItem::pass("disk", "Disk Space", &format!("{label} free — sufficient"))
            } else {
                CheckItem::fail("disk", "Disk Space", &format!("Only {label} free, need at least 5 GB"))
            }
        }
        Err(_) => {
            CheckItem::warn("disk", "Disk Space", "Could not determine free disk space")
        }
    }
}

fn check_memory() -> CheckItem {
    let minimum_bytes: u64 = 8 * 1024 * 1024 * 1024;

    let memory = get_total_physical_memory();
    if memory > 0 {
        let label = format_disk_size(memory);
        if memory >= minimum_bytes {
            return CheckItem::pass("memory", "Memory (RAM)", &format!("{label} — sufficient"));
        } else {
            return CheckItem::fail("memory", "Memory (RAM)", &format!("{label} — 8 GB minimum"));
        }
    }

    CheckItem::warn("memory", "Memory (RAM)", "Could not determine system memory")
}

#[cfg(target_os = "windows")]
fn get_total_physical_memory() -> u64 {
    let output = std::process::Command::new("powershell.exe")
        .args([
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
        ])
        .output();
    match output {
        Ok(out) => {
            let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
            s.parse::<u64>().unwrap_or(0)
        }
        Err(_) => 0,
    }
}

#[cfg(not(target_os = "windows"))]
fn get_total_physical_memory() -> u64 {
    0
}

fn format_disk_size(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;
    const TB: u64 = GB * 1024;

    if bytes >= TB {
        format!("{:.1} TB", bytes as f64 / TB as f64)
    } else if bytes >= GB {
        format!("{:.1} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.1} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.1} KB", bytes as f64 / KB as f64)
    } else {
        format!("{bytes} B")
    }
}
