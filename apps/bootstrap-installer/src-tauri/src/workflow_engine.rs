use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageRoute {
    pub id: String,
    pub name: String,
    pub from_connector_id: String,
    pub to_connector_id: String,
    pub transform_rules: Vec<TransformRule>,
    pub enabled: bool,
    pub filter_conditions: HashMap<String, String>,
    pub condition_groups: Vec<RouteConditionGroup>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteConditionGroup {
    pub operator: ConditionGroupOp,
    pub conditions: Vec<RouteCondition>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ConditionGroupOp {
    All,
    Any,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteCondition {
    pub field: String,
    pub operator: RouteConditionOp,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum RouteConditionOp {
    Equals,
    NotEquals,
    Contains,
    NotContains,
    Regex,
    GreaterThan,
    LessThan,
    StartsWith,
    EndsWith,
    Exists,
    NotExists,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum TransformRule {
    StringReplace { source: String, target: String },
    RegexReplace { pattern: String, replacement: String },
    JsonTransform { template: String },
    AppendText { text: String },
    PrependText { text: String },
    AiTransform { instruction: String, provider_id: Option<String>, model: Option<String> },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScheduledRun {
    pub id: String,
    pub workflow_id: String,
    pub schedule: String,
    pub next_run: String,
    pub last_run: Option<String>,
    pub status: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowTemplate {
    pub id: String,
    pub name: String,
    pub description: String,
    pub category: String,
    pub trigger_type: String,
    pub action_count: usize,
    pub steps: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteEvaluation {
    pub matched: bool,
    pub route_id: Option<String>,
    pub route_name: Option<String>,
    pub transformed_body: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceRouter {
    pub routes: Vec<MessageRoute>,
}

fn extract_field(body: &str, field: &str) -> Option<String> {
    if let Ok(val) = serde_json::from_str::<serde_json::Value>(body) {
        let parts: Vec<&str> = field.split('.').collect();
        let mut current = &val;
        for part in parts {
            match current.get(part) {
                Some(v) => current = v,
                None => return None,
            }
        }
        match current {
            serde_json::Value::String(s) => Some(s.clone()),
            serde_json::Value::Number(n) => Some(n.to_string()),
            serde_json::Value::Bool(b) => Some(b.to_string()),
            other => Some(other.to_string()),
        }
    } else {
        None
    }
}

fn evaluate_route_condition(cond: &RouteCondition, body: &str) -> bool {
    let field_val = extract_field(body, &cond.field).unwrap_or_default();
    let val = field_val.as_str();
    let expected = &cond.value;
    match cond.operator {
        RouteConditionOp::Equals => val == expected,
        RouteConditionOp::NotEquals => val != expected,
        RouteConditionOp::Contains => val.contains(expected),
        RouteConditionOp::NotContains => !val.contains(expected),
        RouteConditionOp::Regex => {
            regex_lite::Regex::new(expected)
                .map(|r| r.is_match(val))
                .unwrap_or(false)
        }
        RouteConditionOp::GreaterThan => {
            val.parse::<f64>().ok().zip(expected.parse::<f64>().ok())
                .map(|(a, b)| a > b).unwrap_or(false)
        }
        RouteConditionOp::LessThan => {
            val.parse::<f64>().ok().zip(expected.parse::<f64>().ok())
                .map(|(a, b)| a < b).unwrap_or(false)
        }
        RouteConditionOp::StartsWith => val.starts_with(expected),
        RouteConditionOp::EndsWith => val.ends_with(expected),
        RouteConditionOp::Exists => !field_val.is_empty(),
        RouteConditionOp::NotExists => field_val.is_empty(),
    }
}

fn evaluate_conditions(route: &MessageRoute, body: &str) -> bool {
    let simple_match = if route.filter_conditions.is_empty() {
        true
    } else {
        route.filter_conditions.iter().all(|(k, v)| body.contains(k) || body.contains(v))
    };
    if !simple_match {
        return false;
    }
    if route.condition_groups.is_empty() {
        return true;
    }
    route.condition_groups.iter().all(|group| match group.operator {
        ConditionGroupOp::All => group.conditions.iter().all(|c| evaluate_route_condition(c, body)),
        ConditionGroupOp::Any => group.conditions.iter().any(|c| evaluate_route_condition(c, body)),
    })
}

impl ServiceRouter {
    pub fn new() -> Self {
        ServiceRouter { routes: Vec::new() }
    }

    pub fn evaluate(&self, from_connector: &str, body: &str) -> Vec<RouteEvaluation> {
        self.routes.iter()
            .filter(|r| r.enabled && r.from_connector_id == from_connector)
            .filter(|r| evaluate_conditions(r, body))
            .map(|r| {
                let transformed = if r.transform_rules.is_empty() {
                    Some(body.to_string())
                } else {
                    let mut result = body.to_string();
                    for rule in &r.transform_rules {
                        result = apply_transform(rule, &result);
                    }
                    Some(result)
                };
                RouteEvaluation {
                    matched: true,
                    route_id: Some(r.id.clone()),
                    route_name: Some(r.name.clone()),
                    transformed_body: transformed,
                }
            })
            .collect()
    }
}

fn apply_transform(rule: &TransformRule, input: &str) -> String {
    match rule {
        TransformRule::StringReplace { source, target } => input.replace(source, target),
        TransformRule::RegexReplace { pattern, replacement } => {
            regex_lite::Regex::new(pattern)
                .map(|r| r.replace_all(input, replacement.as_str()).to_string())
                .unwrap_or_else(|_| input.to_string())
        }
        TransformRule::AppendText { text } => format!("{}{}", input, text),
        TransformRule::PrependText { text } => format!("{}{}", text, input),
        TransformRule::JsonTransform { template } => {
            let mut result = template.clone();
            result = result.replace("{{body}}", input);
            result = result.replace("{{body_escaped}}", &serde_json::to_string(input).unwrap_or_default());
            let parsed = serde_json::from_str::<serde_json::Value>(input).ok();
            if let Some(json) = parsed {
                if let Some(obj) = json.as_object() {
                    for (key, val) in obj {
                        let placeholder = format!("{{{{{}}}}}", key);
                        let val_str = match val {
                            serde_json::Value::String(s) => s.clone(),
                            other => other.to_string(),
                        };
                        result = result.replace(&placeholder, &val_str);
                    }
                }
            }
            result
        }
        TransformRule::AiTransform { .. } => {
            format!("[AI transform queued for: {}]", &input[..input.len().min(100)])
        }
    }
}

fn hub_dir() -> PathBuf {
    crate::paths::aetheros_home().join("hub")
}

fn routes_path() -> PathBuf {
    hub_dir().join("routes.json")
}

fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("route_{:x}", nanos)
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

fn load_routes() -> Vec<MessageRoute> {
    let path = routes_path();
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

fn save_routes(routes: &[MessageRoute]) -> Result<(), String> {
    let path = routes_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(routes).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn create_route(
    name: &str,
    from_connector_id: &str,
    to_connector_id: &str,
    transform_rules: Vec<TransformRule>,
    filter_conditions: HashMap<String, String>,
    condition_groups: Vec<RouteConditionGroup>,
) -> Result<MessageRoute, String> {
    let mut routes = load_routes();
    if routes.iter().any(|r| r.name == name) {
        return Err(format!("Route '{name}' already exists"));
    }
    let route = MessageRoute {
        id: generate_id(),
        name: name.to_string(),
        from_connector_id: from_connector_id.to_string(),
        to_connector_id: to_connector_id.to_string(),
        transform_rules,
        enabled: true,
        filter_conditions,
        condition_groups,
        created_at: iso_now(),
    };
    let result = route.clone();
    routes.push(route);
    save_routes(&routes)?;
    Ok(result)
}

pub fn update_route(
    route_id: &str,
    name: Option<&str>,
    from_connector_id: Option<&str>,
    to_connector_id: Option<&str>,
    transform_rules: Option<Vec<TransformRule>>,
    filter_conditions: Option<HashMap<String, String>>,
    condition_groups: Option<Vec<RouteConditionGroup>>,
) -> Result<MessageRoute, String> {
    let mut routes = load_routes();
    let route = routes.iter_mut().find(|r| r.id == route_id)
        .ok_or_else(|| format!("Route not found: {route_id}"))?;
    if let Some(n) = name { route.name = n.to_string(); }
    if let Some(f) = from_connector_id { route.from_connector_id = f.to_string(); }
    if let Some(t) = to_connector_id { route.to_connector_id = t.to_string(); }
    if let Some(t) = transform_rules { route.transform_rules = t; }
    if let Some(f) = filter_conditions { route.filter_conditions = f; }
    if let Some(c) = condition_groups { route.condition_groups = c; }
    let result = route.clone();
    save_routes(&routes)?;
    Ok(result)
}

pub fn delete_route(route_id: &str) -> Result<(), String> {
    let mut routes = load_routes();
    let pos = routes.iter().position(|r| r.id == route_id)
        .ok_or_else(|| format!("Route not found: {route_id}"))?;
    routes.remove(pos);
    save_routes(&routes)
}

pub fn list_routes() -> Vec<MessageRoute> {
    load_routes()
}

pub fn toggle_route(route_id: &str) -> Result<MessageRoute, String> {
    let mut routes = load_routes();
    let route = routes.iter_mut().find(|r| r.id == route_id)
        .ok_or_else(|| format!("Route not found: {route_id}"))?;
    route.enabled = !route.enabled;
    let result = route.clone();
    save_routes(&routes)?;
    Ok(result)
}

pub fn evaluate_route(route_id: &str, body: &str) -> RouteEvaluation {
    let routes = load_routes();
    if let Some(route) = routes.iter().find(|r| r.id == route_id) {
        if !evaluate_conditions(route, body) {
            return RouteEvaluation {
                matched: false,
                route_id: Some(route.id.clone()),
                route_name: Some(route.name.clone()),
                transformed_body: None,
            };
        }
        let mut result = body.to_string();
        for rule in &route.transform_rules {
            result = apply_transform(rule, &result);
        }
        RouteEvaluation {
            matched: true,
            route_id: Some(route.id.clone()),
            route_name: Some(route.name.clone()),
            transformed_body: Some(result),
        }
    } else {
        RouteEvaluation {
            matched: false,
            route_id: None,
            route_name: None,
            transformed_body: None,
        }
    }
}

pub fn list_templates() -> Vec<WorkflowTemplate> {
    vec![
        WorkflowTemplate {
            id: "tpl_forward_message".into(),
            name: "Forward Message".into(),
            description: "Forward messages from one connector to another".into(),
            category: "messaging".into(),
            trigger_type: "connector_event".into(),
            action_count: 2,
            steps: vec!["Receive message".into(), "Transform content".into(), "Send to target".into()],
        },
        WorkflowTemplate {
            id: "tpl_ai_summarize".into(),
            name: "AI Summarize".into(),
            description: "Summarize incoming messages using AI".into(),
            category: "ai".into(),
            trigger_type: "connector_event".into(),
            action_count: 2,
            steps: vec!["Receive message".into(), "AI summarize".into(), "Store summary".into()],
        },
        WorkflowTemplate {
            id: "tpl_issue_alert".into(),
            name: "Issue Alert".into(),
            description: "Alert when new issues are created in project management".into(),
            category: "monitoring".into(),
            trigger_type: "connector_event".into(),
            action_count: 2,
            steps: vec!["Watch issues".into(), "Filter by criteria".into(), "Send notification".into()],
        },
        WorkflowTemplate {
            id: "tpl_scheduled_report".into(),
            name: "Scheduled Report".into(),
            description: "Generate and send a report on a schedule".into(),
            category: "automation".into(),
            trigger_type: "schedule".into(),
            action_count: 3,
            steps: vec!["Timer trigger".into(), "Collect data".into(), "Send report".into()],
        },
        WorkflowTemplate {
            id: "tpl_webhook_bridge".into(),
            name: "Webhook Bridge".into(),
            description: "Bridge webhook events to messaging channels".into(),
            category: "integration".into(),
            trigger_type: "webhook".into(),
            action_count: 2,
            steps: vec!["Receive webhook".into(), "Transform payload".into(), "Notify channel".into()],
        },
    ]
}

#[tauri::command]
pub async fn engine_create_route(
    name: String, from_connector_id: String, to_connector_id: String,
    transform_rules: Vec<TransformRule>, filter_conditions: HashMap<String, String>,
    condition_groups: Vec<RouteConditionGroup>,
) -> Result<MessageRoute, String> {
    create_route(&name, &from_connector_id, &to_connector_id, transform_rules, filter_conditions, condition_groups)
}

#[tauri::command]
pub async fn engine_update_route(
    route_id: String, name: Option<String>, from_connector_id: Option<String>,
    to_connector_id: Option<String>, transform_rules: Option<Vec<TransformRule>>,
    filter_conditions: Option<HashMap<String, String>>,
    condition_groups: Option<Vec<RouteConditionGroup>>,
) -> Result<MessageRoute, String> {
    update_route(&route_id, name.as_deref(), from_connector_id.as_deref(),
        to_connector_id.as_deref(), transform_rules, filter_conditions, condition_groups)
}

#[tauri::command]
pub async fn engine_delete_route(route_id: String) -> Result<(), String> {
    delete_route(&route_id)
}

#[tauri::command]
pub async fn engine_list_routes() -> Result<Vec<MessageRoute>, String> {
    Ok(list_routes())
}

#[tauri::command]
pub async fn engine_toggle_route(route_id: String) -> Result<MessageRoute, String> {
    toggle_route(&route_id)
}

#[tauri::command]
pub async fn engine_evaluate_route(route_id: String, body: String) -> Result<RouteEvaluation, String> {
    Ok(evaluate_route(&route_id, &body))
}

#[tauri::command]
pub async fn engine_list_templates() -> Result<Vec<WorkflowTemplate>, String> {
    Ok(list_templates())
}
