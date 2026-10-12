use crate::marketplace_package::{MarketplacePackage, PackageType};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CatalogEntry {
    pub package: MarketplacePackage,
    pub rating: f64,
    pub download_count: u64,
    pub install_count: u64,
    pub trending_score: f64,
    pub featured: bool,
    pub editors_choice: bool,
    pub is_new: bool,
    pub has_update: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HomePageData {
    pub featured: Vec<CatalogEntry>,
    pub trending: Vec<CatalogEntry>,
    pub popular: Vec<CatalogEntry>,
    pub recently_updated: Vec<CatalogEntry>,
    pub recommended: Vec<CatalogEntry>,
    pub new_releases: Vec<CatalogEntry>,
    pub editors_choice: Vec<CatalogEntry>,
    pub installed_updates: Vec<CatalogEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub results: Vec<CatalogEntry>,
    pub total_count: usize,
    pub page: usize,
    pub page_size: usize,
    pub facets: SearchFacets,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchFacets {
    pub types: HashMap<String, usize>,
    pub categories: HashMap<String, usize>,
    pub authors: HashMap<String, usize>,
    pub licenses: HashMap<String, usize>,
    pub tags: HashMap<String, usize>,
}

fn builtin_packages() -> Vec<MarketplacePackage> {
    let mut pkgs = Vec::new();
    pkgs.extend(official_extensions());
    pkgs.extend(official_agents());
    pkgs.extend(official_skills());
    pkgs.extend(official_mcp_servers());
    pkgs.extend(official_workflows());
    pkgs
}

fn official_extensions() -> Vec<MarketplacePackage> {
    let base = || MarketplacePackage {
        id: String::new(), name: String::new(), display_name: String::new(),
        description: String::new(), package_type: PackageType::Extension,
        version: "1.0.0".into(), author: aetheros_author(),
        license: "MIT".into(), tags: Vec::new(), categories: vec!["productivity".into()],
        dependencies: Vec::new(), permissions: Vec::new(),
        compatibility: default_compat(), checksum: "".into(), signature: None,
        size_bytes: 0, download_url: "".into(), icon_url: None,
        screenshots: Vec::new(), readme: None, changelog: None,
        install_script: None, uninstall_script: None,
        min_app_version: "0.1.0".into(), max_app_version: None,
        created_at: "2026-01-01T00:00:00Z".into(), updated_at: "2026-06-01T00:00:00Z".into(),
        verified: true, is_official: true, is_open_source: true,
        connector_definition: None,
    };
    let mut exts = Vec::new();
    for (id, name, desc, tags) in [
        ("ext-gh", "GitHub Integration", "Connect GitHub repositories for PR, issue, and workflow management", vec!["github", "devops", "git"]),
        ("ext-slack", "Slack Connector", "Send messages, manage channels, and integrate Slack workflows", vec!["slack", "communication"]),
        ("ext-docker", "Docker Manager", "Manage containers, images, and Docker Compose stacks", vec!["docker", "devops", "containers"]),
        ("ext-notion", "Notion Sync", "Sync pages, databases, and manage Notion workspaces", vec!["notion", "productivity", "docs"]),
        ("ext-gcal", "Google Calendar", "Manage events, reminders, and calendar integration", vec!["google", "calendar", "productivity"]),
        ("ext-gmail", "Gmail Integration", "Send, read, and manage Gmail messages and threads", vec!["google", "email", "communication"]),
        ("ext-jira", "Jira Integration", "Manage issues, sprints, and Jira project workflows", vec!["jira", "project-management"]),
        ("ext-figma", "Figma Connector", "Access Figma designs, components, and design systems", vec!["figma", "design", "collaboration"]),
        ("ext-aws", "AWS Toolkit", "Manage EC2, S3, Lambda, and other AWS services", vec!["aws", "cloud", "devops"]),
        ("ext-azure", "Azure Tools", "Manage Azure resources, VMs, and cloud services", vec!["azure", "cloud", "devops"]),
    ] {
        let mut p = base();
        p.id = id.to_string(); p.name = name.to_string(); p.display_name = name.to_string();
        p.description = desc.to_string(); p.tags = tags.iter().map(|s| s.to_string()).collect();
        p.download_url = format!("https://registry.aetheros.com/api/v1/extensions/{}/download", id);
        exts.push(p);
    }
    exts
}

fn official_agents() -> Vec<MarketplacePackage> {
    let base = || MarketplacePackage {
        id: String::new(), name: String::new(), display_name: String::new(),
        description: String::new(), package_type: PackageType::Agent,
        version: "1.0.0".into(), author: aetheros_author(),
        license: "MIT".into(), tags: Vec::new(), categories: vec!["ai".into()],
        dependencies: Vec::new(), permissions: Vec::new(),
        compatibility: default_compat(), checksum: "".into(), signature: None,
        size_bytes: 0, download_url: "".into(), icon_url: None,
        screenshots: Vec::new(), readme: None, changelog: None,
        install_script: None, uninstall_script: None,
        min_app_version: "0.1.0".into(), max_app_version: None,
        created_at: "2026-01-01T00:00:00Z".into(), updated_at: "2026-06-01T00:00:00Z".into(),
        verified: true, is_official: true, is_open_source: true,
        connector_definition: None,
    };

    let mut agents = Vec::new();
    for (id, name, desc, tags) in [
        ("agent-coder", "Coding Agent", "Expert software developer — writes, debugs, and refactors code across languages", vec!["coding", "development", "programming"]),
        ("agent-research", "Research Agent", "Deep research across web, papers, and knowledge bases with citations", vec!["research", "analysis", "learning"]),
        ("agent-writer", "Writing Agent", "Professional writing assistant for articles, docs, and creative content", vec!["writing", "content", "creative"]),
        ("agent-marketing", "Marketing Agent", "Marketing strategy, copywriting, SEO, and campaign management", vec!["marketing", "business", "content"]),
        ("agent-automation", "Automation Agent", "Build and run automated workflows across tools and services", vec!["automation", "workflow", "productivity"]),
        ("agent-email", "Email Agent", "Manage inbox, draft replies, organize threads and email workflows", vec!["email", "communication", "productivity"]),
        ("agent-business", "Business Agent", "Business strategy, planning, analysis, and decision support", vec!["business", "strategy", "analysis"]),
        ("agent-finance", "Finance Agent", "Financial analysis, budgeting, forecasting, and reporting", vec!["finance", "business", "analysis"]),
        ("agent-support", "Customer Support Agent", "Customer support automation, ticket management, and response generation", vec!["support", "customer-service", "automation"]),
        ("agent-devops", "Developer Agent", "DevOps engineer — CI/CD, infrastructure, monitoring, and deployments", vec!["devops", "infrastructure", "cloud"]),
        ("agent-vision", "Vision Agent", "Image analysis, object detection, OCR, and visual recognition", vec!["vision", "ai", "image-processing"]),
        ("agent-voice", "Voice Agent", "Speech-to-text, text-to-speech, voice commands, and audio processing", vec!["voice", "audio", "speech"]),
        ("agent-data", "Data Analysis Agent", "Data cleaning, visualization, statistical analysis, and reporting", vec!["data", "analytics", "visualization"]),
        ("agent-web", "Web Automation Agent", "Browser automation, web scraping, form filling, and testing", vec!["web", "automation", "testing"]),
    ] {
        let mut p = base();
        p.id = id.to_string(); p.name = name.to_string(); p.display_name = name.to_string();
        p.description = desc.to_string(); p.tags = tags.iter().map(|s| s.to_string()).collect();
        p.download_url = format!("https://registry.aetheros.com/api/v1/agents/{}/download", id);
        agents.push(p);
    }
    agents
}

fn official_skills() -> Vec<MarketplacePackage> {
    let base = || MarketplacePackage {
        id: String::new(), name: String::new(), display_name: String::new(),
        description: String::new(), package_type: PackageType::Skill,
        version: "1.0.0".into(), author: aetheros_author(),
        license: "MIT".into(), tags: Vec::new(), categories: vec!["skill".into()],
        dependencies: Vec::new(), permissions: Vec::new(),
        compatibility: default_compat(), checksum: "".into(), signature: None,
        size_bytes: 0, download_url: "".into(), icon_url: None,
        screenshots: Vec::new(), readme: None, changelog: None,
        install_script: None, uninstall_script: None,
        min_app_version: "0.1.0".into(), max_app_version: None,
        created_at: "2026-01-01T00:00:00Z".into(), updated_at: "2026-06-01T00:00:00Z".into(),
        verified: true, is_official: true, is_open_source: true,
        connector_definition: None,
    };

    let mut skills = Vec::new();
    for (id, name, desc, tags) in [
        ("skill-github", "GitHub Skill", "Manage repos, issues, PRs, actions, and GitHub workflows", vec!["github", "git", "devops"]),
        ("skill-docker", "Docker Skill", "Build, run, and manage Docker containers and images", vec!["docker", "containers"]),
        ("skill-python", "Python Skill", "Python development, testing, packaging, and virtual environments", vec!["python", "programming"]),
        ("skill-nodejs", "Node.js Skill", "Node.js development, npm packages, and JavaScript tooling", vec!["nodejs", "javascript", "programming"]),
        ("skill-aws", "AWS Skill", "Amazon Web Services management — EC2, S3, Lambda, IAM", vec!["aws", "cloud"]),
        ("skill-azure", "Azure Skill", "Microsoft Azure cloud services management", vec!["azure", "cloud"]),
        ("skill-gcloud", "Google Cloud Skill", "Google Cloud Platform services and management", vec!["gcp", "cloud"]),
        ("skill-linux", "Linux Skill", "Linux system administration, shell scripting, and server management", vec!["linux", "sysadmin"]),
        ("skill-office", "Office Skill", "Microsoft Office automation — Word, Excel, PowerPoint, Outlook", vec!["office", "productivity"]),
        ("skill-terminal", "Terminal Skill", "Advanced terminal usage, scripting, and command-line tools", vec!["terminal", "cli"]),
        ("skill-git", "Git Skill", "Git operations — branching, merging, rebasing, and version control", vec!["git", "version-control"]),
        ("skill-sql", "SQL Skill", "Database queries, schema design, and data manipulation", vec!["sql", "database", "data"]),
    ] {
        let mut p = base();
        p.id = id.to_string(); p.name = name.to_string(); p.display_name = name.to_string();
        p.description = desc.to_string(); p.tags = tags.iter().map(|s| s.to_string()).collect();
        p.download_url = format!("https://registry.aetheros.com/api/v1/skills/{}/download", id);
        skills.push(p);
    }
    skills
}

fn official_mcp_servers() -> Vec<MarketplacePackage> {
    let base = || MarketplacePackage {
        id: String::new(), name: String::new(), display_name: String::new(),
        description: String::new(), package_type: PackageType::McpServer,
        version: "1.0.0".into(), author: aetheros_author(),
        license: "MIT".into(), tags: Vec::new(), categories: vec!["mcp".into()],
        dependencies: Vec::new(), permissions: Vec::new(),
        compatibility: default_compat(), checksum: "".into(), signature: None,
        size_bytes: 0, download_url: "".into(), icon_url: None,
        screenshots: Vec::new(), readme: None, changelog: None,
        install_script: None, uninstall_script: None,
        min_app_version: "0.1.0".into(), max_app_version: None,
        created_at: "2026-01-01T00:00:00Z".into(), updated_at: "2026-06-01T00:00:00Z".into(),
        verified: true, is_official: true, is_open_source: true,
        connector_definition: None,
    };

    let mut servers = Vec::new();
    for (id, name, desc, tags) in [
        ("mcp-filesystem", "Filesystem MCP", "Local filesystem access — read, write, search files and directories", vec!["filesystem", "storage"]),
        ("mcp-database", "Database MCP", "SQL database access — queries, schema, and data management", vec!["database", "sql"]),
        ("mcp-browser", "Browser MCP", "Headless browser control — navigation, scraping, and screenshots", vec!["browser", "web"]),
        ("mcp-github", "GitHub MCP", "GitHub API access — repos, issues, PRs, and actions", vec!["github", "git"]),
        ("mcp-slack", "Slack MCP", "Slack API access — messages, channels, and users", vec!["slack", "communication"]),
        ("mcp-email", "Email MCP", "Email sending and receiving via SMTP/IMAP", vec!["email", "communication"]),
        ("mcp-pdf", "PDF MCP", "PDF generation, parsing, and manipulation", vec!["pdf", "documents"]),
        ("mcp-puppeteer", "Puppeteer MCP", "Advanced browser automation with Puppeteer", vec!["browser", "automation", "testing"]),
    ] {
        let mut p = base();
        p.id = id.to_string(); p.name = name.to_string(); p.display_name = name.to_string();
        p.description = desc.to_string(); p.tags = tags.iter().map(|s| s.to_string()).collect();
        p.download_url = format!("https://registry.aetheros.com/api/v1/mcp/{}/download", id);
        servers.push(p);
    }
    servers
}

fn official_workflows() -> Vec<MarketplacePackage> {
    let base = || MarketplacePackage {
        id: String::new(), name: String::new(), display_name: String::new(),
        description: String::new(), package_type: PackageType::Workflow,
        version: "1.0.0".into(), author: aetheros_author(),
        license: "MIT".into(), tags: Vec::new(), categories: vec!["automation".into()],
        dependencies: Vec::new(), permissions: Vec::new(),
        compatibility: default_compat(), checksum: "".into(), signature: None,
        size_bytes: 0, download_url: "".into(), icon_url: None,
        screenshots: Vec::new(), readme: None, changelog: None,
        install_script: None, uninstall_script: None,
        min_app_version: "0.1.0".into(), max_app_version: None,
        created_at: "2026-01-01T00:00:00Z".into(), updated_at: "2026-06-01T00:00:00Z".into(),
        verified: true, is_official: true, is_open_source: true,
        connector_definition: None,
    };

    let mut wfs = Vec::new();
    for (id, name, desc, tags) in [
        ("wf-telegram", "Telegram Automation", "Automated Telegram messaging, broadcasting, and bot management", vec!["telegram", "messaging", "automation"]),
        ("wf-gmail", "Gmail Automation", "Automated email processing, filtering, and response workflows", vec!["gmail", "email", "automation"]),
        ("wf-whatsapp", "WhatsApp Automation", "WhatsApp messaging, group management, and notification workflows", vec!["whatsapp", "messaging", "automation"]),
        ("wf-discord", "Discord Automation", "Discord server management, moderation, and notification bots", vec!["discord", "messaging", "automation"]),
        ("wf-github", "GitHub Automation", "CI/CD workflows, PR management, and release automation", vec!["github", "devops", "automation"]),
        ("wf-notion", "Notion Automation", "Notion page management, database sync, and content workflows", vec!["notion", "productivity", "automation"]),
        ("wf-slack", "Slack Automation", "Slack messaging, channel management, and notification workflows", vec!["slack", "communication", "automation"]),
        ("wf-calendar", "Calendar Automation", "Calendar event management, scheduling, and reminder workflows", vec!["calendar", "scheduling", "automation"]),
    ] {
        let mut p = base();
        p.id = id.to_string(); p.name = name.to_string(); p.display_name = name.to_string();
        p.description = desc.to_string(); p.tags = tags.iter().map(|s| s.to_string()).collect();
        p.download_url = format!("https://registry.aetheros.com/api/v1/workflows/{}/download", id);
        wfs.push(p);
    }
    wfs
}

fn aetheros_author() -> crate::marketplace_package::PackageAuthor {
    crate::marketplace_package::PackageAuthor {
        name: "AetherOS".to_string(),
        email: Some("info@aetheros.com".to_string()),
        website: Some("https://aetheros.com".to_string()),
        github: Some("https://github.com/sabib360/AetherOS".to_string()),
        is_verified: true,
    }
}

fn default_compat() -> crate::marketplace_package::PackageCompatibility {
    crate::marketplace_package::PackageCompatibility {
        os: vec!["windows".into(), "macos".into(), "linux".into()],
        arch: vec!["x64".into(), "arm64".into()],
        app_version: "0.1.0".into(),
        min_ram_mb: None,
        min_disk_mb: None,
    }
}

pub fn get_catalog() -> Vec<CatalogEntry> {
    let installed = crate::marketplace_package::load_installed_packages();
    let installed_ids: std::collections::HashSet<String> =
        installed.iter().map(|p| p.id.clone()).collect();

    builtin_packages()
        .into_iter()
        .map(|pkg| {
            let is_installed = installed_ids.contains(&pkg.id);
            CatalogEntry {
                package: pkg.clone(),
                rating: 4.5,
                download_count: 1000 + rand_mod(&pkg.id, 9000),
                install_count: if is_installed { 1 } else { 0 },
                trending_score: rand_mod(&pkg.id, 100) as f64 / 100.0,
                featured: matches!(pkg.id.as_str(),
                    "agent-coder" | "agent-research" | "ext-gh" | "mcp-filesystem" | "wf-github"),
                editors_choice: matches!(pkg.id.as_str(),
                    "agent-coder" | "ext-docker" | "skill-python" | "mcp-database"),
                is_new: matches!(pkg.id.as_str(), "agent-voice" | "ext-figma" | "mcp-puppeteer"),
                has_update: false,
            }
        })
        .collect()
}

fn rand_mod(id: &str, max: u64) -> u64 {
    id.bytes().fold(0u64, |acc, b| acc.wrapping_mul(31).wrapping_add(b as u64)) % max
}

pub fn home_page_data() -> HomePageData {
    let catalog = get_catalog();
    HomePageData {
        featured: catalog.iter().filter(|e| e.featured).take(8).cloned().collect(),
        trending: { let mut v: Vec<_> = catalog.clone(); v.sort_by(|a, b| b.trending_score.partial_cmp(&a.trending_score).unwrap_or(std::cmp::Ordering::Equal)); v.into_iter().take(12).collect() },
        popular: { let mut v: Vec<_> = catalog.clone(); v.sort_by(|a, b| b.download_count.cmp(&a.download_count)); v.into_iter().take(12).collect() },
        recently_updated: catalog.clone().into_iter().take(12).collect(),
        recommended: catalog.iter().filter(|e| e.rating >= 4.5).take(8).cloned().collect(),
        new_releases: catalog.iter().filter(|e| e.is_new).take(8).cloned().collect(),
        editors_choice: catalog.iter().filter(|e| e.editors_choice).take(6).cloned().collect(),
        installed_updates: catalog.iter().filter(|e| e.has_update).take(10).cloned().collect(),
    }
}

pub fn search_catalog(
    query: &str,
    package_type: Option<PackageType>,
    categories: Option<Vec<String>>,
    tags: Option<Vec<String>>,
    page: usize,
    page_size: usize,
) -> SearchResult {
    let catalog = get_catalog();
    let q = query.to_lowercase();

    let filtered: Vec<CatalogEntry> = catalog
        .into_iter()
        .filter(|e| {
            if q.is_empty() { return true; }
            e.package.name.to_lowercase().contains(&q)
                || e.package.display_name.to_lowercase().contains(&q)
                || e.package.description.to_lowercase().contains(&q)
                || e.package.author.name.to_lowercase().contains(&q)
                || e.package.tags.iter().any(|t| t.to_lowercase().contains(&q))
        })
        .filter(|e| {
            if let Some(ref pt) = package_type {
                e.package.package_type == *pt
            } else { true }
        })
        .filter(|e| {
            if let Some(ref cats) = categories {
                e.package.categories.iter().any(|c| cats.contains(c))
            } else { true }
        })
        .filter(|e| {
            if let Some(ref ts) = tags {
                e.package.tags.iter().any(|t| ts.contains(t))
            } else { true }
        })
        .collect();

    let total_count = filtered.len();
    let start = page * page_size;
    let results: Vec<CatalogEntry> = filtered.iter().skip(start).take(page_size).cloned().collect();

    let mut facets = SearchFacets {
        types: HashMap::new(),
        categories: HashMap::new(),
        authors: HashMap::new(),
        licenses: HashMap::new(),
        tags: HashMap::new(),
    };

    for entry in &filtered {
        *facets.types.entry(format!("{:?}", entry.package.package_type)).or_insert(0) += 1;
        for cat in &entry.package.categories { *facets.categories.entry(cat.clone()).or_insert(0) += 1; }
        *facets.authors.entry(entry.package.author.name.clone()).or_insert(0) += 1;
        *facets.licenses.entry(entry.package.license.clone()).or_insert(0) += 1;
        for tag in &entry.package.tags { *facets.tags.entry(tag.clone()).or_insert(0) += 1; }
    }

    SearchResult { results, total_count, page, page_size, facets }
}

pub fn packages_by_type(package_type: PackageType) -> Vec<CatalogEntry> {
    get_catalog().into_iter().filter(|e| e.package.package_type == package_type).collect()
}

#[tauri::command]
pub async fn get_marketplace_home() -> Result<HomePageData, String> {
    Ok(home_page_data())
}

#[tauri::command]
pub async fn search_marketplace(
    query: String,
    package_type: Option<String>,
    categories: Option<Vec<String>>,
    tags: Option<Vec<String>>,
    page: Option<usize>,
) -> Result<SearchResult, String> {
    let ptype = package_type.as_deref().and_then(|s| match s {
        "extension" => Some(PackageType::Extension),
        "agent" => Some(PackageType::Agent),
        "skill" => Some(PackageType::Skill),
        "template" => Some(PackageType::Template),
        "theme" => Some(PackageType::Theme),
        "workflow" => Some(PackageType::Workflow),
        "automation_pack" => Some(PackageType::AutomationPack),
        "mcp_server" => Some(PackageType::McpServer),
        "ai_tool" => Some(PackageType::AiTool),
        "widget" => Some(PackageType::Widget),
        "icon_pack" => Some(PackageType::IconPack),
        "font" => Some(PackageType::Font),
        "color_scheme" => Some(PackageType::ColorScheme),
        "animation" => Some(PackageType::Animation),
        _ => None,
    });
    Ok(search_catalog(&query, ptype, categories, tags, page.unwrap_or(0), 20))
}

#[tauri::command]
pub async fn get_package_detail(package_id: String) -> Result<Option<CatalogEntry>, String> {
    Ok(get_catalog().into_iter().find(|e| e.package.id == package_id))
}

#[tauri::command]
pub async fn get_packages_by_type(package_type: String) -> Result<Vec<CatalogEntry>, String> {
    let ptype = match package_type.as_str() {
        "extension" => PackageType::Extension,
        "agent" => PackageType::Agent,
        "skill" => PackageType::Skill,
        "template" => PackageType::Template,
        "theme" => PackageType::Theme,
        "workflow" => PackageType::Workflow,
        "mcp_server" => PackageType::McpServer,
        _ => return Err(format!("Unknown type: {package_type}")),
    };
    Ok(packages_by_type(ptype))
}
