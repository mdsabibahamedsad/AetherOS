use serde::{Deserialize, Serialize};

use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SharedKnowledge {
    pub id: String,
    pub org_id: String,
    pub title: String,
    pub content: String,
    pub content_type: KnowledgeType,
    pub created_by: String,
    pub created_at: String,
    pub updated_at: String,
    pub tags: Vec<String>,
    pub shared_with_teams: Vec<String>,
    pub is_public: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum KnowledgeType {
    Document,
    Prompt,
    Agent,
    Skill,
    Workflow,
    Model,
    McpServer,
    CodeSnippet,
    Reference,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SharedDocument {
    pub id: String,
    pub org_id: String,
    pub knowledge_id: String,
    pub content: String,
    pub version: u32,
    pub created_by: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PresenceInfo {
    pub user_id: String,
    pub org_id: String,
    pub status: PresenceStatus,
    pub current_view: Option<String>,
    pub last_seen_at: String,
    pub device: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PresenceStatus {
    Online,
    Away,
    Busy,
    Offline,
    Inactive,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SharedSession {
    pub id: String,
    pub org_id: String,
    pub name: String,
    pub host_id: String,
    pub participant_ids: Vec<String>,
    pub session_type: SessionType,
    pub is_active: bool,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SessionType {
    AiConversation,
    CodeReview,
    DocumentEdit,
    Brainstorm,
    Research,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActivityFeedEntry {
    pub id: String,
    pub org_id: String,
    pub user_id: String,
    pub user_name: String,
    pub action: String,
    pub resource_type: String,
    pub resource_name: String,
    pub timestamp: String,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn knowledge_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("knowledge.json")
}

fn presence_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("presence.json")
}

fn sessions_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("sessions.json")
}

fn activity_feed_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("activity_feed.json")
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
    format!("col_{:x}", nanos)
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

pub fn share_knowledge(
    org_id: &str,
    title: &str,
    content: &str,
    content_type: KnowledgeType,
    created_by: &str,
    tags: Vec<String>,
    shared_with_teams: Vec<String>,
    is_public: bool,
) -> Result<SharedKnowledge, String> {
    let mut items = load_json::<SharedKnowledge>(&knowledge_path(org_id));
    let id = generate_id();
    let now = iso_now();
    let item = SharedKnowledge {
    id: id.clone(),
        org_id: org_id.to_string(),
        title: title.to_string(),
        content: content.to_string(),
        content_type,
        created_by: created_by.to_string(),
        created_at: now.clone(),
        updated_at: now,
        tags,
        shared_with_teams,
        is_public,
    };
    items.push(item.clone());
    save_json(&knowledge_path(org_id), &items)?;
    Ok(item)
}

pub fn list_shared_knowledge(org_id: &str) -> Vec<SharedKnowledge> {
    load_json(&knowledge_path(org_id))
}

pub fn update_presence(
    org_id: &str,
    user_id: &str,
    status: PresenceStatus,
    current_view: Option<&str>,
    device: &str,
) -> Result<(), String> {
    let mut presences = load_json::<PresenceInfo>(&presence_path(org_id));
    let now = iso_now();
    if let Some(existing) = presences.iter_mut().find(|p| p.user_id == user_id) {
        existing.status = status;
        existing.current_view = current_view.map(|s| s.to_string());
        existing.last_seen_at = now;
        existing.device = device.to_string();
    } else {
        presences.push(PresenceInfo {
            user_id: user_id.to_string(),
            org_id: org_id.to_string(),
            status,
            current_view: current_view.map(|s| s.to_string()),
            last_seen_at: now,
            device: device.to_string(),
        });
    }
    save_json(&presence_path(org_id), &presences)
}

pub fn get_presence(org_id: &str) -> Vec<PresenceInfo> {
    load_json(&presence_path(org_id))
}

pub fn create_shared_session(
    org_id: &str,
    name: &str,
    host_id: &str,
    session_type: SessionType,
) -> Result<SharedSession, String> {
    let mut sessions = load_json::<SharedSession>(&sessions_path(org_id));
    let id = generate_id();
    let session = SharedSession {
        id: id.clone(),
        org_id: org_id.to_string(),
        name: name.to_string(),
        host_id: host_id.to_string(),
        participant_ids: vec![host_id.to_string()],
        session_type,
        is_active: true,
        created_at: iso_now(),
    };
    sessions.push(session.clone());
    save_json(&sessions_path(org_id), &sessions)?;
    Ok(session)
}

pub fn join_session(org_id: &str, session_id: &str, user_id: &str) -> Result<(), String> {
    let mut sessions = load_json::<SharedSession>(&sessions_path(org_id));
    let session = sessions.iter_mut().find(|s| s.id == session_id)
        .ok_or_else(|| format!("Session not found: {session_id}"))?;
    if !session.participant_ids.contains(&user_id.to_string()) {
        session.participant_ids.push(user_id.to_string());
    }
    save_json(&sessions_path(org_id), &sessions)
}

pub fn list_sessions(org_id: &str) -> Vec<SharedSession> {
    load_json(&sessions_path(org_id))
}

pub fn add_activity_feed_entry(
    org_id: &str,
    user_id: &str,
    user_name: &str,
    action: &str,
    resource_type: &str,
    resource_name: &str,
) -> Result<(), String> {
    let mut feed = load_json::<ActivityFeedEntry>(&activity_feed_path(org_id));
    let id = generate_id();
    feed.push(ActivityFeedEntry {
        id: id.clone(),
        org_id: org_id.to_string(),
        user_id: user_id.to_string(),
        user_name: user_name.to_string(),
        action: action.to_string(),
        resource_type: resource_type.to_string(),
        resource_name: resource_name.to_string(),
        timestamp: iso_now(),
    });
    if feed.len() > 200 {
        feed.drain(0..(feed.len() - 200));
    }
    save_json(&activity_feed_path(org_id), &feed)
}

pub fn get_activity_feed(org_id: &str) -> Vec<ActivityFeedEntry> {
    let mut feed = load_json(&activity_feed_path(org_id));
    feed.reverse();
    feed
}

#[tauri::command]
pub async fn collab_share_knowledge(
    org_id: String, title: String, content: String, content_type: String,
    created_by: String, tags: Vec<String>, shared_with_teams: Vec<String>, is_public: bool,
) -> Result<SharedKnowledge, String> {
    let ctype = match content_type.as_str() {
        "document" => KnowledgeType::Document,
        "prompt" => KnowledgeType::Prompt,
        "agent" => KnowledgeType::Agent,
        "skill" => KnowledgeType::Skill,
        "workflow" => KnowledgeType::Workflow,
        "model" => KnowledgeType::Model,
        "mcp_server" => KnowledgeType::McpServer,
        "code_snippet" => KnowledgeType::CodeSnippet,
        "reference" => KnowledgeType::Reference,
        _ => return Err("Invalid content type".to_string()),
    };
    share_knowledge(&org_id, &title, &content, ctype, &created_by, tags, shared_with_teams, is_public)
}

#[tauri::command]
pub async fn collab_list_knowledge(org_id: String) -> Result<Vec<SharedKnowledge>, String> {
    Ok(list_shared_knowledge(&org_id))
}

#[tauri::command]
pub async fn collab_update_presence(
    org_id: String, user_id: String, status: String,
    current_view: Option<String>, device: String,
) -> Result<(), String> {
    let pstatus = match status.as_str() {
        "online" => PresenceStatus::Online,
        "away" => PresenceStatus::Away,
        "busy" => PresenceStatus::Busy,
        "offline" => PresenceStatus::Offline,
        _ => PresenceStatus::Inactive,
    };
    update_presence(&org_id, &user_id, pstatus, current_view.as_deref(), &device)
}

#[tauri::command]
pub async fn collab_get_presence(org_id: String) -> Result<Vec<PresenceInfo>, String> {
    Ok(get_presence(&org_id))
}

#[tauri::command]
pub async fn collab_create_session(
    org_id: String, name: String, host_id: String, session_type: String,
) -> Result<SharedSession, String> {
    let stype = match session_type.as_str() {
        "ai_conversation" => SessionType::AiConversation,
        "code_review" => SessionType::CodeReview,
        "document_edit" => SessionType::DocumentEdit,
        "brainstorm" => SessionType::Brainstorm,
        "research" => SessionType::Research,
        _ => return Err("Invalid session type".to_string()),
    };
    create_shared_session(&org_id, &name, &host_id, stype)
}

#[tauri::command]
pub async fn collab_join_session(org_id: String, session_id: String, user_id: String) -> Result<(), String> {
    join_session(&org_id, &session_id, &user_id)
}

#[tauri::command]
pub async fn collab_list_sessions(org_id: String) -> Result<Vec<SharedSession>, String> {
    Ok(list_sessions(&org_id))
}

#[tauri::command]
pub async fn collab_activity_feed(org_id: String) -> Result<Vec<ActivityFeedEntry>, String> {
    Ok(get_activity_feed(&org_id))
}
