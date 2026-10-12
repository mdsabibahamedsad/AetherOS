use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    pub org_id: String,
    pub project_id: Option<String>,
    pub title: String,
    pub description: String,
    pub assignee_id: Option<String>,
    pub creator_id: String,
    pub priority: TaskPriority,
    pub status: TaskStatus,
    pub due_date: Option<String>,
    pub labels: Vec<String>,
    pub created_at: String,
    pub updated_at: String,
    pub completed_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskPriority {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskStatus {
    Todo,
    InProgress,
    InReview,
    Done,
    Cancelled,
    Blocked,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskComment {
    pub id: String,
    pub task_id: String,
    pub user_id: String,
    pub user_name: String,
    pub content: String,
    pub created_at: String,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn tasks_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("tasks.json")
}

fn task_comments_path(org_id: &str, task_id: &str) -> PathBuf {
    team_dir()
        .join("orgs")
        .join(org_id)
        .join("tasks")
        .join(task_id)
        .join("comments.json")
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
    format!("task_{:x}", nanos)
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

pub fn create_task(
    org_id: &str,
    project_id: Option<&str>,
    title: &str,
    description: &str,
    assignee_id: Option<&str>,
    creator_id: &str,
    priority: TaskPriority,
    due_date: Option<&str>,
    labels: Vec<String>,
) -> Result<Task, String> {
    let mut tasks = load_json::<Task>(&tasks_path(org_id));
    let id = generate_id();
    let now = iso_now();
    let task = Task {
        id: id.clone(),
        org_id: org_id.to_string(),
        project_id: project_id.map(|s| s.to_string()),
        title: title.to_string(),
        description: description.to_string(),
        assignee_id: assignee_id.map(|s| s.to_string()),
        creator_id: creator_id.to_string(),
        priority,
        status: TaskStatus::Todo,
        due_date: due_date.map(|s| s.to_string()),
        labels,
        created_at: now.clone(),
        updated_at: now,
        completed_at: None,
    };
    tasks.push(task.clone());
    save_json(&tasks_path(org_id), &tasks)?;
    Ok(task)
}

pub fn update_task_status(org_id: &str, task_id: &str, status: TaskStatus) -> Result<Task, String> {
    let mut tasks = load_json::<Task>(&tasks_path(org_id));
    let task = tasks.iter_mut().find(|t| t.id == task_id)
        .ok_or_else(|| format!("Task not found: {task_id}"))?;
    task.status = status;
    task.updated_at = iso_now();
    if matches!(task.status, TaskStatus::Done) {
        task.completed_at = Some(iso_now());
    }
    let result = task.clone();
    save_json(&tasks_path(org_id), &tasks)?;
    Ok(result)
}

pub fn assign_task(org_id: &str, task_id: &str, assignee_id: &str) -> Result<Task, String> {
    let mut tasks = load_json::<Task>(&tasks_path(org_id));
    let task = tasks.iter_mut().find(|t| t.id == task_id)
        .ok_or_else(|| format!("Task not found: {task_id}"))?;
    task.assignee_id = Some(assignee_id.to_string());
    task.updated_at = iso_now();
    let result = task.clone();
    save_json(&tasks_path(org_id), &tasks)?;
    Ok(result)
}

pub fn list_tasks(org_id: &str) -> Vec<Task> {
    load_json(&tasks_path(org_id))
}

pub fn list_tasks_by_assignee(org_id: &str, assignee_id: &str) -> Vec<Task> {
    load_json::<Task>(&tasks_path(org_id))
        .into_iter()
        .filter(|t| t.assignee_id.as_deref() == Some(assignee_id))
        .collect()
}

pub fn add_comment(
    org_id: &str,
    task_id: &str,
    user_id: &str,
    user_name: &str,
    content: &str,
) -> Result<TaskComment, String> {
    let path = task_comments_path(org_id, task_id);
    let mut comments = load_json::<TaskComment>(&path);
    let id = generate_id();
    let comment = TaskComment {
        id: id.clone(),
        task_id: task_id.to_string(),
        user_id: user_id.to_string(),
        user_name: user_name.to_string(),
        content: content.to_string(),
        created_at: iso_now(),
    };
    comments.push(comment.clone());
    save_json(&path, &comments)?;
    Ok(comment)
}

pub fn list_comments(org_id: &str, task_id: &str) -> Vec<TaskComment> {
    load_json(&task_comments_path(org_id, task_id))
}

pub fn delete_task(org_id: &str, task_id: &str) -> Result<(), String> {
    let mut tasks = load_json::<Task>(&tasks_path(org_id));
    let pos = tasks.iter().position(|t| t.id == task_id)
        .ok_or_else(|| format!("Task not found: {task_id}"))?;
    tasks.remove(pos);
    save_json(&tasks_path(org_id), &tasks)
}

#[tauri::command]
pub async fn task_create(
    org_id: String, project_id: Option<String>, title: String, description: String,
    assignee_id: Option<String>, creator_id: String, priority: String,
    due_date: Option<String>, labels: Vec<String>,
) -> Result<Task, String> {
    let p = match priority.as_str() {
        "low" => TaskPriority::Low,
        "medium" => TaskPriority::Medium,
        "high" => TaskPriority::High,
        "critical" => TaskPriority::Critical,
        _ => TaskPriority::Medium,
    };
    create_task(&org_id, project_id.as_deref(), &title, &description, assignee_id.as_deref(), &creator_id, p, due_date.as_deref(), labels)
}

#[tauri::command]
pub async fn task_update_status(org_id: String, task_id: String, status: String) -> Result<Task, String> {
    let s = match status.as_str() {
        "todo" => TaskStatus::Todo,
        "in_progress" => TaskStatus::InProgress,
        "in_review" => TaskStatus::InReview,
        "done" => TaskStatus::Done,
        "cancelled" => TaskStatus::Cancelled,
        "blocked" => TaskStatus::Blocked,
        _ => return Err("Invalid status".to_string()),
    };
    update_task_status(&org_id, &task_id, s)
}

#[tauri::command]
pub async fn task_assign(org_id: String, task_id: String, assignee_id: String) -> Result<Task, String> {
    assign_task(&org_id, &task_id, &assignee_id)
}

#[tauri::command]
pub async fn task_list(org_id: String) -> Result<Vec<Task>, String> {
    Ok(list_tasks(&org_id))
}

#[tauri::command]
pub async fn task_list_by_assignee(org_id: String, assignee_id: String) -> Result<Vec<Task>, String> {
    Ok(list_tasks_by_assignee(&org_id, &assignee_id))
}

#[tauri::command]
pub async fn task_add_comment(
    org_id: String, task_id: String, user_id: String, user_name: String, content: String,
) -> Result<TaskComment, String> {
    add_comment(&org_id, &task_id, &user_id, &user_name, &content)
}

#[tauri::command]
pub async fn task_list_comments(org_id: String, task_id: String) -> Result<Vec<TaskComment>, String> {
    Ok(list_comments(&org_id, &task_id))
}

#[tauri::command]
pub async fn task_delete(org_id: String, task_id: String) -> Result<(), String> {
    delete_task(&org_id, &task_id)
}
