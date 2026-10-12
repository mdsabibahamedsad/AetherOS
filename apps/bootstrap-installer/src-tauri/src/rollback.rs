use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RollbackEntry {
    pub path: String,
    pub operation: String,
    pub timestamp: String,
    pub success: bool,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RollbackManifest {
    pub entries: Vec<RollbackEntry>,
    pub can_rollback: bool,
    pub total_size: u64,
    pub timestamp: String,
}

fn rollback_manifest_path() -> PathBuf {
    crate::paths::aetheros_home().join("rollback-manifest.json")
}

#[tauri::command]
pub async fn get_rollback_status() -> Result<RollbackManifest, String> {
    let path = rollback_manifest_path();
    if !path.exists() {
        return Ok(RollbackManifest {
            entries: Vec::new(),
            can_rollback: false,
            total_size: 0,
            timestamp: chrono_now(),
        });
    }

    let content = std::fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read rollback manifest: {e}"))?;

    let manifest: RollbackManifest = serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse rollback manifest: {e}"))?;

    Ok(manifest)
}

#[tauri::command]
pub async fn execute_rollback() -> Result<Vec<RollbackEntry>, String> {
    let path = rollback_manifest_path();
    if !path.exists() {
        return Err("No rollback manifest found — nothing to roll back".to_string());
    }

    let content = std::fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read rollback manifest: {e}"))?;

    let manifest: RollbackManifest = serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse rollback manifest: {e}"))?;

    let mut results = Vec::new();

    for entry in &manifest.entries {
        let result = match entry.operation.as_str() {
            "copy" | "install" => {
                let target = PathBuf::from(&entry.path);
                if target.exists() {
                    match std::fs::remove_dir_all(&target) {
                        Ok(_) => RollbackEntry {
                            path: entry.path.clone(),
                            operation: format!("rollback_{}", entry.operation),
                            timestamp: chrono_now(),
                            success: true,
                            error: None,
                        },
                        Err(e) => RollbackEntry {
                            path: entry.path.clone(),
                            operation: format!("rollback_{}", entry.operation),
                            timestamp: chrono_now(),
                            success: false,
                            error: Some(e.to_string()),
                        },
                    }
                } else {
                    RollbackEntry {
                        path: entry.path.clone(),
                        operation: format!("rollback_{}", entry.operation),
                        timestamp: chrono_now(),
                        success: true,
                        error: None,
                    }
                }
            }
            _ => RollbackEntry {
                path: entry.path.clone(),
                operation: format!("rollback_{}", entry.operation),
                timestamp: chrono_now(),
                success: true,
                error: Some("No rollback handler for this operation type".to_string()),
            },
        };
        results.push(result);
    }

    let _ = std::fs::remove_file(&path);

    tracing::info!(
        total = results.len(),
        successes = results.iter().filter(|r| r.success).count(),
        "rollback completed"
    );

    Ok(results)
}

fn chrono_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    format!("{}", duration.as_secs())
}
