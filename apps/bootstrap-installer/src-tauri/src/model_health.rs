use crate::model_registry::{InstalledModel, ModelRegistry};
use crate::model_storage::{self, StorageConfig};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HealthStatus {
    Healthy,
    Corrupted,
    Missing,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelHealthResult {
    pub model_id: String,
    pub model_name: String,
    pub provider: String,
    pub path: String,
    pub status: HealthStatus,
    pub expected_checksum: Option<String>,
    pub actual_checksum: Option<String>,
    pub file_size: u64,
    pub expected_size: u64,
    pub issues: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthReport {
    pub results: Vec<ModelHealthResult>,
    pub total_models: usize,
    pub healthy: usize,
    pub corrupted: usize,
    pub missing: usize,
    pub unknown: usize,
    pub total_recoverable_bytes: u64,
}

fn file_size(path: &std::path::Path) -> u64 {
    std::fs::metadata(path).map(|m| m.len()).unwrap_or(0)
}

pub fn check_model_integrity(
    model: &InstalledModel,
) -> ModelHealthResult {
    let model_path = std::path::Path::new(&model.path);
    let mut issues = Vec::new();

    if !model_path.exists() {
        return ModelHealthResult {
            model_id: model.id.clone(),
            model_name: model.name.clone(),
            provider: model.provider.clone(),
            path: model.path.clone(),
            status: HealthStatus::Missing,
            expected_checksum: model.checksum.clone(),
            actual_checksum: None,
            file_size: 0,
            expected_size: model.size_bytes,
            issues: vec!["File not found on disk".to_string()],
        };
    }

    let actual_size = file_size(model_path);
    let mut health = HealthStatus::Healthy;

    if model.size_bytes > 0 && actual_size != model.size_bytes {
        issues.push(format!(
            "Size mismatch: expected {} bytes, got {} bytes",
            model.size_bytes, actual_size
        ));
        health = HealthStatus::Corrupted;
    }

    let actual_checksum = if let Some(ref expected) = model.checksum {
        match crate::verification::compute_sha256(model_path) {
            Ok(hash) => {
                if hash != *expected {
                    issues.push(format!("Checksum mismatch: expected {expected}, got {hash}"));
                    health = HealthStatus::Corrupted;
                }
                Some(hash)
            }
            Err(e) => {
                issues.push(format!("Cannot compute checksum: {e}"));
                health = HealthStatus::Unknown;
                None
            }
        }
    } else {
        crate::verification::compute_sha256(model_path).ok()
    };

    ModelHealthResult {
        model_id: model.id.clone(),
        model_name: model.name.clone(),
        provider: model.provider.clone(),
        path: model.path.clone(),
        status: health,
        expected_checksum: model.checksum.clone(),
        actual_checksum,
        file_size: actual_size,
        expected_size: model.size_bytes,
        issues,
    }
}

pub fn check_all_models() -> Result<HealthReport, String> {
    let registry = ModelRegistry::load()?;
    let mut results = Vec::new();
    let mut healthy = 0;
    let mut corrupted = 0;
    let mut missing = 0;
    let mut unknown = 0;
    let mut total_recoverable_bytes = 0u64;

    for model in &registry.models {
        let result = check_model_integrity(model);
        match result.status {
            HealthStatus::Healthy => healthy += 1,
            HealthStatus::Corrupted => {
                corrupted += 1;
                total_recoverable_bytes += result.file_size;
            }
            HealthStatus::Missing => {
                missing += 1;
            }
            HealthStatus::Unknown => unknown += 1,
        }
        results.push(result);
    }

    Ok(HealthReport {
        total_models: registry.count(),
        healthy,
        corrupted,
        missing,
        unknown,
        total_recoverable_bytes,
        results,
    })
}

pub fn repair_model(model: &InstalledModel) -> Result<ModelHealthResult, String> {
    let model_path = std::path::Path::new(&model.path);

    if !model_path.exists() {
        return Ok(ModelHealthResult {
            model_id: model.id.clone(),
            model_name: model.name.clone(),
            provider: model.provider.clone(),
            path: model.path.clone(),
            status: HealthStatus::Missing,
            expected_checksum: model.checksum.clone(),
            actual_checksum: None,
            file_size: 0,
            expected_size: model.size_bytes,
            issues: vec!["Cannot repair — file is missing. Re-download required.".to_string()],
        });
    }

    if model.size_bytes > 0 {
        if let Ok(meta) = std::fs::metadata(model_path) {
            if meta.len() != model.size_bytes {
                let _ = std::fs::remove_file(model_path);
                return Ok(ModelHealthResult {
                    model_id: model.id.clone(),
                    model_name: model.name.clone(),
                    provider: model.provider.clone(),
                    path: model.path.clone(),
                    status: HealthStatus::Corrupted,
                    expected_checksum: model.checksum.clone(),
                    actual_checksum: None,
                    file_size: 0,
                    expected_size: model.size_bytes,
                    issues: vec!["File deleted for re-download — size mismatch".to_string()],
                });
            }
        }
    }

    if let Some(ref expected) = model.checksum {
        match crate::verification::compute_sha256(model_path) {
            Ok(hash) if hash == *expected => {
                return Ok(ModelHealthResult {
                    model_id: model.id.clone(),
                    model_name: model.name.clone(),
                    provider: model.provider.clone(),
                    path: model.path.clone(),
                    status: HealthStatus::Healthy,
                    expected_checksum: model.checksum.clone(),
                    actual_checksum: Some(hash),
                    file_size: file_size(model_path),
                    expected_size: model.size_bytes,
                    issues: Vec::new(),
                });
            }
            Ok(hash) => {
                let _ = std::fs::remove_file(model_path);
                return Ok(ModelHealthResult {
                    model_id: model.id.clone(),
                    model_name: model.name.clone(),
                    provider: model.provider.clone(),
                    path: model.path.clone(),
                    status: HealthStatus::Corrupted,
                    expected_checksum: model.checksum.clone(),
                    actual_checksum: Some(hash),
                    file_size: file_size(model_path),
                    expected_size: model.size_bytes,
                    issues: vec!["File deleted for re-download — checksum mismatch".to_string()],
                });
            }
            Err(e) => {
                return Err(format!("Cannot verify checksum for repair: {e}"));
            }
        }
    }

    Ok(check_model_integrity(model))
}

pub fn find_orphaned_files(config: &StorageConfig) -> Result<Vec<PathBuf>, String> {
    let registry = ModelRegistry::load()?;
    let known_paths: std::collections::HashSet<String> = registry
        .models
        .iter()
        .map(|m| {
            std::fs::canonicalize(&m.path)
                .ok()
                .and_then(|p| p.to_str().map(|s| s.to_string()))
                .unwrap_or(m.path.clone())
        })
        .collect();

    let mut orphaned = Vec::new();
    let model_dirs = [
        PathBuf::from(&config.downloaded),
        PathBuf::from(&config.imported),
    ];

    for dir in &model_dirs {
        if !dir.exists() {
            continue;
        }
        if let Ok(entries) = std::fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    if let Ok(sub_entries) = std::fs::read_dir(&path) {
                        for sub in sub_entries.flatten() {
                            let sub_path = sub.path();
                            let canonical = std::fs::canonicalize(&sub_path)
                                .ok()
                                .and_then(|p| p.to_str().map(|s| s.to_string()))
                                .unwrap_or_default();
                            if !known_paths.contains(&canonical) {
                                orphaned.push(sub_path);
                            }
                        }
                    }
                } else {
                    let canonical = std::fs::canonicalize(&path)
                        .ok()
                        .and_then(|p| p.to_str().map(|s| s.to_string()))
                        .unwrap_or_default();
                    if !known_paths.contains(&canonical) {
                        orphaned.push(path);
                    }
                }
            }
        }
    }

    Ok(orphaned)
}

#[tauri::command]
pub async fn get_model_health_report() -> Result<HealthReport, String> {
    check_all_models()
}

#[tauri::command]
pub async fn check_model_health(model_id: String) -> Result<ModelHealthResult, String> {
    let registry = ModelRegistry::load()?;
    let model = registry
        .get(&model_id)
        .ok_or_else(|| format!("Model not found: {model_id}"))?;
    Ok(check_model_integrity(model))
}

#[tauri::command]
pub async fn repair_model_files(model_id: String) -> Result<ModelHealthResult, String> {
    let registry = ModelRegistry::load()?;
    let model = registry
        .get(&model_id)
        .ok_or_else(|| format!("Model not found: {model_id}"))?
        .clone();
    repair_model(&model)
}

#[tauri::command]
pub async fn find_orphaned_model_files() -> Result<Vec<String>, String> {
    let config = model_storage::storage_config();
    let orphaned = find_orphaned_files(&config)?;
    Ok(orphaned.iter().map(|p| p.to_string_lossy().to_string()).collect())
}

#[tauri::command]
pub async fn clean_orphaned_model_files() -> Result<u64, String> {
    let config = model_storage::storage_config();
    let orphaned = find_orphaned_files(&config)?;
    let mut total = 0u64;

    for path in &orphaned {
        if let Ok(meta) = std::fs::metadata(path) {
            total += meta.len();
        }
        if path.is_dir() {
            let _ = std::fs::remove_dir_all(path);
        } else {
            let _ = std::fs::remove_file(path);
        }
    }

    Ok(total)
}
