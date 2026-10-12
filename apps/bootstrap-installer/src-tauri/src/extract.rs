use std::path::{Path, PathBuf};
use std::time::Instant;
use tauri::{AppHandle, Emitter};

pub const EXTRACT_EVENT_CHANNEL: &str = "extract";

#[derive(Debug, Clone, serde::Serialize)]
pub struct ExtractProgress {
    pub file: String,
    pub current: usize,
    pub total: usize,
    pub percent: f64,
    pub elapsed_secs: f64,
}

pub async fn extract_zip(
    app: &AppHandle,
    zip_path: &Path,
    dest: &Path,
) -> Result<u64, String> {
    if !zip_path.exists() {
        return Err(format!(
            "Package not found at {}",
            zip_path.display()
        ));
    }

    if !zip_path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.eq_ignore_ascii_case("zip"))
        .unwrap_or(false)
    {
        return Err(format!(
            "Not a ZIP file: {}",
            zip_path.display()
        ));
    }

    if dest.exists() {
        std::fs::remove_dir_all(dest)
            .map_err(|e| format!("Failed to clean destination {}: {e}", dest.display()))?;
    }
    std::fs::create_dir_all(dest)
        .map_err(|e| format!("Failed to create destination {}: {e}", dest.display()))?;

    let file = std::fs::File::open(zip_path)
        .map_err(|e| format!("Failed to open ZIP file: {e}"))?;

    let mut archive = zip::ZipArchive::new(file)
        .map_err(|e| format!("Failed to read ZIP archive: {e}"))?;

    let total_entries = archive.len();
    let start = Instant::now();

    for i in 0..total_entries {
        let mut entry = archive
            .by_index(i)
            .map_err(|e| format!("Failed to read entry {i}: {e}"))?;

        let entry_path = match entry.enclosed_name() {
            Some(p) => p.to_path_buf(),
            None => continue,
        };

        // Sanitize: reject paths with parent traversal
        let sanitized = sanitize_path(&entry_path);
        let target = dest.join(&sanitized);

        let entry_name = entry_path.to_string_lossy().to_string();

        let is_dir = entry.is_dir();

        if is_dir {
            std::fs::create_dir_all(&target).map_err(|e| {
                format!("Failed to create directory {}: {e}", target.display())
            })?;
        } else {
            if let Some(parent) = target.parent() {
                std::fs::create_dir_all(parent).map_err(|e| {
                    format!(
                        "Failed to create parent directory {}: {e}",
                        parent.display()
                    )
                })?;
            }

            let mut output = std::fs::File::create(&target).map_err(|e| {
                format!("Failed to create file {}: {e}", target.display())
            })?;

            std::io::copy(&mut entry, &mut output).map_err(|e| {
                format!("Failed to extract {}: {e}", target.display())
            })?;
        }

        if i % 10 == 0 || i == total_entries - 1 {
            let elapsed = start.elapsed().as_secs_f64();
            let percent = if total_entries > 0 {
                ((i + 1) as f64 / total_entries as f64) * 100.0
            } else {
                0.0
            };

            let _ = app.emit(
                EXTRACT_EVENT_CHANNEL,
                &ExtractProgress {
                    file: entry_name,
                    current: i + 1,
                    total: total_entries,
                    percent,
                    elapsed_secs: elapsed,
                },
            );
        }
    }

    let elapsed = start.elapsed().as_secs_f64();
    tracing::info!(
        entries = total_entries,
        dest = %dest.display(),
        elapsed_secs = elapsed,
        "extraction complete"
    );

    Ok(total_entries as u64)
}

pub fn verify_zip_integrity(zip_path: &Path) -> Result<(), String> {
    let file = std::fs::File::open(zip_path)
        .map_err(|e| format!("Cannot open ZIP for verification: {e}"))?;

    let mut archive = zip::ZipArchive::new(file)
        .map_err(|e| format!("ZIP archive is corrupt or invalid: {e}"))?;

    for i in 0..archive.len() {
        archive
            .by_index(i)
            .map_err(|e| format!("Entry {i} in ZIP archive is corrupt: {e}"))?;
    }

    Ok(())
}

fn sanitize_path(path: &Path) -> PathBuf {
    let mut sanitized = PathBuf::new();
    for component in path.components() {
        match component {
            std::path::Component::Normal(c) => {
                sanitized.push(c);
            }
            _ => {} // skip parent dirs, root, etc.
        }
    }
    sanitized
}

pub fn cleanup_extraction(extract_dir: &Path) {
    if extract_dir.exists() {
        if let Err(e) = std::fs::remove_dir_all(extract_dir) {
            tracing::warn!(
                ?e,
                "failed to clean up extraction directory {}",
                extract_dir.display()
            );
        }
    }
}

#[allow(dead_code)]
pub fn validate_extraction(
    extract_dir: &Path,
    expected_entries: Option<usize>,
) -> Result<usize, String> {
    if !extract_dir.exists() {
        return Err(format!(
            "Extraction directory does not exist: {}",
            extract_dir.display()
        ));
    }

    let count = count_entries(extract_dir);

    if let Some(expected) = expected_entries {
        if count < expected / 2 {
            return Err(format!(
                "Extraction appears incomplete: found {count} entries, expected ~{expected}"
            ));
        }
    }

    Ok(count)
}

fn count_entries(dir: &Path) -> usize {
    let mut count = 0;
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            count += 1;
            let path = entry.path();
            if path.is_dir() {
                count += count_entries(&path);
            }
        }
    }
    count
}
