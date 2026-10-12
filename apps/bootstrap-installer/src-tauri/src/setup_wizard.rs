use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WizardStep {
    Welcome,
    Profile,
    Theme,
    AIProvider,
    ModelSelection,
    LocalAI,
    APIConfig,
    Services,
    Knowledge,
    Workspace,
    Permissions,
    Summary,
    Finish,
}

impl WizardStep {
    pub fn all() -> &'static [WizardStep] {
        &[
            WizardStep::Welcome,
            WizardStep::Profile,
            WizardStep::Theme,
            WizardStep::AIProvider,
            WizardStep::ModelSelection,
            WizardStep::LocalAI,
            WizardStep::APIConfig,
            WizardStep::Services,
            WizardStep::Knowledge,
            WizardStep::Workspace,
            WizardStep::Permissions,
            WizardStep::Summary,
            WizardStep::Finish,
        ]
    }

    pub fn index(&self) -> usize {
        Self::all().iter().position(|s| s == self).unwrap_or(0)
    }

    pub fn title(&self) -> &'static str {
        match self {
            WizardStep::Welcome => "Welcome to AetherOS",
            WizardStep::Profile => "Your Profile",
            WizardStep::Theme => "Choose Your Theme",
            WizardStep::AIProvider => "AI Provider",
            WizardStep::ModelSelection => "Model Selection",
            WizardStep::LocalAI => "Local AI Setup",
            WizardStep::APIConfig => "API Configuration",
            WizardStep::Services => "Connect Services",
            WizardStep::Knowledge => "Import Knowledge",
            WizardStep::Workspace => "Workspace Setup",
            WizardStep::Permissions => "Permissions",
            WizardStep::Summary => "Review Your Settings",
            WizardStep::Finish => "Getting Started",
        }
    }

    pub fn next(&self) -> Option<WizardStep> {
        let all = Self::all();
        let idx = self.index();
        if idx + 1 < all.len() {
            Some(all[idx + 1])
        } else {
            None
        }
    }

    pub fn previous(&self) -> Option<WizardStep> {
        let idx = self.index();
        if idx > 0 {
            Some(Self::all()[idx - 1])
        } else {
            None
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WizardState {
    pub current_step: WizardStep,
    pub completed_steps: Vec<WizardStep>,
    pub profile: Option<ProfileData>,
    pub theme: Option<ThemeData>,
    pub ai_providers: Vec<AIProviderData>,
    pub models: Option<ModelSelectionData>,
    pub local_ai: Option<LocalAIData>,
    pub api_configs: Vec<APIConfigData>,
    pub services: Vec<ServiceConnectionData>,
    pub knowledge: Option<KnowledgeData>,
    pub permissions: PermissionData,
    pub workspace: Option<WorkspaceData>,
    pub started_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfileData {
    pub display_name: String,
    pub workspace_name: String,
    pub language: String,
    pub region: String,
    pub timezone: String,
    pub accessibility: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThemeData {
    pub mode: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AIProviderData {
    pub provider: String,
    pub enabled: bool,
    pub api_key_set: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelSelectionData {
    pub default_model: String,
    pub reasoning_model: Option<String>,
    pub coding_model: Option<String>,
    pub vision_model: Option<String>,
    pub fast_model: Option<String>,
    pub cheap_model: Option<String>,
    pub offline_model: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalAIData {
    pub provider: String,
    pub endpoint: String,
    pub auto_detected: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct APIConfigData {
    pub provider: String,
    pub api_key: String,
    pub base_url: Option<String>,
    pub organization_id: Option<String>,
    pub proxy: Option<String>,
    pub timeout_secs: Option<u64>,
    pub retry_count: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceConnectionData {
    pub service: String,
    pub enabled: bool,
    pub config: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KnowledgeData {
    pub paths: Vec<String>,
    pub file_types: Vec<String>,
    pub imported: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionData {
    pub notifications: bool,
    pub auto_update: bool,
    pub background_service: bool,
    pub startup: bool,
    pub crash_reports: bool,
    pub analytics: bool,
}

impl Default for PermissionData {
    fn default() -> Self {
        Self {
            notifications: true,
            auto_update: true,
            background_service: true,
            startup: false,
            crash_reports: true,
            analytics: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkspaceData {
    pub projects: bool,
    pub knowledge: bool,
    pub downloads: bool,
    pub extensions: bool,
    pub logs: bool,
    pub models: bool,
    pub cache: bool,
}

impl WizardState {
    pub fn new() -> Self {
        let now = now_iso();
        Self {
            current_step: WizardStep::Welcome,
            completed_steps: Vec::new(),
            profile: None,
            theme: None,
            ai_providers: Vec::new(),
            models: None,
            local_ai: None,
            api_configs: Vec::new(),
            services: Vec::new(),
            knowledge: None,
            permissions: PermissionData::default(),
            workspace: None,
            started_at: now.clone(),
            updated_at: now,
        }
    }

    pub fn advance(&mut self) -> Option<WizardStep> {
        let next = self.current_step.next()?;
        self.completed_steps.push(self.current_step);
        self.current_step = next;
        self.updated_at = now_iso();
        save_wizard_state(self).ok();
        Some(next)
    }

    pub fn go_back(&mut self) -> Option<WizardStep> {
        let prev = self.current_step.previous()?;
        self.completed_steps.pop();
        self.current_step = prev;
        self.updated_at = now_iso();
        save_wizard_state(self).ok();
        Some(prev)
    }

    pub fn skip_to(&mut self, step: WizardStep) {
        if !self.completed_steps.contains(&self.current_step) {
            self.completed_steps.push(self.current_step);
        }
        self.current_step = step;
        self.updated_at = now_iso();
        save_wizard_state(self).ok();
    }
}

fn wizard_state_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("setup-wizard-state.json")
}

fn save_wizard_state(state: &WizardState) -> Result<(), String> {
    let path = wizard_state_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(state).map_err(|e| format!("Serialize error: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write error: {e}"))?;
    Ok(())
}

fn load_wizard_state() -> Option<WizardState> {
    let path = wizard_state_path();
    if !path.exists() {
        return None;
    }
    let content = std::fs::read_to_string(&path).ok()?;
    serde_json::from_str(&content).ok()
}

fn now_iso() -> String {
    let duration = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = duration.as_secs();
    let days = secs / 86400;
    let hours = (secs % 86400) / 3600;
    let minutes = (secs % 3600) / 60;
    let seconds = secs % 60;
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", days / 30 + 1, days % 30 + 1, hours, minutes, seconds)
}

#[tauri::command]
pub async fn get_wizard_state() -> Result<Option<WizardState>, String> {
    Ok(load_wizard_state())
}

#[tauri::command]
pub async fn start_wizard() -> Result<WizardState, String> {
    let state = WizardState::new();
    save_wizard_state(&state)?;
    tracing::info!("setup wizard started");
    Ok(state)
}

#[tauri::command]
pub async fn advance_wizard_step(state: WizardState) -> Result<WizardState, String> {
    let mut s = state;
    s.advance();
    Ok(s)
}

#[tauri::command]
pub async fn go_back_wizard_step(state: WizardState) -> Result<WizardState, String> {
    let mut s = state;
    s.go_back();
    Ok(s)
}

#[tauri::command]
pub async fn skip_wizard_to(step: WizardStep, state: WizardState) -> Result<WizardState, String> {
    let mut s = state;
    s.skip_to(step);
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_profile(state: WizardState, profile: ProfileData) -> Result<WizardState, String> {
    let mut s = state;
    s.profile = Some(profile);
    save_wizard_state(&s)?;
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_theme(state: WizardState, theme: ThemeData) -> Result<WizardState, String> {
    let mut s = state;
    s.theme = Some(theme);
    save_wizard_state(&s)?;
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_ai_providers(state: WizardState, providers: Vec<AIProviderData>) -> Result<WizardState, String> {
    let mut s = state;
    s.ai_providers = providers;
    save_wizard_state(&s)?;
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_models(state: WizardState, models: ModelSelectionData) -> Result<WizardState, String> {
    let mut s = state;
    s.models = Some(models);
    save_wizard_state(&s)?;
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_local_ai(state: WizardState, local_ai: LocalAIData) -> Result<WizardState, String> {
    let mut s = state;
    s.local_ai = Some(local_ai);
    save_wizard_state(&s)?;
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_api_configs(state: WizardState, configs: Vec<APIConfigData>) -> Result<WizardState, String> {
    let mut s = state;
    s.api_configs = configs;
    save_wizard_state(&s)?;
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_services(state: WizardState, services: Vec<ServiceConnectionData>) -> Result<WizardState, String> {
    let mut s = state;
    s.services = services;
    save_wizard_state(&s)?;
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_knowledge(state: WizardState, knowledge: KnowledgeData) -> Result<WizardState, String> {
    let mut s = state;
    s.knowledge = Some(knowledge);
    save_wizard_state(&s)?;
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_permissions(state: WizardState, permissions: PermissionData) -> Result<WizardState, String> {
    let mut s = state;
    s.permissions = permissions;
    save_wizard_state(&s)?;
    Ok(s)
}

#[tauri::command]
pub async fn save_wizard_workspace(state: WizardState, workspace: WorkspaceData) -> Result<WizardState, String> {
    let mut s = state;
    s.workspace = Some(workspace);
    save_wizard_state(&s)?;
    Ok(s)
}
