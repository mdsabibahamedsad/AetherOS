# First-Run Setup Wizard

## Overview

When AetherOS is launched for the first time, the Setup Wizard automatically
starts. It guides the user through:

1. Welcome & System Info
2. User Profile
3. Theme Selection
4. AI Provider Configuration
5. Model Selection
6. Local AI Setup
7. API Configuration
8. Service Connections
9. Knowledge Import
10. Workspace Setup
11. Permissions
12. Summary & Finish

After completion, the wizard never appears again unless the user resets it.

## Detection

First-run detection checks for:
- Bootstrap complete marker (`.aetheros-bootstrap-complete`)
- Existing configuration (`config/config.yaml`)
- Existing profile (`profiles/default/profile.yaml`)
- Existing AI provider settings (`config/ai-providers.json`)
- Wizard complete marker (`config/.setup-wizard-complete`)
- Existing workspace (`knowledge/`, `projects/`)

If any of these exist, the installer skips onboarding and launches
the desktop directly.

## Architecture

| Module | Role |
|--------|------|
| `first_run.rs` | Detection + marker management |
| `setup_wizard.rs` | State machine (13 steps, save/resume) |
| `encryptor.rs` | AES-256-GCM local encryption for secrets |
| `ai_provider.rs` | Multi-provider config + model selection |
| `theme_manager.rs` | Light/Dark/System/HighContrast |
| `service_connector.rs` | 12 supported services |
| `knowledge_importer.rs` | File scanning + import |
| `workspace_builder.rs` | 7 directory structure |
| `permissions_manager.rs` | 6 permission toggles |
| `profile_generator.rs` | Final config generation |

## Tauri Commands

`check_first_run` — Detect if setup wizard should appear
`start_wizard` / `get_wizard_state` — Initialize/resume wizard
`advance_wizard_step` / `go_back_wizard_step` / `skip_wizard_to` — Navigation
`save_wizard_*` — Save each step's data
`generate_setup_configuration` — Apply all settings, encrypt secrets, mark complete
`complete_setup_wizard` / `reset_setup_wizard` — Lifecycle

For AI providers:
`get_available_providers` — List 10 supported providers
`get_configured_providers` / `save_provider_config` / `delete_provider_config`
`save_provider_api_key` / `check_provider_api_key` — Securely store API keys
`detect_local_ai` — Auto-detect Ollama, LM Studio installations
