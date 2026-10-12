use serde::Serialize;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize)]
pub struct LogEntry {
    pub timestamp: String,
    pub level: String,
    pub module: String,
    pub message: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct LogSummary {
    pub log_path: String,
    pub entry_count: usize,
    pub error_count: usize,
    pub warning_count: usize,
}

fn log_path() -> PathBuf {
    crate::paths::log_dir().join("bootstrap-installer.log")
}

#[tauri::command]
pub async fn get_log_summary() -> Result<LogSummary, String> {
    let path = log_path();
    if !path.exists() {
        return Ok(LogSummary {
            log_path: path.to_string_lossy().into_owned(),
            entry_count: 0,
            error_count: 0,
            warning_count: 0,
        });
    }

    let content = std::fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read log: {e}"))?;

    let entry_count = content.lines().filter(|l| !l.is_empty()).count();
    let error_count = content.lines().filter(|l| l.contains(" ERROR ")).count();
    let warning_count = content.lines().filter(|l| l.contains(" WARN ")).count();

    Ok(LogSummary {
        log_path: path.to_string_lossy().into_owned(),
        entry_count,
        error_count,
        warning_count,
    })
}

#[tauri::command]
pub async fn read_log_tail(
    max_lines: Option<usize>,
) -> Result<Vec<String>, String> {
    let path = log_path();
    if !path.exists() {
        return Ok(Vec::new());
    }

    let content = std::fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read log: {e}"))?;

    let lines: Vec<String> = content.lines().map(|l| l.to_string()).collect();
    let max = max_lines.unwrap_or(100);
    if lines.len() > max {
        Ok(lines[lines.len() - max..].to_vec())
    } else {
        Ok(lines)
    }
}
