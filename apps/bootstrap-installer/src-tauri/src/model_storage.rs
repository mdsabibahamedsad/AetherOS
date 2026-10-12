use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageConfig {
    pub base_path: String,
    pub downloaded: String,
    pub imported: String,
    pub cached: String,
    pub temp: String,
    pub shared: String,
}

impl Default for StorageConfig {
    fn default() -> Self {
        let home = crate::paths::aetheros_home();
        Self {
            base_path: home.join("models").to_string_lossy().to_string(),
            downloaded: home.join("models").join("downloaded").to_string_lossy().to_string(),
            imported: home.join("models").join("imported").to_string_lossy().to_string(),
            cached: home.join("cache").join("models").to_string_lossy().to_string(),
            temp: home.join("tmp").join("models").to_string_lossy().to_string(),
            shared: home.join("models").join("shared").to_string_lossy().to_string(),
        }
    }
}

pub fn storage_config() -> StorageConfig {
    let config_path = crate::paths::aetheros_home().join("config").join("model-storage.json");
    if config_path.exists() {
        if let Ok(content) = std::fs::read_to_string(&config_path) {
            if let Ok(config) = serde_json::from_str::<StorageConfig>(&content) {
                return config;
            }
        }
    }
    StorageConfig::default()
}

pub fn save_storage_config(config: &StorageConfig) -> Result<(), String> {
    let config_path = crate::paths::aetheros_home().join("config").join("model-storage.json");
    if let Some(parent) = config_path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(config).map_err(|e| format!("Serialize error: {e}"))?;
    std::fs::write(&config_path, content).map_err(|e| format!("Write error: {e}"))?;
    Ok(())
}

pub fn ensure_dirs(config: &StorageConfig) -> Result<(), String> {
    let dirs = [
        &config.base_path,
        &config.downloaded,
        &config.imported,
        &config.cached,
        &config.temp,
        &config.shared,
    ];
    for dir in dirs {
        std::fs::create_dir_all(dir).map_err(|e| format!("Cannot create {dir}: {e}"))?;
    }
    Ok(())
}

pub fn model_path(provider: &str, model_name: &str, storage: &StorageConfig) -> PathBuf {
    let safe_provider = sanitize_name(provider);
    let safe_name = sanitize_name(model_name);
    PathBuf::from(&storage.downloaded).join(safe_provider).join(safe_name)
}

pub fn temp_download_path(url: &str, storage: &StorageConfig) -> PathBuf {
    let hash = sha256_string(url);
    PathBuf::from(&storage.temp).join(format!("dl-{}.tmp", &hash[..16]))
}

pub fn cached_model_path(hash: &str, storage: &StorageConfig) -> PathBuf {
    PathBuf::from(&storage.cached).join(format!("{}.model", hash))
}

fn sanitize_name(name: &str) -> String {
    name.chars()
        .map(|c| if c.is_alphanumeric() || c == '-' || c == '_' || c == '.' { c } else { '_' })
        .collect()
}

fn sha256_string(input: &str) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    format!("{:x}", hasher.finalize())
}

pub fn get_storage_stats() -> Result<StorageStats, String> {
    let config = storage_config();
    let mut stats = StorageStats {
        total_models: 0,
        total_size: 0,
        downloaded_size: 0,
        imported_size: 0,
        cached_size: 0,
        temp_size: 0,
        free_space: 0,
        config: config.clone(),
    };

    stats.downloaded_size = dir_size(PathBuf::from(&config.downloaded));
    stats.imported_size = dir_size(PathBuf::from(&config.imported));
    stats.cached_size = dir_size(PathBuf::from(&config.cached));
    stats.temp_size = dir_size(PathBuf::from(&config.temp));
    stats.total_size = stats.downloaded_size + stats.imported_size + stats.cached_size;
    stats.free_space = crate::disk_manager::get_free_space(std::path::Path::new(&config.base_path));

    Ok(stats)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageStats {
    pub total_models: u64,
    pub total_size: u64,
    pub downloaded_size: u64,
    pub imported_size: u64,
    pub cached_size: u64,
    pub temp_size: u64,
    pub free_space: u64,
    pub config: StorageConfig,
}

fn dir_size(path: PathBuf) -> u64 {
    let mut total = 0u64;
    if let Ok(entries) = std::fs::read_dir(&path) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() {
                total += dir_size(p);
            } else if let Ok(meta) = entry.metadata() {
                total += meta.len();
            }
        }
    }
    total
}

#[tauri::command]
pub async fn get_model_storage_config() -> Result<StorageConfig, String> {
    Ok(storage_config())
}

#[tauri::command]
pub async fn set_model_storage_config(config: StorageConfig) -> Result<(), String> {
    save_storage_config(&config)?;
    ensure_dirs(&config)
}

#[tauri::command]
pub async fn get_model_storage_stats() -> Result<StorageStats, String> {
    get_storage_stats()
}

#[tauri::command]
pub async fn clean_model_temp_files() -> Result<u64, String> {
    let config = storage_config();
    let tmp = PathBuf::from(&config.temp);
    if !tmp.exists() {
        return Ok(0);
    }
    let mut total = 0u64;
    if let Ok(entries) = std::fs::read_dir(&tmp) {
        for entry in entries.flatten() {
            let path = entry.path();
            if let Ok(meta) = entry.metadata() {
                total += meta.len();
            }
            std::fs::remove_file(&path).ok();
        }
    }
    Ok(total)
}
