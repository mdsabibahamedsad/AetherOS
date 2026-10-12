use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkspaceOptions {
    pub projects: bool,
    pub knowledge: bool,
    pub downloads: bool,
    pub extensions: bool,
    pub logs: bool,
    pub models: bool,
    pub cache: bool,
}

impl Default for WorkspaceOptions {
    fn default() -> Self {
        Self {
            projects: true,
            knowledge: true,
            downloads: true,
            extensions: true,
            logs: true,
            models: true,
            cache: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkspaceResult {
    pub created: Vec<String>,
    pub failed: Vec<String>,
    pub success: bool,
}

fn aetheros_home() -> PathBuf {
    crate::paths::aetheros_home()
}

pub fn build_workspace(options: &WorkspaceOptions) -> Result<WorkspaceResult, String> {
    let home = aetheros_home();
    let mut created = Vec::new();
    let mut failed = Vec::new();

    let dirs = vec![
        ("projects", options.projects, home.join("projects")),
        ("knowledge", options.knowledge, home.join("knowledge")),
        ("downloads", options.downloads, home.join("downloads")),
        ("extensions", options.extensions, home.join("extensions")),
        ("logs", options.logs, home.join("logs")),
        ("models", options.models, home.join("models")),
        ("cache", options.cache, home.join("cache")),
    ];

    for (name, enabled, path) in dirs {
        if !enabled {
            continue;
        }
        match std::fs::create_dir_all(&path) {
            Ok(()) => {
                created.push(name.to_string());
                tracing::info!(dir = %name, path = %path.display(), "workspace dir created");
            }
            Err(e) => {
                failed.push(format!("{name}: {e}"));
                tracing::error!(dir = %name, error = %e, "failed to create workspace dir");
            }
        }
    }

    // Write a .gitkeep in each created dir
    for dir_name in &created {
        let dir: PathBuf = match dir_name.as_str() {
            "projects" => home.join("projects"),
            "knowledge" => home.join("knowledge"),
            "downloads" => home.join("downloads"),
            "extensions" => home.join("extensions"),
            "logs" => home.join("logs"),
            "models" => home.join("models"),
            "cache" => home.join("cache"),
            _ => continue,
        };
        let gitkeep = dir.join(".gitkeep");
        std::fs::write(&gitkeep, b"").ok();
    }

    Ok(WorkspaceResult {
        success: failed.is_empty(),
        created,
        failed,
    })
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkspaceInfo {
    pub exists: bool,
    pub dirs: Vec<DirInfo>,
    pub total_size: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirInfo {
    pub name: String,
    pub exists: bool,
    pub size: u64,
}

pub fn check_workspace() -> WorkspaceInfo {
    let home = aetheros_home();
    let check_dirs = ["projects", "knowledge", "downloads", "extensions", "logs", "models", "cache"];
    let mut dirs = Vec::new();
    let mut total = 0u64;

    for name in &check_dirs {
        let path = home.join(name);
        let exists = path.exists();
        let size = if exists { dir_size(&path) } else { 0 };
        total += size;
        dirs.push(DirInfo {
            name: name.to_string(),
            exists,
            size,
        });
    }

    WorkspaceInfo {
        exists: dirs.iter().any(|d| d.exists),
        dirs,
        total_size: total,
    }
}

fn dir_size(path: &PathBuf) -> u64 {
    let mut total = 0u64;
    if let Ok(entries) = std::fs::read_dir(path) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() {
                total += dir_size(&p);
            } else if let Ok(meta) = entry.metadata() {
                total += meta.len();
            }
        }
    }
    total
}

#[tauri::command]
pub async fn create_workspace(options: WorkspaceOptions) -> Result<WorkspaceResult, String> {
    build_workspace(&options)
}

#[tauri::command]
pub async fn check_workspace_status() -> Result<WorkspaceInfo, String> {
    Ok(check_workspace())
}
