use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InvitationStatus {
    Pending,
    Accepted,
    Expired,
    Revoked,
    Declined,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Invitation {
    pub id: String,
    pub org_id: String,
    pub inviter_id: String,
    pub email: Option<String>,
    pub share_link: Option<String>,
    pub code: String,
    pub qr_data: Option<String>,
    pub role_id: String,
    pub message: Option<String>,
    pub expires_at: String,
    pub status: InvitationStatus,
    pub created_at: String,
    pub accepted_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BulkInvitationResult {
    pub success: Vec<String>,
    pub failed: Vec<(String, String)>,
    pub total: usize,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn invitations_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("invitations.json")
}

pub fn load_invitations(org_id: &str) -> Vec<Invitation> {
    let path = invitations_path(org_id);
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

pub fn save_invitations(org_id: &str, invs: &[Invitation]) -> Result<(), String> {
    let path = invitations_path(org_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(invs).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("inv_{:x}", nanos)
}

fn generate_code() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("AETHEROS-{:06x}", nanos % 0xFFFFFF)
}

fn iso_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let d = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = d.as_secs();
    let millis = d.subsec_millis();
    let days = secs / 86400;
    let time_secs = secs % 86400;
    let hours = time_secs / 3600;
    let minutes = (time_secs % 3600) / 60;
    let seconds = time_secs % 60;
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:03}Z",
        1970 + (days as f64 / 365.25) as u64,
        1 + ((days % 365) / 30),
        1 + (days % 30),
        hours,
        minutes,
        seconds,
        millis
    )
}

fn expiry_date(hours: u64) -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let d = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = d.as_secs() + hours * 3600;
    let millis = 0;
    let days = secs / 86400;
    let time_secs = secs % 86400;
    let hours = time_secs / 3600;
    let minutes = (time_secs % 3600) / 60;
    let seconds = time_secs % 60;
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:03}Z",
        1970 + (days as f64 / 365.25) as u64,
        1 + ((days % 365) / 30),
        1 + (days % 30),
        hours,
        minutes,
        seconds,
        millis
    )
}

pub fn create_invitation(
    org_id: &str,
    inviter_id: &str,
    email: Option<&str>,
    role_id: &str,
    message: Option<&str>,
    expiry_hours: u64,
) -> Result<Invitation, String> {
    let mut invs = load_invitations(org_id);
    let id = generate_id();
    let code = generate_code();
    let now = iso_now();
    let expires = expiry_date(expiry_hours);

    let inv = Invitation {
        id: id.clone(),
        org_id: org_id.to_string(),
        inviter_id: inviter_id.to_string(),
        email: email.map(|e| e.to_string()),
        share_link: None,
        code: code.clone(),
        qr_data: None,
        role_id: role_id.to_string(),
        message: message.map(|m| m.to_string()),
        expires_at: expires,
        status: InvitationStatus::Pending,
        created_at: now,
        accepted_at: None,
    };

    invs.push(inv.clone());
    save_invitations(org_id, &invs)?;
    Ok(inv)
}

pub fn create_share_link(org_id: &str, inviter_id: &str, role_id: &str) -> Result<Invitation, String> {
    let mut invs = load_invitations(org_id);
    let id = generate_id();
    let code = generate_code();
    let now = iso_now();
    let expires = expiry_date(168);
    let link = format!("aetheros://invite/{}", &code);

    let inv = Invitation {
        id: id.clone(),
        org_id: org_id.to_string(),
        inviter_id: inviter_id.to_string(),
        email: None,
        share_link: Some(link),
        code: code.clone(),
        qr_data: Some(format!("aetheros://invite/qr/{}", &code)),
        role_id: role_id.to_string(),
        message: None,
        expires_at: expires,
        status: InvitationStatus::Pending,
        created_at: now,
        accepted_at: None,
    };

    invs.push(inv.clone());
    save_invitations(org_id, &invs)?;
    Ok(inv)
}

pub fn bulk_invite(
    org_id: &str,
    inviter_id: &str,
    emails: Vec<String>,
    role_id: &str,
    message: Option<&str>,
) -> BulkInvitationResult {
    let mut success = Vec::new();
    let mut failed = Vec::new();

    for email in emails {
        match create_invitation(org_id, inviter_id, Some(&email), role_id, message, 168) {
            Ok(_inv) => success.push(email),
            Err(e) => failed.push((email, e)),
        }
    }

    let total = success.len() + failed.len();
    BulkInvitationResult {
        success,
        failed,
        total,
    }
}

pub fn accept_invitation(code: &str) -> Result<Invitation, String> {
    let team_dir = team_dir();
    let orgs_dir = team_dir.join("orgs");
    if !orgs_dir.exists() {
        return Err("No invitations found".to_string());
    }
    let entries = std::fs::read_dir(&orgs_dir).map_err(|e| format!("Read dir: {e}"))?;
    for entry in entries {
        let entry = entry.map_err(|e| format!("Entry: {e}"))?;
        let org_id = entry.file_name().to_string_lossy().to_string();
        let mut invs = load_invitations(&org_id);
        if let Some(inv) = invs.iter_mut().find(|i| i.code == code) {
            inv.status = InvitationStatus::Accepted;
            inv.accepted_at = Some(iso_now());
            let result = inv.clone();
            save_invitations(&org_id, &invs)?;
            return Ok(result);
        }
    }
    Err("Invitation not found or expired".to_string())
}

pub fn revoke_invitation(org_id: &str, invitation_id: &str) -> Result<(), String> {
    let mut invs = load_invitations(org_id);
    let inv = invs
        .iter_mut()
        .find(|i| i.id == invitation_id)
        .ok_or_else(|| format!("Invitation not found: {invitation_id}"))?;
    inv.status = InvitationStatus::Revoked;
    save_invitations(org_id, &invs)
}

#[tauri::command]
pub async fn inv_create(
    org_id: String,
    inviter_id: String,
    email: String,
    role_id: String,
    message: Option<String>,
    expiry_hours: Option<u64>,
) -> Result<Invitation, String> {
    create_invitation(&org_id, &inviter_id, Some(&email), &role_id, message.as_deref(), expiry_hours.unwrap_or(168))
}

#[tauri::command]
pub async fn inv_create_share_link(
    org_id: String,
    inviter_id: String,
    role_id: String,
) -> Result<Invitation, String> {
    create_share_link(&org_id, &inviter_id, &role_id)
}

#[tauri::command]
pub async fn inv_bulk(
    org_id: String,
    inviter_id: String,
    emails: Vec<String>,
    role_id: String,
    message: Option<String>,
) -> Result<BulkInvitationResult, String> {
    Ok(bulk_invite(&org_id, &inviter_id, emails, &role_id, message.as_deref()))
}

#[tauri::command]
pub async fn inv_list(org_id: String) -> Result<Vec<Invitation>, String> {
    Ok(load_invitations(&org_id))
}

#[tauri::command]
pub async fn inv_accept(code: String) -> Result<Invitation, String> {
    accept_invitation(&code)
}

#[tauri::command]
pub async fn inv_revoke(org_id: String, invitation_id: String) -> Result<(), String> {
    revoke_invitation(&org_id, &invitation_id)
}
