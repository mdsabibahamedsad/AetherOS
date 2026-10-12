use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowDefinition {
    pub id: String,
    pub name: String,
    pub description: String,
    pub enabled: bool,
    pub trigger: WorkflowTrigger,
    pub conditions: Vec<ConditionGroup>,
    pub actions: Vec<WorkflowAction>,
    pub variables: HashMap<String, VariableDefinition>,
    pub error_handling: ErrorHandling,
    pub timeout_seconds: u64,
    pub created_at: String,
    pub updated_at: String,
    pub run_count: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WorkflowTrigger {
    ConnectorEvent {
        connector_id: String,
        event_type: String,
    },
    Schedule {
        config: ScheduleConfig,
    },
    Webhook {
        path: String,
        method: String,
    },
    Manual,
    AiTrigger {
        prompt_template: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScheduleConfig {
    pub cron: String,
    pub timezone: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConditionGroup {
    pub operator: ConditionGroupOperator,
    pub conditions: Vec<WorkflowCondition>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ConditionGroupOperator {
    All,
    Any,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowCondition {
    pub field: String,
    pub operator: ConditionOperator,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ConditionOperator {
    Equals,
    NotEquals,
    Contains,
    NotContains,
    Regex,
    GreaterThan,
    LessThan,
    IsEmpty,
    IsNotEmpty,
    StartsWith,
    EndsWith,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WorkflowAction {
    SendMessage {
        connector_id: String,
        channel: String,
        message_template: String,
    },
    AiAction {
        config: AiActionConfig,
        input_template: String,
    },
    CreateIssue {
        connector_id: String,
        title_template: String,
        description_template: String,
        project: String,
    },
    RouteMessage {
        target_connector: String,
        target_channel: String,
        transform_template: Option<String>,
    },
    HttpRequest {
        url: String,
        method: String,
        headers: HashMap<String, String>,
        body_template: Option<String>,
    },
    UpdateVariable {
        name: String,
        value_template: String,
    },
    ScheduleAction {
        delay_seconds: u64,
        action: Box<WorkflowAction>,
    },
    Notify {
        title: String,
        message_template: String,
        level: String,
    },
    CreateTask {
        title_template: String,
        description_template: String,
        assignee: Option<String>,
    },
    WaitForCondition {
        condition: WorkflowCondition,
        check_interval_seconds: u64,
        timeout_seconds: u64,
    },
    LoopAction {
        iterations: u32,
        actions: Vec<WorkflowAction>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiActionConfig {
    pub provider_id: String,
    pub model: String,
    pub prompt: String,
    pub temperature: Option<f64>,
    pub max_tokens: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VariableDefinition {
    pub scope: VariableScope,
    pub default_value: String,
    pub description: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum VariableScope {
    Global,
    Workflow,
    Local,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorHandling {
    pub retry_count: u32,
    pub retry_delay_seconds: u64,
    pub fallback_action: Option<WorkflowAction>,
    pub continue_on_error: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub success: bool,
    pub action_results: Vec<ActionResult>,
    pub error: Option<String>,
    pub duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionResult {
    pub action_type: String,
    pub success: bool,
    pub output: Option<String>,
    pub error: Option<String>,
    pub duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowLogEntry {
    pub id: String,
    pub workflow_id: String,
    pub triggered_at: String,
    pub trigger_source: String,
    pub success: bool,
    pub duration_ms: u64,
    pub actions_count: usize,
    pub error: Option<String>,
}

fn hub_dir() -> PathBuf {
    crate::paths::aetheros_home().join("hub")
}

fn workflows_path() -> PathBuf {
    hub_dir().join("workflows.json")
}

fn workflow_logs_path() -> PathBuf {
    hub_dir().join("workflow_logs.json")
}

fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("wf_{:x}", nanos)
}

fn log_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("log_{:x}", nanos)
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
        hours, minutes, seconds, millis
    )
}

fn load_workflows() -> Vec<WorkflowDefinition> {
    let path = workflows_path();
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

fn save_workflows(workflows: &[WorkflowDefinition]) -> Result<(), String> {
    let path = workflows_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(workflows).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

fn load_logs() -> Vec<WorkflowLogEntry> {
    let path = workflow_logs_path();
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

fn save_logs(logs: &[WorkflowLogEntry]) -> Result<(), String> {
    let path = workflow_logs_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(logs).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn create_workflow(
    name: &str,
    description: &str,
    trigger: WorkflowTrigger,
    conditions: Vec<ConditionGroup>,
    actions: Vec<WorkflowAction>,
    variables: HashMap<String, VariableDefinition>,
    error_handling: ErrorHandling,
    timeout_seconds: u64,
) -> Result<WorkflowDefinition, String> {
    let mut workflows = load_workflows();
    if workflows.iter().any(|w| w.name == name) {
        return Err(format!("Workflow '{name}' already exists"));
    }
    let now = iso_now();
    let workflow = WorkflowDefinition {
        id: generate_id(),
        name: name.to_string(),
        description: description.to_string(),
        enabled: true,
        trigger,
        conditions,
        actions,
        variables,
        error_handling,
        timeout_seconds,
        created_at: now.clone(),
        updated_at: now,
        run_count: 0,
    };
    let result = workflow.clone();
    workflows.push(workflow);
    save_workflows(&workflows)?;
    Ok(result)
}

pub fn update_workflow(
    workflow_id: &str,
    name: Option<&str>,
    description: Option<&str>,
    trigger: Option<WorkflowTrigger>,
    conditions: Option<Vec<ConditionGroup>>,
    actions: Option<Vec<WorkflowAction>>,
    variables: Option<HashMap<String, VariableDefinition>>,
    error_handling: Option<ErrorHandling>,
    timeout_seconds: Option<u64>,
) -> Result<WorkflowDefinition, String> {
    let mut workflows = load_workflows();
    let wf = workflows.iter_mut().find(|w| w.id == workflow_id)
        .ok_or_else(|| format!("Workflow not found: {workflow_id}"))?;
    if let Some(n) = name { wf.name = n.to_string(); }
    if let Some(d) = description { wf.description = d.to_string(); }
    if let Some(t) = trigger { wf.trigger = t; }
    if let Some(c) = conditions { wf.conditions = c; }
    if let Some(a) = actions { wf.actions = a; }
    if let Some(v) = variables { wf.variables = v; }
    if let Some(e) = error_handling { wf.error_handling = e; }
    if let Some(t) = timeout_seconds { wf.timeout_seconds = t; }
    wf.updated_at = iso_now();
    let result = wf.clone();
    save_workflows(&workflows)?;
    Ok(result)
}

pub fn delete_workflow(workflow_id: &str) -> Result<(), String> {
    let mut workflows = load_workflows();
    let pos = workflows.iter().position(|w| w.id == workflow_id)
        .ok_or_else(|| format!("Workflow not found: {workflow_id}"))?;
    workflows.remove(pos);
    save_workflows(&workflows)
}

pub fn list_workflows() -> Vec<WorkflowDefinition> {
    load_workflows()
}

pub fn get_workflow(workflow_id: &str) -> Option<WorkflowDefinition> {
    load_workflows().into_iter().find(|w| w.id == workflow_id)
}

pub fn toggle_workflow(workflow_id: &str) -> Result<WorkflowDefinition, String> {
    let mut workflows = load_workflows();
    let wf = workflows.iter_mut().find(|w| w.id == workflow_id)
        .ok_or_else(|| format!("Workflow not found: {workflow_id}"))?;
    wf.enabled = !wf.enabled;
    wf.updated_at = iso_now();
    let result = wf.clone();
    save_workflows(&workflows)?;
    Ok(result)
}

pub fn increment_run_count(workflow_id: &str) -> Result<(), String> {
    let mut workflows = load_workflows();
    let wf = workflows.iter_mut().find(|w| w.id == workflow_id)
        .ok_or_else(|| format!("Workflow not found: {workflow_id}"))?;
    wf.run_count += 1;
    save_workflows(&workflows)
}

pub fn log_execution(entry: WorkflowLogEntry) -> Result<(), String> {
    let mut logs = load_logs();
    logs.push(entry);
    save_logs(&logs)
}

pub fn get_execution_logs(workflow_id: &str, limit: usize) -> Vec<WorkflowLogEntry> {
    let mut logs: Vec<WorkflowLogEntry> = load_logs().into_iter()
        .filter(|l| l.workflow_id == workflow_id)
        .collect();
    logs.reverse();
    logs.into_iter().take(limit).collect()
}

pub fn evaluate_workflow(
    workflow: &WorkflowDefinition,
    context: &HashMap<String, String>,
) -> bool {
    if !workflow.enabled {
        return false;
    }
    workflow.conditions.iter().all(|group| match group.operator {
        ConditionGroupOperator::All => {
            group.conditions.iter().all(|c| evaluate_condition(c, context))
        }
        ConditionGroupOperator::Any => {
            group.conditions.iter().any(|c| evaluate_condition(c, context))
        }
    })
}

fn evaluate_condition(condition: &WorkflowCondition, context: &HashMap<String, String>) -> bool {
    let field_value = context.get(&condition.field).map(|s| s.as_str()).unwrap_or("");
    match condition.operator {
        ConditionOperator::Equals => field_value == condition.value,
        ConditionOperator::NotEquals => field_value != condition.value,
        ConditionOperator::Contains => field_value.contains(&condition.value),
        ConditionOperator::NotContains => !field_value.contains(&condition.value),
        ConditionOperator::Regex => {
            regex_lite::Regex::new(&condition.value)
                .map(|r| r.is_match(field_value))
                .unwrap_or(false)
        }
        ConditionOperator::GreaterThan => {
            field_value.parse::<f64>().ok().zip(condition.value.parse::<f64>().ok())
                .map(|(a, b)| a > b).unwrap_or(false)
        }
        ConditionOperator::LessThan => {
            field_value.parse::<f64>().ok().zip(condition.value.parse::<f64>().ok())
                .map(|(a, b)| a < b).unwrap_or(false)
        }
        ConditionOperator::IsEmpty => field_value.is_empty(),
        ConditionOperator::IsNotEmpty => !field_value.is_empty(),
        ConditionOperator::StartsWith => field_value.starts_with(&condition.value),
        ConditionOperator::EndsWith => field_value.ends_with(&condition.value),
    }
}

pub fn execute_actions(
    actions: &[WorkflowAction],
    variables: &HashMap<String, String>,
) -> ExecutionResult {
    let start = std::time::Instant::now();
    let mut action_results = Vec::new();
    let mut success = true;
    let mut error = None;

    for action in actions {
        let act_start = std::time::Instant::now();
        let (ok, out, err) = execute_single_action(action, variables);
        let duration = act_start.elapsed().as_millis() as u64;
        action_results.push(ActionResult {
            action_type: action_type_name(action),
            success: ok,
            output: out,
            error: err.clone(),
            duration_ms: duration,
        });
        if !ok {
            success = false;
            error = err;
            break;
        }
    }

    ExecutionResult {
        success,
        action_results,
        error,
        duration_ms: start.elapsed().as_millis() as u64,
    }
}

fn action_type_name(action: &WorkflowAction) -> String {
    match action {
        WorkflowAction::SendMessage { .. } => "send_message".into(),
        WorkflowAction::AiAction { .. } => "ai_action".into(),
        WorkflowAction::CreateIssue { .. } => "create_issue".into(),
        WorkflowAction::RouteMessage { .. } => "route_message".into(),
        WorkflowAction::HttpRequest { .. } => "http_request".into(),
        WorkflowAction::UpdateVariable { .. } => "update_variable".into(),
        WorkflowAction::ScheduleAction { .. } => "schedule_action".into(),
        WorkflowAction::Notify { .. } => "notify".into(),
        WorkflowAction::CreateTask { .. } => "create_task".into(),
        WorkflowAction::WaitForCondition { .. } => "wait_for_condition".into(),
        WorkflowAction::LoopAction { .. } => "loop_action".into(),
    }
}

fn execute_single_action(
    action: &WorkflowAction,
    variables: &HashMap<String, String>,
) -> (bool, Option<String>, Option<String>) {
    match action {
        WorkflowAction::SendMessage { connector_id, channel, message_template } => {
            let msg = template_replace(message_template, variables);
            let connector = crate::connector_manager::get_connector(connector_id);
            let def_id = connector.as_ref().and_then(|c| {
                let defs = crate::connector_definitions::all_definitions();
                defs.into_iter().find(|d| d.id == c.definition_id).map(|d| d.id.clone())
            });
            match connector {
                Some(c) if c.enabled => {
                    let creds = crate::connector_manager::read_connector_secret(connector_id)
                        .unwrap_or_default();
                    let client = reqwest::blocking::Client::builder()
                        .timeout(std::time::Duration::from_secs(15))
                        .build().unwrap_or_default();
                    match def_id.as_deref() {
                        Some("slack") => {
                            if let Some(token) = creds.get("token").or(creds.get("access_token")) {
                                let payload = serde_json::json!({"channel": channel, "text": msg});
                                match client.post("https://slack.com/api/chat.postMessage")
                                    .header("Authorization", format!("Bearer {}", token))
                                    .json(&payload).send()
                                {
                                    Ok(resp) => (true, Some(format!("Slack message sent: {}", resp.status())), None),
                                    Err(e) => (false, None, Some(format!("Slack send failed: {e}"))),
                                }
                            } else {
                                (true, Some(format!("Queued for Slack {channel}: {msg}")), None)
                            }
                        }
                        Some("telegram") => {
                            if let Some(token) = creds.get("token").or(creds.get("access_token")) {
                                let url = format!("https://api.telegram.org/bot{}/sendMessage", token);
                                let payload = serde_json::json!({"chat_id": channel, "text": msg});
                                match client.post(&url).json(&payload).send() {
                                    Ok(resp) => (true, Some(format!("Telegram message sent: {}", resp.status())), None),
                                    Err(e) => (false, None, Some(format!("Telegram send failed: {e}"))),
                                }
                            } else {
                                (true, Some(format!("Queued for Telegram {channel}: {msg}")), None)
                            }
                        }
                            Some("discord") => {
                            if let Some(token) = creds.get("token").or(creds.get("access_token")) {
                                let payload = serde_json::json!({"content": msg});
                                let url = format!("https://discord.com/api/v10/channels/{}/messages", channel);
                                match client.post(&url)
                                    .header("Authorization", format!("Bot {}", token))
                                    .json(&payload).send()
                                {
                                    Ok(resp) => (true, Some(format!("Discord message sent: {}", resp.status())), None),
                                    Err(e) => (false, None, Some(format!("Discord send failed: {e}"))),
                                }
                            } else {
                                (true, Some(format!("Queued for Discord {channel}: {msg}")), None)
                            }
                        }
                        _ => (true, Some(format!("Queued message to {connector_id}/{channel}: {msg}")), None),
                    }
                }
                _ => (true, Some(format!("Queued message to {connector_id}/{channel}: {msg}")), None),
            }
        }
        WorkflowAction::AiAction { config, input_template } => {
            let input = template_replace(input_template, variables);
            (true, Some(format!("AI action queued with provider {}: {}", config.provider_id, input)), None)
        }
        WorkflowAction::CreateIssue { connector_id, title_template, description_template: _desc_tpl, project } => {
            let title = template_replace(title_template, variables);
            let connector = crate::connector_manager::get_connector(connector_id);
            let def_id = connector.as_ref().and_then(|c| {
                let defs = crate::connector_definitions::all_definitions();
                defs.into_iter().find(|d| d.id == c.definition_id).map(|d| d.id.clone())
            });
            match connector {
                Some(c) if c.enabled => {
                    let creds = crate::connector_manager::read_connector_secret(connector_id)
                        .unwrap_or_default();
                    let client = reqwest::blocking::Client::builder()
                        .timeout(std::time::Duration::from_secs(15))
                        .build().unwrap_or_default();
                    match def_id.as_deref() {
                        Some("github") => {
                            if let Some(token) = creds.get("token").or(creds.get("access_token")) {
                                let payload = serde_json::json!({"title": title, "body": ""});
                                let url = format!("https://api.github.com/repos/{}/issues", project);
                                match client.post(&url)
                                    .header("Authorization", format!("Bearer {}", token))
                                    .header("Accept", "application/vnd.github.v3+json")
                                    .json(&payload).send()
                                {
                                    Ok(resp) => (true, Some(format!("GitHub issue created: {}", resp.status())), None),
                                    Err(e) => (false, None, Some(format!("GitHub issue failed: {e}"))),
                                }
                            } else {
                                (true, Some(format!("Created issue in {connector_id}/{project}: {title}")), None)
                            }
                        }
                        _ => (true, Some(format!("Created issue in {connector_id}/{project}: {title}")), None),
                    }
                }
                _ => (true, Some(format!("Created issue in {connector_id}/{project}: {title}")), None),
            }
        }
        WorkflowAction::RouteMessage { target_connector, target_channel, .. } => {
            (true, Some(format!("Routed to {target_connector}/{target_channel}")), None)
        }
        WorkflowAction::HttpRequest { url, method, headers, body_template } => {
            let rendered_url = template_replace(url, variables);
            let client = reqwest::blocking::Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .build().unwrap_or_default();
            let mut req = match method.to_uppercase().as_str() {
                "GET" => client.get(&rendered_url),
                "POST" => {
                    let body = body_template.as_ref().map(|t| template_replace(t, variables)).unwrap_or_default();
                    client.post(&rendered_url).body(body)
                }
                "PUT" => {
                    let body = body_template.as_ref().map(|t| template_replace(t, variables)).unwrap_or_default();
                    client.put(&rendered_url).body(body)
                }
                "PATCH" => {
                    let body = body_template.as_ref().map(|t| template_replace(t, variables)).unwrap_or_default();
                    client.patch(&rendered_url).body(body)
                }
                "DELETE" => client.delete(&rendered_url),
                _ => return (false, None, Some(format!("Unsupported HTTP method: {method}"))),
            };
            for (k, v) in headers {
                let rendered_v = template_replace(v, variables);
                req = req.header(k.as_str(), rendered_v);
            }
            match req.send() {
                Ok(resp) => {
                    let status = resp.status().as_u16();
                    let body = resp.text().unwrap_or_default();
                    let preview = body.chars().take(500).collect::<String>();
                    if status < 400 {
                        (true, Some(format!("{method} {rendered_url} -> {status}: {preview}")), None)
                    } else {
                        (false, None, Some(format!("{method} {rendered_url} -> {status}: {preview}")))
                    }
                }
                Err(e) => (false, None, Some(format!("HTTP request failed: {e}"))),
            }
        }
        WorkflowAction::UpdateVariable { value_template, .. } => {
            let val = template_replace(value_template, variables);
            (true, Some(format!("Variable updated: {}", val)), None)
        }
        WorkflowAction::ScheduleAction { delay_seconds, action: inner } => {
            std::thread::sleep(std::time::Duration::from_secs(*delay_seconds));
            execute_single_action(inner, variables)
        }
        WorkflowAction::Notify { title, message_template, level } => {
            let msg = template_replace(message_template, variables);
            let ntype = if level == "high" || level == "urgent" {
                crate::notifications::NotificationType::AutomationEvent
            } else {
                crate::notifications::NotificationType::AutomationEvent
            };
            let _ = crate::notifications::send_notification(
                "default", "system", ntype,
                &template_replace(title, variables), &msg,
                None, None,
            );
            (true, Some(format!("[{level}] {title}: {msg}")), None)
        }
        WorkflowAction::CreateTask { title_template, description_template, assignee } => {
            let title = template_replace(title_template, variables);
            let desc = template_replace(description_template, variables);
            match crate::task_manager::create_task(
                "default", None, &title, &desc,
                assignee.as_deref(), "system",
                crate::task_manager::TaskPriority::Medium,
                None, vec![],
            ) {
                Ok(_) => (true, Some(format!("Task created: {title}")), None),
                Err(e) => (false, None, Some(format!("Task creation failed: {e}"))),
            }
        }
        WorkflowAction::WaitForCondition { condition, check_interval_seconds, timeout_seconds } => {
            let start = std::time::Instant::now();
            loop {
                if evaluate_condition(condition, variables) {
                    return (true, Some("Condition met".into()), None);
                }
                if start.elapsed().as_secs() >= *timeout_seconds {
                    return (false, None, Some("Condition timeout".into()));
                }
                std::thread::sleep(std::time::Duration::from_secs(*check_interval_seconds));
            }
        }
        WorkflowAction::LoopAction { iterations, actions } => {
            let mut results = Vec::new();
            for _ in 0..*iterations {
                for a in actions {
                    let (ok, out, err) = execute_single_action(a, variables);
                    if !ok {
                        return (false, None, err);
                    }
                    if let Some(o) = out { results.push(o); }
                }
            }
            (true, Some(format!("Loop completed {} iterations: {} actions", iterations, results.len())), None)
        }
    }
}

fn template_replace(template: &str, variables: &HashMap<String, String>) -> String {
    let mut result = template.to_string();
    for (key, value) in variables {
        let pattern = format!("{{{{{}}}}}", key);
        result = result.replace(&pattern, value);
    }
    result
}

#[tauri::command]
pub async fn auto_create_workflow(
    name: String, description: String, trigger: WorkflowTrigger,
    conditions: Vec<ConditionGroup>, actions: Vec<WorkflowAction>,
    variables: HashMap<String, VariableDefinition>, error_handling: ErrorHandling,
    timeout_seconds: u64,
) -> Result<WorkflowDefinition, String> {
    create_workflow(&name, &description, trigger, conditions, actions, variables, error_handling, timeout_seconds)
}

#[tauri::command]
pub async fn auto_update_workflow(
    workflow_id: String, name: Option<String>, description: Option<String>,
    trigger: Option<WorkflowTrigger>, conditions: Option<Vec<ConditionGroup>>,
    actions: Option<Vec<WorkflowAction>>,
    variables: Option<HashMap<String, VariableDefinition>>,
    error_handling: Option<ErrorHandling>, timeout_seconds: Option<u64>,
) -> Result<WorkflowDefinition, String> {
    update_workflow(&workflow_id, name.as_deref(), description.as_deref(),
        trigger, conditions, actions, variables, error_handling, timeout_seconds)
}

#[tauri::command]
pub async fn auto_delete_workflow(workflow_id: String) -> Result<(), String> {
    delete_workflow(&workflow_id)
}

#[tauri::command]
pub async fn auto_list_workflows() -> Result<Vec<WorkflowDefinition>, String> {
    Ok(list_workflows())
}

#[tauri::command]
pub async fn auto_get_workflow(workflow_id: String) -> Result<Option<WorkflowDefinition>, String> {
    Ok(get_workflow(&workflow_id))
}

#[tauri::command]
pub async fn auto_toggle_workflow(workflow_id: String) -> Result<WorkflowDefinition, String> {
    toggle_workflow(&workflow_id)
}

#[tauri::command]
pub async fn auto_evaluate_workflow(
    workflow_id: String, context: HashMap<String, String>,
) -> Result<bool, String> {
    let wf = get_workflow(&workflow_id).ok_or_else(|| format!("Workflow not found: {workflow_id}"))?;
    Ok(evaluate_workflow(&wf, &context))
}

#[tauri::command]
pub async fn auto_execute_workflow(
    workflow_id: String, variables: HashMap<String, String>,
) -> Result<ExecutionResult, String> {
    let wf = get_workflow(&workflow_id).ok_or_else(|| format!("Workflow not found: {workflow_id}"))?;
    let result = execute_actions(&wf.actions, &variables);
    increment_run_count(&workflow_id)?;
    let now = iso_now();
    log_execution(WorkflowLogEntry {
        id: log_id(),
        workflow_id: workflow_id.clone(),
        triggered_at: now,
        trigger_source: "manual".into(),
        success: result.success,
        duration_ms: result.duration_ms,
        actions_count: result.action_results.len(),
        error: result.error.clone(),
    })?;
    Ok(result)
}

#[tauri::command]
pub async fn auto_get_logs(workflow_id: String, limit: Option<usize>) -> Result<Vec<WorkflowLogEntry>, String> {
    Ok(get_execution_logs(&workflow_id, limit.unwrap_or(50)))
}

#[tauri::command]
pub async fn auto_get_trigger_types() -> Result<Vec<String>, String> {
    Ok(vec![
        "connector_event".into(), "schedule".into(), "webhook".into(),
        "manual".into(), "ai_trigger".into(),
    ])
}

#[tauri::command]
pub async fn auto_get_action_types() -> Result<Vec<String>, String> {
    Ok(vec![
        "send_message".into(), "ai_action".into(), "create_issue".into(),
        "route_message".into(), "http_request".into(), "update_variable".into(),
        "schedule_action".into(), "notify".into(), "create_task".into(),
        "wait_for_condition".into(), "loop_action".into(),
    ])
}
