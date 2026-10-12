use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InstallMode {
    Express,
    Recommended,
    Custom,
    Advanced,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallModeConfig {
    pub mode: InstallMode,
    pub auto_runtimes: bool,
    pub auto_shortcuts: bool,
    pub auto_launch: bool,
    pub desktop_app: bool,
    pub cli_tools: bool,
    pub create_shortcuts: bool,
    pub create_profile: bool,
    pub silent: bool,
    pub show_details: bool,
    pub auto_start: bool,
}

impl InstallModeConfig {
    pub fn for_mode(mode: InstallMode) -> Self {
        match mode {
            InstallMode::Express => Self {
                mode,
                auto_runtimes: true,
                auto_shortcuts: true,
                auto_launch: true,
                desktop_app: true,
                cli_tools: true,
                create_shortcuts: true,
                create_profile: true,
                silent: false,
                show_details: false,
                auto_start: true,
            },
            InstallMode::Recommended => Self {
                mode,
                auto_runtimes: true,
                auto_shortcuts: true,
                auto_launch: true,
                desktop_app: true,
                cli_tools: true,
                create_shortcuts: true,
                create_profile: true,
                silent: false,
                show_details: true,
                auto_start: true,
            },
            InstallMode::Custom => Self {
                mode,
                auto_runtimes: false,
                auto_shortcuts: false,
                auto_launch: false,
                desktop_app: true,
                cli_tools: true,
                create_shortcuts: true,
                create_profile: true,
                silent: false,
                show_details: true,
                auto_start: false,
            },
            InstallMode::Advanced => Self {
                mode,
                auto_runtimes: false,
                auto_shortcuts: false,
                auto_launch: false,
                desktop_app: false,
                cli_tools: false,
                create_shortcuts: false,
                create_profile: false,
                silent: true,
                show_details: true,
                auto_start: false,
            },
        }
    }

    pub fn requires_runtime_detection(&self) -> bool {
        !self.auto_runtimes
    }

    pub fn requires_user_input(&self) -> bool {
        matches!(self.mode, InstallMode::Custom | InstallMode::Advanced)
    }

    pub fn description(&self) -> &'static str {
        match self.mode {
            InstallMode::Express => "Quick install with default settings. Best for most users.",
            InstallMode::Recommended => "Balanced install with recommended defaults and progress visibility.",
            InstallMode::Custom => "Full control over every component and setting.",
            InstallMode::Advanced => "Silent installation for enterprise deployment.",
        }
    }
}

pub fn default_mode() -> InstallMode {
    InstallMode::Recommended
}

#[tauri::command]
pub fn get_install_modes() -> Vec<InstallModeConfig> {
    vec![
        InstallModeConfig::for_mode(InstallMode::Express),
        InstallModeConfig::for_mode(InstallMode::Recommended),
        InstallModeConfig::for_mode(InstallMode::Custom),
        InstallModeConfig::for_mode(InstallMode::Advanced),
    ]
}
