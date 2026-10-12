use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageManifest {
    pub name: String,
    pub version: String,
    pub description: String,
    #[serde(default)]
    pub category: String,
    pub checksum: Option<String>,
    pub size: u64,
    #[serde(default)]
    pub dependencies: Vec<PackageDependency>,
    #[serde(default)]
    pub conflicts: Vec<String>,
    pub install: PackageInstall,
    pub uninstall: PackageUninstall,
    pub verification: PackageVerification,
    #[serde(default)]
    pub install_script: Option<String>,
    #[serde(default)]
    pub uninstall_script: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageDependency {
    pub name: String,
    pub version_req: String,
    #[serde(default)]
    pub optional: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum PackageInstall {
    Extract { target: String },
    Copy { source: String, target: String },
    Run { command: String, args: Vec<String> },
    Script { script: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum PackageUninstall {
    Remove { paths: Vec<String> },
    Run { command: String, args: Vec<String> },
    Script { script: String },
    None,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageVerification {
    #[serde(default = "default_true")]
    pub checksum_required: bool,
    #[serde(default)]
    pub signature_required: bool,
    #[serde(default = "default_min_free")]
    pub min_free_space_mb: u64,
}

fn default_true() -> bool { true }
fn default_min_free() -> u64 { 500 }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstalledPackage {
    pub name: String,
    pub version: String,
    pub install_path: String,
    pub installed_at: String,
    pub checksum: Option<String>,
    pub size: u64,
    pub dependencies: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstalledPackagesManifest {
    pub packages: Vec<InstalledPackage>,
}

pub fn installed_packages_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join("installed-packages.json")
}

pub fn load_installed_packages() -> InstalledPackagesManifest {
    let path = installed_packages_path();
    if !path.exists() {
        return InstalledPackagesManifest { packages: Vec::new() };
    }
    match std::fs::read_to_string(&path) {
        Ok(content) => serde_json::from_str(&content).unwrap_or(InstalledPackagesManifest { packages: Vec::new() }),
        Err(_) => InstalledPackagesManifest { packages: Vec::new() },
    }
}

pub fn save_installed_packages(manifest: &InstalledPackagesManifest) -> Result<(), String> {
    let path = installed_packages_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Failed to create config dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(manifest).map_err(|e| format!("Failed to serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Failed to write packages manifest: {e}"))?;
    Ok(())
}

pub fn version_satisfies(installed: &str, requirement: &str) -> bool {
    let req = requirement.trim();
    if req == "*" || req == "any" {
        return true;
    }
    if let Some(min) = req.strip_prefix(">=") {
        return compare_versions(installed, min.trim()) >= 0;
    }
    if let Some(max) = req.strip_prefix("<=") {
        return compare_versions(installed, max.trim()) <= 0;
    }
    if let Some(exact) = req.strip_prefix("==") {
        return installed == exact.trim();
    }
    if let Some(min) = req.strip_prefix(">") {
        return compare_versions(installed, min.trim()) > 0;
    }
    if let Some(max) = req.strip_prefix("<") {
        return compare_versions(installed, max.trim()) < 0;
    }
    if req.contains("..") {
        let parts: Vec<&str> = req.split("..").collect();
        if parts.len() == 2 {
            let low = parts[0].trim();
            let high = parts[1].trim();
            return compare_versions(installed, low) >= 0 && compare_versions(installed, high) <= 0;
        }
    }
    installed == req
}

fn compare_versions(a: &str, b: &str) -> i32 {
    let a_parts: Vec<u32> = a.split('.').filter_map(|p| p.parse().ok()).collect();
    let b_parts: Vec<u32> = b.split('.').filter_map(|p| p.parse().ok()).collect();
    let max_len = a_parts.len().max(b_parts.len());
    for i in 0..max_len {
        let av = a_parts.get(i).copied().unwrap_or(0);
        let bv = b_parts.get(i).copied().unwrap_or(0);
        if av != bv {
            return if av > bv { 1 } else { -1 };
        }
    }
    0
}

pub fn resolve_dependency_order(
    packages: &[PackageManifest],
    names: &[String],
) -> Result<Vec<String>, String> {
    let mut order = Vec::new();
    let mut visited: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut in_progress: std::collections::HashSet<String> = std::collections::HashSet::new();

    let pkg_map: HashMap<&str, &PackageManifest> = packages.iter().map(|p| (p.name.as_str(), p)).collect();

    fn visit(
        name: &str,
        pkg_map: &HashMap<&str, &PackageManifest>,
        visited: &mut std::collections::HashSet<String>,
        in_progress: &mut std::collections::HashSet<String>,
        order: &mut Vec<String>,
    ) -> Result<(), String> {
        if visited.contains(name) {
            return Ok(());
        }
        if in_progress.contains(name) {
            return Err(format!("Circular dependency detected: {name}"));
        }
        in_progress.insert(name.to_string());

        if let Some(pkg) = pkg_map.get(name) {
            for dep in &pkg.dependencies {
                if !dep.optional {
                    visit(&dep.name, pkg_map, visited, in_progress, order)?;
                }
            }
        }

        in_progress.remove(name);
        visited.insert(name.to_string());
        order.push(name.to_string());
        Ok(())
    }

    for name in names {
        visit(name, &pkg_map, &mut visited, &mut in_progress, &mut order)?;
    }

    Ok(order)
}

pub fn packages_dir() -> PathBuf {
    crate::paths::aetheros_home().join("packages")
}

pub fn package_manifest_path(name: &str) -> PathBuf {
    packages_dir().join(format!("{name}.json"))
}

pub fn package_asset_dir(name: &str) -> PathBuf {
    packages_dir().join(name)
}

pub fn checksum_file(path: &Path) -> Result<String, String> {
    use sha2::{Digest, Sha256};
    let mut file = std::fs::File::open(path).map_err(|e| format!("Cannot open {path:?}: {e}"))?;
    let mut hasher = Sha256::new();
    std::io::copy(&mut file, &mut hasher).map_err(|e| format!("Read error on {path:?}: {e}"))?;
    let hash = hasher.finalize();
    Ok(format!("sha256:{:x}", hash))
}

pub fn verify_checksum(path: &Path, expected: &str) -> Result<(), String> {
    let actual = checksum_file(path)?;
    let expected_clean = expected.trim();
    if actual != expected_clean && !actual.ends_with(expected_clean) {
        return Err(format!(
            "Checksum mismatch for {path:?}:\n  expected: {expected_clean}\n  actual:   {actual}"
        ));
    }
    Ok(())
}
