use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ComponentStatus {
    Healthy,
    Missing,
    Corrupted,
    Broken,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComponentHealth {
    pub name: String,
    pub component_type: ComponentType,
    pub path: String,
    pub status: ComponentStatus,
    pub expected_size: u64,
    pub actual_size: u64,
    pub issues: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ComponentType {
    Executable,
    Config,
    Library,
    Data,
    Runtime,
    Script,
    Asset,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthReport {
    pub components: Vec<ComponentHealth>,
    pub total: usize,
    pub healthy: usize,
    pub missing: usize,
    pub corrupted: usize,
    pub broken: usize,
    pub repairable: usize,
    pub repair_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RepairAction {
    pub component: String,
    pub action: String,
    pub success: bool,
    pub message: String,
}

fn expected_components() -> Vec<(String, ComponentType, String, u64)> {
    let home = crate::paths::aetheros_home();
    let install_root = home.join("aetheros");

    vec![
        ("aetheros_cli".into(), ComponentType::Library, install_root.join("aetheros_cli").to_string_lossy().to_string(), 0),
        ("config.yaml".into(), ComponentType::Config, home.join("config.yaml").to_string_lossy().to_string(), 0),
        ("run_agent.py".into(), ComponentType::Script, install_root.join("run_agent.py").to_string_lossy().to_string(), 0),
        ("cli.py".into(), ComponentType::Script, install_root.join("cli.py").to_string_lossy().to_string(), 0),
        ("venv".into(), ComponentType::Runtime, install_root.join("venv").to_string_lossy().to_string(), 0),
        ("model_tools.py".into(), ComponentType::Script, install_root.join("model_tools.py").to_string_lossy().to_string(), 0),
        ("tools".into(), ComponentType::Library, install_root.join("tools").to_string_lossy().to_string(), 0),
        ("gateway".into(), ComponentType::Library, install_root.join("gateway").to_string_lossy().to_string(), 0),
        ("agent".into(), ComponentType::Library, install_root.join("agent").to_string_lossy().to_string(), 0),
    ]
}

pub fn check_component_health() -> HealthReport {
    let components = expected_components();
    let mut results = Vec::new();
    let mut healthy = 0;
    let mut missing = 0;
    let mut corrupted = 0;
    let mut broken = 0;

    for (name, ctype, path_str, expected_size) in &components {
        let path = std::path::Path::new(path_str);
        let mut issues = Vec::new();

        let status = if !path.exists() {
            missing += 1;
            issues.push("Path does not exist".to_string());
            ComponentStatus::Missing
        } else {
            let meta = std::fs::metadata(path);
            match meta {
                Ok(m) => {
                    let actual_size = m.len();
                    if *expected_size > 0 && actual_size != *expected_size {
                        corrupted += 1;
                        issues.push(format!("Size mismatch: expected {expected_size}, got {actual_size}"));
                        ComponentStatus::Corrupted
                    } else {
                        healthy += 1;
                        ComponentStatus::Healthy
                    }
                }
                Err(e) => {
                    broken += 1;
                    issues.push(format!("Cannot read metadata: {e}"));
                    ComponentStatus::Broken
                }
            }
        };

        results.push(ComponentHealth {
            name: name.clone(),
            component_type: *ctype,
            path: path_str.clone(),
            status,
            expected_size: *expected_size,
            actual_size: std::fs::metadata(path).map(|m| m.len()).unwrap_or(0),
            issues,
        });
    }

    let total = results.len();
    let repairable = missing + corrupted;

    HealthReport {
        components: results,
        total,
        healthy,
        missing,
        corrupted,
        broken,
        repairable,
        repair_count: 0,
    }
}

pub fn check_config_integrity() -> Vec<ComponentHealth> {
    let mut results = Vec::new();
    let home = crate::paths::aetheros_home();

    let config_files: Vec<(&str, &str)> = vec![
        ("config.yaml", "config"),
        ("ai-providers.json", "config"),
        ("model-registry.json", "config"),
        ("update-channel.json", "config"),
        ("rollback-manifest.json", "config"),
    ];

    for (name, dir) in config_files {
        let path = if *dir == *"config" {
            home.join("config").join(name)
        } else {
            home.join(name)
        };

        let mut issues = Vec::new();
        let status = if !path.exists() {
            ComponentStatus::Missing
        } else {
            match std::fs::read_to_string(&path) {
                Ok(content) => {
                    if content.trim().is_empty() {
                        issues.push("Config file is empty".to_string());
                        ComponentStatus::Corrupted
                    } else {
                        ComponentStatus::Healthy
                    }
                }
                Err(e) => {
                    issues.push(format!("Cannot read: {e}"));
                    ComponentStatus::Broken
                }
            }
        };

        results.push(ComponentHealth {
            name: name.to_string(),
            component_type: ComponentType::Config,
            path: path.to_string_lossy().to_string(),
            status,
            expected_size: 0,
            actual_size: std::fs::metadata(&path).map(|m| m.len()).unwrap_or(0),
            issues,
        });
    }

    results
}

pub fn check_runtime_integrity() -> Vec<ComponentHealth> {
    let mut results = Vec::new();
    let venv_path = crate::paths::aetheros_home().join("aetheros").join("venv");

    let check_items: Vec<(&str, PathBuf)> = vec![
        ("Python", if cfg!(target_os = "windows") {
            venv_path.join("Scripts").join("python.exe")
        } else {
            venv_path.join("bin").join("python3")
        }),
        ("Pip", if cfg!(target_os = "windows") {
            venv_path.join("Scripts").join("pip.exe")
        } else {
            venv_path.join("bin").join("pip")
        }),
        ("AetherOS CLI", if cfg!(target_os = "windows") {
            venv_path.join("Scripts").join("aetheros.exe")
        } else {
            venv_path.join("bin").join("aetheros")
        }),
    ];

    for (name, path) in &check_items {
        let mut issues = Vec::new();
        let status = if !path.exists() {
            issues.push(format!("{name} not found at {}", path.display()));
            ComponentStatus::Missing
        } else {
            let meta = std::fs::metadata(path);
            match meta {
                Ok(m) if m.len() == 0 => {
                    issues.push("File exists but is empty".to_string());
                    ComponentStatus::Corrupted
                }
                Ok(_) => ComponentStatus::Healthy,
                Err(e) => {
                    issues.push(format!("Cannot read: {e}"));
                    ComponentStatus::Broken
                }
            }
        };

        results.push(ComponentHealth {
            name: name.to_string(),
            component_type: ComponentType::Runtime,
            path: path.to_string_lossy().to_string(),
            status,
            expected_size: 0,
            actual_size: std::fs::metadata(path).map(|m| m.len()).unwrap_or(0),
            issues,
        });
    }

    results
}

pub fn try_repair(report: &HealthReport) -> Result<Vec<RepairAction>, String> {
    let mut actions = Vec::new();

    for component in &report.components {
        match component.status {
            ComponentStatus::Healthy => {
                actions.push(RepairAction {
                    component: component.name.clone(),
                    action: "none".to_string(),
                    success: true,
                    message: "Already healthy".to_string(),
                });
            }
            ComponentStatus::Missing => {
                let path = std::path::Path::new(&component.path);
                if let Some(parent) = path.parent() {
                    if !parent.exists() {
                        match std::fs::create_dir_all(parent) {
                            Ok(_) => {
                                actions.push(RepairAction {
                                    component: component.name.clone(),
                                    action: "created_directory".to_string(),
                                    success: true,
                                    message: format!("Created directory {}", parent.display()),
                                });
                            }
                            Err(e) => {
                                actions.push(RepairAction {
                                    component: component.name.clone(),
                                    action: "repair_failed".to_string(),
                                    success: false,
                                    message: format!("Could not create directory {parent:?}: {e}"),
                                });
                            }
                        }
                    } else {
                        actions.push(RepairAction {
                            component: component.name.clone(),
                            action: "needs_redownload".to_string(),
                            success: false,
                            message: format!("File missing at {}, needs re-download", path.display()),
                        });
                    }
                }
            }
            ComponentStatus::Corrupted => {
                let path = std::path::Path::new(&component.path);
                match std::fs::remove_file(path) {
                    Ok(_) => {
                        actions.push(RepairAction {
                            component: component.name.clone(),
                            action: "removed_corrupted".to_string(),
                            success: true,
                            message: format!("Removed corrupted file at {}", path.display()),
                        });
                    }
                    Err(e) => {
                        actions.push(RepairAction {
                            component: component.name.clone(),
                            action: "repair_failed".to_string(),
                            success: false,
                            message: format!("Could not remove corrupted file: {e}"),
                        });
                    }
                }
            }
            ComponentStatus::Broken => {
                actions.push(RepairAction {
                    component: component.name.clone(),
                    action: "needs_reinstall".to_string(),
                    success: false,
                    message: "Component is broken and needs re-installation".to_string(),
                });
            }
        }
    }

    Ok(actions)
}

#[tauri::command]
pub async fn run_self_health_check() -> Result<HealthReport, String> {
    let mut components = Vec::new();

    components.extend(check_component_health().components);
    components.extend(check_config_integrity());
    components.extend(check_runtime_integrity());

    let total = components.len();
    let healthy = components.iter().filter(|c| c.status == ComponentStatus::Healthy).count();
    let missing = components.iter().filter(|c| c.status == ComponentStatus::Missing).count();
    let corrupted = components.iter().filter(|c| c.status == ComponentStatus::Corrupted).count();
    let broken = components.iter().filter(|c| c.status == ComponentStatus::Broken).count();
    let repairable = missing + corrupted;

    Ok(HealthReport {
        components,
        total,
        healthy,
        missing,
        corrupted,
        broken,
        repairable,
        repair_count: 0,
    })
}

#[tauri::command]
pub async fn repair_installation(report: Option<HealthReport>) -> Result<Vec<RepairAction>, String> {
    let r = match report {
        Some(r) => r,
        None => run_self_health_check().await?,
    };
    try_repair(&r)
}
