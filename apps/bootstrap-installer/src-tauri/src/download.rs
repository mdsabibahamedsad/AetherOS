use futures::StreamExt;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter};
use tokio::io::AsyncWriteExt;
use tokio::sync::Mutex;

pub const DOWNLOAD_EVENT_CHANNEL: &str = "download";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum DownloadStatus {
    Pending,
    Downloading,
    Paused,
    Completed,
    Failed(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DownloadItem {
    pub id: String,
    pub url: String,
    pub dest: String,
    pub size: Option<u64>,
    pub downloaded: u64,
    pub status: DownloadStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DownloadProgress {
    pub id: String,
    pub url: String,
    pub downloaded: u64,
    pub total: Option<u64>,
    pub speed: f64,
    pub elapsed_secs: f64,
    pub eta_secs: Option<f64>,
    pub status: DownloadStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DownloadQueue {
    pub items: Vec<DownloadItem>,
    pub active: Option<String>,
    pub total_downloaded: u64,
    pub total_size: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct DownloadEvent {
    pub id: String,
    pub url: String,
    pub downloaded: u64,
    pub total: Option<u64>,
    pub speed: f64,
    pub status: String,
}

static DOWNLOAD_QUEUE: std::sync::OnceLock<Mutex<Vec<DownloadItem>>> = std::sync::OnceLock::new();

fn queue() -> &'static Mutex<Vec<DownloadItem>> {
    DOWNLOAD_QUEUE.get_or_init(|| Mutex::new(Vec::new()))
}

fn format_size(bytes: u64) -> String {
    const KB: f64 = 1024.0;
    const MB: f64 = KB * 1024.0;
    const GB: f64 = MB * 1024.0;
    if bytes as f64 >= GB {
        format!("{:.1} GB", bytes as f64 / GB)
    } else if bytes as f64 >= MB {
        format!("{:.1} MB", bytes as f64 / MB)
    } else if bytes as f64 >= KB {
        format!("{:.1} KB", bytes as f64 / KB)
    } else {
        format!("{bytes} B")
    }
}

fn format_speed(bytes_per_sec: f64) -> String {
    format!("{}/s", format_size(bytes_per_sec as u64))
}

pub async fn download_file_inner(
    app: &AppHandle,
    url: &str,
    dest: &PathBuf,
) -> Result<DownloadProgress, String> {
    let id = uuid::Uuid::new_v4().to_string();

    if let Some(parent) = dest.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create destination directory: {e}"))?;
    }

    {
        let mut q = queue().lock().await;
        q.push(DownloadItem {
            id: id.clone(),
            url: url.to_string(),
            dest: dest.to_string_lossy().to_string(),
            size: None,
            downloaded: 0,
            status: DownloadStatus::Downloading,
        });
    }

    tracing::info!(url, ?dest, "starting download");

    let client = reqwest::Client::builder()
        .user_agent("aetheros-setup/0.0.1")
        .timeout(Duration::from_secs(3600))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {e}"))?;

    let response = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Download request failed: {e}"))?;

    if !response.status().is_success() {
        return Err(format!(
            "Download failed with HTTP {}",
            response.status()
        ));
    }

    let total = response.content_length();
    let mut downloaded: u64 = 0;
    let start = Instant::now();
    let mut last_emit = Instant::now();

    let tmp_path = dest.with_extension("tmp");
    let mut file = tokio::fs::File::create(&tmp_path)
        .await
        .map_err(|e| format!("Failed to create file: {e}"))?;

    let mut stream = response.bytes_stream();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|e| format!("Stream error: {e}"))?;
        file.write_all(&chunk)
            .await
            .map_err(|e| format!("Write error: {e}"))?;
        downloaded += chunk.len() as u64;

        if last_emit.elapsed() > Duration::from_millis(250) {
            let elapsed = start.elapsed().as_secs_f64();
            let speed = if elapsed > 0.0 {
                downloaded as f64 / elapsed
            } else {
                0.0
            };

            let event = DownloadEvent {
                id: id.clone(),
                url: url.to_string(),
                downloaded,
                total,
                speed,
                status: "downloading".to_string(),
            };
            let _ = app.emit(DOWNLOAD_EVENT_CHANNEL, &event);

            {
                let mut q = queue().lock().await;
                if let Some(item) = q.iter_mut().find(|i| i.id == id) {
                    item.downloaded = downloaded;
                    item.size = total;
                }
            }

            last_emit = Instant::now();
        }
    }

    file.flush().await.map_err(|e| format!("Flush error: {e}"))?;
    drop(file);

    tokio::fs::rename(&tmp_path, dest)
        .await
        .map_err(|e| format!("Failed to finalize download: {e}"))?;

    let elapsed = start.elapsed().as_secs_f64();
    let speed = if elapsed > 0.0 {
        downloaded as f64 / elapsed
    } else {
        0.0
    };

    tracing::info!(url, size = downloaded, elapsed_secs = elapsed, "download completed");

    {
        let mut q = queue().lock().await;
        if let Some(item) = q.iter_mut().find(|i| i.id == id) {
            item.status = DownloadStatus::Completed;
            item.downloaded = downloaded;
            item.size = Some(downloaded);
        }
    }

    let _ = app.emit(DOWNLOAD_EVENT_CHANNEL, &DownloadEvent {
        id: id.clone(),
        url: url.to_string(),
        downloaded,
        total: Some(downloaded),
        speed,
        status: "completed".to_string(),
    });

    Ok(DownloadProgress {
        id,
        url: url.to_string(),
        downloaded,
        total: Some(downloaded),
        speed,
        elapsed_secs: elapsed,
        eta_secs: None,
        status: DownloadStatus::Completed,
    })
}

#[tauri::command]
pub async fn download_file(
    app: AppHandle,
    url: String,
    dest_path: String,
) -> Result<DownloadProgress, String> {
    let dest = PathBuf::from(&dest_path);
    download_file_inner(&app, &url, &dest).await
}

#[tauri::command]
pub async fn get_download_queue() -> Result<DownloadQueue, String> {
    let q = queue().lock().await;
    let total_downloaded: u64 = q.iter().map(|i| i.downloaded).sum();
    let total_size: Option<u64> = q.iter().filter_map(|i| i.size).reduce(|a, b| a + b);
    let active = q.iter().find(|i| i.status == DownloadStatus::Downloading).map(|i| i.id.clone());

    Ok(DownloadQueue {
        items: q.clone(),
        active,
        total_downloaded,
        total_size,
    })
}

#[tauri::command]
pub async fn get_download_progress() -> Result<Vec<DownloadProgress>, String> {
    Ok(Vec::new())
}

#[tauri::command]
pub async fn clear_download_queue() -> Result<(), String> {
    let mut q = queue().lock().await;
    q.retain(|i| i.status == DownloadStatus::Downloading);
    Ok(())
}

#[tauri::command]
pub async fn retry_failed_downloads() -> Result<(), String> {
    let mut q = queue().lock().await;
    for item in q.iter_mut() {
        if matches!(item.status, DownloadStatus::Failed(_)) {
            item.status = DownloadStatus::Pending;
        }
    }
    Ok(())
}
