use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ThemeMode {
    Light,
    Dark,
    System,
    HighContrast,
}

impl ThemeMode {
    pub fn all() -> &'static [ThemeMode] {
        &[ThemeMode::Light, ThemeMode::Dark, ThemeMode::System, ThemeMode::HighContrast]
    }

    pub fn label(&self) -> &'static str {
        match self {
            ThemeMode::Light => "Light",
            ThemeMode::Dark => "Dark",
            ThemeMode::System => "System",
            ThemeMode::HighContrast => "High Contrast",
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            ThemeMode::Light => "Clean, bright interface for daytime use",
            ThemeMode::Dark => "Easy on the eyes in low-light environments",
            ThemeMode::System => "Follows your operating system's theme",
            ThemeMode::HighContrast => "Maximum readability with high contrast colors",
        }
    }

    pub fn css_variables(&self) -> &'static str {
        match self {
            ThemeMode::Light => r##"{
  "bg-primary": "#ffffff",
  "bg-secondary": "#f5f5f5",
  "text-primary": "#1a1a2e",
  "text-secondary": "#555555",
  "accent": "#6366f1",
  "accent-hover": "#4f46e5",
  "border": "#e0e0e0",
  "success": "#22c55e",
  "warning": "#f59e0b",
  "error": "#ef4444",
  "surface": "#ffffff",
  "surface-hover": "#f0f0f0"
}"##,
            ThemeMode::Dark => r##"{
  "bg-primary": "#1a1a2e",
  "bg-secondary": "#16213e",
  "text-primary": "#e0e0e0",
  "text-secondary": "#a0a0a0",
  "accent": "#818cf8",
  "accent-hover": "#6366f1",
  "border": "#2a2a4a",
  "success": "#22c55e",
  "warning": "#f59e0b",
  "error": "#ef4444",
  "surface": "#1e1e3a",
  "surface-hover": "#2a2a4a"
}"##,
            ThemeMode::System => ThemeMode::Light.css_variables(),
            ThemeMode::HighContrast => r##"{
  "bg-primary": "#000000",
  "bg-secondary": "#1a1a1a",
  "text-primary": "#ffffff",
  "text-secondary": "#cccccc",
  "accent": "#ffff00",
  "accent-hover": "#ffcc00",
  "border": "#ffffff",
  "success": "#00ff00",
  "warning": "#ffaa00",
  "error": "#ff0000",
  "surface": "#000000",
  "surface-hover": "#333333"
}"##,
        }
    }
}

fn current_theme_path() -> std::path::PathBuf {
    crate::paths::aetheros_home().join("config").join("theme.json")
}

pub fn save_theme(mode: ThemeMode) -> Result<(), String> {
    let path = current_theme_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create config dir: {e}"))?;
    }
    let content = serde_json::json!({
        "mode": mode,
        "updated_at": now_iso(),
    });
    std::fs::write(&path, serde_json::to_string_pretty(&content).unwrap())
        .map_err(|e| format!("Cannot write theme: {e}"))?;
    tracing::info!(?mode, "theme saved");
    Ok(())
}

pub fn load_theme() -> Result<ThemeMode, String> {
    let path = current_theme_path();
    if !path.exists() {
        return Ok(ThemeMode::System);
    }
    let content = std::fs::read_to_string(&path).map_err(|e| format!("Read error: {e}"))?;
    let json: serde_json::Value = serde_json::from_str(&content).map_err(|e| format!("Parse error: {e}"))?;
    let mode_str = json.get("mode").and_then(|m| m.as_str()).unwrap_or("system");
    match mode_str {
        "light" => Ok(ThemeMode::Light),
        "dark" => Ok(ThemeMode::Dark),
        "high_contrast" | "highcontrast" => Ok(ThemeMode::HighContrast),
        _ => Ok(ThemeMode::System),
    }
}

fn now_iso() -> String {
    let duration = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let _secs = duration.as_secs();
    format!("2026-01-01T00:00:00Z")
}

#[tauri::command]
pub async fn get_available_themes() -> Result<Vec<serde_json::Value>, String> {
    let themes: Vec<serde_json::Value> = ThemeMode::all()
        .iter()
        .map(|mode| {
            serde_json::json!({
                "id": mode,
                "label": mode.label(),
                "description": mode.description(),
                "css_variables": mode.css_variables(),
            })
        })
        .collect();
    Ok(themes)
}

#[tauri::command]
pub async fn get_current_theme() -> Result<ThemeMode, String> {
    load_theme()
}

#[tauri::command]
pub async fn set_theme(mode: ThemeMode) -> Result<(), String> {
    save_theme(mode)
}

#[tauri::command]
pub async fn preview_theme(mode: ThemeMode) -> Result<String, String> {
    Ok(mode.css_variables().to_string())
}
