use crate::marketplace_package::PackagePermission;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionRequest {
    pub package_id: String,
    pub package_name: String,
    pub permissions: Vec<PackagePermission>,
    pub timestamp: String,
    pub resolved: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionDecision {
    pub package_id: String,
    pub permissions: HashMap<String, bool>,
    pub always_allow: bool,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GrantedPermissions {
    pub package_id: String,
    pub filesystem: bool,
    pub internet: bool,
    pub clipboard: bool,
    pub notifications: bool,
    pub ai_provider: bool,
    pub model_access: bool,
    pub microphone: bool,
    pub camera: bool,
    pub extensions: bool,
    pub env_vars: bool,
    pub custom: HashMap<String, bool>,
    pub always_allow: bool,
}

impl Default for GrantedPermissions {
    fn default() -> Self {
        Self {
            package_id: String::new(),
            filesystem: false,
            internet: false,
            clipboard: false,
            notifications: false,
            ai_provider: false,
            model_access: false,
            microphone: false,
            camera: false,
            extensions: false,
            env_vars: false,
            custom: HashMap::new(),
            always_allow: false,
        }
    }
}

pub fn default_permission_set(_package_id: &str) -> Vec<PackagePermission> {
    vec![
        PackagePermission { permission: "filesystem".into(), description: "Read and write files on your computer".into(), required: false, granted: None },
        PackagePermission { permission: "internet".into(), description: "Access the internet".into(), required: true, granted: None },
        PackagePermission { permission: "clipboard".into(), description: "Read and write clipboard contents".into(), required: false, granted: None },
        PackagePermission { permission: "notifications".into(), description: "Send desktop notifications".into(), required: false, granted: None },
        PackagePermission { permission: "ai_provider".into(), description: "Access configured AI providers".into(), required: false, granted: None },
        PackagePermission { permission: "model_access".into(), description: "Access installed AI models".into(), required: false, granted: None },
        PackagePermission { permission: "microphone".into(), description: "Access microphone".into(), required: false, granted: None },
        PackagePermission { permission: "camera".into(), description: "Access camera".into(), required: false, granted: None },
        PackagePermission { permission: "env_vars".into(), description: "Read environment variables".into(), required: false, granted: None },
    ]
}

fn permissions_path() -> std::path::PathBuf {
    crate::paths::aetheros_home().join("config").join("marketplace-permissions.json")
}

pub fn load_permissions() -> Vec<GrantedPermissions> {
    let path = permissions_path();
    if !path.exists() { return Vec::new(); }
    std::fs::read_to_string(&path).ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

pub fn save_permissions(permissions: &[GrantedPermissions]) -> Result<(), String> {
    let path = permissions_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(permissions).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn get_package_permissions(package_id: &str) -> GrantedPermissions {
    let all = load_permissions();
    all.into_iter().find(|p| p.package_id == package_id).unwrap_or_default()
}

pub fn grant_permissions(decision: PermissionDecision) -> Result<(), String> {
    let mut all = load_permissions();
    let mut gp = GrantedPermissions::default();
    gp.package_id = decision.package_id.clone();
    gp.always_allow = decision.always_allow;

    for (perm, granted) in &decision.permissions {
        match perm.as_str() {
            "filesystem" => gp.filesystem = *granted,
            "internet" => gp.internet = *granted,
            "clipboard" => gp.clipboard = *granted,
            "notifications" => gp.notifications = *granted,
            "ai_provider" => gp.ai_provider = *granted,
            "model_access" => gp.model_access = *granted,
            "microphone" => gp.microphone = *granted,
            "camera" => gp.camera = *granted,
            "env_vars" => gp.env_vars = *granted,
            _ => { gp.custom.insert(perm.clone(), *granted); }
        }
    }

    if let Some(existing) = all.iter_mut().find(|p| p.package_id == decision.package_id) {
        *existing = gp;
    } else {
        all.push(gp);
    }

    save_permissions(&all)
}

pub fn revoke_permissions(package_id: &str) -> Result<(), String> {
    let mut all = load_permissions();
    all.retain(|p| p.package_id != package_id);
    save_permissions(&all)
}

pub fn check_permission(package_id: &str, permission: &str) -> bool {
    let gp = get_package_permissions(package_id);
    if gp.always_allow { return true; }
    match permission {
        "filesystem" => gp.filesystem,
        "internet" => gp.internet,
        "clipboard" => gp.clipboard,
        "notifications" => gp.notifications,
        "ai_provider" => gp.ai_provider,
        "model_access" => gp.model_access,
        "microphone" => gp.microphone,
        "camera" => gp.camera,
        "env_vars" => gp.env_vars,
        _ => *gp.custom.get(permission).unwrap_or(&false),
    }
}

#[tauri::command]
pub async fn marketplace_get_permissions(package_id: String) -> Result<GrantedPermissions, String> {
    Ok(get_package_permissions(&package_id))
}

#[tauri::command]
pub async fn marketplace_grant_permissions(decision: PermissionDecision) -> Result<(), String> {
    grant_permissions(decision)
}

#[tauri::command]
pub async fn marketplace_revoke_permissions(package_id: String) -> Result<(), String> {
    revoke_permissions(&package_id)
}

#[tauri::command]
pub async fn marketplace_check_permission(package_id: String, permission: String) -> Result<bool, String> {
    Ok(check_permission(&package_id, &permission))
}
