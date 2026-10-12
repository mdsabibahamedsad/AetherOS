use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Team {
    pub id: String,
    pub org_id: String,
    pub name: String,
    pub description: String,
    pub parent_team_id: Option<String>,
    pub is_public: bool,
    pub created_at: String,
    pub updated_at: String,
    pub member_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Department {
    pub id: String,
    pub org_id: String,
    pub name: String,
    pub description: String,
    pub teams: Vec<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    pub id: String,
    pub org_id: String,
    pub team_id: Option<String>,
    pub name: String,
    pub description: String,
    pub is_private: bool,
    pub is_archived: bool,
    pub is_template: bool,
    pub template_id: Option<String>,
    pub created_by: String,
    pub created_at: String,
    pub updated_at: String,
    pub member_ids: Vec<String>,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectActivity {
    pub id: String,
    pub project_id: String,
    pub user_id: String,
    pub action: String,
    pub details: String,
    pub timestamp: String,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn teams_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("teams.json")
}

fn departments_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("departments.json")
}

fn projects_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("projects.json")
}

fn activities_path(org_id: &str, project_id: &str) -> PathBuf {
    team_dir()
        .join("orgs")
        .join(org_id)
        .join("projects")
        .join(project_id)
        .join("activities.json")
}

fn load_json<T: serde::de::DeserializeOwned>(path: &PathBuf) -> Vec<T> {
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

fn save_json<T: serde::Serialize>(path: &PathBuf, data: &[T]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(data).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("tm_{:x}", nanos)
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

pub fn create_team(
    org_id: &str,
    name: &str,
    description: &str,
    parent_team_id: Option<&str>,
    is_public: bool,
) -> Result<Team, String> {
    let mut teams = load_json::<Team>(&teams_path(org_id));
    let id = generate_id();
    let now = iso_now();
    let team = Team {
        id: id.clone(),
        org_id: org_id.to_string(),
        name: name.to_string(),
        description: description.to_string(),
        parent_team_id: parent_team_id.map(|s| s.to_string()),
        is_public,
        created_at: now.clone(),
        updated_at: now,
        member_count: 0,
    };
    teams.push(team.clone());
    save_json(&teams_path(org_id), &teams)?;
    Ok(team)
}

pub fn delete_team(org_id: &str, team_id: &str) -> Result<(), String> {
    let mut teams = load_json::<Team>(&teams_path(org_id));
    let pos = teams.iter().position(|t| t.id == team_id)
        .ok_or_else(|| format!("Team not found: {team_id}"))?;
    teams.remove(pos);
    save_json(&teams_path(org_id), &teams)
}

pub fn list_teams(org_id: &str) -> Vec<Team> {
    load_json(&teams_path(org_id))
}

pub fn create_department(
    org_id: &str,
    name: &str,
    description: &str,
    team_ids: Vec<String>,
) -> Result<Department, String> {
    let mut depts = load_json::<Department>(&departments_path(org_id));
    let id = generate_id();
    let dept = Department {
        id: id.clone(),
        org_id: org_id.to_string(),
        name: name.to_string(),
        description: description.to_string(),
        teams: team_ids,
        created_at: iso_now(),
    };
    depts.push(dept.clone());
    save_json(&departments_path(org_id), &depts)?;
    Ok(dept)
}

pub fn list_departments(org_id: &str) -> Vec<Department> {
    load_json(&departments_path(org_id))
}

pub fn create_project(
    org_id: &str,
    team_id: Option<&str>,
    name: &str,
    description: &str,
    is_private: bool,
    created_by: &str,
    is_template: bool,
    template_id: Option<&str>,
) -> Result<Project, String> {
    let mut projects = load_json::<Project>(&projects_path(org_id));
    let id = generate_id();
    let now = iso_now();
    let project = Project {
        id: id.clone(),
        org_id: org_id.to_string(),
        team_id: team_id.map(|s| s.to_string()),
        name: name.to_string(),
        description: description.to_string(),
        is_private,
        is_archived: false,
        is_template,
        template_id: template_id.map(|s| s.to_string()),
        created_by: created_by.to_string(),
        created_at: now.clone(),
        updated_at: now,
        member_ids: vec![created_by.to_string()],
        tags: Vec::new(),
    };
    projects.push(project.clone());
    save_json(&projects_path(org_id), &projects)?;
    Ok(project)
}

pub fn list_projects(org_id: &str) -> Vec<Project> {
    load_json(&projects_path(org_id))
}

pub fn archive_project(org_id: &str, project_id: &str) -> Result<Project, String> {
    let mut projects = load_json::<Project>(&projects_path(org_id));
    let project = projects.iter_mut().find(|p| p.id == project_id)
        .ok_or_else(|| format!("Project not found: {project_id}"))?;
    project.is_archived = true;
    project.updated_at = iso_now();
    let result = project.clone();
    save_json(&projects_path(org_id), &projects)?;
    Ok(result)
}

pub fn add_project_member(org_id: &str, project_id: &str, user_id: &str) -> Result<(), String> {
    let mut projects = load_json::<Project>(&projects_path(org_id));
    let project = projects.iter_mut().find(|p| p.id == project_id)
        .ok_or_else(|| format!("Project not found: {project_id}"))?;
    if !project.member_ids.contains(&user_id.to_string()) {
        project.member_ids.push(user_id.to_string());
    }
    save_json(&projects_path(org_id), &projects)
}

pub fn log_activity(
    org_id: &str,
    project_id: &str,
    user_id: &str,
    action: &str,
    details: &str,
) -> Result<(), String> {
    let path = activities_path(org_id, project_id);
    let mut activities = load_json::<ProjectActivity>(&path);
    let id = generate_id();
    activities.push(ProjectActivity {
        id: id.clone(),
        project_id: project_id.to_string(),
        user_id: user_id.to_string(),
        action: action.to_string(),
        details: details.to_string(),
        timestamp: iso_now(),
    });
    save_json(&path, &activities)
}

pub fn get_project_activities(org_id: &str, project_id: &str) -> Vec<ProjectActivity> {
    load_json(&activities_path(org_id, project_id))
}

#[tauri::command]
pub async fn team_create(
    org_id: String, name: String, description: String,
    parent_team_id: Option<String>, is_public: bool,
) -> Result<Team, String> {
    create_team(&org_id, &name, &description, parent_team_id.as_deref(), is_public)
}

#[tauri::command]
pub async fn team_delete(org_id: String, team_id: String) -> Result<(), String> {
    delete_team(&org_id, &team_id)
}

#[tauri::command]
pub async fn team_list(org_id: String) -> Result<Vec<Team>, String> {
    Ok(list_teams(&org_id))
}

#[tauri::command]
pub async fn dept_create(
    org_id: String, name: String, description: String, team_ids: Vec<String>,
) -> Result<Department, String> {
    create_department(&org_id, &name, &description, team_ids)
}

#[tauri::command]
pub async fn dept_list(org_id: String) -> Result<Vec<Department>, String> {
    Ok(list_departments(&org_id))
}

#[tauri::command]
pub async fn project_create(
    org_id: String, team_id: Option<String>, name: String, description: String,
    is_private: bool, created_by: String, is_template: bool, template_id: Option<String>,
) -> Result<Project, String> {
    create_project(&org_id, team_id.as_deref(), &name, &description, is_private, &created_by, is_template, template_id.as_deref())
}

#[tauri::command]
pub async fn project_list(org_id: String) -> Result<Vec<Project>, String> {
    Ok(list_projects(&org_id))
}

#[tauri::command]
pub async fn project_archive(org_id: String, project_id: String) -> Result<Project, String> {
    archive_project(&org_id, &project_id)
}

#[tauri::command]
pub async fn project_add_member(org_id: String, project_id: String, user_id: String) -> Result<(), String> {
    add_project_member(&org_id, &project_id, &user_id)
}

#[tauri::command]
pub async fn project_activities(org_id: String, project_id: String) -> Result<Vec<ProjectActivity>, String> {
    Ok(get_project_activities(&org_id, &project_id))
}
