use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileTypeDefinition {
    pub extension: String,
    pub name: String,
    pub category: String,
    pub icon: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanResult {
    pub total_files: usize,
    pub total_size: u64,
    pub by_type: Vec<FileTypeCount>,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileTypeCount {
    pub extension: String,
    pub count: usize,
    pub size: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportResult {
    pub imported: usize,
    pub skipped: usize,
    pub failed: usize,
    pub errors: Vec<String>,
}

pub fn supported_file_types() -> Vec<FileTypeDefinition> {
    vec![
        FileTypeDefinition { extension: "md".into(), name: "Markdown".into(), category: "documentation".into(), icon: "file-text".into() },
        FileTypeDefinition { extension: "pdf".into(), name: "PDF Document".into(), category: "document".into(), icon: "file".into() },
        FileTypeDefinition { extension: "txt".into(), name: "Text File".into(), category: "text".into(), icon: "file-text".into() },
        FileTypeDefinition { extension: "csv".into(), name: "CSV Spreadsheet".into(), category: "data".into(), icon: "table".into() },
        FileTypeDefinition { extension: "json".into(), name: "JSON Data".into(), category: "data".into(), icon: "code".into() },
        FileTypeDefinition { extension: "yaml".into(), name: "YAML Config".into(), category: "config".into(), icon: "code".into() },
        FileTypeDefinition { extension: "yml".into(), name: "YAML Config".into(), category: "config".into(), icon: "code".into() },
        FileTypeDefinition { extension: "toml".into(), name: "TOML Config".into(), category: "config".into(), icon: "code".into() },
        FileTypeDefinition { extension: "xml".into(), name: "XML Data".into(), category: "data".into(), icon: "code".into() },
        FileTypeDefinition { extension: "html".into(), name: "HTML Document".into(), category: "web".into(), icon: "globe".into() },
        FileTypeDefinition { extension: "py".into(), name: "Python Source".into(), category: "code".into(), icon: "terminal".into() },
        FileTypeDefinition { extension: "js".into(), name: "JavaScript Source".into(), category: "code".into(), icon: "terminal".into() },
        FileTypeDefinition { extension: "ts".into(), name: "TypeScript Source".into(), category: "code".into(), icon: "terminal".into() },
        FileTypeDefinition { extension: "rs".into(), name: "Rust Source".into(), category: "code".into(), icon: "terminal".into() },
        FileTypeDefinition { extension: "go".into(), name: "Go Source".into(), category: "code".into(), icon: "terminal".into() },
        FileTypeDefinition { extension: "java".into(), name: "Java Source".into(), category: "code".into(), icon: "terminal".into() },
        FileTypeDefinition { extension: "cpp".into(), name: "C++ Source".into(), category: "code".into(), icon: "terminal".into() },
        FileTypeDefinition { extension: "docx".into(), name: "Word Document".into(), category: "document".into(), icon: "file".into() },
        FileTypeDefinition { extension: "xlsx".into(), name: "Excel Spreadsheet".into(), category: "data".into(), icon: "table".into() },
    ]
}

pub fn scan_path(path: &Path, allowed_extensions: &[String]) -> Result<ScanResult, String> {
    if !path.exists() {
        return Err(format!("Path does not exist: {}", path.display()));
    }
    if !path.is_dir() {
        return Err(format!("Not a directory: {}", path.display()));
    }

    let mut total_files = 0usize;
    let mut total_size = 0u64;
    let mut by_type: std::collections::HashMap<String, (usize, u64)> = std::collections::HashMap::new();
    let mut errors = Vec::new();

    let lower_allowed: Vec<String> = allowed_extensions.iter()
        .map(|e| e.trim_start_matches('.').to_lowercase())
        .collect();

    scan_recursive(path, &lower_allowed, &mut total_files, &mut total_size, &mut by_type, &mut errors);

    let by_type: Vec<FileTypeCount> = by_type
        .into_iter()
        .map(|(ext, (count, size))| FileTypeCount { extension: ext, count, size })
        .collect();

    Ok(ScanResult { total_files, total_size, by_type, errors })
}

fn scan_recursive(
    dir: &Path,
    allowed: &[String],
    total_files: &mut usize,
    total_size: &mut u64,
    by_type: &mut std::collections::HashMap<String, (usize, u64)>,
    errors: &mut Vec<String>,
) {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                scan_recursive(&path, allowed, total_files, total_size, by_type, errors);
            } else if path.is_file() {
                if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                    let ext_lower = ext.to_lowercase();
                    if !allowed.is_empty() && !allowed.contains(&ext_lower) {
                        continue;
                    }
                    *total_files += 1;
                    if let Ok(meta) = entry.metadata() {
                        *total_size += meta.len();
                    }
                    let entry = by_type.entry(ext_lower).or_insert((0, 0));
                    (*entry).0 += 1;
                    (*entry).1 += 1;
                }
            }
        }
    }
}

pub fn import_knowledge(
    sources: &[PathBuf],
    dest: &Path,
    allowed_extensions: &[String],
) -> Result<ImportResult, String> {
    std::fs::create_dir_all(dest).map_err(|e| format!("Cannot create knowledge dir: {e}"))?;

    let mut imported = 0usize;
    let mut skipped = 0usize;
    let mut failed = 0usize;
    let mut errors = Vec::new();

    for src in sources {
        if !src.exists() {
            skipped += 1;
            errors.push(format!("Source not found: {}", src.display()));
            continue;
        }

        if src.is_dir() {
            match copy_dir_with_filter(src, dest, allowed_extensions) {
                Ok((imp, skp)) => {
                    imported += imp;
                    skipped += skp;
                }
                Err(e) => {
                    failed += 1;
                    errors.push(format!("Failed to import {}: {e}", src.display()));
                }
            }
        } else if let Some(name) = src.file_name() {
            let ext = src.extension().and_then(|e| e.to_str()).unwrap_or("");
            let ext_lower = ext.to_lowercase();
            if !allowed_extensions.is_empty() && !allowed_extensions.contains(&ext_lower.to_string()) {
                skipped += 1;
                continue;
            }
            let dest_path = dest.join(name);
            match std::fs::copy(src, &dest_path) {
                Ok(_) => imported += 1,
                Err(e) => {
                    failed += 1;
                    errors.push(format!("Failed to copy {}: {e}", src.display()));
                }
            }
        }
    }

    Ok(ImportResult { imported, skipped, failed, errors })
}

fn copy_dir_with_filter(
    src: &Path,
    dest: &Path,
    allowed: &[String],
) -> Result<(usize, usize), String> {
    let mut imported = 0usize;
    let mut skipped = 0usize;

    if let Ok(entries) = std::fs::read_dir(src) {
        for entry in entries.flatten() {
            let path = entry.path();
            let relative = path.strip_prefix(src).unwrap_or(&path);
            let dest_path = dest.join(relative);

            if path.is_dir() {
                std::fs::create_dir_all(&dest_path).ok();
                let (imp, skp) = copy_dir_with_filter(&path, &dest_path, allowed)?;
                imported += imp;
                skipped += skp;
            } else if path.is_file() {
                let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
                let ext_lower = ext.to_lowercase();
                if !allowed.is_empty() && !allowed.contains(&ext_lower.to_string()) {
                    skipped += 1;
                    continue;
                }
                if let Some(parent) = dest_path.parent() {
                    std::fs::create_dir_all(parent).ok();
                }
                match std::fs::copy(&path, &dest_path) {
                    Ok(_) => imported += 1,
                    Err(e) => {
                        let _ = e;
                        skipped += 1;
                    }
                }
            }
        }
    }

    Ok((imported, skipped))
}

#[tauri::command]
pub async fn get_supported_file_types() -> Result<Vec<FileTypeDefinition>, String> {
    Ok(supported_file_types())
}

#[tauri::command]
pub async fn scan_directory(path: String, allowed_extensions: Vec<String>) -> Result<ScanResult, String> {
    scan_path(Path::new(&path), &allowed_extensions)
}

#[tauri::command]
pub async fn import_files(sources: Vec<String>, dest: String, allowed_extensions: Vec<String>) -> Result<ImportResult, String> {
    let src_paths: Vec<PathBuf> = sources.iter().map(PathBuf::from).collect();
    import_knowledge(&src_paths, Path::new(&dest), &allowed_extensions)
}
