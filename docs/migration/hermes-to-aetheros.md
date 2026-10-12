# Aetheros → AetherOS Migration Guide

> **Last updated:** July 12, 2026
> **Phase:** 4 (Final Cleanup & Production Readiness)

## Overview

The Aetheros project was originally developed under the codename "Hermes".
As part of the public launch, all user-facing branding has been migrated to
**AetherOS**. This document explains what changed, what stayed the same,
and how to upgrade existing installations.

## What Changed

| Area | Before | After |
|------|--------|-------|
| Project name | Hermes | AetherOS |
| CLI command | `aetheros` | `aetheros` |
| Home directory | `~/.aetheros/` | `~/.aetheros/` (legacy: `%LOCALAPPDATA%\\aetheros`) |
| Windows path | `%LOCALAPPDATA%\\aetheros` | `%LOCALAPPDATA%\\aetheros` |
| Docker container | `aetheros` / `aetheros-dashboard` | `aetheros` / `aetheros-dashboard` |
| Docker image | `aetheros/aetheros` | `aetheros/aetheros` |
| GitHub Action | `aetheros-smoke-test` | `aetheros-smoke-test` |
| s6 service | `main-aetheros` | `main-aetheros` |
| Service name | `aetheros-gateway` | `aetheros-gateway` (planned) |
| Launchd label | `ai.aetheros.gateway` | `ai.aetheros.gateway` |

## Compatibility — What Stayed the Same

The following **still work** and are actively supported:

| Legacy Item | Status |
|-------------|--------|
| `HERMES_HOME` env var | ✅ Supported (fallback to `AETHEROS_HOME`) |
| `HERMES_GIT_SHA` build-arg | ✅ Supported (fallback to `AETHEROS_GIT_SHA`) |
| `HERMES_GATEWAY_*` env vars | ✅ Still functional |
| `HERMES_GID` / `HERMES_UID` | ✅ Still functional |
| `HERMES_WEB_DIST` / `HERMES_TUI_DIR` | ✅ Still functional |
| `HERMES_DASHBOARD_*` env vars | ✅ Still functional |
| `HERMES_PREFILL_MESSAGES_FILE` | ✅ Still functional |
| `docker/aetheros-exec-shim.sh` | ✅ Kept as compat wrapper |
| `_HERMES_CORE_TOOLS` constant | ✅ Backward-compat alias for `_AETHEROS_CORE_TOOLS` |
| `_HERMES_VERSION` / `HERMES_VERSION` constants | ✅ Backward-compat aliases |
| `_HERMES_WEBHOOK_SAFE_TOOLS` constant | ✅ Backward-compat alias |
| `_OPTION_ID_TO_HERMES` constant | ✅ Backward-compat alias for `_OPTION_ID_TO_AETHEROS` |
| `agent/transports/aetheros_tools_mcp_server` | ✅ Import compat shim re-exports from new module |

## Deprecation Timeline

| Legacy Feature | Deprecated In | Planned Removal |
|----------------|---------------|-----------------|
| `HERMES_HOME` env var | Phase 1 | v1.0.0 |
| `HERMES_GIT_SHA` build-arg | Phase 2 | v1.0.0 |
| `docker/aetheros-exec-shim.sh` | Phase 2 | v2.0.0 |
| `HERMES_GATEWAY_*` env vars | TBD | TBD |
| `SERVICE_NAME = "aetheros-gateway"` | Phase 2 | v2.0.0 |

## Upgrade Path

### Existing Users

1. **CLI / interactive**: No action needed. The `aetheros` command works in place of `aetheros`. If you have shell aliases or scripts using `aetheros`, update them at your convenience — the old name still works if symlinked.

2. **Docker users**: Pull the latest image. Container names have changed from `aetheros` to `aetheros`. Update any scripts or compose files that reference the old names.

3. **Systemd / launchd users**: If you installed the gateway as a system service, uninstall and reinstall:
   ```bash
   ./scripts/aetheros-gateway uninstall
   ./scripts/aetheros-gateway install
   ```

4. **Environment variables**: All existing `HERMES_*` env vars continue to work. When you're ready to migrate, use the corresponding `AETHEROS_*` names. The `agent.deprecation` module will warn once per process when legacy names are used.

### New Users

Follow the standard install instructions at https://aetheros.aetheros.com — everything uses AetherOS branding.

## Compatibility Policy

1. **Never break existing installations.** All legacy `HERMES_*` env vars, constants, and import paths will continue working for at least two major versions after deprecation.

2. **Prefer AETHEROS_* when both are set.** Code checks the `AETHEROS_*` name first, then falls back to `HERMES_*`. A deprecation warning fires once per process on first legacy fallback.

3. **Remove with a major version bump.** Each deprecated feature lists its planned removal version. When that version arrives, the legacy code path is removed, and only the `AETHEROS_*` path remains.

## Migration Script

For users who want to update their personal configs and scripts:

```bash
# Update shell aliases
alias aetheros='aetheros'  # replace any existing 'aetheros' alias

# Update environment variables in .env
# Replace HERMES_HOME with AETHEROS_HOME
# Replace HERMES_GID with AETHEROS_GID
```

No automated migration script is needed — all legacy paths remain functional.
