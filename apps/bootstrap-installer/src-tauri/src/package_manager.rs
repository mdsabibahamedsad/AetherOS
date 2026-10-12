use crate::disk_manager;
use crate::install_modes::InstallModeConfig;
use crate::package_cache;
use crate::package_format::{self, PackageManifest};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PackageStatus {
    Pending,
    Resolved,
    Downloading,
    Verifying,
    Installing,
    Installed,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageOperation {
    pub manifest: PackageManifest,
    pub status: PackageStatus,
    pub download_url: Option<String>,
    pub local_path: Option<PathBuf>,
    pub size: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageInstallationProgress {
    pub current_package: String,
    pub package_index: usize,
    pub total_packages: usize,
    pub overall_progress: f64,
    pub stage: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallationSummary {
    pub success: bool,
    pub packages_installed: usize,
    pub packages_failed: usize,
    pub total_size: u64,
    pub errors: Vec<String>,
    pub duration_secs: f64,
}

pub struct PackageManager {
    install_root: PathBuf,
    mode: InstallModeConfig,
    operations: Vec<PackageOperation>,
}

impl PackageManager {
    pub fn new(install_root: PathBuf, mode: InstallModeConfig) -> Self {
        Self {
            install_root,
            mode,
            operations: Vec::new(),
        }
    }

    pub fn with_operations(mut self, ops: Vec<PackageOperation>) -> Self {
        self.operations = ops;
        self
    }

    pub async fn resolve_operations(&mut self) -> Result<(), String> {
        let names: Vec<String> = self.operations.iter().map(|o| o.manifest.name.clone()).collect();
        let manifests: Vec<PackageManifest> = self.operations.iter().map(|o| o.manifest.clone()).collect();

        if names.is_empty() {
            return Ok(());
        }

        let sorted = package_format::resolve_dependency_order(&manifests, &names)
            .map_err(|e| format!("Dependency resolution failed: {e}"))?;

        let mut ordered = Vec::with_capacity(sorted.len());
        let mut map: std::collections::HashMap<&str, PackageOperation> = self
            .operations
            .iter()
            .map(|o| (o.manifest.name.as_str(), o.clone()))
            .collect();

        for name in &sorted {
            if let Some(op) = map.remove(name.as_str()) {
                ordered.push(op);
            }
        }
        for op in map.into_values() {
            ordered.push(op);
        }
        self.operations = ordered;
        Ok(())
    }

    pub async fn run_installation(
        &self,
        app_handle: tauri::AppHandle,
    ) -> InstallationSummary {
        let start = std::time::Instant::now();
        let total = self.operations.len();
        let mut installed = 0usize;
        let mut failed = 0usize;
        let mut total_size = 0u64;
        let mut errors = Vec::new();

        for (idx, op) in self.operations.iter().enumerate() {
            let overall_progress = if total > 0 { (idx as f64) / (total as f64) } else { 1.0 };
            tracing::info!(
                progress = %overall_progress,
                package = %op.manifest.name,
                version = %op.manifest.version,
                "Installing package"
            );

            match self.install_single_package(&app_handle, op).await {
                Ok(size) => {
                    installed += 1;
                    total_size += size;
                    tracing::info!("Installed {} v{}", op.manifest.name, op.manifest.version);
                }
                Err(e) => {
                    failed += 1;
                    errors.push(format!("{}: {e}", op.manifest.name));
                    tracing::error!(package = %op.manifest.name, error = %e, "install failed");
                }
            }
        }

        let duration = start.elapsed().as_secs_f64();
        InstallationSummary {
            success: failed == 0,
            packages_installed: installed,
            packages_failed: failed,
            total_size,
            errors,
            duration_secs: duration,
        }
    }

    async fn install_single_package(&self, app_handle: &tauri::AppHandle, op: &PackageOperation) -> Result<u64, String> {
        let dest = self.install_root.join("packages").join(&op.manifest.name);

        let package_archive = match &op.local_path {
            Some(p) if p.exists() => p.clone(),
            _ => {
                let cached = package_cache::find_in_cache(
                    &op.manifest.name, &op.manifest.version
                ).await;
                match cached {
                    Some(c) => c,
                    None => {
                        return Err(format!(
                            "No local source for package {} v{}. Provide download_url or local_path.",
                            op.manifest.name, op.manifest.version
                        ));
                    }
                }
            }
        };

        // Verify checksum
        if op.manifest.verification.checksum_required {
            if let Some(ref expected) = op.manifest.checksum {
                package_format::verify_checksum(&package_archive, expected)?;
            }
        }

        // Extract the package archive
        let extract_dir = dest.join("_extract");
        std::fs::create_dir_all(&extract_dir)
            .map_err(|e| format!("Cannot create extract dir: {e}"))?;

        crate::extract::extract_zip(
            app_handle,
            &package_archive,
            &extract_dir,
        ).await?;

        // Run install script if present
        if let Some(script_path) = &op.manifest.install_script {
            let full_path = if Path::new(script_path).is_relative() {
                extract_dir.join(script_path)
            } else {
                PathBuf::from(script_path)
            };
            if full_path.exists() {
                run_install_script(full_path, &dest, &op.manifest.name)?;
            }
        }

        // Register in installed packages
        let mut installed = package_format::load_installed_packages();
        installed.packages.push(package_format::InstalledPackage {
            name: op.manifest.name.clone(),
            version: op.manifest.version.clone(),
            install_path: dest.to_string_lossy().to_string(),
            installed_at: chrono_now(),
            checksum: op.manifest.checksum.clone(),
            size: op.manifest.size,
            dependencies: op.manifest.dependencies.iter().map(|d| d.name.clone()).collect(),
        });
        package_format::save_installed_packages(&installed)?;

        // Move extracted contents to final location
        merge_directories(&extract_dir, &dest)?;

        // Cleanup temp
        if extract_dir.exists() {
            std::fs::remove_dir_all(&extract_dir).ok();
        }

        let meta = std::fs::metadata(&package_archive)
            .map_err(|e| format!("Cannot stat archive: {e}"))?;
        Ok(meta.len())
    }

    pub async fn check_disk_space_required(&self) -> Result<u64, String> {
        let total: u64 = self.operations.iter().map(|o| o.size).sum();
        let extra = total / 10;
        Ok(total + extra)
    }
}

fn chrono_now() -> String {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = now.as_secs();
    format!("1970-01-01T00:{:02}:{:02}Z", (secs / 60) % 60, secs % 60)
}

fn run_install_script(
    script_path: PathBuf,
    _dest: &Path,
    _package_name: &str,
) -> Result<(), String> {
    let _script_str = std::fs::read_to_string(&script_path)
        .map_err(|e| format!("Cannot read install script: {e}"))?;

    if cfg!(target_os = "windows") {
        let output = std::process::Command::new("powershell")
            .arg("-ExecutionPolicy")
            .arg("Bypass")
            .arg("-File")
            .arg(&script_path)
            .output()
            .map_err(|e| format!("Failed to run install script: {e}"))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Install script failed: {stderr}"));
        }
        Ok(())
    } else {
        let output = std::process::Command::new("sh")
            .arg(&script_path)
            .output()
            .map_err(|e| format!("Failed to run install script: {e}"))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Install script failed: {stderr}"));
        }
        Ok(())
    }
}

fn merge_directories(src: &Path, dest: &Path) -> Result<(), String> {
    if !dest.exists() {
        std::fs::create_dir_all(dest)
            .map_err(|e| format!("Cannot create dest: {e}"))?;
    }

    if let Ok(entries) = std::fs::read_dir(src) {
        for entry in entries.flatten() {
            let name = entry.file_name();
            let src_path = entry.path();
            let dest_path = dest.join(&name);
            if src_path.is_dir() {
                merge_directories(&src_path, &dest_path)?;
                std::fs::remove_dir_all(&src_path).ok();
            } else {
                std::fs::rename(&src_path, &dest_path)
                    .or_else(|_| std::fs::copy(&src_path, &dest_path).map(|_| ()))
                    .map_err(|e| format!("Failed to move {}: {e}", name.to_string_lossy()))?;
                std::fs::remove_file(&src_path).ok();
            }
        }
    }

    if src.exists() {
        std::fs::remove_dir(src).ok();
    }
    Ok(())
}

#[tauri::command]
pub async fn start_package_installation(
    app_handle: tauri::AppHandle,
    mode: crate::install_modes::InstallMode,
    packages: Vec<PackageManifest>,
) -> Result<InstallationSummary, String> {
    let install_root = crate::installer::install_root();
    let mode_config = crate::install_modes::InstallModeConfig::for_mode(mode);

    let ops: Vec<PackageOperation> = packages
        .into_iter()
        .map(|m| PackageOperation {
            manifest: m,
            status: PackageStatus::Pending,
            download_url: None,
            local_path: None,
            size: 0,
        })
        .collect();

    let mut pm = PackageManager::new(install_root.clone(), mode_config)
        .with_operations(ops);
    pm.resolve_operations().await?;

    let required = pm.check_disk_space_required().await?;
    let available = disk_manager::get_free_space(&install_root);
    if available < required {
        return Err(format!(
            "Insufficient disk space. Required: {} MB, Available: {} MB",
            required / 1_048_576,
            available / 1_048_576,
        ));
    }

    let result = pm.run_installation(app_handle).await;
    Ok(result)
}
