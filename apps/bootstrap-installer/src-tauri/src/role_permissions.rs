use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RoleType {
    Owner,
    Administrator,
    Manager,
    Developer,
    Operator,
    Researcher,
    Guest,
    Viewer,
    Custom,
}

impl RoleType {
    pub fn as_str(&self) -> &'static str {
        match self {
            RoleType::Owner => "owner",
            RoleType::Administrator => "administrator",
            RoleType::Manager => "manager",
            RoleType::Developer => "developer",
            RoleType::Operator => "operator",
            RoleType::Researcher => "researcher",
            RoleType::Guest => "guest",
            RoleType::Viewer => "viewer",
            RoleType::Custom => "custom",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "owner" => Some(RoleType::Owner),
            "administrator" => Some(RoleType::Administrator),
            "manager" => Some(RoleType::Manager),
            "developer" => Some(RoleType::Developer),
            "operator" => Some(RoleType::Operator),
            "researcher" => Some(RoleType::Researcher),
            "guest" => Some(RoleType::Guest),
            "viewer" => Some(RoleType::Viewer),
            "custom" => Some(RoleType::Custom),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionDef {
    pub id: String,
    pub name: String,
    pub description: String,
    pub category: PermissionCategory,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PermissionCategory {
    Workspace,
    Knowledge,
    Model,
    Marketplace,
    Extension,
    Agent,
    Billing,
    UserManagement,
    Security,
    Automation,
    Api,
    Plugin,
    Project,
    Team,
    Organization,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoleDefinition {
    pub id: String,
    pub org_id: String,
    pub name: String,
    pub description: String,
    pub role_type: RoleType,
    pub permissions: Vec<String>,
    pub is_system_role: bool,
    pub priority: u32,
    pub created_at: String,
}

fn team_dir() -> PathBuf {
    crate::paths::aetheros_home().join("team")
}

fn roles_path(org_id: &str) -> PathBuf {
    team_dir().join("orgs").join(org_id).join("roles.json")
}

pub fn load_roles(org_id: &str) -> Vec<RoleDefinition> {
    let path = roles_path(org_id);
    if !path.exists() {
        return default_roles();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|c| serde_json::from_str(&c).ok())
        .unwrap_or_else(default_roles)
}

pub fn save_roles(org_id: &str, roles: &[RoleDefinition]) -> Result<(), String> {
    let path = roles_path(org_id);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Create dir: {e}"))?;
    }
    let content = serde_json::to_string_pretty(roles).map_err(|e| format!("Serialize: {e}"))?;
    std::fs::write(&path, content).map_err(|e| format!("Write: {e}"))?;
    Ok(())
}

pub fn all_permission_definitions() -> Vec<PermissionDef> {
    vec![
        PermissionDef { id: "workspace.view".into(), name: "View Workspace".into(), description: "View workspace contents".into(), category: PermissionCategory::Workspace },
        PermissionDef { id: "workspace.edit".into(), name: "Edit Workspace".into(), description: "Edit workspace settings".into(), category: PermissionCategory::Workspace },
        PermissionDef { id: "workspace.delete".into(), name: "Delete Workspace".into(), description: "Delete workspace".into(), category: PermissionCategory::Workspace },
        PermissionDef { id: "knowledge.view".into(), name: "View Knowledge".into(), description: "View knowledge base".into(), category: PermissionCategory::Knowledge },
        PermissionDef { id: "knowledge.edit".into(), name: "Edit Knowledge".into(), description: "Add/edit knowledge".into(), category: PermissionCategory::Knowledge },
        PermissionDef { id: "knowledge.share".into(), name: "Share Knowledge".into(), description: "Share knowledge with others".into(), category: PermissionCategory::Knowledge },
        PermissionDef { id: "knowledge.delete".into(), name: "Delete Knowledge".into(), description: "Delete knowledge entries".into(), category: PermissionCategory::Knowledge },
        PermissionDef { id: "model.view".into(), name: "View Models".into(), description: "View available models".into(), category: PermissionCategory::Model },
        PermissionDef { id: "model.use".into(), name: "Use Models".into(), description: "Use AI models".into(), category: PermissionCategory::Model },
        PermissionDef { id: "model.install".into(), name: "Install Models".into(), description: "Install new models".into(), category: PermissionCategory::Model },
        PermissionDef { id: "model.configure".into(), name: "Configure Models".into(), description: "Configure model settings".into(), category: PermissionCategory::Model },
        PermissionDef { id: "marketplace.view".into(), name: "View Marketplace".into(), description: "Browse marketplace".into(), category: PermissionCategory::Marketplace },
        PermissionDef { id: "marketplace.install".into(), name: "Install from Marketplace".into(), description: "Install packages".into(), category: PermissionCategory::Marketplace },
        PermissionDef { id: "marketplace.publish".into(), name: "Publish to Marketplace".into(), description: "Publish packages".into(), category: PermissionCategory::Marketplace },
        PermissionDef { id: "extension.install".into(), name: "Install Extensions".into(), description: "Install extensions".into(), category: PermissionCategory::Extension },
        PermissionDef { id: "extension.remove".into(), name: "Remove Extensions".into(), description: "Remove extensions".into(), category: PermissionCategory::Extension },
        PermissionDef { id: "agent.install".into(), name: "Install Agents".into(), description: "Install AI agents".into(), category: PermissionCategory::Agent },
        PermissionDef { id: "agent.configure".into(), name: "Configure Agents".into(), description: "Configure agent settings".into(), category: PermissionCategory::Agent },
        PermissionDef { id: "agent.run".into(), name: "Run Agents".into(), description: "Execute agents".into(), category: PermissionCategory::Agent },
        PermissionDef { id: "billing.view".into(), name: "View Billing".into(), description: "View billing info".into(), category: PermissionCategory::Billing },
        PermissionDef { id: "billing.manage".into(), name: "Manage Billing".into(), description: "Manage billing/payments".into(), category: PermissionCategory::Billing },
        PermissionDef { id: "users.view".into(), name: "View Users".into(), description: "View user list".into(), category: PermissionCategory::UserManagement },
        PermissionDef { id: "users.invite".into(), name: "Invite Users".into(), description: "Invite new members".into(), category: PermissionCategory::UserManagement },
        PermissionDef { id: "users.remove".into(), name: "Remove Users".into(), description: "Remove members".into(), category: PermissionCategory::UserManagement },
        PermissionDef { id: "users.manage_roles".into(), name: "Manage Roles".into(), description: "Assign/change roles".into(), category: PermissionCategory::UserManagement },
        PermissionDef { id: "security.view".into(), name: "View Security".into(), description: "View security settings".into(), category: PermissionCategory::Security },
        PermissionDef { id: "security.configure".into(), name: "Configure Security".into(), description: "Edit security settings".into(), category: PermissionCategory::Security },
        PermissionDef { id: "security.2fa".into(), name: "Manage 2FA".into(), description: "Manage two-factor auth".into(), category: PermissionCategory::Security },
        PermissionDef { id: "automation.view".into(), name: "View Automation".into(), description: "View automations".into(), category: PermissionCategory::Automation },
        PermissionDef { id: "automation.create".into(), name: "Create Automation".into(), description: "Create automations".into(), category: PermissionCategory::Automation },
        PermissionDef { id: "automation.run".into(), name: "Run Automation".into(), description: "Execute automations".into(), category: PermissionCategory::Automation },
        PermissionDef { id: "api.access".into(), name: "API Access".into(), description: "Access API endpoints".into(), category: PermissionCategory::Api },
        PermissionDef { id: "api.manage_keys".into(), name: "Manage API Keys".into(), description: "Create/revoke API keys".into(), category: PermissionCategory::Api },
        PermissionDef { id: "plugin.install".into(), name: "Install Plugins".into(), description: "Install plugins".into(), category: PermissionCategory::Plugin },
        PermissionDef { id: "plugin.remove".into(), name: "Remove Plugins".into(), description: "Remove plugins".into(), category: PermissionCategory::Plugin },
        PermissionDef { id: "project.create".into(), name: "Create Projects".into(), description: "Create new projects".into(), category: PermissionCategory::Project },
        PermissionDef { id: "project.edit".into(), name: "Edit Projects".into(), description: "Edit any project".into(), category: PermissionCategory::Project },
        PermissionDef { id: "project.delete".into(), name: "Delete Projects".into(), description: "Delete projects".into(), category: PermissionCategory::Project },
        PermissionDef { id: "team.create".into(), name: "Create Teams".into(), description: "Create teams".into(), category: PermissionCategory::Team },
        PermissionDef { id: "team.manage".into(), name: "Manage Teams".into(), description: "Edit/delete teams".into(), category: PermissionCategory::Team },
        PermissionDef { id: "org.manage".into(), name: "Manage Organization".into(), description: "Manage org settings".into(), category: PermissionCategory::Organization },
        PermissionDef { id: "org.delete".into(), name: "Delete Organization".into(), description: "Delete org".into(), category: PermissionCategory::Organization },
    ]
}

fn default_roles() -> Vec<RoleDefinition> {
    let all_perms: Vec<String> = all_permission_definitions().iter().map(|p| p.id.clone()).collect();
    let now = "2026-07-01T00:00:00.000Z".to_string();

    vec![
        RoleDefinition {
            id: "owner".into(), org_id: String::new(), name: "Owner".into(),
            description: "Full access to all features and settings".into(),
            role_type: RoleType::Owner, permissions: all_perms.clone(),
            is_system_role: true, priority: 100, created_at: now.clone(),
        },
        RoleDefinition {
            id: "administrator".into(), org_id: String::new(), name: "Administrator".into(),
            description: "Administrative access, can manage users and settings".into(),
            role_type: RoleType::Administrator,
            permissions: vec![
                "workspace.view".into(), "workspace.edit".into(),
                "knowledge.view".into(), "knowledge.edit".into(), "knowledge.share".into(), "knowledge.delete".into(),
                "model.view".into(), "model.use".into(), "model.install".into(), "model.configure".into(),
                "marketplace.view".into(), "marketplace.install".into(),
                "extension.install".into(), "extension.remove".into(),
                "agent.install".into(), "agent.configure".into(), "agent.run".into(),
                "billing.view".into(), "users.view".into(), "users.invite".into(), "users.remove".into(),
                "users.manage_roles".into(), "security.view".into(), "security.configure".into(),
                "automation.view".into(), "automation.create".into(), "automation.run".into(),
                "api.access".into(), "project.create".into(), "project.edit".into(), "project.delete".into(),
                "team.create".into(), "team.manage".into(), "org.manage".into(),
            ],
            is_system_role: true, priority: 90, created_at: now.clone(),
        },
        RoleDefinition {
            id: "manager".into(), org_id: String::new(), name: "Manager".into(),
            description: "Can manage projects, teams, and content".into(),
            role_type: RoleType::Manager,
            permissions: vec![
                "workspace.view".into(), "workspace.edit".into(),
                "knowledge.view".into(), "knowledge.edit".into(), "knowledge.share".into(),
                "model.view".into(), "model.use".into(),
                "marketplace.view".into(), "marketplace.install".into(),
                "extension.install".into(),
                "agent.install".into(), "agent.configure".into(), "agent.run".into(),
                "users.view".into(), "users.invite".into(),
                "automation.view".into(), "automation.create".into(), "automation.run".into(),
                "api.access".into(), "project.create".into(), "project.edit".into(),
                "team.create".into(), "team.manage".into(),
            ],
            is_system_role: true, priority: 80, created_at: now.clone(),
        },
        RoleDefinition {
            id: "developer".into(), org_id: String::new(), name: "Developer".into(),
            description: "Can develop and use AI tools and extensions".into(),
            role_type: RoleType::Developer,
            permissions: vec![
                "workspace.view".into(),
                "knowledge.view".into(), "knowledge.edit".into(),
                "model.view".into(), "model.use".into(), "model.install".into(),
                "marketplace.view".into(), "marketplace.install".into(),
                "extension.install".into(),
                "agent.install".into(), "agent.configure".into(), "agent.run".into(),
                "automation.view".into(), "automation.create".into(), "automation.run".into(),
                "api.access".into(), "project.create".into(), "project.edit".into(),
            ],
            is_system_role: true, priority: 70, created_at: now.clone(),
        },
        RoleDefinition {
            id: "operator".into(), org_id: String::new(), name: "Operator".into(),
            description: "Can run automations and agents".into(),
            role_type: RoleType::Operator,
            permissions: vec![
                "workspace.view".into(),
                "knowledge.view".into(),
                "model.view".into(), "model.use".into(),
                "marketplace.view".into(),
                "agent.run".into(),
                "automation.view".into(), "automation.run".into(),
                "api.access".into(),
            ],
            is_system_role: true, priority: 60, created_at: now.clone(),
        },
        RoleDefinition {
            id: "researcher".into(), org_id: String::new(), name: "Researcher".into(),
            description: "Can access knowledge and use AI models for research".into(),
            role_type: RoleType::Researcher,
            permissions: vec![
                "workspace.view".into(),
                "knowledge.view".into(), "knowledge.edit".into(),
                "model.view".into(), "model.use".into(),
                "marketplace.view".into(),
                "agent.run".into(),
            ],
            is_system_role: true, priority: 50, created_at: now.clone(),
        },
        RoleDefinition {
            id: "viewer".into(), org_id: String::new(), name: "Viewer".into(),
            description: "Read-only access to workspace content".into(),
            role_type: RoleType::Viewer,
            permissions: vec![
                "workspace.view".into(),
                "knowledge.view".into(),
                "model.view".into(),
                "marketplace.view".into(),
            ],
            is_system_role: true, priority: 30, created_at: now.clone(),
        },
        RoleDefinition {
            id: "guest".into(), org_id: String::new(), name: "Guest".into(),
            description: "Limited guest access".into(),
            role_type: RoleType::Guest,
            permissions: vec!["workspace.view".into()],
            is_system_role: true, priority: 10, created_at: now.clone(),
        },
    ]
}

pub fn get_role(org_id: &str, role_id: &str) -> Option<RoleDefinition> {
    load_roles(org_id).into_iter().find(|r| r.id == role_id)
}

pub fn get_member_permissions(org_id: &str, user_id: &str) -> Vec<String> {
    let members = crate::org_workspace::load_members(org_id);
    let member = match members.into_iter().find(|m| m.user_id == user_id) {
        Some(m) => m,
        None => return Vec::new(),
    };
    let roles = load_roles(org_id);
    match roles.into_iter().find(|r| r.id == member.role_id) {
        Some(role) => role.permissions,
        None => Vec::new(),
    }
}

pub fn check_permission(org_id: &str, user_id: &str, permission: &str) -> bool {
    get_member_permissions(org_id, user_id).contains(&permission.to_string())
}

pub fn create_custom_role(
    org_id: &str,
    name: &str,
    description: &str,
    permissions: Vec<String>,
) -> Result<RoleDefinition, String> {
    let mut roles = load_roles(org_id);
    let id = format!("custom_{}", roles.len() + 1);
    let role = RoleDefinition {
        id: id.clone(),
        org_id: org_id.to_string(),
        name: name.to_string(),
        description: description.to_string(),
        role_type: RoleType::Custom,
        permissions,
        is_system_role: false,
        priority: 40,
        created_at: "2026-07-01T00:00:00.000Z".to_string(),
    };
    roles.push(role.clone());
    save_roles(org_id, &roles)?;
    Ok(role)
}

pub fn update_role(
    org_id: &str,
    role_id: &str,
    name: Option<&str>,
    permissions: Option<Vec<String>>,
) -> Result<RoleDefinition, String> {
    let mut roles = load_roles(org_id);
    let role = roles
        .iter_mut()
        .find(|r| r.id == role_id)
        .ok_or_else(|| format!("Role not found: {role_id}"))?;
    if role.is_system_role {
        return Err("Cannot modify system roles".to_string());
    }
    if let Some(n) = name {
        role.name = n.to_string();
    }
    if let Some(p) = permissions {
        role.permissions = p;
    }
    let result = role.clone();
    save_roles(org_id, &roles)?;
    Ok(result)
}

pub fn delete_role(org_id: &str, role_id: &str) -> Result<(), String> {
    let mut roles = load_roles(org_id);
    let pos = roles
        .iter()
        .position(|r| r.id == role_id)
        .ok_or_else(|| format!("Role not found: {role_id}"))?;
    if roles[pos].is_system_role {
        return Err("Cannot delete system roles".to_string());
    }
    roles.remove(pos);
    save_roles(org_id, &roles)
}

#[tauri::command]
pub async fn perm_get_all_definitions() -> Result<Vec<PermissionDef>, String> {
    Ok(all_permission_definitions())
}

#[tauri::command]
pub async fn perm_list_roles(org_id: String) -> Result<Vec<RoleDefinition>, String> {
    Ok(load_roles(&org_id))
}

#[tauri::command]
pub async fn perm_get_role(org_id: String, role_id: String) -> Result<Option<RoleDefinition>, String> {
    Ok(get_role(&org_id, &role_id))
}

#[tauri::command]
pub async fn perm_create_custom_role(
    org_id: String,
    name: String,
    description: String,
    permissions: Vec<String>,
) -> Result<RoleDefinition, String> {
    create_custom_role(&org_id, &name, &description, permissions)
}

#[tauri::command]
pub async fn perm_update_role(
    org_id: String,
    role_id: String,
    name: Option<String>,
    permissions: Option<Vec<String>>,
) -> Result<RoleDefinition, String> {
    update_role(&org_id, &role_id, name.as_deref(), permissions)
}

#[tauri::command]
pub async fn perm_delete_role(org_id: String, role_id: String) -> Result<(), String> {
    delete_role(&org_id, &role_id)
}

#[tauri::command]
pub async fn perm_get_member_permissions(
    org_id: String,
    user_id: String,
) -> Result<Vec<String>, String> {
    Ok(get_member_permissions(&org_id, &user_id))
}

#[tauri::command]
pub async fn perm_check(
    org_id: String,
    user_id: String,
    permission: String,
) -> Result<bool, String> {
    Ok(check_permission(&org_id, &user_id, &permission))
}
