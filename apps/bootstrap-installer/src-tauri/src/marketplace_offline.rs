use crate::marketplace_package::MarketplacePackage;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OfflineBundleManifest {
    pub version: String,
    pub created_at: String,
    pub packages: Vec<MarketplacePackage>,
    pub total_size: u64,
    pub bundle_checksum: String,
}

pub fn bundle_path() -> PathBuf {
    crate::paths::aetheros_home().join("marketplace").join("offline-bundle")
}

pub fn export_offline_bundle(
    package_ids: &[String],
    output_path: &PathBuf,
) -> Result<OfflineBundleManifest, String> {
    let catalog = crate::marketplace_catalog::get_catalog();
    let packages: Vec<MarketplacePackage> = catalog
        .into_iter()
        .filter(|e| package_ids.contains(&e.package.id))
        .map(|e| e.package)
        .collect();

    let total_size: u64 = packages.iter().map(|p| p.size_bytes).sum();
    let checksum = compute_bundle_checksum(&packages);

    let manifest = OfflineBundleManifest {
        version: "1.0".to_string(),
        created_at: now_iso(),
        packages: packages.clone(),
        total_size,
        bundle_checksum: checksum.clone(),
    };

    std::fs::create_dir_all(output_path).map_err(|e| format!("Create dir: {e}"))?;

    let manifest_json =
        serde_json::to_string_pretty(&manifest).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(output_path.join("manifest.json"), &manifest_json)
        .map_err(|e| format!("Write manifest: {e}"))?;

    std::fs::write(output_path.join("CHECKSUM"), &checksum)
        .map_err(|e| format!("Write checksum: {e}"))?;

    tracing::info!(count = packages.len(), size = total_size, "offline bundle exported");

    Ok(manifest)
}

pub fn import_offline_bundle(bundle_path: &PathBuf) -> Result<Vec<MarketplacePackage>, String> {
    let manifest_path = bundle_path.join("manifest.json");
    if !manifest_path.exists() {
        return Err("manifest.json not found in bundle".to_string());
    }

    let content = std::fs::read_to_string(&manifest_path)
        .map_err(|e| format!("Read manifest: {e}"))?;
    let manifest: OfflineBundleManifest =
        serde_json::from_str(&content).map_err(|e| format!("Parse manifest: {e}"))?;

    let checksum_path = bundle_path.join("CHECKSUM");
    if checksum_path.exists() {
        let expected = std::fs::read_to_string(&checksum_path)
            .map_err(|e| format!("Read checksum: {e}"))?;
        let actual = compute_bundle_checksum(&manifest.packages);
        if expected.trim() != actual {
            return Err("Bundle checksum mismatch — possible corruption".to_string());
        }
    }

    let mut installed = crate::marketplace_package::load_installed_packages();
    for pkg in &manifest.packages {
        if !installed.iter().any(|p| p.id == pkg.id) {
            installed.push(pkg.clone());
        }
    }
    crate::marketplace_package::save_installed_packages(&installed)?;

    tracing::info!(count = manifest.packages.len(), "offline bundle imported");

    Ok(manifest.packages)
}

fn compute_bundle_checksum(packages: &[MarketplacePackage]) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    for pkg in packages {
        hasher.update(pkg.id.as_bytes());
        hasher.update(pkg.version.as_bytes());
    }
    format!("{:x}", hasher.finalize())
}

fn now_iso() -> String {
    let d = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default();
    let s = d.as_secs();
    format!("2026-{:02}-{:02}T{:02}:{:02}:{:02}Z", (s / 86400) % 30 + 1, s % 86400 / 3600 + 1, (s % 3600) / 60, s % 60, 0)
}

#[tauri::command]
pub async fn marketplace_export_offline(
    package_ids: Vec<String>,
    output_path: String,
) -> Result<OfflineBundleManifest, String> {
    export_offline_bundle(&package_ids, &PathBuf::from(output_path))
}

#[tauri::command]
pub async fn marketplace_import_offline(bundle_path: String) -> Result<Vec<MarketplacePackage>, String> {
    import_offline_bundle(&PathBuf::from(bundle_path))
}
