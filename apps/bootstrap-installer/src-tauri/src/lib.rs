//! Aetheros Setup — Tauri entrypoint.
//!
//! Spawns a single window pointed at the React frontend (apps/bootstrap-installer/src/).
//! All install-time work lives in `bootstrap.rs` and is invoked through the Tauri
//! commands registered at the bottom of `run()`.
//!
//! The Windows-subsystem strip lives on the binary crate (src/main.rs), not
//! here — a crate-level attribute on a lib doesn't propagate to the linker
//! flags of the executable that consumes it.

mod ai_provider;
mod bootstrap;
mod config;
mod disk_manager;
mod download;
mod encryptor;
mod events;
mod extension_updater;
mod extract;
mod first_run;
mod install_modes;
mod installer;
mod knowledge_importer;
mod local_model_detector;
mod logging;
mod model_download;
mod model_health;
mod model_manager;
mod model_recommender;
mod model_registry;
mod model_storage;
mod model_store;
mod offline_bundle;
mod package;
mod package_cache;
mod package_format;
mod package_manager;
mod path_manager;
mod paths;
mod permissions_manager;
mod profile_generator;
mod recovery;
mod release_manager;
mod rollback;
mod rollback_manager;
mod runtime;
mod self_healing;
mod service_connector;
mod setup_wizard;
mod shortcuts;
mod system_check;
mod theme_manager;
mod uninstaller;
mod update;
mod update_channel;
mod update_downloader;
mod update_installer;
mod update_notifier;
mod verification;
mod workspace_builder;

use std::sync::Arc;
use tokio::sync::Mutex;

// Legacy PowerShell script runner — kept for reference; no longer invoked at runtime.
// All bootstrap operations now use the self-contained extractor (bootstrap.rs).
mod powershell;

// Phase 10 — Marketplace & Ecosystem (continued below)
mod marketplace_package;
mod marketplace_catalog;
mod marketplace_store;
mod marketplace_permissions;
mod marketplace_ratings;
mod marketplace_offline;
mod marketplace_developer;
mod extension_store;
mod agent_store;
mod skill_store;
mod mcp_store;
mod workflow_store;
mod theme_store;

// Phase 11 — Team Collaboration, Enterprise & Organization
mod org_workspace;
mod role_permissions;
mod invitations;
mod team_management;
mod collaboration;
mod task_manager;
mod notifications;
mod audit_log;
mod enterprise_policy;
mod admin_dashboard;

// Phase 12 — Universal Communication Hub & Automation Platform
mod connector_manager;
mod connector_definitions;
mod automation_engine;
mod workflow_engine;
mod unified_inbox;
mod service_health;

/// How the installer was invoked. Resolved once from the process args in
/// `run()` and exposed to the frontend via `get_mode` so it can route to the
/// install flow (first-run onboarding) or the update flow (driven by the
/// desktop app handing off via `AetherOS-Setup.exe --update`).
///
/// Bare launch (double-click, first-run) => Install.
/// `--update` (spawned by the desktop's "Update" button) => Update.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum AppMode {
    Install,
    Update,
}

impl AppMode {
    /// Resolve the mode from an argument iterator. Anything containing the
    /// `--update` flag selects Update; otherwise Install. Kept arg-iterator
    /// generic (not reading `std::env` directly) so it's unit-testable.
    pub fn from_args<I, S>(args: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        for a in args {
            if a.as_ref() == "--update" {
                return AppMode::Update;
            }
        }
        AppMode::Install
    }
}

/// Returns true when the args request a forced installer UI (repair/reinstall)
/// via `--reinstall` or `--repair`, which overrides the macOS launcher
/// fast-path so a broken install can be repaired. Arg-iterator generic so it's
/// unit-testable, mirroring `AppMode::from_args`. Independent of mode selection:
/// these flags never flip Install<->Update.
pub fn force_setup_from_args<I, S>(args: I) -> bool
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    args.into_iter()
        .any(|a| a.as_ref() == "--reinstall" || a.as_ref() == "--repair")
}

/// Process-wide install state, shared across Tauri commands.
///
/// The bootstrap is a one-shot, single-tenant process — we only need one
/// of these per window. `Arc<Mutex<...>>` lets command handlers grab it
/// without lifetime gymnastics.
pub struct AppState {
    pub bootstrap: Mutex<Option<bootstrap::BootstrapHandle>>,
    /// How this process was launched (install vs update). Immutable for the
    /// lifetime of the process; read by the `get_mode` command.
    pub mode: AppMode,
    pub config: Mutex<config::InstallConfigState>,
    pub runtime_manager: Mutex<runtime::RuntimeManagerState>,
}

impl AppState {
    fn new(mode: AppMode) -> Self {
        Self {
            bootstrap: Mutex::new(None),
            mode,
            config: Mutex::new(config::InstallConfigState::new()),
            runtime_manager: Mutex::new(runtime::RuntimeManagerState {
                runtimes: Vec::new(),
                running: false,
            }),
        }
    }
}

/// Frontend → Rust: which flow should the UI render?
#[tauri::command]
fn get_mode(state: tauri::State<'_, Arc<AppState>>) -> AppMode {
    state.mode
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Tracing → bootstrap-installer.log under AETHEROS_HOME/logs/ so install
    // failures leave a trail for support. Console output also goes here in
    // debug builds.
    let _guard = paths::init_logging();

    let mode = AppMode::from_args(std::env::args().skip(1));
    // Escape hatch: `--reinstall`/`--repair` forces the installer UI even when
    // AetherOS is already installed, so users can re-run setup to repair a broken
    // install instead of the launcher fast path silently relaunching the app.
    let force_setup = force_setup_from_args(std::env::args().skip(1));
    tracing::info!(?mode, force_setup, "Aetheros installer starting");

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_shell::init())
        .manage(Arc::new(AppState::new(mode)))
        .setup(move |app| {
            use tauri::Manager;
            // Launcher fast path (macOS only): a bare ("Install") launch when
            // AetherOS is already installed should NOT show the installer or
            // rebuild — it should just open the app, so the /Applications
            // "AetherOS" doubles as a normal launcher (first run installs, every
            // later run launches instantly). The window is kept hidden until
            // here via `"visible": false` so this path never flashes a window.
            //
            // Gated to macOS deliberately: on Windows/Linux the installer keeps
            // its existing behavior (Windows users relaunch via the Start
            // Menu/Desktop "AetherOS" shortcuts that install.ps1 creates, and a
            // reliable detached relaunch there needs the DETACHED_PROCESS +
            // startup-grace handling used by launch_aetheros_desktop — out of
            // scope here). So this is a pure no-op on non-macOS.
            //
            // `--reinstall`/`--repair` opts out so a broken install can be
            // repaired by re-running setup instead of launching the bad app.
            if cfg!(target_os = "macos") && mode == AppMode::Install && !force_setup {
                let install_root = paths::aetheros_home().join("aetheros");
                if bootstrap::aetheros_is_installed(&install_root) {
                    match bootstrap::spawn_installed_desktop(&install_root) {
                        Ok(()) => {
                            // Brief grace so the spawned app is registered
                            // before we exit (mirrors launch_aetheros_desktop).
                            std::thread::sleep(std::time::Duration::from_millis(200));
                            tracing::info!(
                                "aetheros already installed — relaunched desktop; exiting installer"
                            );
                            app.handle().exit(0);
                            return Ok(());
                        }
                        Err(err) => {
                            tracing::warn!(
                                ?err,
                                "relaunch of installed desktop failed; showing installer UI"
                            );
                        }
                    }
                }
            }
            // First run / repair install, or Update mode: reveal the UI.
            match app.get_webview_window("main") {
                Some(win) => {
                    if let Err(err) = win.show() {
                        tracing::error!(?err, "failed to show main installer window");
                    }
                }
                None => {
                    tracing::error!("main installer window not found; installer UI will not appear");
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Mode (install vs update)
            get_mode,
            // Bootstrap lifecycle
            bootstrap::start_bootstrap,
            bootstrap::start_package_bootstrap,
            bootstrap::cancel_bootstrap,
            bootstrap::get_bootstrap_status,
            // Package release info
            package::fetch_release_info_command,
            // Update lifecycle
            update::start_update,
            // Hand-off
            bootstrap::launch_aetheros_desktop,
            // Diagnostics
            paths::get_log_path,
            paths::get_aetheros_home,
            paths::open_log_dir,
            // System checks
            system_check::run_system_checks,
            // Install configuration
            config::get_install_config,
            config::set_install_location,
            config::set_components,
            config::validate_install_location,
            // Download (real)
            download::download_file,
            download::get_download_queue,
            download::get_download_progress,
            download::clear_download_queue,
            download::retry_failed_downloads,
            // Verification
            verification::verify_file_checksum,
            verification::verify_file_signature,
            // Logging
            logging::get_log_summary,
            logging::read_log_tail,
            // Rollback
            rollback::get_rollback_status,
            rollback::execute_rollback,
            // Shortcuts
            shortcuts::create_installer_shortcuts,
            // Recovery
            recovery::check_recovery_status,
            recovery::clear_recovery_state,
            recovery::check_existing_install,
            // Runtime Manager
            runtime::detect_runtimes,
            runtime::install_runtimes,
            runtime::get_runtime_status,
            // PATH Manager
            path_manager::check_runtime_paths,
            path_manager::add_to_system_path,
            path_manager::refresh_system_environment,
            // Disk Manager
            disk_manager::check_install_disk_space,
            disk_manager::clean_install_temp_files,
            // Install Modes
            install_modes::get_install_modes,
            // Offline Bundle
            offline_bundle::open_offline_bundle,
            offline_bundle::validate_offline_bundle,
            offline_bundle::extract_from_bundle,
            // Package Cache
            package_cache::get_cache_status,
            package_cache::clear_cache_command,
            // Package Manager
            package_manager::start_package_installation,
            // Uninstaller
            uninstaller::get_uninstall_plan,
            uninstaller::run_uninstall,
            // First Run Detection
            first_run::check_first_run,
            first_run::complete_setup_wizard,
            first_run::reset_setup_wizard,
            // Setup Wizard
            setup_wizard::get_wizard_state,
            setup_wizard::start_wizard,
            setup_wizard::advance_wizard_step,
            setup_wizard::go_back_wizard_step,
            setup_wizard::skip_wizard_to,
            setup_wizard::save_wizard_profile,
            setup_wizard::save_wizard_theme,
            setup_wizard::save_wizard_ai_providers,
            setup_wizard::save_wizard_models,
            setup_wizard::save_wizard_local_ai,
            setup_wizard::save_wizard_api_configs,
            setup_wizard::save_wizard_services,
            setup_wizard::save_wizard_knowledge,
            setup_wizard::save_wizard_permissions,
            setup_wizard::save_wizard_workspace,
            // AI Provider
            ai_provider::get_available_providers,
            ai_provider::get_configured_providers,
            ai_provider::save_provider_config,
            ai_provider::delete_provider_config,
            ai_provider::detect_local_ai,
            ai_provider::save_provider_api_key,
            ai_provider::check_provider_api_key,
            // Theme
            theme_manager::get_available_themes,
            theme_manager::get_current_theme,
            theme_manager::set_theme,
            theme_manager::preview_theme,
            // Services
            service_connector::get_available_services,
            service_connector::get_service_connections,
            service_connector::save_service_connections,
            service_connector::connect_service,
            service_connector::disconnect_service,
            // Knowledge Import
            knowledge_importer::get_supported_file_types,
            knowledge_importer::scan_directory,
            knowledge_importer::import_files,
            // Workspace
            workspace_builder::create_workspace,
            workspace_builder::check_workspace_status,
            // Permissions
            permissions_manager::get_permission_definitions,
            permissions_manager::get_current_permissions,
            permissions_manager::save_permission_state,
            // Profile Generator
            profile_generator::generate_setup_configuration,
            // Model Registry
            model_registry::get_installed_models,
            model_registry::get_model_registry_stats,
            // Model Storage
            model_storage::get_model_storage_config,
            model_storage::set_model_storage_config,
            model_storage::get_model_storage_stats,
            model_storage::clean_model_temp_files,
            // Model Store
            model_store::get_model_catalog,
            model_store::search_model_catalog,
            model_store::filter_model_catalog,
            model_store::get_catalog_providers,
            // Model Download
            model_download::start_model_download,
            model_download::pause_model_download,
            model_download::resume_model_download,
            model_download::retry_model_download,
            model_download::cancel_model_download,
            model_download::get_model_download_queue,
            model_download::set_max_concurrent_downloads,
            model_download::clear_model_download_queue,
            // Model Recommender
            model_recommender::get_hardware_spec,
            model_recommender::get_model_recommendations,
            // Model Health
            model_health::get_model_health_report,
            model_health::check_model_health,
            model_health::repair_model_files,
            model_health::find_orphaned_model_files,
            model_health::clean_orphaned_model_files,
            // Local Model Detector
            local_model_detector::detect_local_ai_engines,
            local_model_detector::scan_engine_models,
            // Model Manager
            model_manager::get_model_manager_state,
            model_manager::install_catalog_model,
            model_manager::uninstall_model,
            model_manager::install_and_download_model,
            model_manager::search_and_install,
            model_manager::get_recommended_for_hardware,
            // Update Channel
            update_channel::get_update_channel,
            update_channel::set_update_channel,
            update_channel::get_available_channels,
            // Release Manager
            release_manager::get_current_version,
            release_manager::check_update,
            release_manager::get_update_sources,
            // Update Downloader
            update_downloader::start_update_download,
            update_downloader::pause_update_download,
            update_downloader::resume_update_download,
            update_downloader::cancel_update_download,
            update_downloader::retry_update_download,
            update_downloader::get_update_download_status,
            update_downloader::set_bandwidth_limit,
            // Update Installer
            update_installer::install_update,
            update_installer::get_install_state,
            update_installer::get_install_history_command,
            // Self Healing
            self_healing::run_self_health_check,
            self_healing::repair_installation,
            // Rollback Manager
            rollback_manager::get_rollback_snapshots,
            rollback_manager::execute_rollback_to,
            rollback_manager::rollback_to_previous_version,
            rollback_manager::create_backup,
            rollback_manager::clean_old_snapshots_command,
            // Extension Updater
            extension_updater::scan_extensions,
            extension_updater::check_extension_updates_command,
            extension_updater::update_extension_command,
            // Update Notifier
            update_notifier::send_update_notification,
            update_notifier::get_notifications,
            update_notifier::dismiss_notification,
            update_notifier::clear_all_notifications,
            // Phase 10 — Marketplace Home & Catalog
            marketplace_catalog::get_marketplace_home,
            marketplace_catalog::search_marketplace,
            marketplace_catalog::get_package_detail,
            marketplace_catalog::get_packages_by_type,
            // Marketplace Store
            marketplace_store::marketplace_install,
            marketplace_store::marketplace_uninstall,
            marketplace_store::marketplace_update,
            marketplace_store::marketplace_check_updates,
            marketplace_store::marketplace_list_installed,
            marketplace_store::marketplace_get_state,
            marketplace_store::marketplace_disable,
            marketplace_store::marketplace_enable,
            // Marketplace Permissions
            marketplace_permissions::marketplace_get_permissions,
            marketplace_permissions::marketplace_grant_permissions,
            marketplace_permissions::marketplace_revoke_permissions,
            marketplace_permissions::marketplace_check_permission,
            // Marketplace Ratings & Reviews
            marketplace_ratings::marketplace_get_ratings,
            marketplace_ratings::marketplace_submit_review,
            // Marketplace Offline Bundles
            marketplace_offline::marketplace_export_offline,
            marketplace_offline::marketplace_import_offline,
            // Marketplace Developer Center
            marketplace_developer::developer_publish,
            marketplace_developer::developer_list_packages,
            marketplace_developer::developer_create_package,
            // Extension Store
            extension_store::extension_install,
            extension_store::extension_uninstall,
            extension_store::extension_get_config,
            extension_store::extension_set_config,
            extension_store::extension_list_installed,
            extension_store::extension_list_statuses,
            extension_store::extension_enable,
            extension_store::extension_disable,
            // Agent Store
            agent_store::agent_install,
            agent_store::agent_uninstall,
            agent_store::agent_get_config,
            agent_store::agent_set_config,
            agent_store::agent_list_installed,
            agent_store::agent_list_statuses,
            agent_store::agent_enable,
            agent_store::agent_disable,
            // Skill Store
            skill_store::skill_install,
            skill_store::skill_uninstall,
            skill_store::skill_get_config,
            skill_store::skill_set_config,
            skill_store::skill_list_installed,
            skill_store::skill_list_statuses,
            skill_store::skill_activate,
            skill_store::skill_deactivate,
            skill_store::skill_enable,
            skill_store::skill_disable,
            // MCP Server Store
            mcp_store::mcp_install,
            mcp_store::mcp_uninstall,
            mcp_store::mcp_get_config,
            mcp_store::mcp_set_config,
            mcp_store::mcp_list_installed,
            mcp_store::mcp_list_statuses,
            mcp_store::mcp_start,
            mcp_store::mcp_stop,
            mcp_store::mcp_enable,
            mcp_store::mcp_disable,
            // Workflow Store
            workflow_store::workflow_install,
            workflow_store::workflow_uninstall,
            workflow_store::workflow_get_config,
            workflow_store::workflow_set_config,
            workflow_store::workflow_list_installed,
            workflow_store::workflow_list_statuses,
            workflow_store::workflow_run,
            workflow_store::workflow_stop,
            workflow_store::workflow_enable,
            workflow_store::workflow_disable,
            // Theme Store
            theme_store::theme_install,
            theme_store::theme_uninstall,
            theme_store::theme_get_config,
            theme_store::theme_set_config,
            theme_store::theme_list_installed,
            theme_store::theme_list_statuses,
            theme_store::theme_apply,
            theme_store::theme_get_active,
            theme_store::theme_enable,
            theme_store::theme_disable,
            // Phase 11 — Organization & Workspace
            org_workspace::org_create,
            org_workspace::org_list,
            org_workspace::org_get,
            org_workspace::org_rename,
            org_workspace::org_delete,
            org_workspace::org_list_members,
            org_workspace::org_add_member,
            org_workspace::org_remove_member,
            org_workspace::org_suspend_member,
            org_workspace::org_reactivate_member,
            org_workspace::org_transfer_ownership,
            org_workspace::org_set_member_role,
            // Role & Permissions
            role_permissions::perm_get_all_definitions,
            role_permissions::perm_list_roles,
            role_permissions::perm_get_role,
            role_permissions::perm_create_custom_role,
            role_permissions::perm_update_role,
            role_permissions::perm_delete_role,
            role_permissions::perm_get_member_permissions,
            role_permissions::perm_check,
            // Invitations
            invitations::inv_create,
            invitations::inv_create_share_link,
            invitations::inv_bulk,
            invitations::inv_list,
            invitations::inv_accept,
            invitations::inv_revoke,
            // Team Management
            team_management::team_create,
            team_management::team_delete,
            team_management::team_list,
            team_management::dept_create,
            team_management::dept_list,
            team_management::project_create,
            team_management::project_list,
            team_management::project_archive,
            team_management::project_add_member,
            team_management::project_activities,
            // Collaboration
            collaboration::collab_share_knowledge,
            collaboration::collab_list_knowledge,
            collaboration::collab_update_presence,
            collaboration::collab_get_presence,
            collaboration::collab_create_session,
            collaboration::collab_join_session,
            collaboration::collab_list_sessions,
            collaboration::collab_activity_feed,
            // Task Management
            task_manager::task_create,
            task_manager::task_update_status,
            task_manager::task_assign,
            task_manager::task_list,
            task_manager::task_list_by_assignee,
            task_manager::task_add_comment,
            task_manager::task_list_comments,
            task_manager::task_delete,
            // Notifications
            notifications::notif_send,
            notifications::notif_list,
            notifications::notif_unread_count,
            notifications::notif_mark_read,
            notifications::notif_mark_all_read,
            notifications::notif_delete,
            // Audit Log
            audit_log::audit_log_event,
            audit_log::audit_log_list,
            audit_log::audit_log_search,
            audit_log::audit_log_summary,
            // Enterprise Policies & Security
            enterprise_policy::policy_create,
            enterprise_policy::policy_list,
            enterprise_policy::policy_toggle,
            enterprise_policy::policy_delete,
            enterprise_policy::policy_check_allows,
            enterprise_policy::security_get_settings,
            enterprise_policy::security_save_settings,
            enterprise_policy::device_register,
            enterprise_policy::device_list,
            enterprise_policy::device_trust,
            enterprise_policy::device_remove,
            // Admin Dashboard
            admin_dashboard::admin_get_dashboard,
            // Phase 12 — Connector Manager
            connector_manager::hub_connector_install,
            connector_manager::hub_connector_remove,
            connector_manager::hub_connector_enable,
            connector_manager::hub_connector_disable,
            connector_manager::hub_connector_update_config,
            connector_manager::hub_connector_set_credentials,
            connector_manager::hub_connector_get,
            connector_manager::hub_connector_list,
            connector_manager::hub_connector_list_by_definition,
            connector_manager::hub_connector_repair,
            connector_manager::hub_connector_start_oauth,
            connector_manager::hub_connector_complete_oauth,
            connector_manager::hub_connector_get_secret,
            connector_manager::hub_connector_record_health,
            connector_manager::hub_connector_list_by_category,
            // Connector Definitions
            connector_definitions::hub_get_connector_definitions,
            connector_definitions::hub_get_connector_definition,
            // Automation Engine
            automation_engine::auto_create_workflow,
            automation_engine::auto_update_workflow,
            automation_engine::auto_delete_workflow,
            automation_engine::auto_list_workflows,
            automation_engine::auto_get_workflow,
            automation_engine::auto_toggle_workflow,
            automation_engine::auto_evaluate_workflow,
            automation_engine::auto_execute_workflow,
            automation_engine::auto_get_logs,
            automation_engine::auto_get_trigger_types,
            automation_engine::auto_get_action_types,
            // Workflow Engine
            workflow_engine::engine_create_route,
            workflow_engine::engine_update_route,
            workflow_engine::engine_delete_route,
            workflow_engine::engine_list_routes,
            workflow_engine::engine_toggle_route,
            workflow_engine::engine_evaluate_route,
            workflow_engine::engine_list_templates,
            // Unified Inbox
            unified_inbox::inbox_add_message,
            unified_inbox::inbox_get_messages,
            unified_inbox::inbox_search,
            unified_inbox::inbox_update_status,
            unified_inbox::inbox_bulk_mark_read,
            unified_inbox::inbox_delete_message,
            unified_inbox::inbox_get_stats,
            unified_inbox::inbox_set_ai_summary,
            unified_inbox::inbox_generate_ai_summary,
            // Service Health
            service_health::health_check,
            service_health::health_dashboard_cmd,
            service_health::health_check_all,
            service_health::health_get_unhealthy,
        ])
        .run(tauri::generate_context!())
        .expect("error while running AetherOS Setup");
}

#[cfg(test)]
mod tests {
    use super::{force_setup_from_args, AppMode};

    #[test]
    fn bare_args_are_install() {
        assert_eq!(AppMode::from_args(Vec::<String>::new()), AppMode::Install);
        assert_eq!(AppMode::from_args(["--foo", "bar"]), AppMode::Install);
    }

    #[test]
    fn update_flag_selects_update() {
        assert_eq!(AppMode::from_args(["--update"]), AppMode::Update);
        assert_eq!(
            AppMode::from_args(["--something", "--update", "--else"]),
            AppMode::Update
        );
    }

    #[test]
    fn reinstall_and_repair_flags_force_setup() {
        assert!(force_setup_from_args(["--reinstall"]));
        assert!(force_setup_from_args(["--repair"]));
        assert!(force_setup_from_args(["--foo", "--repair", "--bar"]));
    }

    #[test]
    fn bare_or_unrelated_args_do_not_force_setup() {
        assert!(!force_setup_from_args(Vec::<String>::new()));
        assert!(!force_setup_from_args(["--foo", "bar"]));
        // --update must not be mistaken for a force-setup flag.
        assert!(!force_setup_from_args(["--update"]));
    }

    #[test]
    fn force_setup_flags_do_not_affect_mode_selection() {
        // The repair flags must never flip Install<->Update.
        assert_eq!(AppMode::from_args(["--reinstall"]), AppMode::Install);
        assert_eq!(AppMode::from_args(["--repair"]), AppMode::Install);
        assert_eq!(
            AppMode::from_args(["--update", "--reinstall"]),
            AppMode::Update
        );
    }
}
