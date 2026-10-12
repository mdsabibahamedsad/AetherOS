use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderDefinition {
    pub id: String,
    pub name: String,
    pub description: String,
    pub requires_api_key: bool,
    pub supports_models: bool,
    pub is_local: bool,
    pub default_base_url: Option<String>,
    pub supported_models: Vec<String>,
}

pub fn available_providers() -> Vec<ProviderDefinition> {
    vec![
        ProviderDefinition {
            id: "openai".to_string(),
            name: "OpenAI".to_string(),
            description: "GPT-4, GPT-4o, GPT-4o-mini, o3, o4-mini".to_string(),
            requires_api_key: true,
            supports_models: true,
            is_local: false,
            default_base_url: Some("https://api.openai.com/v1".to_string()),
            supported_models: vec![
                "gpt-4o".into(), "gpt-4o-mini".into(),
                "o3".into(), "o4-mini".into(),
                "gpt-4.1".into(), "gpt-4.1-mini".into(),
                "gpt-4.1-nano".into(),
            ],
        },
        ProviderDefinition {
            id: "anthropic".to_string(),
            name: "Anthropic".to_string(),
            description: "Claude 4 Sonnet, Claude 3.5 Haiku, Claude Opus".to_string(),
            requires_api_key: true,
            supports_models: true,
            is_local: false,
            default_base_url: Some("https://api.anthropic.com/v1".to_string()),
            supported_models: vec![
                "claude-sonnet-4-20250514".into(),
                "claude-3-5-haiku-20241022".into(),
                "claude-opus-4-20250514".into(),
            ],
        },
        ProviderDefinition {
            id: "google".to_string(),
            name: "Google Gemini".to_string(),
            description: "Gemini 2.5 Pro, Gemini 2.5 Flash".to_string(),
            requires_api_key: true,
            supports_models: true,
            is_local: false,
            default_base_url: Some("https://generativelanguage.googleapis.com/v1beta".to_string()),
            supported_models: vec![
                "gemini-2.5-pro".into(), "gemini-2.5-flash".into(),
            ],
        },
        ProviderDefinition {
            id: "openrouter".to_string(),
            name: "OpenRouter".to_string(),
            description: "Access 200+ models through a single API".to_string(),
            requires_api_key: true,
            supports_models: true,
            is_local: false,
            default_base_url: Some("https://openrouter.ai/api/v1".to_string()),
            supported_models: vec![],
        },
        ProviderDefinition {
            id: "ollama".to_string(),
            name: "Ollama".to_string(),
            description: "Local models via Ollama (Llama, Mistral, Qwen, etc.)".to_string(),
            requires_api_key: false,
            supports_models: true,
            is_local: true,
            default_base_url: Some("http://localhost:11434/v1".to_string()),
            supported_models: vec![],
        },
        ProviderDefinition {
            id: "lm_studio".to_string(),
            name: "LM Studio".to_string(),
            description: "Local models via LM Studio server".to_string(),
            requires_api_key: false,
            supports_models: true,
            is_local: true,
            default_base_url: Some("http://localhost:1234/v1".to_string()),
            supported_models: vec![],
        },
        ProviderDefinition {
            id: "llamacpp".to_string(),
            name: "llama.cpp".to_string(),
            description: "Local models via llama.cpp server".to_string(),
            requires_api_key: false,
            supports_models: true,
            is_local: true,
            default_base_url: Some("http://localhost:8080/v1".to_string()),
            supported_models: vec![],
        },
        ProviderDefinition {
            id: "openai_compatible".to_string(),
            name: "OpenAI Compatible".to_string(),
            description: "Any OpenAI-compatible API endpoint".to_string(),
            requires_api_key: false,
            supports_models: true,
            is_local: false,
            default_base_url: None,
            supported_models: vec![],
        },
        ProviderDefinition {
            id: "azure".to_string(),
            name: "Azure OpenAI".to_string(),
            description: "Microsoft Azure OpenAI Service".to_string(),
            requires_api_key: true,
            supports_models: true,
            is_local: false,
            default_base_url: None,
            supported_models: vec![],
        },
        ProviderDefinition {
            id: "custom".to_string(),
            name: "Custom Provider".to_string(),
            description: "Configure your own AI provider".to_string(),
            requires_api_key: false,
            supports_models: true,
            is_local: false,
            default_base_url: None,
            supported_models: vec![],
        },
    ]
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderConfig {
    pub provider_id: String,
    pub display_name: String,
    pub api_key: Option<String>,
    pub base_url: Option<String>,
    pub organization_id: Option<String>,
    pub azure_deployment: Option<String>,
    pub azure_api_version: Option<String>,
    pub proxy: Option<String>,
    pub timeout_secs: u64,
    pub retry_count: u32,
    pub enabled: bool,
    pub models: ModelRoleAssignment,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelRoleAssignment {
    pub default_model: Option<String>,
    pub reasoning_model: Option<String>,
    pub coding_model: Option<String>,
    pub vision_model: Option<String>,
    pub fast_model: Option<String>,
    pub cheap_model: Option<String>,
    pub offline_model: Option<String>,
}

impl Default for ModelRoleAssignment {
    fn default() -> Self {
        Self {
            default_model: None,
            reasoning_model: None,
            coding_model: None,
            vision_model: None,
            fast_model: None,
            cheap_model: None,
            offline_model: None,
        }
    }
}

pub fn providers_config_path() -> std::path::PathBuf {
    crate::paths::aetheros_home().join("config").join("ai-providers.json")
}

pub fn save_providers_config(providers: &[ProviderConfig]) -> Result<(), String> {
    let path = providers_config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(providers)
        .map_err(|e| format!("Serialize error: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write error: {e}"))?;
    tracing::info!(count = providers.len(), "AI providers config saved");
    Ok(())
}

pub fn load_providers_config() -> Result<Vec<ProviderConfig>, String> {
    let path = providers_config_path();
    if !path.exists() {
        return Ok(Vec::new());
    }
    let content = std::fs::read_to_string(&path).map_err(|e| format!("Read error: {e}"))?;
    serde_json::from_str(&content).map_err(|e| format!("Parse error: {e}"))
}

pub fn store_provider_api_key(provider_id: &str, api_key: &str) -> Result<(), String> {
    let key = format!("ai_provider_{}", provider_id);
    crate::encryptor::store_secret(&key, api_key)
}

pub fn read_provider_api_key(provider_id: &str) -> Result<Option<String>, String> {
    let key = format!("ai_provider_{}", provider_id);
    crate::encryptor::read_secret(&key)
}

fn detect_local_instances() -> Vec<HashMap<String, String>> {
    let mut result = Vec::new();

    // Check Ollama
    if ollama_detected() {
        let mut info = HashMap::new();
        info.insert("provider".to_string(), "ollama".to_string());
        info.insert("endpoint".to_string(), "http://localhost:11434".to_string());
        info.insert("status".to_string(), "running".to_string());
        result.push(info);
    }

    // Check LM Studio
    if lm_studio_detected() {
        let mut info = HashMap::new();
        info.insert("provider".to_string(), "lm_studio".to_string());
        info.insert("endpoint".to_string(), "http://localhost:1234".to_string());
        info.insert("status".to_string(), "running".to_string());
        result.push(info);
    }

    result
}

fn ollama_detected() -> bool {
    use std::process::Command;
    if cfg!(target_os = "windows") {
        Command::new("where").arg("ollama").output().is_ok()
    } else {
        Command::new("which").arg("ollama").output().is_ok()
    }
}

fn lm_studio_detected() -> bool {
    if cfg!(target_os = "windows") {
        let paths = [
            std::path::Path::new(&std::env::var("LOCALAPPDATA").unwrap_or_default())
                .join("Programs").join("LM Studio").join("LM Studio.exe"),
            PathBuf::from("C:\\Program Files\\LM Studio\\LM Studio.exe"),
        ];
        paths.iter().any(|p| p.exists())
    } else if cfg!(target_os = "macos") {
        std::path::Path::new("/Applications/LM Studio.app").exists()
    } else {
        false
    }
}

#[tauri::command]
pub async fn get_available_providers() -> Result<Vec<ProviderDefinition>, String> {
    Ok(available_providers())
}

#[tauri::command]
pub async fn get_configured_providers() -> Result<Vec<ProviderConfig>, String> {
    load_providers_config()
}

#[tauri::command]
pub async fn save_provider_config(config: ProviderConfig) -> Result<(), String> {
    let mut providers = load_providers_config()?;
    if let Some(existing) = providers.iter_mut().find(|p| p.provider_id == config.provider_id) {
        *existing = config.clone();
    } else {
        providers.push(config);
    }
    save_providers_config(&providers)
}

#[tauri::command]
pub async fn delete_provider_config(provider_id: String) -> Result<(), String> {
    let mut providers = load_providers_config()?;
    providers.retain(|p| p.provider_id != provider_id);
    save_providers_config(&providers)
}

#[tauri::command]
pub async fn detect_local_ai() -> Result<Vec<HashMap<String, String>>, String> {
    Ok(detect_local_instances())
}

#[tauri::command]
pub async fn save_provider_api_key(provider_id: String, api_key: String) -> Result<(), String> {
    store_provider_api_key(&provider_id, &api_key)
}

#[tauri::command]
pub async fn check_provider_api_key(provider_id: String) -> Result<bool, String> {
    Ok(read_provider_api_key(&provider_id)?.is_some())
}
