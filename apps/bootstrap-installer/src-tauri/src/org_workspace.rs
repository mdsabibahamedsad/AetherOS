use serde::{Deserialize, Serialize};

use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WorkspaceType {
    Personal,
    Family,
    Startup,
    Business,
    Enterprise,
    Education,
    Developer,
    Research,
}

impl WorkspaceType {
    pub fn as_str(&self) -> &'static str {
        match self {
            WorkspaceType::Personal => "personal",
            WorkspaceType::Family => "family",
            WorkspaceType::Startup => "startup",
            WorkspaceType::Business => "business",
            WorkspaceType::Enterprise => "enterprise",
            WorkspaceType::Education => "education",
            WorkspaceType::Developer => "developer",
            WorkspaceType::Research => "research",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "personal" => Some(WorkspaceType::Personal),
            "family" => Some(WorkspaceType::Family),
            "startup" => Some(WorkspaceType::Startup),
            "business" => Some(WorkspaceType::Business),
            "enterprise" => Some(WorkspaceType::Enterprise),
            "education" => Some(WorkspaceType::Education),
            "developer" => Some(WorkspaceType::Developer),
            "research" => Some(WorkspaceType::Research),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Organization {
    pub id: String,
    pub name: String,
    pub slug: String,
    pub workspace_type: WorkspaceType,
    pub owner_id: String,
    pub description: String,
    pub logo_url: Option<String>,
    pub website: Option<String>,
    pub created_at: String,
    pub updated_at: String,
    pub max_members: u32,
    pub storage_limit_mb: u64,
    pub settings: OrganizationSettings,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrganizationSettings {
    pub allow_guest_access: bool,
    pub allow_public_sharing: bool,
    pub require_2fa: bool,
    pub auto_approve_invites: bool,
    pub session_timeout_minutes: u32,
    pub max_login_attempts: u32,
    pub password_min_length: u32,
}

impl Default for OrganizationSettings {
    fn default() -> Self {
        Self {
            allow_guest_access: true,
            allow_public_sharing: true,
            require_2fa: false,
            auto_approve_invites: false,
            session_timeout_minutes: 480,
            max_login_attempts: 5,
            password_min_length: 8,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum MemberStatus {
    Active,
    Suspended,
    Invited,
    Inactive,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Member {
    pub user_id: String,
    pub display_name: String,
    pub email: String,
    pub role_id: String,
    pub custom_role_name: Option<String>,
    pub joined_at: String,
    pub status: MemberStatus,
    pub last_active_at: Option<String>,
    pub teams: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrgMember {
    pub member: Member,
    pub permissions: Vec<String>,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn orgs_path() -> PathBuf {
    team_dir().join("organizations.json")
}

fn members_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("members.json")
}

fn org_dir(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id)
}

pub fn load_organizations() -> Vec<Organization> {
    let path = orgs_path();
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

pub fn save_organizations(orgs: &[Organization]) -> Result<(), String> {
    let path = orgs_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(orgs).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn load_members(org_id: &str) -> Vec<Member> {
    let path = members_path(org_id);
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

pub fn save_members(org_id: &str, members: &[Member]) -> Result<(), String> {
    let path = members_path(org_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(members).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("org_{:x}", nanos)
}

fn slugify(name: &str) -> String {
    name.to_lowercase()
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == '-' || *c == '_' || *c == ' ')
        .collect::<String>()
        .trim()
        .replace(' ', "-")
}

pub fn create_organization(
    name: &str,
    workspace_type: WorkspaceType,
    owner_id: &str,
    owner_email: &str,
    owner_name: &str,
) -> Result<Organization, String> {
    let mut orgs = load_organizations();
    let id = generate_id();
    let slug = slugify(name);
    let now = iso_now();

    let org = Organization {
        id: id.clone(),
        name: name.to_string(),
        slug,
        workspace_type: workspace_type.clone(),
        owner_id: owner_id.to_string(),
        description: String::new(),
        logo_url: None,
        website: None,
        created_at: now.clone(),
        updated_at: now.clone(),
        max_members: match workspace_type.clone() {
            WorkspaceType::Personal => 1,
            WorkspaceType::Family => 6,
            WorkspaceType::Startup => 25,
            WorkspaceType::Business => 100,
            WorkspaceType::Enterprise => 10000,
            WorkspaceType::Education => 500,
            WorkspaceType::Developer => 10,
            WorkspaceType::Research => 50,
        },
        storage_limit_mb: match workspace_type {
            WorkspaceType::Personal => 1024,
            WorkspaceType::Family => 5120,
            WorkspaceType::Startup => 25600,
            WorkspaceType::Business => 102400,
            WorkspaceType::Enterprise => 1048576,
            WorkspaceType::Education => 51200,
            WorkspaceType::Developer => 5120,
            WorkspaceType::Research => 25600,
        },
        settings: OrganizationSettings::default(),
    };

    let owner = Member {
        user_id: owner_id.to_string(),
        display_name: owner_name.to_string(),
        email: owner_email.to_string(),
        role_id: "owner".to_string(),
        custom_role_name: None,
        joined_at: now.clone(),
        status: MemberStatus::Active,
        last_active_at: Some(now),
        teams: Vec::new(),
    };

    save_members(&id, &[owner])?;
    orgs.push(org.clone());
    save_organizations(&orgs)?;

    Ok(org)
}

pub fn rename_organization(org_id: &str, new_name: &str) -> Result<Organization, String> {
    let mut orgs = load_organizations();
    let org = orgs
        .iter_mut()
        .find(|o| o.id == org_id)
        .ok_or_else(|| format!("Organization not found: {org_id}"))?;
    org.name = new_name.to_string();
    org.slug = slugify(new_name);
    org.updated_at = iso_now();
    let result = org.clone();
    save_organizations(&orgs)?;
    Ok(result)
}

pub fn delete_organization(org_id: &str) -> Result<(), String> {
    let mut orgs = load_organizations();
    let pos = orgs
        .iter()
        .position(|o| o.id == org_id)
        .ok_or_else(|| format!("Organization not found: {org_id}"))?;
    orgs.remove(pos);
    save_organizations(&orgs)?;

    let dir = org_dir(org_id);
    if dir.exists() {
        std::fs::remove_dir_all(&dir).ok();
    }
    Ok(())
}

pub fn get_organization(org_id: &str) -> Option<Organization> {
    load_organizations().into_iter().find(|o| o.id == org_id)
}

pub fn get_organization_by_slug(slug: &str) -> Option<Organization> {
    load_organizations()
        .into_iter()
        .find(|o| o.slug == slug)
}

pub fn add_member(
    org_id: &str,
    user_id: &str,
    display_name: &str,
    email: &str,
    role_id: &str,
) -> Result<Member, String> {
    let org = get_organization(org_id).ok_or_else(|| format!("Org not found: {org_id}"))?;
    let mut members = load_members(org_id);
    if members.len() >= org.max_members as usize {
        return Err("Organization member limit reached".to_string());
    }
    if members.iter().any(|m| m.user_id == user_id) {
        return Err("Member already exists".to_string());
    }
    let now = iso_now();
    let member = Member {
        user_id: user_id.to_string(),
        display_name: display_name.to_string(),
        email: email.to_string(),
        role_id: role_id.to_string(),
        custom_role_name: None,
        joined_at: now.clone(),
        status: MemberStatus::Active,
        last_active_at: Some(now),
        teams: Vec::new(),
    };
    members.push(member.clone());
    save_members(org_id, &members)?;
    Ok(member)
}

pub fn remove_member(org_id: &str, user_id: &str) -> Result<(), String> {
    let mut members = load_members(org_id);
    let pos = members
        .iter()
        .position(|m| m.user_id == user_id)
        .ok_or_else(|| format!("Member not found: {user_id}"))?;
    members.remove(pos);
    save_members(org_id, &members)
}

pub fn suspend_member(org_id: &str, user_id: &str) -> Result<(), String> {
    let mut members = load_members(org_id);
    let member = members
        .iter_mut()
        .find(|m| m.user_id == user_id)
        .ok_or_else(|| format!("Member not found: {user_id}"))?;
    member.status = MemberStatus::Suspended;
    save_members(org_id, &members)
}

pub fn reactivate_member(org_id: &str, user_id: &str) -> Result<(), String> {
    let mut members = load_members(org_id);
    let member = members
        .iter_mut()
        .find(|m| m.user_id == user_id)
        .ok_or_else(|| format!("Member not found: {user_id}"))?;
    member.status = MemberStatus::Active;
    save_members(org_id, &members)
}

pub fn transfer_ownership(org_id: &str, new_owner_id: &str) -> Result<Organization, String> {
    let mut orgs = load_organizations();
    let org = orgs
        .iter_mut()
        .find(|o| o.id == org_id)
        .ok_or_else(|| format!("Organization not found: {org_id}"))?;
    let members = load_members(org_id);
    if !members.iter().any(|m| m.user_id == new_owner_id) {
        return Err("New owner must be a member".to_string());
    }
    org.owner_id = new_owner_id.to_string();
    org.updated_at = iso_now();
    let result = org.clone();
    save_organizations(&orgs)?;
    Ok(result)
}

pub fn set_member_role(
    org_id: &str,
    user_id: &str,
    new_role_id: &str,
) -> Result<Member, String> {
    let mut members = load_members(org_id);
    let member = members
        .iter_mut()
        .find(|m| m.user_id == user_id)
        .ok_or_else(|| format!("Member not found: {user_id}"))?;
    member.role_id = new_role_id.to_string();
    let result = member.clone();
    save_members(org_id, &members)?;
    Ok(result)
}

pub fn assign_team(org_id: &str, user_id: &str, team_id: &str) -> Result<(), String> {
    let mut members = load_members(org_id);
    let member = members
        .iter_mut()
        .find(|m| m.user_id == user_id)
        .ok_or_else(|| format!("Member not found: {user_id}"))?;
    if !member.teams.contains(&team_id.to_string()) {
        member.teams.push(team_id.to_string());
    }
    save_members(org_id, &members)
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

#[tauri::command]
pub async fn org_create(
    name: String,
    workspace_type: String,
    owner_id: String,
    owner_email: String,
    owner_name: String,
) -> Result<Organization, String> {
    let wtype =
        WorkspaceType::from_str(&workspace_type).ok_or_else(|| "Invalid workspace type".to_string())?;
    create_organization(&name, wtype, &owner_id, &owner_email, &owner_name)
}

#[tauri::command]
pub async fn org_list(owner_id: String) -> Result<Vec<Organization>, String> {
    Ok(load_organizations()
        .into_iter()
        .filter(|o| o.owner_id == owner_id)
        .collect())
}

#[tauri::command]
pub async fn org_get(org_id: String) -> Result<Option<Organization>, String> {
    Ok(get_organization(&org_id))
}

#[tauri::command]
pub async fn org_rename(org_id: String, new_name: String) -> Result<Organization, String> {
    rename_organization(&org_id, &new_name)
}

#[tauri::command]
pub async fn org_delete(org_id: String) -> Result<(), String> {
    delete_organization(&org_id)
}

#[tauri::command]
pub async fn org_list_members(org_id: String) -> Result<Vec<Member>, String> {
    Ok(load_members(&org_id))
}

#[tauri::command]
pub async fn org_add_member(
    org_id: String,
    user_id: String,
    display_name: String,
    email: String,
    role_id: String,
) -> Result<Member, String> {
    add_member(&org_id, &user_id, &display_name, &email, &role_id)
}

#[tauri::command]
pub async fn org_remove_member(org_id: String, user_id: String) -> Result<(), String> {
    remove_member(&org_id, &user_id)
}

#[tauri::command]
pub async fn org_suspend_member(org_id: String, user_id: String) -> Result<(), String> {
    suspend_member(&org_id, &user_id)
}

#[tauri::command]
pub async fn org_reactivate_member(org_id: String, user_id: String) -> Result<(), String> {
    reactivate_member(&org_id, &user_id)
}

#[tauri::command]
pub async fn org_transfer_ownership(
    org_id: String,
    new_owner_id: String,
) -> Result<Organization, String> {
    transfer_ownership(&org_id, &new_owner_id)
}

#[tauri::command]
pub async fn org_set_member_role(
    org_id: String,
    user_id: String,
    role_id: String,
) -> Result<Member, String> {
    set_member_role(&org_id, &user_id, &role_id)
}
