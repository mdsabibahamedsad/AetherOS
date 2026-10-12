use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheEntry {
    pub url: String,
    pub filename: String,
    pub size: u64,
    pub checksum: Option<String>,
    pub downloaded_at: u64,
    pub last_accessed: u64,
    pub access_count: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheManifest {
    pub entries: HashMap<String, CacheEntry>,
    pub max_size_bytes: u64,
    pub created_at: u64,
}

const DEFAULT_MAX_CACHE_SIZE: u64 = 2_000_000_000; // 2 GB
const CACHE_CLEANUP_INTERVAL_SECS: u64 = 86400; // 24 hours
const STALE_DAYS: u64 = 30;

pub fn cache_dir() -> PathBuf {
    crate::paths::aetheros_home().join("cache").join("packages")
}

fn cache_manifest_path() -> PathBuf {
    cache_dir().join(".cache-manifest.json")
}

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn load_cache_manifest() -> CacheManifest {
    let path = cache_manifest_path();
    if !path.exists() {
        let _ = std::fs::create_dir_all(cache_dir());
        return CacheManifest {
            entries: HashMap::new(),
            max_size_bytes: DEFAULT_MAX_CACHE_SIZE,
            created_at: now_secs(),
        };
    }
    match std::fs::read_to_string(&path) {
        Ok(content) => serde_json::from_str(&content).unwrap_or(CacheManifest {
            entries: HashMap::new(),
            max_size_bytes: DEFAULT_MAX_CACHE_SIZE,
            created_at: now_secs(),
        }),
        Err(_) => CacheManifest {
            entries: HashMap::new(),
            max_size_bytes: DEFAULT_MAX_CACHE_SIZE,
            created_at: now_secs(),
        },
    }
}

fn save_cache_manifest(manifest: &CacheManifest) -> Result<(), String> {
    let path = cache_manifest_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Failed to create cache dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(manifest)
        .map_err(|e| format!("Failed to serialize cache: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Failed to write cache: {e}"))?;
    Ok(())
}

pub fn cached_path(url: &str, _expected_filename: Option<&str>) -> Option<PathBuf> {
    let manifest = load_cache_manifest();
    let entry = manifest.entries.get(url)?;
    let cached = cache_dir().join(&entry.filename);
    if !cached.exists() {
        return None;
    }
    drop(manifest);
    touch_cache_entry(url);
    Some(cached)
}

pub fn add_to_cache(url: &str, file_path: &Path, checksum: Option<&str>) -> Result<PathBuf, String> {
    let filename = file_path
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| {
            let name = url.rsplit('/').next().unwrap_or("unknown");
            sanitize_filename(name)
        });

    let size = std::fs::metadata(file_path)
        .map_err(|e| format!("Cannot stat cached file: {e}"))?
        .len();

    let cached_dest = cache_dir().join(&filename);
    if cached_dest.exists() {
        let _ = std::fs::remove_file(&cached_dest);
    }

    std::fs::copy(file_path, &cached_dest)
        .map_err(|e| format!("Failed to copy to cache: {e}"))?;

    let mut manifest = load_cache_manifest();
    manifest.entries.insert(
        url.to_string(),
        CacheEntry {
            url: url.to_string(),
            filename,
            size,
            checksum: checksum.map(|s| s.to_string()),
            downloaded_at: now_secs(),
            last_accessed: now_secs(),
            access_count: 1,
        },
    );

    enforce_cache_size(&mut manifest)?;
    save_cache_manifest(&manifest)?;

    Ok(cached_dest)
}

fn touch_cache_entry(url: &str) {
    let mut manifest = load_cache_manifest();
    if let Some(entry) = manifest.entries.get_mut(url) {
        entry.last_accessed = now_secs();
        entry.access_count += 1;
    }
    let _ = save_cache_manifest(&manifest);
}

fn enforce_cache_size(manifest: &mut CacheManifest) -> Result<(), String> {
    let total: u64 = manifest.entries.values().map(|e| e.size).sum();
    if total <= manifest.max_size_bytes {
        return Ok(());
    }

    let mut entries: Vec<(String, u64, String, f64)> = manifest.entries.iter()
        .map(|(k, v)| {
            let score = v.access_count as f64 / (now_secs() - v.last_accessed + 1).max(1) as f64;
            (k.clone(), v.size, v.filename.clone(), score)
        })
        .collect();
    entries.sort_by(|a, b| a.3.partial_cmp(&b.3).unwrap_or(std::cmp::Ordering::Equal));

    let mut removed: u64 = 0;
    let target = manifest.max_size_bytes / 2;
    for (url, size, filename, _score) in &entries {
        if total - removed <= target {
            break;
        }
        let cached = cache_dir().join(filename);
        if cached.exists() {
            let _ = std::fs::remove_file(&cached);
        }
        manifest.entries.remove(url);
        removed += size;
    }

    tracing::info!(removed_bytes = removed, "cache cleanup completed");
    Ok(())
}

pub fn cleanup_stale_entries(max_age_days: Option<u64>) -> Result<u64, String> {
    let max_age = max_age_days.unwrap_or(STALE_DAYS);
    let cutoff = now_secs() - (max_age * 86400);
    let mut manifest = load_cache_manifest();
    let mut removed = 0u64;

    let stale: Vec<String> = manifest
        .entries
        .iter()
        .filter(|(_, e)| e.last_accessed < cutoff)
        .map(|(k, _)| k.clone())
        .collect();

    for url in &stale {
        if let Some(entry) = manifest.entries.remove(url) {
            let cached = cache_dir().join(&entry.filename);
            if cached.exists() {
                let _ = std::fs::remove_file(&cached);
            }
            removed += entry.size;
        }
    }

    if !stale.is_empty() {
        save_cache_manifest(&manifest)?;
        tracing::info!(stale_count = stale.len(), removed_bytes = removed, "stale cache cleanup");
    }

    Ok(removed)
}

pub fn get_cache_size() -> Result<(u64, usize), String> {
    let manifest = load_cache_manifest();
    let total: u64 = manifest.entries.values().map(|e| e.size).sum();
    Ok((total, manifest.entries.len()))
}

pub fn clear_cache() -> Result<u64, String> {
    let mut manifest = load_cache_manifest();
    let total: u64 = manifest.entries.values().map(|e| e.size).sum();
    for entry in manifest.entries.values() {
        let cached = cache_dir().join(&entry.filename);
        if cached.exists() {
            let _ = std::fs::remove_file(&cached);
        }
    }
    manifest.entries.clear();
    save_cache_manifest(&manifest)?;
    Ok(total)
}

fn sanitize_filename(name: &str) -> String {
    name.chars()
        .map(|c| if c.is_alphanumeric() || c == '.' || c == '-' || c == '_' { c } else { '_' })
        .collect()
}

pub async fn find_in_cache(name: &str, version: &str) -> Option<PathBuf> {
    let dir = cache_dir();
    if !dir.exists() {
        return None;
    }
    let pattern = format!("{name}-{version}");
    if let Ok(entries) = std::fs::read_dir(&dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if let Some(filename) = path.file_name().and_then(|n| n.to_str()) {
                if filename.contains(&pattern) || filename == name {
                    return Some(path);
                }
            }
        }
    }
    None
}

#[tauri::command]
pub async fn get_cache_status() -> Result<serde_json::Value, String> {
    let (size, count) = get_cache_size()?;
    Ok(serde_json::json!({
        "size_bytes": size,
        "entry_count": count,
        "max_size_bytes": DEFAULT_MAX_CACHE_SIZE,
    }))
}

#[tauri::command]
pub async fn clear_cache_command() -> Result<u64, String> {
    clear_cache()
}
