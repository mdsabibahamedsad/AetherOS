use crate::model_download::{self, ModelDownloadProgress};

use crate::model_recommender::{self, ModelRecommendation};
use crate::model_registry::{InstalledModel, ModelCategory, ModelRegistry, ModelType};
use crate::model_storage::{self, StorageConfig, StorageStats};
use crate::model_store::{self, ModelStoreEntry};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelManagerState {
    pub registry: ModelRegistry,
    pub storage: StorageConfig,
    pub storage_stats: StorageStats,
    pub installed_count: usize,
    pub total_size_bytes: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallModelRequest {
    pub catalog_id: String,
    pub storage_config: Option<StorageConfig>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelOperationResult {
    pub success: bool,
    pub message: String,
    pub model_id: Option<String>,
}

fn now_iso() -> String {
    let duration = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = duration.as_secs();
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", (secs / 86400) % 30 + 1, secs % 86400 / 3600 + 1, (secs % 3600) / 60, secs % 60, 0)
}

pub fn install_model_from_catalog(
    entry: &ModelStoreEntry,
) -> Result<ModelOperationResult, String> {
    let config = model_storage::storage_config();
    model_storage::ensure_dirs(&config)?;

    let storage_path = model_storage::model_path(&entry.provider, &entry.name, &config);

    if storage_path.exists() {
        return Ok(ModelOperationResult {
            success: false,
            message: format!("Model already installed at {}", storage_path.display()),
            model_id: None,
        });
    }

    if entry.source == "local" && entry.download_url.is_none() {
        return Err(format!("Model {} has no download URL", entry.id));
    }

    let mut registry = ModelRegistry::load()?;

    let model = InstalledModel {
        id: entry.id.clone(),
        name: entry.name.clone(),
        provider: entry.provider.clone(),
        source: entry.source.clone(),
        version: entry.version.clone(),
        size_bytes: entry.size_bytes,
        path: storage_path.to_string_lossy().to_string(),
        model_type: category_to_model_type(entry.category),
        category: category_to_model_category(entry.category),
        checksum: entry.checksum.clone(),
        installed_at: now_iso(),
        last_used: None,
        metadata: HashMap::new(),
    };

    registry.add(model);
    registry.save()?;

    Ok(ModelOperationResult {
        success: true,
        message: format!("Model {} registered for installation", entry.name),
        model_id: Some(entry.id.clone()),
    })
}

fn category_to_model_type(cat: model_store::ModelStoreCategory) -> ModelType {
    match cat {
        model_store::ModelStoreCategory::General => ModelType::Chat,
        model_store::ModelStoreCategory::Coding => ModelType::Coding,
        model_store::ModelStoreCategory::Reasoning => ModelType::Reasoning,
        model_store::ModelStoreCategory::Vision => ModelType::Vision,
        model_store::ModelStoreCategory::Embedding => ModelType::Embedding,
        model_store::ModelStoreCategory::Voice => ModelType::Voice,
        model_store::ModelStoreCategory::ImageGeneration => ModelType::ImageGeneration,
        model_store::ModelStoreCategory::SpeechToText => ModelType::SpeechToText,
        model_store::ModelStoreCategory::TextToSpeech => ModelType::TextToSpeech,
        model_store::ModelStoreCategory::Offline => ModelType::Chat,
        model_store::ModelStoreCategory::Experimental => ModelType::Experimental,
    }
}

fn category_to_model_category(cat: model_store::ModelStoreCategory) -> ModelCategory {
    match cat {
        model_store::ModelStoreCategory::General => ModelCategory::General,
        model_store::ModelStoreCategory::Coding => ModelCategory::Coding,
        model_store::ModelStoreCategory::Reasoning => ModelCategory::Reasoning,
        model_store::ModelStoreCategory::Vision => ModelCategory::Vision,
        model_store::ModelStoreCategory::Embedding => ModelCategory::Embedding,
        model_store::ModelStoreCategory::Voice => ModelCategory::Voice,
        model_store::ModelStoreCategory::ImageGeneration => ModelCategory::ImageGeneration,
        model_store::ModelStoreCategory::SpeechToText => ModelCategory::SpeechToText,
        model_store::ModelStoreCategory::TextToSpeech => ModelCategory::TextToSpeech,
        model_store::ModelStoreCategory::Offline => ModelCategory::Offline,
        model_store::ModelStoreCategory::Experimental => ModelCategory::Experimental,
    }
}

pub fn remove_model(model_id: &str, delete_files: bool) -> Result<ModelOperationResult, String> {
    let mut registry = ModelRegistry::load()?;

    let model = registry
        .get(model_id)
        .ok_or_else(|| format!("Model not found: {model_id}"))?
        .clone();

    if delete_files {
        let path = std::path::Path::new(&model.path);
        if path.exists() {
            if path.is_dir() {
                std::fs::remove_dir_all(path)
                    .map_err(|e| format!("Failed to remove model directory: {e}"))?;
            } else {
                std::fs::remove_file(path)
                    .map_err(|e| format!("Failed to remove model file: {e}"))?;
            }
        }
    }

    registry.remove(model_id);
    registry.save()?;

    tracing::info!(model_id, delete_files, "model removed");

    Ok(ModelOperationResult {
        success: true,
        message: format!("Model {} removed successfully", model.name),
        model_id: Some(model_id.to_string()),
    })
}

pub fn get_manager_state() -> Result<ModelManagerState, String> {
    let registry = ModelRegistry::load()?;
    let storage = model_storage::storage_config();
    let storage_stats = model_storage::get_storage_stats()?;

    Ok(ModelManagerState {
        installed_count: registry.count(),
        total_size_bytes: registry.total_size(),
        registry,
        storage,
        storage_stats,
    })
}

#[tauri::command]
pub async fn install_catalog_model(
    catalog_id: String,
) -> Result<ModelOperationResult, String> {
    let catalog = model_store::builtin_catalog();
    let entry = catalog
        .iter()
        .find(|e| e.id == catalog_id)
        .ok_or_else(|| format!("Model not found in catalog: {catalog_id}"))?;

    install_model_from_catalog(entry)
}

#[tauri::command]
pub async fn uninstall_model(
    model_id: String,
    delete_files: bool,
) -> Result<ModelOperationResult, String> {
    remove_model(&model_id, delete_files)
}

#[tauri::command]
pub async fn get_model_manager_state() -> Result<ModelManagerState, String> {
    get_manager_state()
}

#[tauri::command]
pub async fn install_and_download_model(
    app: tauri::AppHandle,
    catalog_id: String,
) -> Result<ModelDownloadProgress, String> {
    let catalog = model_store::builtin_catalog();
    let entry = catalog
        .iter()
        .find(|e| e.id == catalog_id)
        .ok_or_else(|| format!("Model not found in catalog: {catalog_id}"))?;

    let result = install_model_from_catalog(entry)?;
    if !result.success {
        return Err(result.message);
    }

    let download_url = entry
        .download_url
        .as_ref()
        .ok_or_else(|| format!("Model {} has no download URL", entry.id))?;

    model_download::start_model_download(
        app,
        entry.id.clone(),
        entry.name.clone(),
        entry.provider.clone(),
        download_url.clone(),
        entry.checksum.clone(),
    )
    .await
}

#[tauri::command]
pub async fn search_and_install(
    _app: tauri::AppHandle,
    query: String,
) -> Result<Vec<ModelOperationResult>, String> {
    let catalog = model_store::builtin_catalog();
    let matches = model_store::search_catalog(&query, &catalog);
    let mut results = Vec::new();

    for entry in matches {
        let result = install_model_from_catalog(&entry)?;
        results.push(result);
    }

    Ok(results)
}

#[tauri::command]
pub async fn get_recommended_for_hardware(
    count: Option<usize>,
    task: Option<String>,
) -> Result<Vec<ModelRecommendation>, String> {
    model_recommender::get_model_recommendations(count, task).await
}
