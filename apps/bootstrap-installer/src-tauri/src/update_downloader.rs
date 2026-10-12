use crate::release_manager::ReleaseInfo;
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

pub const UPDATE_DOWNLOAD_EVENT_CHANNEL: &str = "update-download";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum UpdateDownloadStatus {
    Pending,
    Downloading,
    Paused,
    Verifying,
    Completed,
    Failed(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateDownloadItem {
    pub id: String,
    pub version: String,
    pub url: String,
    pub dest: PathBuf,
    pub temp_path: PathBuf,
    pub size: Option<u64>,
    pub downloaded: u64,
    pub status: UpdateDownloadStatus,
    pub checksum: Option<String>,
    pub signature: Option<String>,
    pub error_count: u32,
    pub max_retries: u32,
    pub is_background: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateDownloadProgress {
    pub id: String,
    pub version: String,
    pub downloaded: u64,
    pub total: Option<u64>,
    pub speed: f64,
    pub elapsed_secs: f64,
    pub eta_secs: Option<f64>,
    pub status: UpdateDownloadStatus,
    pub progress_pct: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct UpdateDownloadEvent {
    pub id: String,
    pub version: String,
    pub downloaded: u64,
    pub total: Option<u64>,
    pub speed: f64,
    pub status: String,
    pub progress_pct: f64,
}

struct DownloadManager {
    queue: Mutex<Vec<UpdateDownloadItem>>,
    paused: Mutex<HashMap<String, Arc<AtomicBool>>>,
    bandwidth_limit: Mutex<Option<u64>>,
}

impl DownloadManager {
    fn new() -> Self {
        Self {
            queue: Mutex::new(Vec::new()),
            paused: Mutex::new(HashMap::new()),
            bandwidth_limit: Mutex::new(None),
        }
    }
}

static DOWNLOAD_MANAGER: std::sync::OnceLock<Arc<DownloadManager>> = std::sync::OnceLock::new();

fn manager() -> &'static Arc<DownloadManager> {
    DOWNLOAD_MANAGER.get_or_init(|| Arc::new(DownloadManager::new()))
}

fn update_download_dir() -> PathBuf {
    crate::paths::aetheros_home().join("updates").join("downloads")
}

fn progress_pct(downloaded: u64, total: Option<u64>) -> f64 {
    match total {
        Some(t) if t > 0 => (downloaded as f64 / t as f64) * 100.0,
        _ => 0.0,
    }
}

async fn download_update_package(
    app: AppHandle,
    item: &UpdateDownloadItem,
    pause_flag: Arc<AtomicBool>,
    bandwidth_limit: Option<u64>,
) -> Result<UpdateDownloadProgress, String> {
    let start = Instant::now();
    let mut downloaded: u64 = 0;
    let mut last_emit = Instant::now();

    if let Some(parent) = item.dest.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }

    let client = reqwest::Client::builder()
        .user_agent("aetheros-setup/0.0.1")
        .timeout(Duration::from_secs(7200))
        .build()
        .map_err(|e| format!("Client: {e}"))?;

    let response = client
        .get(&item.url)
        .send()
        .await
        .map_err(|e| format!("Download request failed: {e}"))?;

    if !response.status().is_success() {
        return Err(format!("HTTP {}", response.status()));
    }

    let total = response.content_length();
    let mut file = tokio::fs::File::create(&item.temp_path)
        .await
        .map_err(|e| format!("Create temp: {e}"))?;

    let mut stream = response.bytes_stream();
    let mut last_bandwidth_check = Instant::now();
    let mut bytes_this_window: u64 = 0;

    while let Some(chunk) = stream.next().await {
        if pause_flag.load(Ordering::Relaxed) {
            file.flush().await.ok();
            drop(file);
            return Ok(UpdateDownloadProgress {
                id: item.id.clone(),
                version: item.version.clone(),
                downloaded,
                total,
                speed: 0.0,
                elapsed_secs: start.elapsed().as_secs_f64(),
                eta_secs: None,
                status: UpdateDownloadStatus::Paused,
                progress_pct: progress_pct(downloaded, total),
            });
        }

        let chunk = chunk.map_err(|e| format!("Stream error: {e}"))?;
        file.write_all(&chunk)
            .await
            .map_err(|e| format!("Write: {e}"))?;

        let chunk_len = chunk.len() as u64;
        downloaded += chunk_len;
        bytes_this_window += chunk_len;

        if let Some(limit_bps) = bandwidth_limit {
            let window_elapsed = last_bandwidth_check.elapsed().as_secs_f64();
            if window_elapsed > 0.0 {
                let current_rate = bytes_this_window as f64 / window_elapsed;
                if current_rate > limit_bps as f64 * 1024.0 {
                    let sleep_secs = (bytes_this_window as f64 / (limit_bps as f64 * 1024.0)) - window_elapsed;
                    if sleep_secs > 0.0 {
                        tokio::time::sleep(Duration::from_secs_f64(sleep_secs)).await;
                    }
                }
            }
            if last_bandwidth_check.elapsed() > Duration::from_secs(1) {
                bytes_this_window = 0;
                last_bandwidth_check = Instant::now();
            }
        }

        if last_emit.elapsed() > Duration::from_millis(250) {
            let elapsed = start.elapsed().as_secs_f64();
            let speed = if elapsed > 0.0 { downloaded as f64 / elapsed } else { 0.0 };
            let pct = progress_pct(downloaded, total);
            let eta = total.and_then(|t| {
                if speed > 0.0 { Some((t - downloaded) as f64 / speed) } else { None }
            });

            let event = UpdateDownloadEvent {
                id: item.id.clone(),
                version: item.version.clone(),
                downloaded,
                total,
                speed,
                status: "downloading".to_string(),
                progress_pct: pct,
            };
            let _ = app.emit(UPDATE_DOWNLOAD_EVENT_CHANNEL, &event);

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

    file.flush().await.map_err(|e| format!("Flush: {e}"))?;
    drop(file);

    if let Some(ref checksum) = item.checksum {
        let computed = crate::verification::compute_sha256(&item.temp_path)
            .map_err(|e| format!("Checksum: {e}"))?;
        if computed != *checksum {
            let _ = tokio::fs::remove_file(&item.temp_path).await;
            return Err(format!("Checksum mismatch: expected {checksum}, got {computed}"));
        }
    }

    if let Some(ref _sig) = item.signature {
        let verify_result = crate::verification::verify_file_signature(
            item.temp_path.to_string_lossy().to_string(),
        )
        .await
        .map_err(|e| format!("Signature verify: {e}"))?;
        if !verify_result.trusted {
            let _ = tokio::fs::remove_file(&item.temp_path).await;
            return Err(format!("Signature verification failed: {}", verify_result.message));
        }
    }

    tokio::fs::rename(&item.temp_path, &item.dest)
        .await
        .map_err(|e| format!("Finalize: {e}"))?;

    let elapsed = start.elapsed().as_secs_f64();
    let speed = if elapsed > 0.0 { downloaded as f64 / elapsed } else { 0.0 };

    {
        let mut q = manager().queue.lock().await;
        if let Some(qi) = q.iter_mut().find(|i| i.id == item.id) {
            qi.status = UpdateDownloadStatus::Completed;
            qi.downloaded = downloaded;
            qi.size = Some(downloaded);
        }
    }

    let _ = app.emit(UPDATE_DOWNLOAD_EVENT_CHANNEL, &UpdateDownloadEvent {
        id: item.id.clone(),
        version: item.version.clone(),
        downloaded,
        total: Some(downloaded),
        speed,
        status: "completed".to_string(),
        progress_pct: 100.0,
    });

    tracing::info!(version = item.version, size = downloaded, elapsed, "update download completed");

    Ok(UpdateDownloadProgress {
        id: item.id.clone(),
        version: item.version.clone(),
        downloaded,
        total: Some(downloaded),
        speed,
        elapsed_secs: elapsed,
        eta_secs: None,
        status: UpdateDownloadStatus::Completed,
        progress_pct: 100.0,
    })
}

#[tauri::command]
pub async fn start_update_download(
    app: AppHandle,
    release: ReleaseInfo,
    is_background: bool,
) -> Result<UpdateDownloadProgress, String> {
    let dl_dir = update_download_dir();
    std::fs::create_dir_all(&dl_dir).map_err(|e| format!("Create dl dir: {e}"))?;

    let filename = format!("aetheros-update-{}.zip", release.version);
    let dest = dl_dir.join(&filename);
    let temp_path = dl_dir.join(format!("{}.tmp", filename));

    if dest.exists() {
        if let Some(ref checksum) = Option::from(&release.checksum).filter(|c| !c.is_empty()) {
            let existing = crate::verification::compute_sha256(&dest).ok();
            if existing.as_deref() == Some(checksum.as_str()) {
                return Ok(UpdateDownloadProgress {
                    id: "cached".to_string(),
                    version: release.version.clone(),
                    downloaded: release.size_bytes,
                    total: Some(release.size_bytes),
                    speed: 0.0,
                    elapsed_secs: 0.0,
                    eta_secs: None,
                    status: UpdateDownloadStatus::Completed,
                    progress_pct: 100.0,
                });
            }
        }
        let _ = tokio::fs::remove_file(&dest).await;
    }
    let _ = tokio::fs::remove_file(&temp_path).await;

    let id = uuid::Uuid::new_v4().to_string();
    let pause_flag = Arc::new(AtomicBool::new(false));

    {
        let mut paused = manager().paused.lock().await;
        paused.insert(id.clone(), pause_flag.clone());
    }

    let checksum = if release.checksum.is_empty() { None } else { Some(release.checksum.clone()) };
    let signature = release.signature.clone();

    {
        let mut q = manager().queue.lock().await;
        q.push(UpdateDownloadItem {
            id: id.clone(),
            version: release.version.clone(),
            url: release.download_url.clone(),
            dest: dest.clone(),
            temp_path: temp_path.clone(),
            size: Some(release.size_bytes),
            downloaded: 0,
            status: UpdateDownloadStatus::Pending,
            checksum,
            signature,
            error_count: 0,
            max_retries: 3,
            is_background,
        });
    }

    let item = UpdateDownloadItem {
        id: id.clone(),
        version: release.version.clone(),
        url: release.download_url.clone(),
        dest,
        temp_path,
        size: Some(release.size_bytes),
        downloaded: 0,
        status: UpdateDownloadStatus::Pending,
        checksum: if release.checksum.is_empty() { None } else { Some(release.checksum) },
        signature: release.signature,
        error_count: 0,
        max_retries: 3,
        is_background,
    };

    let bandwidth = *manager().bandwidth_limit.lock().await;
    let result = download_update_package(app.clone(), &item, pause_flag.clone(), bandwidth).await;

    if let Err(ref e) = result {
        {
            let mut q = manager().queue.lock().await;
            if let Some(qi) = q.iter_mut().find(|i| i.id == id) {
                qi.error_count += 1;
                if qi.error_count >= qi.max_retries {
                    qi.status = UpdateDownloadStatus::Failed(e.clone());
                } else {
                    qi.status = UpdateDownloadStatus::Pending;
                }
            }
        }
    }

    result
}

#[tauri::command]
pub async fn pause_update_download(id: String) -> Result<(), String> {
    let paused = manager().paused.lock().await;
    if let Some(flag) = paused.get(&id) {
        flag.store(true, Ordering::Relaxed);
        Ok(())
    } else {
        Err(format!("No active download: {id}"))
    }
}

#[tauri::command]
pub async fn resume_update_download(id: String) -> Result<(), String> {
    let mut paused = manager().paused.lock().await;
    if paused.contains_key(&id) {
        paused.get(&id).unwrap().store(false, Ordering::Relaxed);
        Ok(())
    } else {
        Err(format!("No paused download: {id}"))
    }
}

#[tauri::command]
pub async fn cancel_update_download(id: String) -> Result<(), String> {
    let mut q = manager().queue.lock().await;
    let mut paused = manager().paused.lock().await;
    paused.remove(&id);

    if let Some(item) = q.iter_mut().find(|i| i.id == id) {
        item.status = UpdateDownloadStatus::Failed("cancelled".to_string());
        let _ = tokio::fs::remove_file(&item.temp_path).await;
    }

    q.retain(|i| i.id != id);
    Ok(())
}

#[tauri::command]
pub async fn get_update_download_status() -> Result<Vec<UpdateDownloadItem>, String> {
    let q = manager().queue.lock().await;
    Ok(q.clone())
}

#[tauri::command]
pub async fn set_bandwidth_limit(kbps: Option<u64>) -> Result<(), String> {
    *manager().bandwidth_limit.lock().await = kbps;
    Ok(())
}

#[tauri::command]
pub async fn retry_update_download(app: AppHandle, id: String) -> Result<(), String> {
    let item = {
        let mut q = manager().queue.lock().await;
        q.iter().find(|i| i.id == id).cloned()
    };

    if let Some(mut item) = item {
        item.error_count = 0;
        item.status = UpdateDownloadStatus::Pending;
        let pause_flag = Arc::new(AtomicBool::new(false));

        {
            let mut paused = manager().paused.lock().await;
            paused.insert(id.clone(), pause_flag.clone());
        }

        {
            let mut q = manager().queue.lock().await;
            if let Some(qi) = q.iter_mut().find(|i| i.id == id) {
                qi.status = UpdateDownloadStatus::Pending;
                qi.error_count = 0;
            }
        }

        let bandwidth = *manager().bandwidth_limit.lock().await;
        let _ = download_update_package(app, &item, pause_flag, bandwidth).await;
        Ok(())
    } else {
        Err(format!("No download: {id}"))
    }
}
