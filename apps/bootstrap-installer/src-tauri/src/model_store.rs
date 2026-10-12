use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelStoreEntry {
    pub id: String,
    pub name: String,
    pub provider: String,
    pub provider_display: String,
    pub source: String,
    pub version: String,
    pub description: String,
    pub size_bytes: u64,
    pub license: String,
    pub category: ModelStoreCategory,
    pub capabilities: Vec<String>,
    pub ram_required_mb: u64,
    pub vram_required_mb: u64,
    pub recommended_hardware: String,
    pub download_url: Option<String>,
    pub checksum: Option<String>,
    pub is_local: bool,
    pub requires_api_key: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ModelStoreCategory {
    General,
    Coding,
    Reasoning,
    Vision,
    Voice,
    Embedding,
    ImageGeneration,
    SpeechToText,
    TextToSpeech,
    Offline,
    Experimental,
}

pub fn builtin_catalog() -> Vec<ModelStoreEntry> {
    let mut catalog = Vec::new();

    // OpenAI
    for (id, name, size, category, vram) in [
        ("openai/gpt-4o", "GPT-4o", 0, ModelStoreCategory::General, 0),
        ("openai/gpt-4o-mini", "GPT-4o Mini", 0, ModelStoreCategory::General, 0),
        ("openai/o3", "o3", 0, ModelStoreCategory::Reasoning, 0),
        ("openai/o4-mini", "o4 Mini", 0, ModelStoreCategory::Reasoning, 0),
        ("openai/gpt-4.1", "GPT-4.1", 0, ModelStoreCategory::Coding, 0),
    ] {
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: "openai".to_string(),
            provider_display: "OpenAI".to_string(),
            source: "cloud".to_string(),
            version: "latest".to_string(),
            description: format!("{name} — OpenAI's flagship model"),
            size_bytes: size,
            license: "Proprietary".to_string(),
            category,
            capabilities: vec!["chat".into(), "reasoning".into(), "coding".into()],
            ram_required_mb: 0,
            vram_required_mb: vram,
            recommended_hardware: "Cloud API".to_string(),
            download_url: None,
            checksum: None,
            is_local: false,
            requires_api_key: true,
        });
    }

    // Anthropic
    for (id, name, category) in [
        ("anthropic/claude-sonnet-4", "Claude Sonnet 4", ModelStoreCategory::Reasoning),
        ("anthropic/claude-3.5-haiku", "Claude 3.5 Haiku", ModelStoreCategory::General),
        ("anthropic/claude-opus-4", "Claude Opus 4", ModelStoreCategory::Reasoning),
    ] {
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: "anthropic".to_string(),
            provider_display: "Anthropic".to_string(),
            source: "cloud".to_string(),
            version: "latest".to_string(),
            description: format!("{name} — Anthropic's Claude model"),
            size_bytes: 0,
            license: "Proprietary".to_string(),
            category,
            capabilities: vec!["chat".into(), "reasoning".into()],
            ram_required_mb: 0,
            vram_required_mb: 0,
            recommended_hardware: "Cloud API".to_string(),
            download_url: None,
            checksum: None,
            is_local: false,
            requires_api_key: true,
        });
    }

    // Google
    for (id, name, category) in [
        ("google/gemini-2.5-pro", "Gemini 2.5 Pro", ModelStoreCategory::Reasoning),
        ("google/gemini-2.5-flash", "Gemini 2.5 Flash", ModelStoreCategory::General),
    ] {
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: "google".to_string(),
            provider_display: "Google Gemini".to_string(),
            source: "cloud".to_string(),
            version: "latest".to_string(),
            description: format!("{name} — Google's Gemini model"),
            size_bytes: 0,
            license: "Proprietary".to_string(),
            category,
            capabilities: vec!["chat".into(), "reasoning".into(), "vision".into()],
            ram_required_mb: 0,
            vram_required_mb: 0,
            recommended_hardware: "Cloud API".to_string(),
            download_url: None,
            checksum: None,
            is_local: false,
            requires_api_key: true,
        });
    }

    // OpenRouter
    catalog.push(ModelStoreEntry {
        id: "openrouter/all".to_string(),
        name: "All Models".to_string(),
        provider: "openrouter".to_string(),
        provider_display: "OpenRouter".to_string(),
        source: "cloud".to_string(),
        version: "latest".to_string(),
        description: "Access 200+ models through OpenRouter API".to_string(),
        size_bytes: 0,
        license: "Various".to_string(),
        category: ModelStoreCategory::General,
        capabilities: vec!["chat".into(), "reasoning".into(), "coding".into(), "vision".into()],
        ram_required_mb: 0,
        vram_required_mb: 0,
        recommended_hardware: "Cloud API".to_string(),
        download_url: None,
        checksum: None,
        is_local: false,
        requires_api_key: true,
    });

    // Groq
    for (id, name, category) in [
        ("groq/llama-3.3-70b", "Llama 3.3 70B", ModelStoreCategory::General),
        ("groq/mixtral-8x7b", "Mixtral 8x7B", ModelStoreCategory::General),
        ("groq/llama-3.1-8b", "Llama 3.1 8B", ModelStoreCategory::Coding),
    ] {
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: "groq".to_string(),
            provider_display: "Groq".to_string(),
            source: "cloud".to_string(),
            version: "latest".to_string(),
            description: format!("{name} — hosted on Groq's LPU inference engine"),
            size_bytes: 0,
            license: "Various".to_string(),
            category,
            capabilities: vec!["chat".into(), "coding".into()],
            ram_required_mb: 0,
            vram_required_mb: 0,
            recommended_hardware: "Cloud API".to_string(),
            download_url: None,
            checksum: None,
            is_local: false,
            requires_api_key: true,
        });
    }

    // DeepSeek
    for (id, name, category, size, ram, vram) in [
        ("deepseek/deepseek-chat", "DeepSeek Chat", ModelStoreCategory::General, 0, 0, 0),
        ("deepseek/deepseek-coder", "DeepSeek Coder", ModelStoreCategory::Coding, 0, 0, 0),
    ] {
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: "deepseek".to_string(),
            provider_display: "DeepSeek".to_string(),
            source: "cloud".to_string(),
            version: "latest".to_string(),
            description: format!("{name} — DeepSeek's AI model"),
            size_bytes: size,
            license: "Proprietary".to_string(),
            category,
            capabilities: vec!["chat".into(), "coding".into()],
            ram_required_mb: ram,
            vram_required_mb: vram,
            recommended_hardware: "Cloud API".to_string(),
            download_url: None,
            checksum: None,
            is_local: false,
            requires_api_key: true,
        });
    }

    // Mistral
    for (id, name, category) in [
        ("mistral/mistral-large", "Mistral Large", ModelStoreCategory::General),
        ("mistral/codestral", "Codestral", ModelStoreCategory::Coding),
        ("mistral/mistral-small", "Mistral Small", ModelStoreCategory::General),
    ] {
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: "mistral".to_string(),
            provider_display: "Mistral".to_string(),
            source: "cloud".to_string(),
            version: "latest".to_string(),
            description: format!("{name} — Mistral AI's model"),
            size_bytes: 0,
            license: "Proprietary".to_string(),
            category,
            capabilities: vec!["chat".into(), "coding".into()],
            ram_required_mb: 0,
            vram_required_mb: 0,
            recommended_hardware: "Cloud API".to_string(),
            download_url: None,
            checksum: None,
            is_local: false,
            requires_api_key: true,
        });
    }

    // Cohere
    for (id, name, category) in [
        ("cohere/command-r", "Command R", ModelStoreCategory::General),
        ("cohere/command-r-plus", "Command R+", ModelStoreCategory::Reasoning),
    ] {
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: "cohere".to_string(),
            provider_display: "Cohere".to_string(),
            source: "cloud".to_string(),
            version: "latest".to_string(),
            description: format!("{name} — Cohere's command model"),
            size_bytes: 0,
            license: "Proprietary".to_string(),
            category,
            capabilities: vec!["chat".into(), "rag".into()],
            ram_required_mb: 0,
            vram_required_mb: 0,
            recommended_hardware: "Cloud API".to_string(),
            download_url: None,
            checksum: None,
            is_local: false,
            requires_api_key: true,
        });
    }

    // Together AI
    for (id, name, category) in [
        ("together/mixtral-8x22b", "Mixtral 8x22B", ModelStoreCategory::General),
        ("together/llama-3.3-70b", "Llama 3.3 70B", ModelStoreCategory::General),
        ("together/deepseek-coder", "DeepSeek Coder V2", ModelStoreCategory::Coding),
    ] {
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: "together".to_string(),
            provider_display: "Together AI".to_string(),
            source: "cloud".to_string(),
            version: "latest".to_string(),
            description: format!("{name} — hosted on Together AI"),
            size_bytes: 0,
            license: "Various".to_string(),
            category,
            capabilities: vec!["chat".into(), "coding".into()],
            ram_required_mb: 0,
            vram_required_mb: 0,
            recommended_hardware: "Cloud API".to_string(),
            download_url: None,
            checksum: None,
            is_local: false,
            requires_api_key: true,
        });
    }

    // Fireworks AI
    for (id, name, category) in [
        ("fireworks/llama-3.3-70b", "Llama 3.3 70B", ModelStoreCategory::General),
        ("fireworks/mixtral-8x7b", "Mixtral 8x7B", ModelStoreCategory::General),
    ] {
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: "fireworks".to_string(),
            provider_display: "Fireworks AI".to_string(),
            source: "cloud".to_string(),
            version: "latest".to_string(),
            description: format!("{name} — hosted on Fireworks AI"),
            size_bytes: 0,
            license: "Various".to_string(),
            category,
            capabilities: vec!["chat".into()],
            ram_required_mb: 0,
            vram_required_mb: 0,
            recommended_hardware: "Cloud API".to_string(),
            download_url: None,
            checksum: None,
            is_local: false,
            requires_api_key: true,
        });
    }

    // Perplexity
    catalog.push(ModelStoreEntry {
        id: "perplexity/sonar-pro".to_string(),
        name: "Sonar Pro".to_string(),
        provider: "perplexity".to_string(),
        provider_display: "Perplexity".to_string(),
        source: "cloud".to_string(),
        version: "latest".to_string(),
        description: "Perplexity's Sonar Pro — search-grounded model".to_string(),
        size_bytes: 0,
        license: "Proprietary".to_string(),
        category: ModelStoreCategory::General,
        capabilities: vec!["chat".into(), "search".into()],
        ram_required_mb: 0,
        vram_required_mb: 0,
        recommended_hardware: "Cloud API".to_string(),
        download_url: None,
        checksum: None,
        is_local: false,
        requires_api_key: true,
    });

    // Local GGUF models
    for (id, name, provider, size, ram, vram, category, desc) in &[
        ("ollama/llama-3.2-3b", "Llama 3.2 3B (Q4)", "ollama", 1_900_000_000u64, 4096, 2048, ModelStoreCategory::General, "Meta Llama 3.2 3B parameter Q4 quantized GGUF — good for low-end hardware"),
        ("ollama/llama-3.2-1b", "Llama 3.2 1B (Q4)", "ollama", 700_000_000u64, 2048, 1024, ModelStoreCategory::General, "Meta Llama 3.2 1B Q4 — ultra-lightweight local model"),
        ("ollama/mistral-7b", "Mistral 7B (Q4)", "ollama", 4_100_000_000u64, 8192, 4096, ModelStoreCategory::General, "Mistral 7B Q4 quantized GGUF"),
        ("ollama/codellama-7b", "CodeLlama 7B (Q4)", "ollama", 3_800_000_000u64, 8192, 4096, ModelStoreCategory::Coding, "CodeLlama 7B Q4 — specialized for code generation"),
        ("ollama/llama-3.1-8b", "Llama 3.1 8B (Q4)", "ollama", 4_700_000_000u64, 16384, 6144, ModelStoreCategory::General, "Meta Llama 3.1 8B Q4 — balanced performance"),
        ("ollama/qwen-2.5-7b", "Qwen 2.5 7B (Q4)", "ollama", 4_200_000_000u64, 8192, 4096, ModelStoreCategory::General, "Alibaba Qwen 2.5 7B Q4 — strong multi-language support"),
        ("ollama/deepseek-coder-v2", "DeepSeek Coder V2 (Q4)", "ollama", 8_400_000_000u64, 16384, 8192, ModelStoreCategory::Coding, "DeepSeek Coder V2 Q4 — specialized coding model"),
        ("ollama/phi-3-mini", "Phi-3 Mini (Q4)", "ollama", 2_200_000_000u64, 4096, 2048, ModelStoreCategory::General, "Microsoft Phi-3 Mini Q4 — efficient small model"),
        ("ollama/gemma-2-2b", "Gemma 2 2B (Q4)", "ollama", 1_300_000_000u64, 2048, 1024, ModelStoreCategory::General, "Google Gemma 2 2B Q4 — compact and capable"),
        ("ollama/llama-3.2-vision-11b", "Llama 3.2 Vision 11B (Q4)", "ollama", 6_500_000_000u64, 16384, 8192, ModelStoreCategory::Vision, "Meta Llama 3.2 Vision 11B Q4 — vision-language model"),
        ("ollama/nomic-embed-text", "Nomic Embed Text", "ollama", 300_000_000u64, 1024, 512, ModelStoreCategory::Embedding, "Nomic Embed Text — text embedding model"),
        ("ollama/llama-3.2-3b", "Llama 3.2 3B (Q4)", "ollama", 1_900_000_000u64, 4096, 2048, ModelStoreCategory::General, "Meta Llama 3.2 3B Q4 — good for low-end hardware"),
    ] {
        if *id == "ollama/llama-3.2-3b" && catalog.iter().any(|e| e.id == "ollama/llama-3.2-3b") {
            continue;
        }
        catalog.push(ModelStoreEntry {
            id: id.to_string(),
            name: name.to_string(),
            provider: provider.to_string(),
            provider_display: provider_display_name(provider),
            source: "local".to_string(),
            version: "latest".to_string(),
            description: desc.to_string(),
            size_bytes: *size,
            license: match *provider {
                "ollama" => "Various".to_string(),
                "lm_studio" => "Various".to_string(),
                _ => "Various".to_string(),
            },
            category: *category,
            capabilities: capabilities_for(category),
            ram_required_mb: *ram,
            vram_required_mb: *vram,
            recommended_hardware: match *ram {
                r if r <= 2048 => "Low-end PC (4GB RAM)".to_string(),
                r if r <= 4096 => "Mid-range PC (8GB RAM)".to_string(),
                r if r <= 8192 => "High-end PC (16GB RAM)".to_string(),
                _ => "Workstation (32GB+ RAM)".to_string(),
            },
            download_url: Some(format!("https://registry.aetheros.com/models/{id}/download")),
            checksum: None,
            is_local: true,
            requires_api_key: false,
        });
    }

    // Same entry with ollama==lm_studio to support both unless we deduplicate
    catalog
}

fn provider_display_name(provider: &str) -> String {
    match provider {
        "ollama" => "Ollama".to_string(),
        "lm_studio" => "LM Studio".to_string(),
        "llamacpp" => "llama.cpp".to_string(),
        "openai" => "OpenAI".to_string(),
        "anthropic" => "Anthropic".to_string(),
        "google" => "Google Gemini".to_string(),
        "openrouter" => "OpenRouter".to_string(),
        "azure" => "Azure OpenAI".to_string(),
        "groq" => "Groq".to_string(),
        "deepseek" => "DeepSeek".to_string(),
        "mistral" => "Mistral".to_string(),
        "cohere" => "Cohere".to_string(),
        "together" => "Together AI".to_string(),
        "fireworks" => "Fireworks AI".to_string(),
        "perplexity" => "Perplexity".to_string(),
        _ => provider.to_string(),
    }
}

fn capabilities_for(category: &ModelStoreCategory) -> Vec<String> {
    match category {
        ModelStoreCategory::General => vec!["chat".into()],
        ModelStoreCategory::Coding => vec!["chat".into(), "coding".into()],
        ModelStoreCategory::Reasoning => vec!["chat".into(), "reasoning".into()],
        ModelStoreCategory::Vision => vec!["chat".into(), "vision".into()],
        ModelStoreCategory::Voice => vec!["voice".into()],
        ModelStoreCategory::Embedding => vec!["embedding".into()],
        ModelStoreCategory::ImageGeneration => vec!["image-generation".into()],
        ModelStoreCategory::SpeechToText => vec!["speech-to-text".into()],
        ModelStoreCategory::TextToSpeech => vec!["text-to-speech".into()],
        ModelStoreCategory::Offline => vec!["chat".into(), "offline".into()],
        ModelStoreCategory::Experimental => vec!["experimental".into()],
    }
}

pub fn search_catalog(query: &str, catalog: &[ModelStoreEntry]) -> Vec<ModelStoreEntry> {
    let q = query.to_lowercase();
    catalog.iter()
        .filter(|m| m.name.to_lowercase().contains(&q) || m.provider.to_lowercase().contains(&q) || m.description.to_lowercase().contains(&q))
        .cloned()
        .collect()
}

pub fn filter_catalog(
    catalog: &[ModelStoreEntry],
    provider: Option<&str>,
    category: Option<ModelStoreCategory>,
    min_ram: Option<u64>,
    local_only: bool,
    cloud_only: bool,
) -> Vec<ModelStoreEntry> {
    catalog.iter()
        .filter(|m| {
            if let Some(p) = provider { m.provider == p } else { true }
        })
        .filter(|m| {
            if let Some(c) = category { m.category == c } else { true }
        })
        .filter(|m| {
            if let Some(r) = min_ram { m.ram_required_mb <= r } else { true }
        })
        .filter(|m| {
            if local_only { m.is_local } else { true }
        })
        .filter(|m| {
            if cloud_only { !m.is_local } else { true }
        })
        .cloned()
        .collect()
}

pub fn providers_in_catalog(catalog: &[ModelStoreEntry]) -> Vec<String> {
    let mut providers: Vec<String> = catalog.iter().map(|m| m.provider.clone()).collect();
    providers.sort();
    providers.dedup();
    providers
}

#[tauri::command]
pub async fn get_model_catalog() -> Result<Vec<ModelStoreEntry>, String> {
    Ok(builtin_catalog())
}

#[tauri::command]
pub async fn search_model_catalog(query: String) -> Result<Vec<ModelStoreEntry>, String> {
    let catalog = builtin_catalog();
    Ok(search_catalog(&query, &catalog))
}

#[tauri::command]
pub async fn filter_model_catalog(
    provider: Option<String>,
    category: Option<String>,
    local_only: bool,
    cloud_only: bool,
) -> Result<Vec<ModelStoreEntry>, String> {
    let catalog = builtin_catalog();
    let category_enum = category.as_deref().and_then(|c| {
        match c {
            "general" => Some(ModelStoreCategory::General),
            "coding" => Some(ModelStoreCategory::Coding),
            "reasoning" => Some(ModelStoreCategory::Reasoning),
            "vision" => Some(ModelStoreCategory::Vision),
            "voice" => Some(ModelStoreCategory::Voice),
            "embedding" => Some(ModelStoreCategory::Embedding),
            "image_generation" => Some(ModelStoreCategory::ImageGeneration),
            "speech_to_text" => Some(ModelStoreCategory::SpeechToText),
            "text_to_speech" => Some(ModelStoreCategory::TextToSpeech),
            "offline" => Some(ModelStoreCategory::Offline),
            "experimental" => Some(ModelStoreCategory::Experimental),
            _ => None,
        }
    });
    Ok(filter_catalog(&catalog, provider.as_deref(), category_enum, None, local_only, cloud_only))
}

#[tauri::command]
pub async fn get_catalog_providers() -> Result<Vec<String>, String> {
    Ok(providers_in_catalog(&builtin_catalog()))
}
