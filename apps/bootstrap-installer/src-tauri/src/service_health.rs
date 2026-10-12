use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthCheckResult {
    pub connector_id: String,
    pub connector_name: String,
    pub status: String,
    pub latency_ms: u64,
    pub rate_limit_remaining: Option<u32>,
    pub rate_limit_reset: Option<String>,
    pub error: Option<String>,
    pub checked_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthDashboard {
    pub total: usize,
    pub connected: usize,
    pub disconnected: usize,
    pub error: usize,
    pub rate_limited: usize,
    pub avg_latency_ms: f64,
    pub total_messages_processed: u64,
    pub errors_last_hour: u32,
}

struct HealthPing {
    status: String,
    error: Option<String>,
    rate_limit_remaining: Option<u32>,
    rate_limit_reset: Option<String>,
}

impl HealthPing {
    fn ok() -> Self {
        HealthPing { status: "connected".into(), error: None, rate_limit_remaining: None, rate_limit_reset: None }
    }
    fn err(msg: &str) -> Self {
        HealthPing { status: "error".into(), error: Some(msg.into()), rate_limit_remaining: None, rate_limit_reset: None }
    }
    fn from_response(resp: &reqwest::Response) -> Self {
        let rl_remaining = resp.headers().get("x-rate-limit-remaining")
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.parse().ok());
        let rl_reset = resp.headers().get("x-rate-limit-reset")
            .and_then(|v| v.to_str().ok())
            .map(|s| s.to_string());
        if resp.status().is_success() || resp.status().is_client_error() {
            HealthPing { status: "connected".into(), error: None, rate_limit_remaining: rl_remaining, rate_limit_reset: rl_reset }
        } else {
            HealthPing { status: "error".into(), error: Some(format!("HTTP {}", resp.status())), rate_limit_remaining: rl_remaining, rate_limit_reset: rl_reset }
        }
    }
}

fn client() -> reqwest::Client {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(15))
        .user_agent("AetherosHub/1.0")
        .build()
        .unwrap_or_default()
}

fn iso_now() -> String {
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

pub async fn check_connector_health(
    connector_id: &str,
    connector_name: &str,
) -> HealthCheckResult {
    let now = iso_now();
    let connector = crate::connector_manager::get_connector(connector_id);

    let (def, cfg, creds) = match &connector {
        Some(c) if c.enabled => {
            let defs = crate::connector_definitions::all_definitions();
            match defs.into_iter().find(|d| d.id == c.definition_id) {
                Some(def) => {
                    let creds = crate::connector_manager::read_connector_secret(connector_id)
                        .unwrap_or_default();
                    (def, c.config.clone(), creds)
                }
                None => {
                    return HealthCheckResult {
                        connector_id: connector_id.to_string(),
                        connector_name: connector_name.to_string(),
                        status: "error".into(),
                        latency_ms: 0,
                        rate_limit_remaining: None,
                        rate_limit_reset: None,
                        error: Some("Connector definition not found".into()),
                        checked_at: now,
                    };
                }
            }
        }
        Some(_) => {
            return HealthCheckResult {
                connector_id: connector_id.to_string(),
                connector_name: connector_name.to_string(),
                status: "disconnected".into(),
                latency_ms: 0,
                rate_limit_remaining: None,
                rate_limit_reset: None,
                error: Some("Connector is disabled".into()),
                checked_at: now,
            };
        }
        None => {
            return HealthCheckResult {
                connector_id: connector_id.to_string(),
                connector_name: connector_name.to_string(),
                status: "unknown".into(),
                latency_ms: 0,
                rate_limit_remaining: None,
                rate_limit_reset: None,
                error: Some("Connector not found".into()),
                checked_at: now,
            };
        }
    };

    let start = SystemTime::now();
    let hp = ping_service(&def.id, &cfg, &creds).await;
    let elapsed = start.elapsed().unwrap_or_default().as_millis() as u64;

    let hstatus = match hp.status.as_str() {
        "connected" => crate::connector_manager::HealthStatus::Connected,
        "rate_limited" => crate::connector_manager::HealthStatus::RateLimited,
        "expired" => crate::connector_manager::HealthStatus::Expired,
        _ => crate::connector_manager::HealthStatus::Error,
    };
    let _ = crate::connector_manager::record_health(
        connector_id, hstatus, elapsed,
        hp.error.as_deref(), hp.rate_limit_remaining, hp.rate_limit_reset.as_deref(),
    );

    HealthCheckResult {
        connector_id: connector_id.to_string(),
        connector_name: connector_name.to_string(),
        status: hp.status,
        latency_ms: elapsed,
        rate_limit_remaining: hp.rate_limit_remaining,
        rate_limit_reset: hp.rate_limit_reset,
        error: hp.error,
        checked_at: now,
    }
}

async fn ping_service(
    def_id: &str,
    config: &HashMap<String, String>,
    credentials: &HashMap<String, String>,
) -> HealthPing {
    let client = client();
    match def_id {
        "telegram" => ping_telegram(&client, credentials).await,
        "discord" => ping_discord(&client, credentials).await,
        "slack" => ping_slack(&client, credentials).await,
        "gmail" | "google_drive" | "google_calendar" | "google_meet" => ping_google_oauth(&client, credentials).await,
        "outlook" | "microsoft_teams" | "one_drive" | "outlook_calendar" => ping_microsoft_graph(&client, credentials).await,
        "whatsapp" => ping_whatsapp(&client, credentials).await,
        "github" => ping_github(&client, credentials).await,
        "gitlab" => ping_gitlab(&client, config, credentials).await,
        "notion" => ping_notion(&client, credentials).await,
        "dropbox" => ping_dropbox(&client, credentials).await,
        "jira" => ping_jira(&client, config, credentials).await,
        "linear" => ping_linear(&client, credentials).await,
        "trello" => ping_trello(&client, config, credentials).await,
        "clickup" => ping_clickup(&client, credentials).await,
        "zoom" => ping_zoom(&client, credentials).await,
        "rss" => ping_rss(&client, config).await,
        "webhook" => ping_webhook(config),
        "custom_http" => ping_custom_http(&client, config, credentials).await,
        _ => HealthPing { status: "unknown".into(), error: Some("Unknown connector type".into()), rate_limit_remaining: None, rate_limit_reset: None },
    }
}

async fn ping_telegram(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("token").or_else(|| creds.get("access_token")) {
        Some(t) => t,
        None => return HealthPing::err("No token configured"),
    };
    let url = format!("https://api.telegram.org/bot{}/getMe", token);
    client.get(&url).send().await.map(|r| HealthPing::from_response(&r)).unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_discord(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("token").or_else(|| creds.get("access_token")) {
        Some(t) => t,
        None => return HealthPing::err("No token configured"),
    };
    client.get("https://discord.com/api/v10/users/@me")
        .header("Authorization", format!("Bot {}", token))
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_slack(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("token").or_else(|| creds.get("access_token")) {
        Some(t) => t,
        None => return HealthPing::err("No token configured"),
    };
    client.get("https://slack.com/api/auth.test")
        .header("Authorization", format!("Bearer {}", token))
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_google_oauth(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("access_token") {
        Some(t) => t,
        None => return HealthPing::err("No access token"),
    };
    client.get("https://www.googleapis.com/oauth2/v1/tokeninfo")
        .query(&[("access_token", token)])
        .send().await
        .map(|r| if r.status().is_success() { HealthPing::ok() } else { HealthPing::err("Token invalid or expired") })
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_microsoft_graph(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("access_token") {
        Some(t) => t,
        None => return HealthPing::err("No access token"),
    };
    client.get("https://graph.microsoft.com/v1.0/me")
        .header("Authorization", format!("Bearer {}", token))
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_whatsapp(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("token").or_else(|| creds.get("access_token")) {
        Some(t) => t,
        None => return HealthPing::err("No token configured"),
    };
    client.get("https://graph.facebook.com/v18.0/me")
        .header("Authorization", format!("Bearer {}", token))
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_github(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("token").or_else(|| creds.get("access_token")) {
        Some(t) => t,
        None => return HealthPing::err("No token configured"),
    };
    client.get("https://api.github.com/user")
        .header("Authorization", format!("Bearer {}", token))
        .header("Accept", "application/vnd.github.v3+json")
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_gitlab(client: &reqwest::Client, config: &HashMap<String, String>, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("token").or_else(|| creds.get("access_token")) {
        Some(t) => t,
        None => return HealthPing::err("No token configured"),
    };
    let base = config.get("base_url").cloned().unwrap_or_else(|| "https://gitlab.com".into());
    client.get(format!("{}/api/v4/user", base))
        .header("Authorization", format!("Bearer {}", token))
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_notion(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("token").or_else(|| creds.get("access_token")) {
        Some(t) => t,
        None => return HealthPing::err("No token configured"),
    };
    client.get("https://api.notion.com/v1/users/me")
        .header("Authorization", format!("Bearer {}", token))
        .header("Notion-Version", "2022-06-28")
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_dropbox(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("access_token") {
        Some(t) => t,
        None => return HealthPing::err("No access token"),
    };
    client.post("https://api.dropboxapi.com/2/users/get_current_account")
        .header("Authorization", format!("Bearer {}", token))
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_jira(client: &reqwest::Client, config: &HashMap<String, String>, creds: &HashMap<String, String>) -> HealthPing {
    let base = match config.get("base_url") {
        Some(url) => url.clone(),
        None => return HealthPing::err("Jira base URL not configured"),
    };
    let username = creds.get("username").cloned().unwrap_or_default();
    let password = creds.get("password").cloned().unwrap_or_default();
    let auth = base64::Engine::encode(&base64::engine::general_purpose::STANDARD, format!("{}:{}", username, password).as_bytes());
    client.get(format!("{}/rest/api/2/myself", base))
        .header("Authorization", format!("Basic {}", auth))
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_linear(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let key = match creds.get("api_key").or_else(|| creds.get("token")) {
        Some(k) => k,
        None => return HealthPing::err("No API key configured"),
    };
    let query = serde_json::json!({"query": "{ viewer { id } }"});
    client.post("https://api.linear.app/graphql")
        .header("Authorization", format!("Bearer {}", key))
        .json(&query)
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_trello(client: &reqwest::Client, config: &HashMap<String, String>, creds: &HashMap<String, String>) -> HealthPing {
    let api_key = match config.get("api_key").or_else(|| creds.get("api_key")) {
        Some(k) => k,
        None => return HealthPing::err("No API key configured"),
    };
    let token = match creds.get("token").or_else(|| creds.get("access_token")) {
        Some(t) => t,
        None => return HealthPing::err("No token configured"),
    };
    client.get("https://api.trello.com/1/members/me")
        .query(&[("key", api_key), ("token", token)])
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_clickup(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("token").or_else(|| creds.get("access_token")) {
        Some(t) => t,
        None => return HealthPing::err("No token configured"),
    };
    client.get("https://api.clickup.com/api/v2/user")
        .header("Authorization", token)
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_zoom(client: &reqwest::Client, creds: &HashMap<String, String>) -> HealthPing {
    let token = match creds.get("access_token") {
        Some(t) => t,
        None => return HealthPing::err("No access token"),
    };
    client.get("https://api.zoom.us/v2/users/me")
        .header("Authorization", format!("Bearer {}", token))
        .send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

async fn ping_rss(client: &reqwest::Client, config: &HashMap<String, String>) -> HealthPing {
    let url = match config.get("feed_url") {
        Some(u) => u.clone(),
        None => return HealthPing::err("RSS feed URL not configured"),
    };
    client.get(&url).send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

fn ping_webhook(_config: &HashMap<String, String>) -> HealthPing {
    HealthPing::ok()
}

async fn ping_custom_http(client: &reqwest::Client, config: &HashMap<String, String>, creds: &HashMap<String, String>) -> HealthPing {
    let base = match config.get("base_url") {
        Some(u) => u.clone(),
        None => return HealthPing::err("Custom HTTP base URL not configured"),
    };
    let mut req = client.get(&base);
    if let Some(key) = creds.get("api_key").or_else(|| creds.get("token")) {
        let header_name = config.get("auth_header").cloned().unwrap_or_else(|| "Authorization".into());
        let prefix = config.get("auth_prefix").cloned().unwrap_or_else(|| "Bearer ".into());
        req = req.header(&header_name, format!("{}{}", prefix, key));
    }
    req.send().await
        .map(|r| HealthPing::from_response(&r))
        .unwrap_or_else(|e| HealthPing::err(&e.to_string()))
}

pub async fn health_dashboard() -> HealthDashboard {
    let connectors = crate::connector_manager::list_all_connectors();
    let total = connectors.len();
    let mut connected = 0;
    let mut disconnected = 0;
    let mut error_count = 0;
    let mut rate_limited = 0;
    let mut total_latency: u64 = 0;
    let mut latency_count: u64 = 0;
    let mut total_messages_processed: u64 = 0;
    let mut errors_last_hour: u32 = 0;

    for c in &connectors {
        total_messages_processed += c.total_messages_processed;
        match c.health.status {
            crate::connector_manager::HealthStatus::Connected => {
                connected += 1;
                total_latency += c.health.latency_ms;
                latency_count += 1;
            }
            crate::connector_manager::HealthStatus::Disconnected => disconnected += 1,
            crate::connector_manager::HealthStatus::Error => {
                error_count += 1;
                errors_last_hour += c.error_count;
            }
            crate::connector_manager::HealthStatus::RateLimited => rate_limited += 1,
            _ => {}
        }
    }

    let avg_latency_ms = if latency_count > 0 {
        total_latency as f64 / latency_count as f64
    } else {
        0.0
    };

    HealthDashboard {
        total,
        connected,
        disconnected,
        error: error_count,
        rate_limited,
        avg_latency_ms,
        total_messages_processed,
        errors_last_hour,
    }
}

pub async fn check_all_connectors() -> Vec<HealthCheckResult> {
    let connectors = crate::connector_manager::list_all_connectors();
    let mut results = Vec::new();
    for c in &connectors {
        let result = check_connector_health(&c.id, &c.name).await;
        results.push(result);
    }
    results
}

pub async fn get_unhealthy_connectors() -> Vec<HealthCheckResult> {
    let connectors = crate::connector_manager::list_all_connectors();
    let mut results = Vec::new();
    for c in &connectors {
        if c.health.status != crate::connector_manager::HealthStatus::Connected {
            let result = check_connector_health(&c.id, &c.name).await;
            results.push(result);
        }
    }
    results
}

#[tauri::command]
pub async fn health_check(connector_id: String, connector_name: String) -> Result<HealthCheckResult, String> {
    Ok(check_connector_health(&connector_id, &connector_name).await)
}

#[tauri::command]
pub async fn health_dashboard_cmd() -> Result<HealthDashboard, String> {
    Ok(health_dashboard().await)
}

#[tauri::command]
pub async fn health_check_all() -> Result<Vec<HealthCheckResult>, String> {
    Ok(check_all_connectors().await)
}

#[tauri::command]
pub async fn health_get_unhealthy() -> Result<Vec<HealthCheckResult>, String> {
    Ok(get_unhealthy_connectors().await)
}
