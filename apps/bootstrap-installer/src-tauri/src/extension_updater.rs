use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtensionInfo {
    pub id: String,
    pub name: String,
    pub extension_type: ExtensionType,
    pub version: String,
    pub installed_path: String,
    pub remote_version: Option<String>,
    pub update_available: bool,
    pub checksum: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExtensionType {
    Plugin,
    Skill,
    Template,
    Theme,
    MarketplacePackage,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtensionUpdateResult {
    pub id: String,
    pub name: String,
    pub update_available: bool,
    pub installed_version: String,
    pub available_version: Option<String>,
    pub updated: bool,
    pub success: bool,
    pub message: String,
}

fn extensions_dir() -> PathBuf {
    crate::paths::aetheros_home().join("extensions")
}

fn plugins_dir() -> PathBuf {
    crate::paths::aetheros_home().join("aetheros").join("plugins")
}

fn skills_dir() -> PathBuf {
    crate::paths::aetheros_home().join("aetheros").join("skills")
}

fn themes_dir() -> PathBuf {
    crate::paths::aetheros_home().join("skins")
}

fn scan_directory_extensions(dir: &PathBuf, ext_type: ExtensionType) -> Vec<ExtensionInfo> {
    let mut extensions = Vec::new();
    if !dir.exists() {
        return extensions;
    }

    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if !path.is_dir() {
                continue;
            }
            let name = path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("")
                .to_string();

            let version = find_version_in_dir(&path);
            extensions.push(ExtensionInfo {
                id: format!("{}_{}", ext_type_name(ext_type), name),
                name,
                extension_type: ext_type,
                version,
                installed_path: path.to_string_lossy().to_string(),
                remote_version: None,
                update_available: false,
                checksum: None,
            });
        }
    }

    extensions
}

fn ext_type_name(ext_type: ExtensionType) -> &'static str {
    match ext_type {
        ExtensionType::Plugin => "plugin",
        ExtensionType::Skill => "skill",
        ExtensionType::Template => "template",
        ExtensionType::Theme => "theme",
        ExtensionType::MarketplacePackage => "marketplace",
    }
}

fn find_version_in_dir(dir: &PathBuf) -> String {
    let meta_paths = [
        dir.join("plugin.yaml"),
        dir.join("SKILL.md"),
        dir.join("package.json"),
        dir.join("theme.yaml"),
    ];

    for meta_path in &meta_paths {
        if meta_path.exists() {
            if let Ok(content) = std::fs::read_to_string(meta_path) {
                for line in content.lines() {
                    let lower = line.to_lowercase();
                    if lower.contains("version:") || lower.contains("\"version\"") {
                        let parts: Vec<&str> = if lower.contains(':') {
                            line.split(':').collect()
                        } else {
                            continue;
                        };
                        if parts.len() >= 2 {
                            let v = parts[1].trim().trim_matches('"').trim_matches('\'').to_string();
                            if !v.is_empty() {
                                return v;
                            }
                        }
                    }
                }
            }
        }
    }

    "0.0.0".to_string()
}

pub fn scan_installed_extensions() -> Vec<ExtensionInfo> {
    let mut all = Vec::new();

    all.extend(scan_directory_extensions(&plugins_dir(), ExtensionType::Plugin));
    all.extend(scan_directory_extensions(&skills_dir(), ExtensionType::Skill));
    all.extend(scan_directory_extensions(&themes_dir(), ExtensionType::Theme));

    let ext_dir = extensions_dir();
    if ext_dir.exists() {
        all.extend(scan_directory_extensions(&ext_dir, ExtensionType::MarketplacePackage));
    }

    all
}

async fn check_remote_version(extension: &ExtensionInfo) -> Option<String> {
    let ext_type = ext_type_name(extension.extension_type);
    let url = format!(
        "https://registry.aetheros.com/api/v1/{}/{}/latest",
        ext_type, extension.name
    );

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .ok()?;

    let resp = client.get(&url).send().await.ok()?;
    if !resp.status().is_success() {
        return None;
    }

    let json: serde_json::Value = resp.json().await.ok()?;
    json["version"].as_str().map(|s| s.to_string())
}

pub async fn check_extension_updates() -> Vec<ExtensionUpdateResult> {
    let extensions = scan_installed_extensions();
    let mut results = Vec::new();

    for ext in extensions {
        let remote = check_remote_version(&ext).await;

        let update_available = match (&remote, &ext.version) {
            (Some(r), _) if r != &ext.version => true,
            _ => false,
        };

        results.push(ExtensionUpdateResult {
            id: ext.id.clone(),
            name: ext.name.clone(),
            update_available,
            installed_version: ext.version.clone(),
            available_version: remote,
            updated: false,
            success: true,
            message: if update_available {
                "Update available".to_string()
            } else {
                "Up to date".to_string()
            },
        });
    }

    results
}

pub async fn update_extension(name: &str, ext_type: ExtensionType) -> Result<ExtensionUpdateResult, String> {
    let download_url = format!(
        "https://registry.aetheros.com/api/v1/{}/{}/download",
        ext_type_name(ext_type),
        name
    );

    let dest = match ext_type {
        ExtensionType::Plugin => plugins_dir().join(name),
        ExtensionType::Skill => skills_dir().join(name),
        ExtensionType::Theme => themes_dir().join(name),
        ExtensionType::Template => templates_dir().join(name),
        ExtensionType::MarketplacePackage => extensions_dir().join(name),
    };

    if dest.exists() {
        std::fs::remove_dir_all(&dest)
            .map_err(|e| format!("Remove old: {e}"))?;
    }

    let temp_dir = crate::paths::aetheros_home()
        .join("tmp")
        .join(format!("ext-{name}-update"));
    std::fs::create_dir_all(&temp_dir)
        .map_err(|e| format!("Create temp: {e}"))?;

    let zip_path = temp_dir.join("extension.zip");
    let client = reqwest::Client::new();
    let resp = client
        .get(&download_url)
        .send()
        .await
        .map_err(|e| format!("Download failed: {e}"))?;

    if !resp.status().is_success() {
        return Err(format!("HTTP {}", resp.status()));
    }

    let bytes = resp.bytes().await.map_err(|e| format!("Read body: {e}"))?;
    std::fs::write(&zip_path, &bytes).map_err(|e| format!("Write zip: {e}"))?;

    use std::io::Read;
    let file = std::fs::File::open(&zip_path).map_err(|e| format!("Open zip: {e}"))?;
    let mut archive = zip::ZipArchive::new(file).map_err(|e| format!("Read zip: {e}"))?;

    std::fs::create_dir_all(&dest).map_err(|e| format!("Create dest: {e}"))?;

    for i in 0..archive.len() {
        let mut entry = archive.by_index(i).map_err(|e| format!("Entry {i}: {e}"))?;
        let out_path = dest.join(entry.name());
        if entry.name().ends_with('/') {
            std::fs::create_dir_all(&out_path).ok();
        } else {
            if let Some(parent) = out_path.parent() {
                std::fs::create_dir_all(parent).ok();
            }
            let mut outfile =
                std::fs::File::create(&out_path).map_err(|e| format!("Create {out_path:?}: {e}"))?;
            let mut buffer = Vec::new();
            entry.read_to_end(&mut buffer).map_err(|e| format!("Read entry: {e}"))?;
            std::io::copy(&mut buffer.as_slice(), &mut outfile)
                .map_err(|e| format!("Write {out_path:?}: {e}"))?;
        }
    }

    let _ = std::fs::remove_dir_all(&temp_dir);

    Ok(ExtensionUpdateResult {
        id: format!("{}_{}", ext_type_name(ext_type), name),
        name: name.to_string(),
        update_available: true,
        installed_version: "0.0.0".to_string(),
        available_version: None,
        updated: true,
        success: true,
        message: format!("Updated {name} successfully"),
    })
}

fn templates_dir() -> PathBuf {
    crate::paths::aetheros_home().join("templates")
}

#[tauri::command]
pub async fn scan_extensions() -> Result<Vec<ExtensionInfo>, String> {
    Ok(scan_installed_extensions())
}

#[tauri::command]
pub async fn check_extension_updates_command() -> Result<Vec<ExtensionUpdateResult>, String> {
    Ok(check_extension_updates().await)
}

#[tauri::command]
pub async fn update_extension_command(
    name: String,
    ext_type: String,
) -> Result<ExtensionUpdateResult, String> {
    let etype = match ext_type.as_str() {
        "plugin" => ExtensionType::Plugin,
        "skill" => ExtensionType::Skill,
        "template" => ExtensionType::Template,
        "theme" => ExtensionType::Theme,
        "marketplace" => ExtensionType::MarketplacePackage,
        _ => return Err(format!("Unknown extension type: {ext_type}")),
    };
    update_extension(&name, etype).await
}
