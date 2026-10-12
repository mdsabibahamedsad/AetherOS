use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardData {
    pub organization: OrgSummary,
    pub users: UserStats,
    pub teams: TeamStats,
    pub storage: StorageStats,
    pub models: ModelStats,
    pub extensions: ExtensionStats,
    pub automation: AutomationStats,
    pub security: SecurityStats,
    pub activity: ActivityStats,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrgSummary {
    pub total_orgs: usize,
    pub total_members: usize,
    pub active_members: usize,
    pub suspended_members: usize,
    pub invited_members: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserStats {
    pub total_users: usize,
    pub by_role: HashMap<String, usize>,
    pub recently_joined: Vec<String>,
    pub active_today: usize,
    pub active_this_week: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TeamStats {
    pub total_teams: usize,
    pub total_departments: usize,
    pub total_projects: usize,
    pub public_teams: usize,
    pub private_teams: usize,
    pub archived_projects: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageStats {
    pub total_storage_mb: u64,
    pub used_storage_mb: u64,
    pub knowledge_size_mb: u64,
    pub model_size_mb: u64,
    pub extension_size_mb: u64,
    pub cache_size_mb: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelStats {
    pub total_models: usize,
    pub installed_models: usize,
    pub active_models: usize,
    pub model_providers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtensionStats {
    pub total_extensions: usize,
    pub installed_extensions: usize,
    pub active_agents: usize,
    pub active_skills: usize,
    pub mcp_servers: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutomationStats {
    pub total_workflows: usize,
    pub active_workflows: usize,
    pub total_runs: u64,
    pub failed_runs: u64,
    pub scheduled_jobs: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityStats {
    pub device_count: usize,
    pub trusted_devices: usize,
    pub recent_logins: usize,
    pub failed_logins: usize,
    pub active_sessions: usize,
    pub policies_enforced: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActivityStats {
    pub total_actions_24h: usize,
    pub top_actions: Vec<(String, usize)>,
    pub top_users: Vec<(String, usize)>,
    pub actions_by_hour: Vec<usize>,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn dashboard_cache_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("dashboard_cache.json")
}

fn dir_size(path: &std::path::Path) -> u64 {
    if !path.exists() {
        return 0;
    }
    let mut total = 0u64;
    if let Ok(entries) = std::fs::read_dir(path) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                total += std::fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
            } else if path.is_dir() {
                total += dir_size(&path);
            }
        }
    }
    total
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

pub fn get_dashboard(org_id: &str) -> DashboardData {
    let aetheros_home = crate::paths::aetheros_home();
    let _team_base = team_dir();

    let members = crate::org_workspace::load_members(org_id);
    let teams = crate::team_management::list_teams(org_id);
    let projects = crate::team_management::list_projects(org_id);
    let depts = crate::team_management::list_departments(org_id);
    let policies = crate::enterprise_policy::list_policies(org_id);

    let mut by_role: HashMap<String, usize> = HashMap::new();
    let mut active_members = 0;
    let mut suspended = 0;
    let mut invited = 0;
    for m in &members {
        *by_role.entry(m.role_id.clone()).or_insert(0) += 1;
        match m.status {
            super::org_workspace::MemberStatus::Active => active_members += 1,
            super::org_workspace::MemberStatus::Suspended => suspended += 1,
            super::org_workspace::MemberStatus::Invited => invited += 1,
            _ => {}
        }
    }

    let public_teams = teams.iter().filter(|t| t.is_public).count();
    let archived = projects.iter().filter(|p| p.is_archived).count();

    let marketplace_dir = aetheros_home.join("marketplace");
    let knowledge_dir = aetheros_home.join("knowledge");
    let models_dir = aetheros_home.join("models");

    let total_storage = dir_size(&aetheros_home) / (1024 * 1024);
    let knowledge_size = dir_size(&knowledge_dir) / (1024 * 1024);
    let model_size = dir_size(&models_dir) / (1024 * 1024);
    let extension_size = dir_size(&marketplace_dir) / (1024 * 1024);

    let installed_extensions = crate::marketplace_store::list_installed_by_type(
        super::marketplace_package::PackageType::Extension,
    )
    .len();
    let agents = crate::marketplace_store::list_installed_by_type(
        super::marketplace_package::PackageType::Agent,
    )
    .len();
    let skills = crate::marketplace_store::list_installed_by_type(
        super::marketplace_package::PackageType::Skill,
    )
    .len();
    let mcp_count = crate::marketplace_store::list_installed_by_type(
        super::marketplace_package::PackageType::McpServer,
    )
    .len();
    let workflows = crate::marketplace_store::list_installed_by_type(
        super::marketplace_package::PackageType::Workflow,
    )
    .len();

    let devices = crate::enterprise_policy::list_devices(org_id, "");
    let device_count = devices.len();
    let trusted = devices.iter().filter(|d| d.trusted).count();
    let policies_enforced = policies.iter().filter(|p| p.enabled).count();

    let audit_entries = crate::audit_log::get_audit_log(org_id);
    let recent_24h: Vec<_> = audit_entries
        .iter()
        .filter(|e| {
            let secs = crate::audit_log::parse_iso_secs_fallback(&e.timestamp);
            use std::time::{SystemTime, UNIX_EPOCH};
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();
            now.saturating_sub(secs) < 86400
        })
        .collect();

    let mut top_actions_map: HashMap<String, usize> = HashMap::new();
    let mut top_users_map: HashMap<String, usize> = HashMap::new();
    for e in &recent_24h {
        *top_actions_map.entry(e.action.clone()).or_insert(0) += 1;
        *top_users_map.entry(e.user_name.clone()).or_insert(0) += 1;
    }
    let mut top_actions: Vec<(String, usize)> = top_actions_map.into_iter().collect();
    top_actions.sort_by(|a, b| b.1.cmp(&a.1));
    top_actions.truncate(10);
    let mut top_users: Vec<(String, usize)> = top_users_map.into_iter().collect();
    top_users.sort_by(|a, b| b.1.cmp(&a.1));
    top_users.truncate(10);

    DashboardData {
        organization: OrgSummary {
            total_orgs: 1,
            total_members: members.len(),
            active_members,
            suspended_members: suspended,
            invited_members: invited,
        },
        users: UserStats {
            total_users: members.len(),
            by_role,
            recently_joined: members.iter().take(5).map(|m| m.display_name.clone()).collect(),
            active_today: recent_24h.len(),
            active_this_week: recent_24h.len(),
        },
        teams: TeamStats {
            total_teams: teams.len(),
            total_departments: depts.len(),
            total_projects: projects.len(),
            public_teams,
            private_teams: teams.len() - public_teams,
            archived_projects: archived,
        },
        storage: StorageStats {
            total_storage_mb: total_storage + 1,
            used_storage_mb: total_storage,
            knowledge_size_mb: knowledge_size,
            model_size_mb: model_size,
            extension_size_mb: extension_size,
            cache_size_mb: 0,
        },
        models: ModelStats {
            total_models: 0,
            installed_models: 0,
            active_models: 0,
            model_providers: Vec::new(),
        },
        extensions: ExtensionStats {
            total_extensions: installed_extensions + agents + skills,
            installed_extensions,
            active_agents: agents,
            active_skills: skills,
            mcp_servers: mcp_count,
        },
        automation: AutomationStats {
            total_workflows: workflows,
            active_workflows: workflows,
            total_runs: 0,
            failed_runs: 0,
            scheduled_jobs: 0,
        },
        security: SecurityStats {
            device_count,
            trusted_devices: trusted,
            recent_logins: recent_24h.iter().filter(|e| e.action == "login").count(),
            failed_logins: recent_24h.iter().filter(|e| !e.success).count(),
            active_sessions: 0,
            policies_enforced,
        },
        activity: ActivityStats {
            total_actions_24h: recent_24h.len(),
            top_actions,
            top_users,
            actions_by_hour: vec![0; 24],
        },
    }
}

#[tauri::command]
pub async fn admin_get_dashboard(org_id: String) -> Result<DashboardData, String> {
    Ok(get_dashboard(&org_id))
}
