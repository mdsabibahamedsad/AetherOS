# Changelog

## Phase 6 — First-Run Setup Wizard & AI Provider Configuration

### Added

#### New Rust Modules (11)
- `encryptor.rs` — AES-256-GCM local encryption for API keys, tokens, secrets
- `first_run.rs` — First-run detection (bootstrap marker, config, profile, AI settings, wizard marker, workspace)
- `setup_wizard.rs` — 13-step wizard state machine with save/resume/navigation
- `ai_provider.rs` — 10 provider definitions, multi-provider config, model role assignment, local AI detection
- `theme_manager.rs` — Light/Dark/System/HighContrast with CSS variable preview
- `service_connector.rs` — 12 service definitions (GitHub, Google, Telegram, Discord, Slack, etc.)
- `knowledge_importer.rs` — Directory scanning, file type filtering, recursive import
- `workspace_builder.rs` — 7-directory workspace creation with .gitkeep
- `permissions_manager.rs` — 6 permission toggles with defaults
- `profile_generator.rs` — Final config.yaml/profile.yaml/secrets/agent config generation
- `workspace_builder.rs` — Workspace status check

#### New Tauri Commands (39)
- First-run: `check_first_run`, `complete_setup_wizard`, `reset_setup_wizard`
- Wizard: `get_wizard_state`, `start_wizard`, `advance_wizard_step`, `go_back_wizard_step`, `skip_wizard_to`, `save_wizard_*` (10 commands)
- AI Provider: `get_available_providers`, `get_configured_providers`, `save_provider_config`, `delete_provider_config`, `detect_local_ai`, `save_provider_api_key`, `check_provider_api_key`
- Theme: `get_available_themes`, `get_current_theme`, `set_theme`, `preview_theme`
- Services: `get_available_services`, `get_service_connections`, `save_service_connections`, `connect_service`, `disconnect_service`
- Knowledge: `get_supported_file_types`, `scan_directory`, `import_files`
- Workspace: `create_workspace`, `check_workspace_status`
- Permissions: `get_permission_definitions`, `get_current_permissions`, `save_permission_state`
- Profile: `generate_setup_configuration`

#### Dependencies
- `aes-gcm = "0.10"` — AES-256-GCM encryption
- `base64 = "0.22"` — Base64 encoding for encrypted blobs
- `rand = "0.8"` — Cryptographically secure random nonces

### Changed
- `lib.rs` — Added 11 module declarations and 39 Tauri command registrations
- `bootstrap.rs` — Added first-run detection awareness in bootstrap flow
- `events.rs` — Added Phase 6 setup wizard stage documentation
- `Cargo.toml` — Added encryption dependencies

### Security
- API keys encrypted with AES-256-GCM before storage
- Machine-derived encryption key stored in config/.machine-key
- Secrets stored in config/secrets.json (never plaintext)
- Frontend never receives raw API keys after storage
