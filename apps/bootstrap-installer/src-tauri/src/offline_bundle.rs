use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::io::Read;
use std::path::{Path, PathBuf};

/// Offline bundle contains all packages needed for offline installation.
/// Format: ZIP archive with a manifest.json at root + packages/*.bin
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OfflineBundleManifest {
    pub format_version: u32,
    pub created_at: String,
    pub total_size: u64,
    pub package_count: u32,
    pub os_arch: String,
    pub min_bootstrap_version: String,
    pub packages: Vec<OfflinePackageEntry>,
    pub checksums: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OfflinePackageEntry {
    pub name: String,
    pub version: String,
    pub filename: String,
    pub size: u64,
    pub compressed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OfflineBundleValidation {
    pub valid: bool,
    pub package_count: u32,
    pub total_size: u64,
    pub errors: Vec<String>,
}

pub struct OfflineBundle {
    pub manifest: OfflineBundleManifest,
    pub bundle_path: PathBuf,
}

impl OfflineBundle {
    pub fn open(path: &Path) -> Result<Self, String> {
        let file = std::fs::File::open(path)
            .map_err(|e| format!("Failed to open bundle: {e}"))?;

        let mut archive = zip::ZipArchive::new(file)
            .map_err(|e| format!("Failed to read archive: {e}"))?;

        let manifest = archive
            .by_name("manifest.json")
            .map_err(|_| "Missing manifest.json in bundle".to_string())?;

        let manifest: OfflineBundleManifest = serde_json::from_reader(manifest)
            .map_err(|e| format!("Invalid manifest: {e}"))?;

        Ok(Self {
            manifest,
            bundle_path: path.to_path_buf(),
        })
    }

    pub fn validate(&self) -> OfflineBundleValidation {
        let file = match std::fs::File::open(&self.bundle_path) {
            Ok(f) => f,
            Err(e) => return OfflineBundleValidation {
                valid: false,
                package_count: 0,
                total_size: 0,
                errors: vec![format!("Cannot open: {e}")],
            },
        };

        let mut archive = match zip::ZipArchive::new(file) {
            Ok(a) => a,
            Err(e) => return OfflineBundleValidation {
                valid: false,
                package_count: 0,
                total_size: 0,
                errors: vec![format!("Bad archive: {e}")],
            },
        };

        let mut errors = Vec::new();
        let mut checksum_failures = 0u32;

        for pkg in &self.manifest.packages {
            let expected = self.manifest.checksums.get(&pkg.name);
            let mut entry = match archive.by_name(&pkg.filename) {
                Ok(e) => e,
                Err(_) => {
                    errors.push(format!("Missing package file: {}", pkg.filename));
                    continue;
                }
            };

            if let Some(expected_hash) = expected {
                let mut hasher = Sha256::new();
                let mut buf = [0u8; 65536];
                loop {
                    match entry.read(&mut buf) {
                        Ok(0) => break,
                        Ok(n) => hasher.update(&buf[..n]),
                        Err(e) => {
                            errors.push(format!("Read error in {}: {e}", pkg.filename));
                            break;
                        }
                    }
                }
                let actual = format!("{:x}", hasher.finalize());
                if &actual != expected_hash {
                    checksum_failures += 1;
                    errors.push(format!(
                        "Checksum mismatch for {}: expected {expected_hash}, got {actual}",
                        pkg.name
                    ));
                }
            }
        }

        OfflineBundleValidation {
            valid: checksum_failures == 0 && errors.is_empty(),
            package_count: self.manifest.package_count,
            total_size: self.manifest.total_size,
            errors,
        }
    }

    pub fn extract_package(
        &self,
        package_name: &str,
        dest: &Path,
    ) -> Result<(), String> {
        let file = std::fs::File::open(&self.bundle_path)
            .map_err(|e| format!("Cannot open bundle: {e}"))?;
        let mut archive = zip::ZipArchive::new(file)
            .map_err(|e| format!("Bad archive: {e}"))?;

        let pkg = self.manifest.packages
            .iter()
            .find(|p| p.name == package_name)
            .ok_or_else(|| format!("Package {package_name} not in bundle"))?;

        let mut entry = archive
            .by_name(&pkg.filename)
            .map_err(|_| format!("Missing file {} in bundle", pkg.filename))?;

        std::fs::create_dir_all(dest)
            .map_err(|e| format!("Cannot create dest dir: {e}"))?;

        let out_path = dest.join(&pkg.filename);
        let mut out = std::fs::File::create(&out_path)
            .map_err(|e| format!("Cannot create output: {e}"))?;

        std::io::copy(&mut entry, &mut out)
            .map_err(|e| format!("Extraction error: {e}"))?;

        Ok(())
    }

    pub fn list_packages(&self) -> &[OfflinePackageEntry] {
        &self.manifest.packages
    }

    pub fn total_size(&self) -> u64 {
        self.manifest.total_size
    }
}

/// Detect if the given path is an offline bundle
pub fn is_offline_bundle(path: &Path) -> bool {
    if !path.is_file() {
        return false;
    }
    let ext = path.extension().and_then(|s| s.to_str()).unwrap_or("");
    ext == "zip" || ext == "aos" || ext == "aether"
}

#[tauri::command]
pub async fn open_offline_bundle(path: String) -> Result<OfflineBundleManifest, String> {
    let bundle = OfflineBundle::open(Path::new(&path))?;
    Ok(bundle.manifest)
}

#[tauri::command]
pub async fn validate_offline_bundle(path: String) -> Result<OfflineBundleValidation, String> {
    let bundle = OfflineBundle::open(Path::new(&path))?;
    Ok(bundle.validate())
}

#[tauri::command]
pub async fn extract_from_bundle(path: String, package_name: String, dest: String) -> Result<(), String> {
    let bundle = OfflineBundle::open(Path::new(&path))?;
    bundle.extract_package(&package_name, Path::new(&dest))
}
