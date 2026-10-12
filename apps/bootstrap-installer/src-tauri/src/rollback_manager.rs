use crate::release_manager::version_gt;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SnapshotEntry {
    pub path: String,
    pub operation: String,
    pub timestamp: String,
    pub success: bool,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RollbackSnapshot {
    pub id: String,
    pub version: String,
    pub label: String,
    pub timestamp: String,
    pub entries: Vec<SnapshotEntry>,
    pub total_size: u64,
    pub config_backup_path: Option<String>,
    pub settings_backup_path: Option<String>,
    pub extensions_backup_path: Option<String>,
    pub models_backup_path: Option<String>,
}

fn backup_dir() -> PathBuf {
    crate::paths::aetheros_home().join("backups")
}

fn snapshot_manifest_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("rollback-snapshots.json")
}

fn load_snapshots() -> Vec<RollbackSnapshot> {
    let path = snapshot_manifest_path();
    if !path.exists() {
        return Vec::new();
    }
    let content = std::fs::read_to_string(&path).ok();
    match content {
        Some(c) => serde_json::from_str(&c).unwrap_or_default(),
        None => Vec::new(),
    }
}

fn save_snapshots(snapshots: &[RollbackSnapshot]) -> Result<(), String> {
    let path = snapshot_manifest_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(snapshots).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub async fn create_backup_snapshot(label: &str, version: &str) -> Result<RollbackSnapshot, String> {
    let id = uuid::Uuid::new_v4().to_string();
    let ts = now_iso();
    let snapshot_dir = backup_dir().join(&id);
    let config_dir = crate::paths::aetheros_home().join("config");
    let install_dir = crate::paths::aetheros_home().join("aetheros");

    std::fs::create_dir_all(&snapshot_dir).map_err(|e| format!("Create snapshot dir: {e}"))?;

    let mut entries = Vec::new();
    let mut total_size = 0u64;

    let config_backup = snapshot_dir.join("config-backup");
    if config_dir.exists() {
        match copy_dir(&config_dir, &config_backup) {
            Ok(size) => {
                total_size += size;
                entries.push(SnapshotEntry {
                    path: config_backup.to_string_lossy().to_string(),
                    operation: "backup_config".to_string(),
                    timestamp: ts.clone(),
                    success: true,
                    error: None,
                });
            }
            Err(e) => {
                entries.push(SnapshotEntry {
                    path: config_dir.to_string_lossy().to_string(),
                    operation: "backup_config".to_string(),
                    timestamp: ts.clone(),
                    success: false,
                    error: Some(e),
                });
            }
        }
    }

    let install_backup = snapshot_dir.join("install-backup");
    if install_dir.exists() {
        match copy_dir(&install_dir, &install_backup) {
            Ok(size) => {
                total_size += size;
                entries.push(SnapshotEntry {
                    path: install_backup.to_string_lossy().to_string(),
                    operation: "backup_install".to_string(),
                    timestamp: ts.clone(),
                    success: true,
                    error: None,
                });
            }
            Err(e) => {
                entries.push(SnapshotEntry {
                    path: install_dir.to_string_lossy().to_string(),
                    operation: "backup_install".to_string(),
                    timestamp: ts.clone(),
                    success: false,
                    error: Some(e),
                });
            }
        }
    }

    let snapshot = RollbackSnapshot {
        id: id.clone(),
        version: version.to_string(),
        label: label.to_string(),
        timestamp: ts,
        entries,
        total_size,
        config_backup_path: Some(config_backup.to_string_lossy().to_string()),
        settings_backup_path: None,
        extensions_backup_path: None,
        models_backup_path: None,
    };

    let mut snapshots = load_snapshots();
    snapshots.push(snapshot.clone());
    save_snapshots(&snapshots)?;

    tracing::info!(id, version, size = total_size, "backup snapshot created");
    Ok(snapshot)
}

fn copy_dir(src: &PathBuf, dst: &PathBuf) -> Result<u64, String> {
    let mut total = 0u64;

    if !src.exists() {
        return Ok(0);
    }

    if src.is_file() {
        std::fs::create_dir_all(dst.parent().ok_or("No parent")?)
            .map_err(|e| format!("Create dir: {e}"))?;
        std::fs::copy(src, dst).map_err(|e| format!("Copy: {e}"))?;
        return Ok(std::fs::metadata(dst).map(|m| m.len()).unwrap_or(0));
    }

    let entries = std::fs::read_dir(src).map_err(|e| format!("Read dir {src:?}: {e}"))?;
    for entry in entries.flatten() {
        let src_path = entry.path();
        let rel = src_path.strip_prefix(src).unwrap_or(&src_path);
        let dst_path = dst.join(rel);

        if src_path.is_dir() {
            std::fs::create_dir_all(&dst_path)
                .map_err(|e| format!("Create dir {dst_path:?}: {e}"))?;
            total += copy_dir(&src_path, &dst_path).unwrap_or(0);
        } else {
            if let Some(parent) = dst_path.parent() {
                std::fs::create_dir_all(parent)
                    .map_err(|e| format!("Create parent {parent:?}: {e}"))?;
            }
            std::fs::copy(&src_path, &dst_path)
                .map_err(|e| format!("Copy {src_path:?} -> {dst_path:?}: {e}"))?;
            if let Ok(meta) = std::fs::metadata(&dst_path) {
                total += meta.len();
            }
        }
    }

    Ok(total)
}

pub fn list_rollback_snapshots() -> Result<Vec<RollbackSnapshot>, String> {
    Ok(load_snapshots())
}

async fn restore_snapshot(snapshot: &RollbackSnapshot) -> Result<Vec<SnapshotEntry>, String> {
    let mut results = Vec::new();
    let config_dir = crate::paths::aetheros_home().join("config");
    let install_dir = crate::paths::aetheros_home().join("aetheros");

    for entry in &snapshot.entries {
        let result = match entry.operation.as_str() {
            "backup_config" => {
                let src = PathBuf::from(&entry.path);
                if src.exists() {
                    if config_dir.exists() {
                        std::fs::remove_dir_all(&config_dir)
                            .map_err(|e| format!("Remove config: {e}"))?;
                    }
                    std::fs::create_dir_all(&config_dir).ok();
                    copy_dir(&src, &config_dir)
                        .map(|_| SnapshotEntry {
                            path: config_dir.to_string_lossy().to_string(),
                            operation: "restore_config".to_string(),
                            timestamp: now_iso(),
                            success: true,
                            error: None,
                        })
                        .unwrap_or_else(|e| SnapshotEntry {
                            path: config_dir.to_string_lossy().to_string(),
                            operation: "restore_config".to_string(),
                            timestamp: now_iso(),
                            success: false,
                            error: Some(e),
                        })
                } else {
                    SnapshotEntry {
                        path: config_dir.to_string_lossy().to_string(),
                        operation: "restore_config".to_string(),
                        timestamp: now_iso(),
                        success: false,
                        error: Some("Backup not found".to_string()),
                    }
                }
            }
            "backup_install" => {
                let src = PathBuf::from(&entry.path);
                if src.exists() {
                    if install_dir.exists() {
                        std::fs::remove_dir_all(&install_dir)
                            .map_err(|e| format!("Remove install: {e}"))?;
                    }
                    std::fs::create_dir_all(&install_dir).ok();
                    copy_dir(&src, &install_dir)
                        .map(|_| SnapshotEntry {
                            path: install_dir.to_string_lossy().to_string(),
                            operation: "restore_install".to_string(),
                            timestamp: now_iso(),
                            success: true,
                            error: None,
                        })
                        .unwrap_or_else(|e| SnapshotEntry {
                            path: install_dir.to_string_lossy().to_string(),
                            operation: "restore_install".to_string(),
                            timestamp: now_iso(),
                            success: false,
                            error: Some(e),
                        })
                } else {
                    SnapshotEntry {
                        path: install_dir.to_string_lossy().to_string(),
                        operation: "restore_install".to_string(),
                        timestamp: now_iso(),
                        success: false,
                        error: Some("Backup not found".to_string()),
                    }
                }
            }
            _ => SnapshotEntry {
                path: entry.path.clone(),
                operation: format!("restore_{}", entry.operation),
                timestamp: now_iso(),
                success: true,
                error: None,
            },
        };
        results.push(result);
    }

    if results.iter().any(|r| r.success) {
        tracing::info!(snapshot = snapshot.id, version = snapshot.version, "rollback partially restored");
    }

    Ok(results)
}

pub async fn rollback_to_snapshot(snapshot_id: &str) -> Result<Vec<SnapshotEntry>, String> {
    let snapshots = load_snapshots();
    let snapshot = snapshots
        .iter()
        .find(|s| s.id == snapshot_id)
        .ok_or_else(|| format!("Snapshot not found: {snapshot_id}"))?
        .clone();

    restore_snapshot(&snapshot).await
}

pub async fn rollback_to_version(version: &str) -> Result<Vec<SnapshotEntry>, String> {
    let snapshots = load_snapshots();
    let matching: Vec<&RollbackSnapshot> = snapshots.iter().filter(|s| s.version == version).collect();

    if matching.is_empty() {
        return Err(format!("No snapshots found for version {version}"));
    }

    let latest = matching.into_iter()
        .max_by_key(|s| s.timestamp.clone())
        .ok_or_else(|| format!("No valid snapshot for {version}"))?;

    restore_snapshot(latest).await
}

pub fn clean_old_snapshots(keep_count: usize) -> Result<usize, String> {
    let mut snapshots = load_snapshots();
    snapshots.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));

    if snapshots.len() <= keep_count {
        return Ok(0);
    }

    let to_remove: Vec<RollbackSnapshot> = snapshots.drain(keep_count..).collect();
    let count = to_remove.len();

    for snapshot in &to_remove {
        let snapshot_dir = backup_dir().join(&snapshot.id);
        if snapshot_dir.exists() {
            let _ = std::fs::remove_dir_all(&snapshot_dir);
        }
    }

    save_snapshots(&snapshots)?;
    Ok(count)
}

fn now_iso() -> String {
    let d = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let s = d.as_secs();
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", (s / 86400) % 30 + 1, s % 86400 / 3600 + 1, (s % 3600) / 60, s % 60, 0)
}

#[tauri::command]
pub async fn get_rollback_snapshots() -> Result<Vec<RollbackSnapshot>, String> {
    list_rollback_snapshots()
}

#[tauri::command]
pub async fn execute_rollback_to(snapshot_id: String) -> Result<Vec<SnapshotEntry>, String> {
    rollback_to_snapshot(&snapshot_id).await
}

#[tauri::command]
pub async fn rollback_to_previous_version(version: String) -> Result<Vec<SnapshotEntry>, String> {
    rollback_to_version(&version).await
}

#[tauri::command]
pub async fn create_backup(label: String, version: String) -> Result<RollbackSnapshot, String> {
    create_backup_snapshot(&label, &version).await
}

#[tauri::command]
pub async fn clean_old_snapshots_command(keep: Option<usize>) -> Result<usize, String> {
    clean_old_snapshots(keep.unwrap_or(5))
}
