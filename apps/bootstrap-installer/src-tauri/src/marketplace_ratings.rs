use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Review {
    pub id: String,
    pub package_id: String,
    pub author: String,
    pub rating: u8,
    pub title: Option<String>,
    pub body: Option<String>,
    pub version: String,
    pub created_at: String,
    pub updated_at: Option<String>,
    pub helpful_count: u32,
    pub verified_purchase: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageRatings {
    pub package_id: String,
    pub average_rating: f64,
    pub total_reviews: u32,
    pub total_downloads: u64,
    pub distribution: [u32; 5],
    pub recent_reviews: Vec<Review>,
}

fn ratings_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("marketplace-ratings.json")
}

fn load_reviews() -> Vec<Review> {
    let path = ratings_path();
    if !path.exists() { return Vec::new(); }
    std::fs::read_to_string(&path).ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_default()
}

fn save_reviews(reviews: &[Review]) -> Result<(), String> {
    let path = ratings_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(reviews).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn get_package_ratings(package_id: &str) -> PackageRatings {
    let reviews = load_reviews();
    let package_reviews: Vec<&Review> = reviews.iter().filter(|r| r.package_id == package_id).collect();

    let total = package_reviews.len() as u32;
    let sum: u32 = package_reviews.iter().map(|r| r.rating as u32).sum();
    let avg = if total > 0 { sum as f64 / total as f64 } else { 0.0 };

    let mut dist = [0u32; 5];
    for r in &package_reviews {
        let idx = (r.rating.saturating_sub(1)).min(4) as usize;
        dist[idx] += 1;
    }

    let mut recent: Vec<Review> = package_reviews.into_iter().cloned().collect();
    recent.sort_by(|a, b| b.created_at.cmp(&a.created_at));
    recent.truncate(10);

    PackageRatings {
        package_id: package_id.to_string(),
        average_rating: avg,
        total_reviews: total,
        total_downloads: 0,
        distribution: dist,
        recent_reviews: recent,
    }
}

pub fn submit_review(review: Review) -> Result<Review, String> {
    let mut reviews = load_reviews();
    if review.rating < 1 || review.rating > 5 {
        return Err("Rating must be between 1 and 5".to_string());
    }
    reviews.push(review.clone());
    save_reviews(&reviews)?;
    Ok(review)
}

pub fn record_download(package_id: &str) -> Result<(), String> {
    let path = crate::paths::aetheros_home().join("config").join("marketplace-stats.json");
    let mut stats: Vec<(String, u64)> = if path.exists() {
        let c = std::fs::read_to_string(&path).map_err(|e| format!("Read: {e}"))?;
        serde_json::from_str(&c).unwrap_or_default()
    } else { Vec::new() };

    if let Some(entry) = stats.iter_mut().find(|(id, _)| id == package_id) {
        entry.1 += 1;
    } else {
        stats.push((package_id.to_string(), 1));
    }

    if let Some(parent) = path.parent() { std::fs::create_dir_all(parent).ok(); }
    let content = serde_json::to_string_pretty(&stats).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

fn now_iso() -> String {
    let d = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default();
    let s = d.as_secs();
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", (s / 86400) % 30 + 1, s % 86400 / 3600 + 1, (s % 3600) / 60, s % 60, 0)
}

#[tauri::command]
pub async fn marketplace_get_ratings(package_id: String) -> Result<PackageRatings, String> {
    Ok(get_package_ratings(&package_id))
}

#[tauri::command]
pub async fn marketplace_submit_review(
    package_id: String,
    author: String,
    rating: u8,
    title: Option<String>,
    body: Option<String>,
) -> Result<Review, String> {
    let review = Review {
        id: uuid::Uuid::new_v4().to_string(),
        package_id,
        author,
        rating,
        title,
        body,
        version: "1.0.0".into(),
        created_at: now_iso(),
        updated_at: None,
        helpful_count: 0,
        verified_purchase: true,
    };
    submit_review(review)
}
