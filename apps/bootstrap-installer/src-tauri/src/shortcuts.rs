use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShortcutResult {
    pub name: String,
    pub location: String,
    pub created: bool,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShortcutOptions {
    pub start_menu: bool,
    pub desktop: bool,
    pub taskbar: bool,
    pub path_alias: bool,
}

fn installer_path() -> PathBuf {
    crate::paths::installer_dest()
}

#[tauri::command]
pub async fn create_installer_shortcuts(
    options: ShortcutOptions,
) -> Result<Vec<ShortcutResult>, String> {
    let mut results = Vec::new();
    let target = installer_path();

    if !target.exists() {
        return Err("Installer binary not found at expected location".to_string());
    }

    if options.start_menu || options.desktop {
        if cfg!(target_os = "windows") {
            if options.start_menu {
                results.push(create_windows_start_menu_shortcut(&target));
            }
            if options.desktop {
                results.push(create_windows_desktop_shortcut(&target));
            }
        } else if cfg!(target_os = "macos") {
            results.push(create_macos_applications_link(&target));
        }
    }

    if results.is_empty() {
        results.push(ShortcutResult {
            name: "shortcuts".to_string(),
            location: "none".to_string(),
            created: false,
            message: "No shortcuts were requested".to_string(),
        });
    }

    Ok(results)
}

#[cfg(target_os = "windows")]
fn create_windows_start_menu_shortcut(target: &PathBuf) -> ShortcutResult {
    let start_menu = std::env::var("APPDATA")
        .map(PathBuf::from)
        .unwrap_or_default()
        .join("Microsoft")
        .join("Windows")
        .join("Start Menu")
        .join("Programs")
        .join("Aetheros");

    if let Err(e) = std::fs::create_dir_all(&start_menu) {
        return ShortcutResult {
            name: "Start Menu".to_string(),
            location: start_menu.to_string_lossy().into_owned(),
            created: false,
            message: format!("Could not create start menu directory: {e}"),
        };
    }

    let shortcut_path = start_menu.join("Aetheros Setup.lnk");

    match create_lnk_file(&shortcut_path, target, "Aetheros Setup") {
        Ok(()) => ShortcutResult {
            name: "Start Menu".to_string(),
            location: shortcut_path.to_string_lossy().into_owned(),
            created: true,
            message: "Start menu shortcut created".to_string(),
        },
        Err(e) => ShortcutResult {
            name: "Start Menu".to_string(),
            location: shortcut_path.to_string_lossy().into_owned(),
            created: false,
            message: format!("Could not create shortcut: {e}"),
        },
    }
}

#[cfg(target_os = "windows")]
fn create_windows_desktop_shortcut(target: &PathBuf) -> ShortcutResult {
    let desktop = std::env::var("PUBLIC")
        .map(PathBuf::from)
        .unwrap_or_default()
        .join("Desktop");

    let shortcut_path = desktop.join("Aetheros Setup.lnk");

    match create_lnk_file(&shortcut_path, target, "Aetheros Setup") {
        Ok(()) => ShortcutResult {
            name: "Desktop".to_string(),
            location: shortcut_path.to_string_lossy().into_owned(),
            created: true,
            message: "Desktop shortcut created".to_string(),
        },
        Err(e) => ShortcutResult {
            name: "Desktop".to_string(),
            location: shortcut_path.to_string_lossy().into_owned(),
            created: false,
            message: format!("Could not create shortcut: {e}"),
        },
    }
}

#[cfg(target_os = "windows")]
fn create_lnk_file(
    shortcut_path: &PathBuf,
    target: &PathBuf,
    description: &str,
) -> Result<(), String> {
    let ps_script = format!(
        r#"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{}')
$Shortcut.TargetPath = '{}'
$Shortcut.Description = '{}'
$Shortcut.Save()
"#,
        shortcut_path.display().to_string().replace('\'', "''"),
        target.display().to_string().replace('\'', "''"),
        description.replace('\'', "''"),
    );

    let output = std::process::Command::new("powershell.exe")
        .args(["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", &ps_script])
        .output()
        .map_err(|e| format!("Failed to run PowerShell: {e}"))?;

    if output.status.success() {
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("PowerShell failed: {stderr}"))
    }
}

#[cfg(target_os = "macos")]
fn create_macos_applications_link(target: &PathBuf) -> ShortcutResult {
    let applications = PathBuf::from("/Applications");
    let link_name = applications.join("Aetheros Setup");

    match std::os::unix::fs::symlink(target, &link_name) {
        Ok(()) => ShortcutResult {
            name: "Applications".to_string(),
            location: link_name.to_string_lossy().into_owned(),
            created: true,
            message: "Application link created".to_string(),
        },
        Err(e) => ShortcutResult {
            name: "Applications".to_string(),
            location: link_name.to_string_lossy().into_owned(),
            created: false,
            message: format!("Could not create link: {e}"),
        },
    }
}

#[cfg(not(target_os = "macos"))]
fn create_macos_applications_link(_target: &PathBuf) -> ShortcutResult {
    ShortcutResult {
        name: "macOS Applications".to_string(),
        location: "/Applications".to_string(),
        created: false,
        message: "Not available on this platform".to_string(),
    }
}
