use crate::model_store::{self, ModelStoreCategory, ModelStoreEntry};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HardwareTier {
    LowEnd,
    Balanced,
    HighPerformance,
    Workstation,
    CloudOnly,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareSpec {
    pub total_ram_mb: u64,
    pub total_vram_mb: u64,
    pub cpu_cores: u32,
    pub has_gpu: bool,
    pub gpu_name: Option<String>,
    pub gpu_vram_mb: Option<u64>,
    pub disk_free_mb: u64,
    pub is_laptop: bool,
    pub tier: HardwareTier,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelRecommendation {
    pub model: ModelStoreEntry,
    pub score: f64,
    pub reason: String,
    pub compatibility: Compatibility,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Compatibility {
    Excellent,
    Good,
    Fair,
    Poor,
    Insufficient,
}

pub fn detect_hardware_tier() -> HardwareSpec {
    let total_ram_mb = estimate_ram_mb();
    let cpu_cores = estimate_cpu_cores();
    let has_gpu = detect_gpu();

    let tier = if !has_gpu || total_ram_mb < 4096 {
        HardwareTier::LowEnd
    } else if total_ram_mb < 8192 {
        HardwareTier::Balanced
    } else if total_ram_mb < 16384 {
        HardwareTier::HighPerformance
    } else if total_ram_mb >= 32768 && has_gpu {
        HardwareTier::Workstation
    } else {
        HardwareTier::Balanced
    };

    HardwareSpec {
        total_ram_mb,
        total_vram_mb: 0,
        cpu_cores,
        has_gpu,
        gpu_name: None,
        gpu_vram_mb: None,
        disk_free_mb: estimate_disk_free_mb(),
        is_laptop: detect_laptop(),
        tier,
    }
}

fn estimate_ram_mb() -> u64 {
    let info = sys_info::mem_info().ok();
    info.map(|m| m.total / 1024).unwrap_or(8192)
}

fn estimate_cpu_cores() -> u32 {
    sys_info::cpu_num().ok().map(|c| c as u32).unwrap_or(4)
}

fn estimate_disk_free_mb() -> u64 {
    let path = crate::paths::aetheros_home();
    let free = crate::disk_manager::get_free_space(&path);
    free / (1024 * 1024)
}

fn detect_gpu() -> bool {
    detect_nvidia_gpu().is_some() || detect_amd_gpu() || detect_apple_silicon()
}

fn detect_nvidia_gpu() -> Option<String> {
    let out = std::process::Command::new("nvidia-smi")
        .arg("--query-gpu=name,memory.total")
        .arg("--format=csv,noheader,nounits")
        .output()
        .ok()?;
    let stdout = String::from_utf8_lossy(&out.stdout);
    stdout.lines().next().map(|l| l.trim().to_string())
}

fn detect_amd_gpu() -> bool {
    if cfg!(target_os = "windows") {
        std::process::Command::new("wmic")
            .args(["path", "win32_VideoController", "get", "name"])
            .output()
            .ok()
            .and_then(|o| {
                let s = String::from_utf8_lossy(&o.stdout);
                Some(s.contains("AMD") || s.contains("Radeon"))
            })
            .unwrap_or(false)
    } else {
        std::process::Command::new("lspci")
            .output()
            .ok()
            .and_then(|o| {
                let s = String::from_utf8_lossy(&o.stdout);
                Some(s.contains("AMD") || s.contains("Radeon"))
            })
            .unwrap_or(false)
    }
}

fn detect_apple_silicon() -> bool {
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("sysctl")
            .args(["-n", "machdep.cpu.brand_string"])
            .output()
            .ok()
            .and_then(|o| {
                let s = String::from_utf8_lossy(&o.stdout);
                Some(s.contains("Apple"))
            })
            .unwrap_or(false)
    }
    #[cfg(not(target_os = "macos"))]
    false
}

fn detect_laptop() -> bool {
    if cfg!(target_os = "macos") {
        return true;
    }
    if cfg!(target_os = "windows") {
        if let Ok(out) = std::process::Command::new("wmic")
            .args(["path", "Win32_Battery", "get", "Status"])
            .output()
        {
            let s = String::from_utf8_lossy(&out.stdout);
            return s.contains("2") || s.contains("OK");
        }
    }
    let is_power_supply = std::path::Path::new("/sys/class/power_supply").exists();
    is_power_supply
}

fn compatibility_for(
    model: &ModelStoreEntry,
    spec: &HardwareSpec,
) -> (Compatibility, String) {
    if !model.is_local {
        return (Compatibility::Excellent, "Cloud-hosted API — no hardware requirements".to_string());
    }

    let needed_ram = model.ram_required_mb;
    let _needed_vram = model.vram_required_mb;

    if spec.total_ram_mb < needed_ram {
        let deficit = needed_ram - spec.total_ram_mb;
        return (
            Compatibility::Insufficient,
            format!("{deficit} MB more RAM needed (requires {} MB, have {} MB)", needed_ram, spec.total_ram_mb),
        );
    }

    if spec.total_ram_mb >= needed_ram * 2 {
        (Compatibility::Excellent, format!("Plenty of RAM ({} MB) for this model (needs {} MB)", spec.total_ram_mb, needed_ram))
    } else if spec.total_ram_mb >= needed_ram {
        (Compatibility::Good, format!("Sufficient RAM ({} MB) for this model (needs {} MB)", spec.total_ram_mb, needed_ram))
    } else {
        (Compatibility::Fair, format!("Barely meets RAM requirements ({} MB, needs {} MB)", spec.total_ram_mb, needed_ram))
    }
}

fn score_model(model: &ModelStoreEntry, spec: &HardwareSpec) -> f64 {
    let mut score = 50.0f64;

    if !model.is_local {
        score += 30.0;
        return score;
    }

    let ram_ratio = if model.ram_required_mb > 0 {
        spec.total_ram_mb as f64 / model.ram_required_mb as f64
    } else {
        2.0
    };

    score += (ram_ratio * 20.0).clamp(0.0, 30.0);

    if model.size_bytes > 0 {
        let free_mb = spec.disk_free_mb * 1024 * 1024;
        if free_mb as u64 > model.size_bytes * 2 {
            score += 10.0;
        } else if free_mb as u64 > model.size_bytes {
            score += 5.0;
        } else {
            score -= 10.0;
        }
    }

    if spec.tier == HardwareTier::LowEnd && model.vram_required_mb <= 2048 {
        score += 15.0;
    }
    if spec.tier == HardwareTier::Workstation && model.vram_required_mb > 8192 {
        score += 10.0;
    }
    if spec.is_laptop && model.size_bytes > 5_000_000_000 {
        score -= 10.0;
    }

    match model.category {
        ModelStoreCategory::Offline => score += 5.0,
        ModelStoreCategory::Embedding => {
            if spec.tier == HardwareTier::LowEnd || spec.tier == HardwareTier::Balanced {
                score += 10.0;
            }
        }
        ModelStoreCategory::Reasoning => {
            if spec.tier == HardwareTier::HighPerformance || spec.tier == HardwareTier::Workstation {
                score += 10.0;
            }
        }
        _ => {}
    }

    score.clamp(0.0, 100.0)
}

pub fn recommend_models(
    catalog: &[ModelStoreEntry],
    spec: &HardwareSpec,
    count: usize,
) -> Vec<ModelRecommendation> {
    let mut recommendations: Vec<ModelRecommendation> = catalog
        .iter()
        .map(|model| {
            let (compat, reason) = compatibility_for(model, spec);
            let score = score_model(model, spec);
            ModelRecommendation {
                model: model.clone(),
                score,
                reason,
                compatibility: compat,
            }
        })
        .filter(|r| r.compatibility != Compatibility::Insufficient)
        .collect();

    recommendations.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    recommendations.truncate(count.max(1));
    recommendations
}

pub fn recommend_for_task(
    catalog: &[ModelStoreEntry],
    spec: &HardwareSpec,
    task: &str,
    count: usize,
) -> Vec<ModelRecommendation> {
    let filtered: Vec<ModelStoreEntry> = catalog
        .iter()
        .filter(|m| {
            let task_lower = task.to_lowercase();
            m.capabilities.iter().any(|c| task_lower.contains(c))
                || match task_lower.as_str() {
                    t if t.contains("code") || t.contains("program") => {
                        m.category == ModelStoreCategory::Coding
                    }
                    t if t.contains("reason") || t.contains("think") => {
                        m.category == ModelStoreCategory::Reasoning
                    }
                    t if t.contains("vision") || t.contains("image") || t.contains("see") => {
                        m.category == ModelStoreCategory::Vision
                    }
                    t if t.contains("embed") => {
                        m.category == ModelStoreCategory::Embedding
                    }
                    _ => true,
                }
        })
        .cloned()
        .collect();

    recommend_models(&filtered, spec, count)
}

#[tauri::command]
pub async fn get_hardware_spec() -> Result<HardwareSpec, String> {
    Ok(detect_hardware_tier())
}

#[tauri::command]
pub async fn get_model_recommendations(
    count: Option<usize>,
    task: Option<String>,
) -> Result<Vec<ModelRecommendation>, String> {
    let catalog = model_store::builtin_catalog();
    let spec = detect_hardware_tier();
    let count = count.unwrap_or(10);

    Ok(match task {
        Some(t) => recommend_for_task(&catalog, &spec, &t, count),
        None => recommend_models(&catalog, &spec, count),
    })
}
