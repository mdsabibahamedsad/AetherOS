use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnifiedMessage {
    pub id: String,
    pub connector_id: String,
    pub connector_name: String,
    pub source_message_id: String,
    pub sender: String,
    pub sender_avatar: Option<String>,
    pub subject: Option<String>,
    pub body: String,
    pub html_body: Option<String>,
    pub received_at: String,
    pub is_read: bool,
    pub is_starred: bool,
    pub is_pinned: bool,
    pub labels: Vec<String>,
    pub category: String,
    pub ai_summary: Option<String>,
    pub priority: String,
    pub attachments: Vec<MessageAttachment>,
    pub conversation_id: Option<String>,
    pub thread_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageAttachment {
    pub id: String,
    pub name: String,
    pub mime_type: String,
    pub size_bytes: u64,
    pub url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InboxFilter {
    pub connector_ids: Option<Vec<String>>,
    pub labels: Option<Vec<String>>,
    pub search_query: Option<String>,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    pub is_read: Option<bool>,
    pub is_starred: Option<bool>,
    pub category: Option<String>,
    pub priority: Option<String>,
    pub limit: Option<usize>,
    pub offset: Option<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InboxStats {
    pub total: usize,
    pub unread: usize,
    pub starred: usize,
    pub pinned: usize,
    pub by_connector: HashMap<String, ConnectorInboxStats>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectorInboxStats {
    pub total: usize,
    pub unread: usize,
}

fn hub_dir() -> PathBuf {
    crate::paths::aetheros_home().join("hub")
}

fn inbox_path() -> PathBuf {
    hub_dir().join("inbox.json")
}

fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("msg_{:x}", nanos)
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

fn load_messages() -> Vec<UnifiedMessage> {
    let path = inbox_path();
    if !path.exists() {
        return Vec::new();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

fn save_messages(messages: &[UnifiedMessage]) -> Result<(), String> {
    let path = inbox_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(messages).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn add_message(
    connector_id: &str,
    connector_name: &str,
    source_message_id: &str,
    sender: &str,
    sender_avatar: Option<String>,
    subject: Option<String>,
    body: &str,
    html_body: Option<String>,
    labels: Vec<String>,
    category: &str,
    priority: &str,
    attachments: Vec<MessageAttachment>,
    conversation_id: Option<String>,
    thread_id: Option<String>,
) -> Result<UnifiedMessage, String> {
    let mut messages = load_messages();
    if messages.iter().any(|m| m.connector_id == connector_id && m.source_message_id == source_message_id) {
        let existing = messages.iter().find(|m| m.connector_id == connector_id && m.source_message_id == source_message_id).unwrap();
        return Ok(existing.clone());
    }
    let msg = UnifiedMessage {
        id: generate_id(),
        connector_id: connector_id.to_string(),
        connector_name: connector_name.to_string(),
        source_message_id: source_message_id.to_string(),
        sender: sender.to_string(),
        sender_avatar,
        subject,
        body: body.to_string(),
        html_body,
        received_at: iso_now(),
        is_read: false,
        is_starred: false,
        is_pinned: false,
        labels,
        category: category.to_string(),
        ai_summary: None,
        priority: priority.to_string(),
        attachments,
        conversation_id,
        thread_id,
    };
    let result = msg.clone();
    messages.insert(0, msg);
    save_messages(&messages)?;
    Ok(result)
}

pub fn get_messages(filter: InboxFilter) -> Vec<UnifiedMessage> {
    let mut messages = load_messages();
    if let Some(ids) = &filter.connector_ids {
        messages.retain(|m| ids.contains(&m.connector_id));
    }
    if let Some(labels) = &filter.labels {
        messages.retain(|m| labels.iter().any(|l| m.labels.contains(l)));
    }
    if let Some(q) = &filter.search_query {
        let q_lower = q.to_lowercase();
        messages.retain(|m| {
            m.body.to_lowercase().contains(&q_lower)
                || m.sender.to_lowercase().contains(&q_lower)
                || m.subject.as_ref().map(|s| s.to_lowercase().contains(&q_lower)).unwrap_or(false)
        });
    }
    if let Some(read) = filter.is_read {
        messages.retain(|m| m.is_read == read);
    }
    if let Some(starred) = filter.is_starred {
        messages.retain(|m| m.is_starred == starred);
    }
    if let Some(cat) = &filter.category {
        messages.retain(|m| m.category == *cat);
    }
    if let Some(pri) = &filter.priority {
        messages.retain(|m| m.priority == *pri);
    }
    if let Some(from) = &filter.date_from {
        messages.retain(|m| m.received_at >= *from);
    }
    if let Some(to) = &filter.date_to {
        messages.retain(|m| m.received_at <= *to);
    }
    let offset = filter.offset.unwrap_or(0);
    let limit = filter.limit.unwrap_or(50);
    messages.into_iter().skip(offset).take(limit).collect()
}

pub fn search_messages(query: &str, limit: usize) -> Vec<UnifiedMessage> {
    let messages = load_messages();
    let q_lower = query.to_lowercase();
    let mut results: Vec<UnifiedMessage> = messages.into_iter()
        .filter(|m| {
            m.body.to_lowercase().contains(&q_lower)
                || m.sender.to_lowercase().contains(&q_lower)
                || m.subject.as_ref().map(|s| s.to_lowercase().contains(&q_lower)).unwrap_or(false)
                || m.labels.iter().any(|l| l.to_lowercase().contains(&q_lower))
        })
        .collect();
    results.truncate(limit);
    results
}

pub fn update_message_status(
    message_id: &str,
    is_read: Option<bool>,
    is_starred: Option<bool>,
    is_pinned: Option<bool>,
    labels: Option<Vec<String>>,
) -> Result<UnifiedMessage, String> {
    let mut messages = load_messages();
    let msg = messages.iter_mut().find(|m| m.id == message_id)
        .ok_or_else(|| format!("Message not found: {message_id}"))?;
    if let Some(r) = is_read { msg.is_read = r; }
    if let Some(s) = is_starred { msg.is_starred = s; }
    if let Some(p) = is_pinned { msg.is_pinned = p; }
    if let Some(l) = labels { msg.labels = l; }
    let result = msg.clone();
    save_messages(&messages)?;
    Ok(result)
}

pub fn bulk_mark_read(message_ids: Vec<String>) -> Result<usize, String> {
    let mut messages = load_messages();
    let mut count = 0;
    for msg in messages.iter_mut() {
        if message_ids.contains(&msg.id) && !msg.is_read {
            msg.is_read = true;
            count += 1;
        }
    }
    save_messages(&messages)?;
    Ok(count)
}

pub fn delete_message(message_id: &str) -> Result<(), String> {
    let mut messages = load_messages();
    let pos = messages.iter().position(|m| m.id == message_id)
        .ok_or_else(|| format!("Message not found: {message_id}"))?;
    messages.remove(pos);
    save_messages(&messages)
}

pub fn get_stats() -> InboxStats {
    let messages = load_messages();
    let total = messages.len();
    let unread = messages.iter().filter(|m| !m.is_read).count();
    let starred = messages.iter().filter(|m| m.is_starred).count();
    let pinned = messages.iter().filter(|m| m.is_pinned).count();

    let mut by_connector: HashMap<String, ConnectorInboxStats> = HashMap::new();
    for msg in &messages {
        let entry = by_connector.entry(msg.connector_id.clone()).or_insert(ConnectorInboxStats { total: 0, unread: 0 });
        entry.total += 1;
        if !msg.is_read {
            entry.unread += 1;
        }
    }

    InboxStats { total, unread, starred, pinned, by_connector }
}

fn extractive_summary(text: &str, max_sentences: usize) -> String {
    let sentences: Vec<&str> = text.split(|c| c == '.' || c == '!' || c == '?')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect();
    if sentences.len() <= max_sentences {
        let len = text.len().min(500);
        format!("{}...", &text[..len])
    } else {
        let summary: String = sentences[..max_sentences].join(". ");
        if summary.len() > 500 {
            format!("{}...", &summary[..500])
        } else {
            format!("{}.", summary)
        }
    }
}

pub fn generate_ai_summary(message_id: &str) -> Result<UnifiedMessage, String> {
    let messages = load_messages();
    let msg = messages.iter().find(|m| m.id == message_id)
        .ok_or_else(|| format!("Message not found: {message_id}"))?;

    let text = msg.subject.as_deref().unwrap_or("")
        .to_owned() + " " + &msg.body;

    let providers = crate::ai_provider::load_providers_config().unwrap_or_default();
    let enabled = providers.iter().find(|p| p.enabled);

    let summary = match enabled {
        Some(provider) => {
            let api_key = crate::ai_provider::read_provider_api_key(&provider.provider_id)
                .ok()
                .flatten();
            match api_key {
                Some(key) => generate_llm_summary(provider, &key, &text),
                None => Ok(extractive_summary(&text, 3)),
            }
        }
        None => Ok(extractive_summary(&text, 3)),
    };

    let summary_str = summary.unwrap_or_else(|_| extractive_summary(&text, 3));

    let mut messages = load_messages();
    let m = messages.iter_mut().find(|m| m.id == message_id)
        .ok_or_else(|| format!("Message not found: {message_id}"))?;
    m.ai_summary = Some(summary_str);
    let result = m.clone();
    save_messages(&messages)?;
    Ok(result)
}

fn generate_llm_summary(
    provider: &crate::ai_provider::ProviderConfig,
    api_key: &str,
    text: &str,
) -> Result<String, String> {
    let max_chars = text.len().min(4000);
    let truncated = &text[..max_chars];
    let model = provider.models.default_model.as_deref()
        .or(provider.models.fast_model.as_deref())
        .unwrap_or("gpt-4o-mini");
    let base_url = provider.base_url.as_deref()
        .unwrap_or("https://api.openai.com/v1");
    let api_url = format!("{}/chat/completions", base_url.trim_end_matches('/'));

    let payload = serde_json::json!({
        "model": model,
        "messages": [
            {"role": "system", "content": "Summarize the following message concisely in 1-2 sentences."},
            {"role": "user", "content": truncated}
        ],
        "max_tokens": 150,
        "temperature": 0.3,
    });

    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build().map_err(|e| format!("Build client: {e}"))?;

    let resp = client.post(&api_url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json")
        .json(&payload)
        .send()
        .map_err(|e| format!("AI API request failed: {e}"))?;

    let body: serde_json::Value = resp.json().map_err(|e| format!("Parse response: {e}"))?;

    let content = body["choices"][0]["message"]["content"]
        .as_str()
        .ok_or_else(|| format!("No content in AI response: {}", body))?
        .trim()
        .to_string();

    Ok(content)
}

pub fn set_ai_summary(message_id: &str, summary: &str) -> Result<UnifiedMessage, String> {
    let mut messages = load_messages();
    let msg = messages.iter_mut().find(|m| m.id == message_id)
        .ok_or_else(|| format!("Message not found: {message_id}"))?;
    msg.ai_summary = Some(summary.to_string());
    let result = msg.clone();
    save_messages(&messages)?;
    Ok(result)
}

#[tauri::command]
pub async fn inbox_add_message(
    connector_id: String, connector_name: String, source_message_id: String,
    sender: String, sender_avatar: Option<String>, subject: Option<String>,
    body: String, html_body: Option<String>, labels: Vec<String>,
    category: String, priority: String, attachments: Vec<MessageAttachment>,
    conversation_id: Option<String>, thread_id: Option<String>,
) -> Result<UnifiedMessage, String> {
    add_message(&connector_id, &connector_name, &source_message_id, &sender,
        sender_avatar, subject, &body, html_body, labels, &category, &priority,
        attachments, conversation_id, thread_id)
}

#[tauri::command]
pub async fn inbox_get_messages(filter: InboxFilter) -> Result<Vec<UnifiedMessage>, String> {
    Ok(get_messages(filter))
}

#[tauri::command]
pub async fn inbox_search(query: String, limit: Option<usize>) -> Result<Vec<UnifiedMessage>, String> {
    Ok(search_messages(&query, limit.unwrap_or(50)))
}

#[tauri::command]
pub async fn inbox_update_status(
    message_id: String, is_read: Option<bool>, is_starred: Option<bool>,
    is_pinned: Option<bool>, labels: Option<Vec<String>>,
) -> Result<UnifiedMessage, String> {
    update_message_status(&message_id, is_read, is_starred, is_pinned, labels)
}

#[tauri::command]
pub async fn inbox_bulk_mark_read(message_ids: Vec<String>) -> Result<usize, String> {
    bulk_mark_read(message_ids)
}

#[tauri::command]
pub async fn inbox_delete_message(message_id: String) -> Result<(), String> {
    delete_message(&message_id)
}

#[tauri::command]
pub async fn inbox_get_stats() -> Result<InboxStats, String> {
    Ok(get_stats())
}

#[tauri::command]
pub async fn inbox_set_ai_summary(message_id: String, summary: String) -> Result<UnifiedMessage, String> {
    set_ai_summary(&message_id, &summary)
}

#[tauri::command]
pub async fn inbox_generate_ai_summary(message_id: String) -> Result<UnifiedMessage, String> {
    generate_ai_summary(&message_id)
}
