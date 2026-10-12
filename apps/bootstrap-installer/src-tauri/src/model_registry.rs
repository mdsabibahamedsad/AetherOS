use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstalledModel {
    pub id: String,
    pub name: String,
    pub provider: String,
    pub source: String,
    pub version: String,
    pub size_bytes: u64,
    pub path: String,
    pub model_type: ModelType,
    pub category: ModelCategory,
    pub checksum: Option<String>,
    pub installed_at: String,
    pub last_used: Option<String>,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ModelType {
    Chat,
    Reasoning,
    Coding,
    Vision,
    Embedding,
    Voice,
    ImageGeneration,
    SpeechToText,
    TextToSpeech,
    Experimental,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ModelCategory {
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelRegistry {
    pub models: Vec<InstalledModel>,
    pub model_map: HashMap<String, usize>,
}

impl ModelRegistry {
    pub fn load() -> Result<Self, String> {
        let path = registry_path();
        if !path.exists() {
            return Ok(Self { models: Vec::new(), model_map: HashMap::new() });
        }
        let content = std::fs::read_to_string(&path).map_err(|e| format!("Read error: {e}"))?;
        let models: Vec<InstalledModel> = serde_json::from_str(&content).map_err(|e| format!("Parse error: {e}"))?;
        let model_map = models.iter().enumerate().map(|(i, m)| (m.id.clone(), i)).collect();
        Ok(Self { models, model_map })
    }

    pub fn save(&self) -> Result<(), String> {
        let path = registry_path();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create dir: {e}"))?;
        }
        let content = serde_json::to_string_pretty(&self.models).map_err(|e| format!("Serialize error: {e}"))?;
        std::fs::write(&path, content).map_err(|e| format!("Write error: {e}"))?;
        Ok(())
    }

    pub fn get(&self, id: &str) -> Option<&InstalledModel> {
        self.model_map.get(id).map(|&i| &self.models[i])
    }

    pub fn get_mut(&mut self, id: &str) -> Option<&mut InstalledModel> {
        self.model_map.get(id).map(|&i| &mut self.models[i])
    }

    pub fn add(&mut self, model: InstalledModel) {
        self.model_map.insert(model.id.clone(), self.models.len());
        self.models.push(model);
    }

    pub fn remove(&mut self, id: &str) -> Option<InstalledModel> {
        if let Some(&idx) = self.model_map.get(id) {
            let model = self.models.remove(idx);
            self.model_map.remove(id);
            for (i, m) in self.models.iter().enumerate().skip(idx) {
                self.model_map.insert(m.id.clone(), i);
            }
            Some(model)
        } else {
            None
        }
    }

    pub fn list(&self) -> &[InstalledModel] {
        &self.models
    }

    pub fn count(&self) -> usize {
        self.models.len()
    }

    pub fn total_size(&self) -> u64 {
        self.models.iter().map(|m| m.size_bytes).sum()
    }

    pub fn by_provider(&self, provider: &str) -> Vec<&InstalledModel> {
        self.models.iter().filter(|m| m.provider == provider).collect()
    }

    pub fn by_category(&self, category: ModelCategory) -> Vec<&InstalledModel> {
        self.models.iter().filter(|m| m.category == category).collect()
    }

    pub fn by_source(&self, source: &str) -> Vec<&InstalledModel> {
        self.models.iter().filter(|m| m.source == source).collect()
    }

    pub fn find_by_name(&self, name: &str) -> Option<&InstalledModel> {
        self.models.iter().find(|m| m.name == name || m.id == name)
    }

    pub fn mark_used(&mut self, id: &str) {
        if let Some(model) = self.get_mut(id) {
            model.last_used = Some(now_iso());
        }
    }
}

fn registry_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("model-registry.json")
}

fn now_iso() -> String {
    let duration = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = duration.as_secs();
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", (secs / 86400) % 30 + 1, secs % 86400 / 3600 + 1, (secs % 3600) / 60, secs % 60, 0)
}

#[tauri::command]
pub async fn get_installed_models() -> Result<Vec<InstalledModel>, String> {
    let registry = ModelRegistry::load()?;
    Ok(registry.models)
}

#[tauri::command]
pub async fn get_model_registry_stats() -> Result<serde_json::Value, String> {
    let registry = ModelRegistry::load()?;
    Ok(serde_json::json!({
        "count": registry.count(),
        "total_size_bytes": registry.total_size(),
        "by_provider": registry.models.iter().fold(HashMap::new(), |mut acc, m| {
            *acc.entry(m.provider.clone()).or_insert(0) += 1;
            acc
        }),
    }))
}
