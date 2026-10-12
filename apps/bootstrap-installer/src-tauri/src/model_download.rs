use crate::model_storage::{self};
use futures::StreamExt;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter};
use tokio::io::AsyncWriteExt;
use tokio::sync::Mutex;

pub const MODEL_DOWNLOAD_EVENT_CHANNEL: &str = "model-download";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ModelDownloadStatus {
    Pending,
    Downloading,
    Paused,
    Completed,
    Failed(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelDownloadItem {
    pub id: String,
    pub model_id: String,
    pub model_name: String,
    pub provider: String,
    pub url: String,
    pub dest: PathBuf,
    pub temp_path: PathBuf,
    pub size: Option<u64>,
    pub downloaded: u64,
    pub status: ModelDownloadStatus,
    pub checksum: Option<String>,
    pub error_count: u32,
    pub max_retries: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelDownloadProgress {
    pub id: String,
    pub model_id: String,
    pub model_name: String,
    pub downloaded: u64,
    pub total: Option<u64>,
    pub speed: f64,
    pub elapsed_secs: f64,
    pub eta_secs: Option<f64>,
    pub status: ModelDownloadStatus,
    pub progress_pct: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelDownloadQueue {
    pub items: Vec<ModelDownloadItem>,
    pub active_ids: Vec<String>,
    pub max_concurrent: usize,
    pub total_downloaded: u64,
    pub total_size: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ModelDownloadEvent {
    pub id: String,
    pub model_id: String,
    pub downloaded: u64,
    pub total: Option<u64>,
    pub speed: f64,
    pub status: String,
    pub progress_pct: f64,
}

static DOWNLOAD_MANAGER: std::sync::OnceLock<Arc<DownloadManager>> = std::sync::OnceLock::new();

struct DownloadManager {
    queue: Mutex<Vec<ModelDownloadItem>>,
    paused: Mutex<HashMap<String, Arc<AtomicBool>>>,
    max_concurrent: Mutex<usize>,
    active_count: Mutex<usize>,
}

impl DownloadManager {
    fn new() -> Self {
        Self {
            queue: Mutex::new(Vec::new()),
            paused: Mutex::new(HashMap::new()),
            max_concurrent: Mutex::new(3),
            active_count: Mutex::new(0),
        }
    }
}

fn manager() -> &'static Arc<DownloadManager> {
    DOWNLOAD_MANAGER.get_or_init(|| Arc::new(DownloadManager::new()))
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

fn progress_pct(downloaded: u64, total: Option<u64>) -> f64 {
    match total {
        Some(t) if t > 0 => (downloaded as f64 / t as f64) * 100.0,
        _ => 0.0,
    }
}

async fn download_file_with_pause(
    app: AppHandle,
    item: &ModelDownloadItem,
    pause_flag: Arc<AtomicBool>,
) -> Result<ModelDownloadProgress, String> {
    let start = Instant::now();
    let mut downloaded: u64 = 0;
    let mut last_emit = Instant::now();

    let client = reqwest::Client::builder()
        .user_agent("aetheros-setup/0.0.1")
        .timeout(Duration::from_secs(7200))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {e}"))?;

    let response = client
        .get(&item.url)
        .send()
        .await
        .map_err(|e| format!("Download request failed: {e}"))?;

    if !response.status().is_success() {
        return Err(format!("Download failed with HTTP {}", response.status()));
    }

    let total = response.content_length();
    let mut file = tokio::fs::File::create(&item.temp_path)
        .await
        .map_err(|e| format!("Failed to create temp file: {e}"))?;

    let mut stream = response.bytes_stream();
    while let Some(chunk) = stream.next().await {
        if pause_flag.load(Ordering::Relaxed) {
            file.flush().await.ok();
            drop(file);
            return Ok(ModelDownloadProgress {
                id: item.id.clone(),
                model_id: item.model_id.clone(),
                model_name: item.model_name.clone(),
                downloaded,
                total,
                speed: 0.0,
                elapsed_secs: start.elapsed().as_secs_f64(),
                eta_secs: None,
                status: ModelDownloadStatus::Paused,
                progress_pct: progress_pct(downloaded, total),
            });
        }

        let chunk = chunk.map_err(|e| format!("Stream error: {e}"))?;
        file.write_all(&chunk)
            .await
            .map_err(|e| format!("Write error: {e}"))?;
        downloaded += chunk.len() as u64;

        if last_emit.elapsed() > Duration::from_millis(250) {
            let elapsed = start.elapsed().as_secs_f64();
            let speed = if elapsed > 0.0 { downloaded as f64 / elapsed } else { 0.0 };
            let pct = progress_pct(downloaded, total);

            let event = ModelDownloadEvent {
                id: item.id.clone(),
                model_id: item.model_id.clone(),
                downloaded,
                total,
                speed,
                status: "downloading".to_string(),
                progress_pct: pct,
            };
            let _ = app.emit(MODEL_DOWNLOAD_EVENT_CHANNEL, &event);

            {
                let mut q = manager().queue.lock().await;
                if let Some(qi) = q.iter_mut().find(|i| i.id == item.id) {
                    qi.downloaded = downloaded;
                    qi.size = total;
                }
            }

            last_emit = Instant::now();
        }
    }

    file.flush().await.map_err(|e| format!("Flush error: {e}"))?;
    drop(file);

    tokio::fs::rename(&item.temp_path, &item.dest)
        .await
        .map_err(|e| format!("Failed to finalize download: {e}"))?;

    if let Some(ref checksum) = item.checksum {
        let computed = crate::verification::compute_sha256(&item.dest)
            .map_err(|e| format!("Checksum error: {e}"))?;
        if computed != *checksum {
            let _ = tokio::fs::remove_file(&item.dest).await;
            return Err(format!("Checksum mismatch: expected {checksum}, got {computed}"));
        }
    }

    let elapsed = start.elapsed().as_secs_f64();
    let speed = if elapsed > 0.0 { downloaded as f64 / elapsed } else { 0.0 };
    let pct = 100.0;

    {
        let mut q = manager().queue.lock().await;
        if let Some(qi) = q.iter_mut().find(|i| i.id == item.id) {
            qi.status = ModelDownloadStatus::Completed;
            qi.downloaded = downloaded;
            qi.size = Some(downloaded);
        }
    }

    let _ = app.emit(MODEL_DOWNLOAD_EVENT_CHANNEL, &ModelDownloadEvent {
        id: item.id.clone(),
        model_id: item.model_id.clone(),
        downloaded,
        total: Some(downloaded),
        speed,
        status: "completed".to_string(),
        progress_pct: pct,
    });

    tracing::info!(model = item.model_name, size = downloaded, elapsed, "model download completed");

    Ok(ModelDownloadProgress {
        id: item.id.clone(),
        model_id: item.model_id.clone(),
        model_name: item.model_name.clone(),
        downloaded,
        total: Some(downloaded),
        speed,
        elapsed_secs: elapsed,
        eta_secs: None,
        status: ModelDownloadStatus::Completed,
        progress_pct: pct,
    })
}

#[tauri::command]
pub async fn start_model_download(
    app: AppHandle,
    model_id: String,
    model_name: String,
    provider: String,
    url: String,
    checksum: Option<String>,
) -> Result<ModelDownloadProgress, String> {
    let config = model_storage::storage_config();
    model_storage::ensure_dirs(&config).map_err(|e| format!("Storage setup error: {e}"))?;

    let storage_path = model_storage::model_path(&provider, &model_name, &config);
    let temp_path = model_storage::temp_download_path(&url, &config);

    if storage_path.exists() {
        return Err(format!("Model already downloaded at {}", storage_path.display()));
    }

    let id = uuid::Uuid::new_v4().to_string();
    let pause_flag = Arc::new(AtomicBool::new(false));

    {
        let mut paused = manager().paused.lock().await;
        paused.insert(id.clone(), pause_flag.clone());
    }

    {
        let mut q = manager().queue.lock().await;
        q.push(ModelDownloadItem {
            id: id.clone(),
            model_id: model_id.clone(),
            model_name: model_name.clone(),
            provider: provider.clone(),
            url: url.clone(),
            dest: storage_path.clone(),
            temp_path: temp_path.clone(),
            size: None,
            downloaded: 0,
            status: ModelDownloadStatus::Pending,
            checksum: checksum.clone(),
            error_count: 0,
            max_retries: 3,
        });
    }

    let item = ModelDownloadItem {
        id: id.clone(),
        model_id,
        model_name,
        provider,
        url,
        dest: storage_path,
        temp_path,
        size: None,
        downloaded: 0,
        status: ModelDownloadStatus::Pending,
        checksum,
        error_count: 0,
        max_retries: 3,
    };

    {
        let mut active = manager().active_count.lock().await;
        *active += 1;
    }

    let result = download_file_with_pause(app.clone(), &item, pause_flag.clone()).await;

    {
        let mut active = manager().active_count.lock().await;
        *active = active.saturating_sub(1);
    }

    if let Err(ref e) = result {
        {
            let mut q = manager().queue.lock().await;
            if let Some(qi) = q.iter_mut().find(|i| i.id == id) {
                qi.error_count += 1;
                if qi.error_count >= qi.max_retries {
                    qi.status = ModelDownloadStatus::Failed(e.clone());
                } else {
                    qi.status = ModelDownloadStatus::Pending;
                }
            }
        }

        let _ = app.emit(MODEL_DOWNLOAD_EVENT_CHANNEL, &ModelDownloadEvent {
            id: id.clone(),
            model_id: item.model_id,
            downloaded: 0,
            total: None,
            speed: 0.0,
            status: "failed".to_string(),
            progress_pct: 0.0,
        });
    }

    result
}

#[tauri::command]
pub async fn pause_model_download(id: String) -> Result<(), String> {
    let paused = manager().paused.lock().await;
    if let Some(flag) = paused.get(&id) {
        flag.store(true, Ordering::Relaxed);
        tracing::info!(id, "model download paused");
        Ok(())
    } else {
        Err(format!("No active download with id {id}"))
    }
}

#[tauri::command]
pub async fn resume_model_download(id: String) -> Result<(), String> {
    let paused = manager().paused.lock().await;
    if let Some(flag) = paused.get(&id) {
        flag.store(false, Ordering::Relaxed);
        tracing::info!(id, "model download resumed");
        Ok(())
    } else {
        Err(format!("No paused download with id {id}"))
    }
}

#[tauri::command]
pub async fn retry_model_download(app: AppHandle, id: String) -> Result<(), String> {
    let item = {
        let mut q = manager().queue.lock().await;
        q.iter_mut().find(|i| i.id == id).cloned()
    };

    if let Some(mut item) = item {
        item.error_count = 0;
        item.status = ModelDownloadStatus::Pending;
        let pause_flag = Arc::new(AtomicBool::new(false));

        {
            let mut paused = manager().paused.lock().await;
            paused.insert(id.clone(), pause_flag.clone());
        }

        {
            let mut q = manager().queue.lock().await;
            if let Some(qi) = q.iter_mut().find(|i| i.id == id) {
                qi.status = ModelDownloadStatus::Pending;
                qi.error_count = 0;
            }
        }

        let _ = download_file_with_pause(app, &item, pause_flag).await;
        Ok(())
    } else {
        Err(format!("No download with id {id}"))
    }
}

#[tauri::command]
pub async fn cancel_model_download(id: String) -> Result<(), String> {
    let mut q = manager().queue.lock().await;
    let mut paused = manager().paused.lock().await;
    paused.remove(&id);

    if let Some(item) = q.iter_mut().find(|i| i.id == id) {
        item.status = ModelDownloadStatus::Failed("cancelled".to_string());
        let _ = tokio::fs::remove_file(&item.temp_path).await;
    }

    if let Some(item) = q.iter().find(|i| i.id == id) {
        let _ = tokio::fs::remove_file(&item.temp_path).await;
    }

    q.retain(|i| i.id != id);
    Ok(())
}

#[tauri::command]
pub async fn get_model_download_queue() -> Result<ModelDownloadQueue, String> {
    let q = manager().queue.lock().await;
    let total_downloaded: u64 = q.iter().map(|i| i.downloaded).sum();
    let total_size: Option<u64> = q.iter().filter_map(|i| i.size).reduce(|a, b| a + b);
    let active_ids: Vec<String> = q.iter()
        .filter(|i| i.status == ModelDownloadStatus::Downloading)
        .map(|i| i.id.clone())
        .collect();
    let max_concurrent = *manager().max_concurrent.lock().await;

    Ok(ModelDownloadQueue {
        items: q.clone(),
        active_ids,
        max_concurrent,
        total_downloaded,
        total_size,
    })
}

#[tauri::command]
pub async fn set_max_concurrent_downloads(max: usize) -> Result<(), String> {
    let clamped = max.clamp(1, 10);
    *manager().max_concurrent.lock().await = clamped;
    Ok(())
}

#[tauri::command]
pub async fn clear_model_download_queue() -> Result<(), String> {
    let mut q = manager().queue.lock().await;
    let mut paused = manager().paused.lock().await;
    q.retain(|i| i.status == ModelDownloadStatus::Downloading);
    paused.clear();
    Ok(())
}
