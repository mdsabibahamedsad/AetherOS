use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiskSpaceInfo {
    pub available_bytes: u64,
    pub required_bytes: u64,
    pub sufficient: bool,
    pub message: String,
    pub total_bytes: u64,
}

pub const MIN_INSTALL_SPACE: u64 = 1_500_000_000; // 1.5 GB
pub const MIN_CACHE_SPACE: u64 = 500_000_000; // 500 MB
pub const MIN_TEMP_SPACE: u64 = 200_000_000; // 200 MB

pub fn check_disk_space(path: &Path) -> DiskSpaceInfo {
    let available = get_free_space(path);
    let required = MIN_INSTALL_SPACE + MIN_CACHE_SPACE + MIN_TEMP_SPACE;

    DiskSpaceInfo {
        available_bytes: available,
        required_bytes: required,
        sufficient: available >= required,
        message: format_disk_message(available, required),
        total_bytes: get_total_space(path),
    }
}

pub fn estimate_install_required(additional: u64) -> DiskSpaceInfo {
    let install_path = crate::paths::aetheros_home();
    let available = get_free_space(&install_path);
    let required = MIN_INSTALL_SPACE + MIN_CACHE_SPACE + MIN_TEMP_SPACE + additional;

    DiskSpaceInfo {
        available_bytes: available,
        required_bytes: required,
        sufficient: available >= required,
        message: format_disk_message(available, required),
        total_bytes: get_total_space(&install_path),
    }
}

pub fn get_free_space(path: &Path) -> u64 {
    use fs2::available_space;
    available_space(path).unwrap_or(1_000_000_000_000)
}

pub fn get_total_space(path: &Path) -> u64 {
    // Estimate from free space (we don't have a cross-platform total-space API
    // without extra deps; this is a reasonable proxy)
    get_free_space(path) * 2
}

pub async fn clean_temp_files() -> Result<u64, String> {
    let tmp_dir = crate::paths::aetheros_home().join("tmp");
    let mut total = 0u64;

    if !tmp_dir.exists() {
        return Ok(0);
    }

    let entries: Vec<_> = std::fs::read_dir(&tmp_dir)
        .map_err(|e| format!("Cannot read tmp dir: {e}"))?
        .flatten()
        .collect();

    for entry in &entries {
        let path = entry.path();
        if path.is_dir() {
            if let Ok(size) = dir_size(&path) {
                total += size;
            }
            let _ = std::fs::remove_dir_all(&path);
        } else {
            if let Ok(meta) = std::fs::metadata(&path) {
                total += meta.len();
            }
            let _ = std::fs::remove_file(&path);
        }
    }

    tracing::info!(removed = total, "temp files cleaned");
    Ok(total)
}

pub async fn clean_extraction_dirs() -> Result<u64, String> {
    let cache_dir = crate::paths::aetheros_home().join("bootstrap-cache");
    let mut total = 0u64;

    if !cache_dir.exists() {
        return Ok(0);
    }

    let entries: Vec<_> = std::fs::read_dir(&cache_dir)
        .map_err(|e| format!("Cannot read cache dir: {e}"))?
        .flatten()
        .collect();

    for entry in &entries {
        let path = entry.path();
        if path.is_dir() && path.file_name().and_then(|n| n.to_str()).map_or(false, |n| n.starts_with("extract-")) {
            if let Ok(size) = dir_size(&path) {
                total += size;
            }
            let _ = std::fs::remove_dir_all(&path);
        }
    }

    tracing::info!(removed = total, "extraction dirs cleaned");
    Ok(total)
}

fn dir_size(path: &Path) -> std::io::Result<u64> {
    let mut total = 0u64;
    if path.is_dir() {
        for entry in std::fs::read_dir(path)? {
            let entry = entry?;
            let path = entry.path();
            if path.is_dir() {
                total += dir_size(&path)?;
            } else {
                total += entry.metadata()?.len();
            }
        }
    }
    Ok(total)
}

fn format_disk_message(available: u64, required: u64) -> String {
    let avail_mb = available / (1024 * 1024);
    let req_mb = required / (1024 * 1024);

    if available >= required {
        format!("{avail_mb} MB available — sufficient for installation ({req_mb} MB required)")
    } else {
        let short_mb = req_mb - avail_mb;
        format!(
            "Only {avail_mb} MB available, but {req_mb} MB is required. \
             Please free at least {short_mb} MB and try again."
        )
    }
}

#[tauri::command]
pub async fn check_install_disk_space() -> Result<DiskSpaceInfo, String> {
    Ok(check_disk_space(&crate::paths::aetheros_home()))
}

#[tauri::command]
pub async fn clean_install_temp_files() -> Result<u64, String> {
    let cleaned = clean_temp_files().await?;
    let extracted = clean_extraction_dirs().await?;
    Ok(cleaned + extracted)
}
