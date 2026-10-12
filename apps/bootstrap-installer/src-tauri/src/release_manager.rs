use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReleaseInfo {
    pub version: String,
    pub channel: String,
    pub published_at: String,
    pub download_url: String,
    pub checksum: String,
    pub signature: Option<String>,
    pub size_bytes: u64,
    pub changelog: String,
    pub is_security_update: bool,
    pub is_hotfix: bool,
    pub is_prerelease: bool,
    pub minimum_version: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReleaseSource {
    pub source_type: ReleaseSourceType,
    pub url: String,
    pub priority: u32,
    pub latency_ms: Option<u64>,
    pub is_available: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ReleaseSourceType {
    GitHubReleases,
    PrivateServer,
    Mirror,
    OfflinePackage,
    EnterpriseRepository,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReleaseCheckResult {
    pub current_version: String,
    pub latest_version: Option<String>,
    pub update_available: bool,
    pub release: Option<ReleaseInfo>,
    pub sources: Vec<ReleaseSource>,
    pub selected_source: Option<ReleaseSource>,
    pub checked_at: String,
}

static CURRENT_VERSION: &str = env!("CARGO_PKG_VERSION");

pub fn current_version() -> String {
    CURRENT_VERSION.to_string()
}

fn parse_version(v: &str) -> Vec<u32> {
    v.trim_start_matches('v')
        .split(|c: char| !c.is_ascii_digit())
        .filter_map(|p| p.parse::<u32>().ok())
        .collect()
}

pub fn version_gt(a: &str, b: &str) -> bool {
    let av = parse_version(a);
    let bv = parse_version(b);
    for (ai, bi) in av.iter().zip(bv.iter()) {
        if ai != bi {
            return ai > bi;
        }
    }
    av.len() > bv.len()
}

pub fn version_gte(a: &str, b: &str) -> bool {
    a == b || version_gt(a, b)
}

pub fn version_matches_channel(version: &str, channel: &str) -> bool {
    let v = version.to_lowercase();
    match channel {
        "stable" => !v.contains("beta") && !v.contains("nightly") && !v.contains("dev") && !v.contains("rc"),
        "beta" => v.contains("beta") || v.contains("rc"),
        "nightly" => v.contains("nightly") || v.contains("dev"),
        "development" => true,
        "enterprise" => true,
        _ => true,
    }
}

fn github_releases_source() -> ReleaseSource {
    ReleaseSource {
        source_type: ReleaseSourceType::GitHubReleases,
        url: "https://api.github.com/repos/sabib360/AetherOS/releases".to_string(),
        priority: 10,
        latency_ms: None,
        is_available: true,
    }
}

fn private_server_source() -> ReleaseSource {
    ReleaseSource {
        source_type: ReleaseSourceType::PrivateServer,
        url: "https://releases.aetheros.com/api/v1/updates".to_string(),
        priority: 20,
        latency_ms: None,
        is_available: true,
    }
}

fn mirror_source() -> ReleaseSource {
    ReleaseSource {
        source_type: ReleaseSourceType::Mirror,
        url: "https://aetheros-releases.s3.amazonaws.com/updates".to_string(),
        priority: 30,
        latency_ms: None,
        is_available: true,
    }
}

pub fn configured_sources() -> Vec<ReleaseSource> {
    vec![
        github_releases_source(),
        private_server_source(),
        mirror_source(),
    ]
}

async fn measure_latency(url: &str) -> Option<u64> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .ok()?;
    let start = Instant::now();
    let head = client.head(url).send().await;
    match head {
        Ok(_) => Some(start.elapsed().as_millis() as u64),
        Err(_) => {
            let get = client.get(url).send().await;
            match get {
                Ok(_) => Some(start.elapsed().as_millis() as u64),
                Err(_) => None,
            }
        }
    }
}

pub async fn select_fastest_source(sources: &[ReleaseSource]) -> Option<ReleaseSource> {
    let mut with_latency: Vec<ReleaseSource> = Vec::new();
    for source in sources {
        let latency = measure_latency(&source.url).await;
        let mut s = source.clone();
        s.latency_ms = latency;
        s.is_available = latency.is_some();
        with_latency.push(s);
    }
    with_latency.sort_by(|a, b| {
        a.latency_ms.unwrap_or(u64::MAX)
            .cmp(&b.latency_ms.unwrap_or(u64::MAX))
    });
    with_latency.into_iter().find(|s| s.is_available)
}

pub async fn check_for_updates(
    channel: &str,
) -> Result<ReleaseCheckResult, String> {
    let sources = configured_sources();
    let selected = select_fastest_source(&sources).await;
    let current = current_version();

    let mut result = ReleaseCheckResult {
        current_version: current.clone(),
        latest_version: None,
        update_available: false,
        release: None,
        sources,
        selected_source: selected.clone(),
        checked_at: now_iso(),
    };

    if let Some(ref source) = selected {
        let releases = fetch_releases(source).await?;
        let channel_releases: Vec<ReleaseInfo> = releases
            .into_iter()
            .filter(|r| version_matches_channel(&r.version, channel))
            .collect();

        if let Some(latest) = channel_releases.first() {
            result.latest_version = Some(latest.version.clone());
            result.update_available = version_gt(&latest.version, &current);
            result.release = Some(latest.clone());
        }
    }

    Ok(result)
}

async fn fetch_releases(source: &ReleaseSource) -> Result<Vec<ReleaseInfo>, String> {
    match source.source_type {
        ReleaseSourceType::GitHubReleases => fetch_github_releases(&source.url).await,
        ReleaseSourceType::PrivateServer => fetch_private_releases(&source.url).await,
        ReleaseSourceType::Mirror => fetch_mirror_releases(&source.url).await,
        ReleaseSourceType::OfflinePackage => fetch_offline_releases(&source.url).await,
        ReleaseSourceType::EnterpriseRepository => fetch_enterprise_releases(&source.url).await,
    }
}

async fn fetch_github_releases(api_url: &str) -> Result<Vec<ReleaseInfo>, String> {
    let client = reqwest::Client::builder()
        .user_agent("aetheros-setup/0.0.1")
        .timeout(Duration::from_secs(15))
        .build()
        .map_err(|e| format!("Client: {e}"))?;

    let resp = client
        .get(api_url)
        .send()
        .await
        .map_err(|e| format!("GitHub API request failed: {e}"))?;

    if !resp.status().is_success() {
        return Err(format!("GitHub API HTTP {}", resp.status()));
    }

    let json: Vec<serde_json::Value> = resp
        .json()
        .await
        .map_err(|e| format!("JSON parse: {e}"))?;

    let mut releases = Vec::new();
    for entry in json {
        let tag_name = entry["tag_name"].as_str().unwrap_or("").to_string();
        let version = tag_name.trim_start_matches('v').to_string();
        if version.is_empty() {
            continue;
        }

        let published = entry["published_at"].as_str().unwrap_or("").to_string();
        let prerelease = entry["prerelease"].as_bool().unwrap_or(false);
        let body = entry["body"].as_str().unwrap_or("").to_string();
        let is_security = body.to_lowercase().contains("security");
        let is_hotfix = body.to_lowercase().contains("hotfix");

        let download_url = entry["assets"]
            .as_array()
            .and_then(|assets| assets.first())
            .and_then(|a| a["browser_download_url"].as_str())
            .unwrap_or("")
            .to_string();

        let size = entry["assets"]
            .as_array()
            .and_then(|assets| assets.first())
            .and_then(|a| a["size"].as_u64())
            .unwrap_or(0);

        releases.push(ReleaseInfo {
            version,
            channel: if prerelease { "beta".into() } else { "stable".into() },
            published_at: published,
            download_url,
            checksum: String::new(),
            signature: None,
            size_bytes: size,
            changelog: body,
            is_security_update: is_security,
            is_hotfix,
            is_prerelease: prerelease,
            minimum_version: None,
        });
    }

    releases.sort_by(|a, b| {
        let va = parse_version(&a.version);
        let vb = parse_version(&b.version);
        vb.cmp(&va)
    });

    Ok(releases)
}

async fn fetch_private_releases(url: &str) -> Result<Vec<ReleaseInfo>, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("Client: {e}"))?;

    let resp = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Private server request failed: {e}"))?;

    if !resp.status().is_success() {
        return Err(format!("Private server HTTP {}", resp.status()));
    }

    let json: Vec<serde_json::Value> = resp.json().await.map_err(|e| format!("JSON: {e}"))?;
    Ok(parse_release_json(&json))
}

async fn fetch_mirror_releases(url: &str) -> Result<Vec<ReleaseInfo>, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("Client: {e}"))?;

    let resp = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Mirror request failed: {e}"))?;

    if !resp.status().is_success() {
        return Err(format!("Mirror HTTP {}", resp.status()));
    }

    let json: Vec<serde_json::Value> = resp.json().await.map_err(|e| format!("JSON: {e}"))?;
    Ok(parse_release_json(&json))
}

async fn fetch_offline_releases(_url: &str) -> Result<Vec<ReleaseInfo>, String> {
    let offline_path = crate::paths::aetheros_home().join("updates").join("release-manifest.json");
    if !offline_path.exists() {
        return Ok(Vec::new());
    }
    let content = std::fs::read_to_string(&offline_path).map_err(|e| format!("Read: {e}"))?;
    let json: Vec<serde_json::Value> = serde_json::from_str(&content).map_err(|e| format!("JSON: {e}"))?;
    Ok(parse_release_json(&json))
}

async fn fetch_enterprise_releases(url: &str) -> Result<Vec<ReleaseInfo>, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("Client: {e}"))?;

    let resp = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Enterprise server request failed: {e}"))?;

    if !resp.status().is_success() {
        return Err(format!("Enterprise HTTP {}", resp.status()));
    }

    let json: Vec<serde_json::Value> = resp.json().await.map_err(|e| format!("JSON: {e}"))?;
    Ok(parse_release_json(&json))
}

fn parse_release_json(json: &[serde_json::Value]) -> Vec<ReleaseInfo> {
    let mut releases = Vec::new();
    for entry in json {
        let version = entry["version"].as_str().unwrap_or("").to_string();
        if version.is_empty() {
            continue;
        }
        releases.push(ReleaseInfo {
            version,
            channel: entry["channel"].as_str().unwrap_or("stable").to_string(),
            published_at: entry["published_at"].as_str().unwrap_or("").to_string(),
            download_url: entry["download_url"].as_str().unwrap_or("").to_string(),
            checksum: entry["checksum"].as_str().unwrap_or("").to_string(),
            signature: entry["signature"].as_str().map(|s| s.to_string()),
            size_bytes: entry["size_bytes"].as_u64().unwrap_or(0),
            changelog: entry["changelog"].as_str().unwrap_or("").to_string(),
            is_security_update: entry["is_security_update"].as_bool().unwrap_or(false),
            is_hotfix: entry["is_hotfix"].as_bool().unwrap_or(false),
            is_prerelease: entry["is_prerelease"].as_bool().unwrap_or(false),
            minimum_version: entry["minimum_version"].as_str().map(|s| s.to_string()),
        });
    }
    releases.sort_by(|a, b| {
        let va = parse_version(&a.version);
        let vb = parse_version(&b.version);
        vb.cmp(&va)
    });
    releases
}

fn now_iso() -> String {
    let duration = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = duration.as_secs();
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", (secs / 86400) % 30 + 1, secs % 86400 / 3600 + 1, (secs % 3600) / 60, secs % 60, 0)
}

#[tauri::command]
pub async fn get_current_version() -> Result<String, String> {
    Ok(current_version())
}

#[tauri::command]
pub async fn check_update(channel: Option<String>) -> Result<ReleaseCheckResult, String> {
    let ch = channel.unwrap_or_else(|| "stable".to_string());
    check_for_updates(&ch).await
}

#[tauri::command]
pub async fn get_update_sources() -> Result<Vec<ReleaseSource>, String> {
    Ok(configured_sources())
}
