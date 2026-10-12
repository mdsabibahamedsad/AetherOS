use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalEngineInfo {
    pub engine_type: EngineType,
    pub name: String,
    pub version: Option<String>,
    pub executable_path: Option<String>,
    pub endpoint_url: String,
    pub is_running: bool,
    pub models: Vec<LocalModelInfo>,
    pub data_path: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EngineType {
    Ollama,
    LmStudio,
    Llamacpp,
    CustomOpenai,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalModelInfo {
    pub name: String,
    pub model_path: Option<String>,
    pub size_bytes: Option<u64>,
    pub digest: Option<String>,
    pub parameters: Option<String>,
    pub quantization: Option<String>,
    pub modified_at: Option<String>,
    pub family: Option<String>,
}

pub fn detect_all_engines() -> Vec<LocalEngineInfo> {
    let mut engines = Vec::new();

    if let Some(ollama) = detect_ollama() {
        engines.push(ollama);
    }

    if let Some(lm) = detect_lm_studio() {
        engines.push(lm);
    }

    if let Some(llama) = detect_llamacpp() {
        engines.push(llama);
    }

    engines
}

fn detect_ollama() -> Option<LocalEngineInfo> {
    let ollama_path = find_ollama_executable()?;
    let version = get_ollama_version(&ollama_path);
    let models = get_ollama_models().unwrap_or_default();
    let is_running = check_ollama_running();

    Some(LocalEngineInfo {
        engine_type: EngineType::Ollama,
        name: "Ollama".to_string(),
        version,
        executable_path: Some(ollama_path.to_string_lossy().to_string()),
        endpoint_url: "http://localhost:11434".to_string(),
        is_running,
        models,
        data_path: get_ollama_data_path(),
    })
}

fn find_ollama_executable() -> Option<PathBuf> {
    if cfg!(target_os = "windows") {
        let local_app_data = std::env::var("LOCALAPPDATA").ok()?;
        let paths = [
            PathBuf::from(&local_app_data).join("Programs").join("Ollama").join("ollama.exe"),
            PathBuf::from(&local_app_data).join("Ollama").join("ollama.exe"),
            PathBuf::from("C:\\Program Files\\Ollama\\ollama.exe"),
        ];
        paths.iter().find(|p| p.exists()).cloned()
    } else {
        which::which("ollama").ok()
    }
}

fn get_ollama_version(path: &PathBuf) -> Option<String> {
    std::process::Command::new(path)
        .arg("--version")
        .output()
        .ok()
        .and_then(|o| {
            let s = String::from_utf8_lossy(&o.stdout).to_string();
            s.lines().next().map(|l| l.trim().to_string())
        })
}

fn get_ollama_models() -> Result<Vec<LocalModelInfo>, String> {
    let output = std::process::Command::new("ollama")
        .arg("list")
        .output()
        .map_err(|e| format!("Failed to run ollama list: {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut models = Vec::new();

    for line in stdout.lines().skip(1) {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() >= 2 {
            let name = parts[0].to_string();
            let size_str = parts[parts.len() - 1];
            let size_bytes = parse_size(size_str);

            models.push(LocalModelInfo {
                name: name.clone(),
                model_path: None,
                size_bytes,
                digest: None,
                parameters: None,
                quantization: None,
                modified_at: None,
                family: name.split(':').next().map(|s| s.to_string()),
            });
        }
    }

    Ok(models)
}

fn parse_size(s: &str) -> Option<u64> {
    let s = s.trim().to_lowercase();
    if s.ends_with("gb") {
        let num: f64 = s.trim_end_matches("gb").trim().parse().ok()?;
        Some((num * 1_073_741_824.0) as u64)
    } else if s.ends_with("mb") {
        let num: f64 = s.trim_end_matches("mb").trim().parse().ok()?;
        Some((num * 1_048_576.0) as u64)
    } else if s.ends_with("kb") {
        let num: f64 = s.trim_end_matches("kb").trim().parse().ok()?;
        Some((num * 1024.0) as u64)
    } else {
        s.parse::<u64>().ok()
    }
}

fn check_ollama_running() -> bool {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .ok();
    match client {
        Some(c) => c.get("http://localhost:11434/api/tags").send().ok().is_some(),
        None => false,
    }
}

fn get_ollama_data_path() -> Option<String> {
    if cfg!(target_os = "windows") {
        let path = PathBuf::from(std::env::var("USERPROFILE").ok()?)
            .join(".ollama")
            .join("models");
        Some(path.to_string_lossy().to_string())
    } else {
        let path = dirs::home_dir()?.join(".ollama").join("models");
        Some(path.to_string_lossy().to_string())
    }
}

fn detect_lm_studio() -> Option<LocalEngineInfo> {
    let lm_studio_path = find_lm_studio_executable()?;
    let is_running = check_lm_studio_running();
    let models = get_lm_studio_models().unwrap_or_default();

    Some(LocalEngineInfo {
        engine_type: EngineType::LmStudio,
        name: "LM Studio".to_string(),
        version: None,
        executable_path: Some(lm_studio_path.to_string_lossy().to_string()),
        endpoint_url: "http://localhost:1234".to_string(),
        is_running,
        models,
        data_path: get_lm_studio_data_path(),
    })
}

fn find_lm_studio_executable() -> Option<PathBuf> {
    if cfg!(target_os = "windows") {
        let local_app_data = std::env::var("LOCALAPPDATA").ok()?;
        let paths = [
            PathBuf::from(&local_app_data).join("Programs").join("LM Studio").join("LM Studio.exe"),
            PathBuf::from("C:\\Program Files\\LM Studio\\LM Studio.exe"),
        ];
        paths.iter().find(|p| p.exists()).cloned()
    } else if cfg!(target_os = "macos") {
        let path = PathBuf::from("/Applications/LM Studio.app");
        if path.exists() { Some(path) } else { None }
    } else {
        None
    }
}

fn check_lm_studio_running() -> bool {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .ok();
    match client {
        Some(c) => c.get("http://localhost:1234/v1/models").send().ok().is_some(),
        None => false,
    }
}

fn get_lm_studio_models() -> Result<Vec<LocalModelInfo>, String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| format!("Client error: {e}"))?;

    let resp = client
        .get("http://localhost:1234/v1/models")
        .send()
        .map_err(|_| "Cannot reach LM Studio".to_string())?;

    let json: serde_json::Value = resp
        .json()
        .map_err(|e| format!("JSON error: {e}"))?;

    let mut models = Vec::new();
    if let Some(data) = json["data"].as_array() {
        for entry in data {
            let id = entry["id"].as_str().unwrap_or("unknown").to_string();
            models.push(LocalModelInfo {
                name: id,
                model_path: None,
                size_bytes: None,
                digest: None,
                parameters: None,
                quantization: None,
                modified_at: None,
                family: None,
            });
        }
    }

    Ok(models)
}

fn get_lm_studio_data_path() -> Option<String> {
    if cfg!(target_os = "windows") {
        Some(
            PathBuf::from(std::env::var("USERPROFILE").ok()?)
                .join(".lm-studio")
                .join("models")
                .to_string_lossy()
                .to_string(),
        )
    } else {
        Some(
            dirs::home_dir()?
                .join(".lm-studio")
                .join("models")
                .to_string_lossy()
                .to_string(),
        )
    }
}

fn detect_llamacpp() -> Option<LocalEngineInfo> {
    let is_running = check_llamacpp_running();
    let models = get_llamacpp_models().unwrap_or_default();

    Some(LocalEngineInfo {
        engine_type: EngineType::Llamacpp,
        name: "llama.cpp".to_string(),
        version: None,
        executable_path: None,
        endpoint_url: "http://localhost:8080".to_string(),
        is_running,
        models,
        data_path: None,
    })
}

fn check_llamacpp_running() -> bool {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .ok();
    match client {
        Some(c) => c.get("http://localhost:8080/v1/models").send().ok().is_some(),
        None => false,
    }
}

fn get_llamacpp_models() -> Result<Vec<LocalModelInfo>, String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| format!("Client error: {e}"))?;

    let resp = client
        .get("http://localhost:8080/v1/models")
        .send()
        .map_err(|_| "Cannot reach llama.cpp".to_string())?;

    let json: serde_json::Value = resp
        .json()
        .map_err(|e| format!("JSON error: {e}"))?;

    let mut models = Vec::new();
    if let Some(data) = json["data"].as_array() {
        for entry in data {
            let id = entry["id"].as_str().unwrap_or("unknown").to_string();
            models.push(LocalModelInfo {
                name: id,
                model_path: None,
                size_bytes: None,
                digest: None,
                parameters: None,
                quantization: None,
                modified_at: None,
                family: None,
            });
        }
    }

    Ok(models)
}

pub fn detect_engine_models(engine_type: EngineType) -> Vec<LocalModelInfo> {
    match engine_type {
        EngineType::Ollama => get_ollama_models().unwrap_or_default(),
        EngineType::LmStudio => get_lm_studio_models().unwrap_or_default(),
        EngineType::Llamacpp => get_llamacpp_models().unwrap_or_default(),
        EngineType::CustomOpenai => Vec::new(),
    }
}

#[tauri::command]
pub async fn detect_local_ai_engines() -> Result<Vec<LocalEngineInfo>, String> {
    Ok(detect_all_engines())
}

#[tauri::command]
pub async fn scan_engine_models(engine_type: String) -> Result<Vec<LocalModelInfo>, String> {
    let etype = match engine_type.as_str() {
        "ollama" => EngineType::Ollama,
        "lm_studio" => EngineType::LmStudio,
        "llamacpp" => EngineType::Llamacpp,
        "custom_openai" => EngineType::CustomOpenai,
        _ => return Err(format!("Unknown engine type: {engine_type}")),
    };
    Ok(detect_engine_models(etype))
}
