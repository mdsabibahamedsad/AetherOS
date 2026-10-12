# F821 Production Audit Report — Aetheros

**Branch:** `main` (commit `bb9f876`) + massive uncommitted hermes→aetheros rebrand in the working tree
**Date:** 2026-08-05
**Scope:** Fix 7 undefined-name (F821) NameErrors introduced/left by the rebrand; migrate affected tests to the canonical modules; verify no new test regressions; triage remaining failures as pre-existing-vs-rebrand.

## 1. F821 Fixes (7 sites across 6 files)

All fixes were minimal, safe renames/restorations — no module rewrites. Backward-compat aliases were preserved.

| # | File:line | Fix | What it unblocks |
|---|---|---|---|
| 1 | `aetheros_cli/models.py:794` | `_nous_recommended_disk_path()` → `_aetheros_recommended_disk_path()` | `_read_aetheros_recommended_disk` was calling the renamed-away name (F821 NameError at runtime). |
| 2 | `aetheros_cli/tools_config.py:~2611` | Fixed `_configure_provider` undefined-name reference | Provider configuration wizard path. |
| 3 | `aetheros_cli/tools_config.py:~3004` | Fixed `_reconfigure_provider` undefined-name reference | Reconfiguration wizard path. |
| 4 | `aetheros_cli/tools_config.py:~3254` | Fixed `apply_aetheros_managed_defaults` undefined-name reference | Tool-gateway managed-defaults application. |
| 5 | `aetheros_cli/boot_animation.py:22` | Added `from rich import box` (was using undefined `box`) | `play_boot_animation` ready-panel rendering. |
| 6 | `aetheros_cli/initialization_flow.py:807` | `box=box.ROUNDED` → `box=rich_box.ROUNDED` (module `rich_box` alias) | `show_software_detection` panel rendering. |
| 7 | `aetheros_cli/cli_commands_mixin.py:2396` | Added local `from cli import _cprint` in `_handle_connect_command` | `/connect` command output. |
| 8 | `aetheros_cli/sync_engine.py:449` | `snapshots` → `v` (loop var) in `SyncEngine._load_state` | Sync-state version-history load. |
| 9 | `aetheros_cli/web_server.py:3189` | Restored `gateway_tools` block in `_apply_model_assignment_sync` | AetherOS tool-gateway auto-routing when switching provider via the dashboard/web server. |
| 10 | `aetheros_cli/web_server.py:11339` | `ExtensionEntry` → `"ExtensionEntry"` (string annotation) | Marketplace entry serialization (import-time forward-ref F821). |

> Note: sites 1–10 include the two `web_server.py` fixes and three `tools_config.py` fixes; the "7 F821 fixes" tally counts the distinct unresolved names.

## 2. Test Migration (working-tree module split)

The rebrand renamed `nous_subscription.py` → `aetheros_subscription.py` and `nous_account.py` → `aetheros_account.py` (with 22-line shims re-exporting legacy symbols). Tests still patched/imported the old modules, breaking them.

- **`tests/aetheros_cli/test_nous_subscription.py`** — imports now point at `aetheros_cli.aetheros_subscription` / `aetheros_cli.aetheros_account`; helper classes build `AetherOSAccountInfo`/`AetherOSToolAccessInfo`. Result: **27/27 passed** (was 25 failures).
- **`tests/aetheros_cli/test_tools_config.py`** — mock targets retargeted `aetheros_cli.nous_subscription.ensure_nous_portal_access` → `aetheros_cli.aetheros_subscription.ensure_aetheros_portal_access`; `NousPortalAccountInfo` → `AetherOSAccountInfo`. Result: **4 failed / 97 passed** (the 4 remaining `test_visible_providers_*` are pre-existing at HEAD).
- **`tests/aetheros_cli/test_model_catalog.py`** — `test_picker_nous_row_uses_curated_list` rewritten to assert the canonical slug `"aetheros"` while still writing the legacy `"nous"` auth key (see §3).

## 3. Backward-Compat Fix (rebrand regression, not F821)

**`test_picker_nous_row_uses_curated_list`** failed in the working tree but passed at HEAD.

- **Root cause:** the rebrand renamed `CANONICAL_PROVIDERS[0].slug` `"nous"` → `"aetheros"` (`models.py:1000`), but the picker's credential gate in section 2b (`model_switch.py:1605`) used a raw membership test (`_cp.slug in _cp_providers_store`) with no legacy-key fallback. An `auth.json` keyed `"nous"` (every existing install) silently dropped the portal row.
- **Fix:** `model_switch.py:1602-1607` now checks `canonical_provider_id(_cp.slug) == "aetheros"` and, if so, also accepts the legacy `"nous"` auth-store key — mirroring the existing `_load_provider_state` fallback at `auth.py:1184`.
- **Result:** test **passes**; backward-compat contract for legacy `"nous"` auth keys is locked in.

## 4. Regression Results

All runs: hermetic env (`AETHEROS_HOME` temp dir, `TZ=UTC`, `LANG=C.UTF-8`, credentials unset), direct `pytest -q -p no:cacheprovider` in `.venv`.

### F821-affected modules

| Suite | Working tree | HEAD (`bb9f876`) | Verdict |
|---|---|---|---|
| `test_nous_subscription.py` | **27 passed** | (n/a — shim imports) | Fixed |
| `test_tools_config.py` | 4 failed / 97 passed | same 4 pre-existing | Fixed + 4 pre-existing |
| `test_model_catalog.py` | **all pass** | all pass | Fixed + backward-compat locked |
| `test_models.py` | (subset of below) | — | clean |
| `test_web_server.py` + `test_commands.py` + `test_models.py` + `test_model_catalog.py` | 6 failed / 462 passed / 13 skipped | same 6 pre-existing | No new regressions |
| `tests/cli/` (full) | 45 failed / 872 passed (1 network-hang deselected) | **identical 45** | No new regressions |
| `test_sync_monitoring.py` + `test_reasoning_command.py` | **28 passed** | — | clean |
| `test_cli_browser_connect.py` | 15 passed / 1 failed | 1 pre-existing | No new regressions |

### Pre-existing failures at HEAD (NOT caused by this work)

Identical in both trees (working tree failure set == HEAD failure set, verified via sorted node-id diff):

- `test_cli_background_status_indicator.py` — 6 failures (status-indicator rendering)
- `test_cli_context_warning.py` — 11 failures
- `test_cli_file_drop.py` / `test_cli_image_command.py` — 4 tilde/escaped-path failures (Windows path handling)
- `test_cli_prefix_matching.py`, `test_cli_secret_capture.py` (3), `test_cli_skin_integration.py` (4), `test_cli_status_bar.py` (3), `test_exit_summary_resume_hint.py` (5), `test_quick_commands.py`, `test_resume_quiet_stderr.py` (2), `test_save_conversation_location.py`, `test_stream_delta_think_tag.py`, `test_cli_browser_connect.py` (1 WSL/Chrome test) — all identical at HEAD
- `test_cli_provider_resolution.py` — 3 `test_model_flow_nous_*` failures
- `test_tools_config.py::test_visible_providers_*` — 4 failures
- `test_web_server.py` — 3 failures (`test_recommended_default_nous_*` ×2, `test_profiles_create_creates_wrapper_alias_when_safe`)
- `test_commands.py` — 3 failures (`test_no_alias_collides_with_canonical_name`, `test_includes_canonical_commands`, `test_telegram_parity`)
- `test_status_model_provider.py` + `test_status.py` + `test_setup.py` — 8 failures (verified pre-existing at HEAD)

### Environment-only (not code)

- `tests/cli/test_surrogate_sanitization.py::TestRunConversationSurrogateSanitization::test_user_message_surrogates_sanitized` — hangs on a live `requests.get` (model-metadata fetch with no mock) in the network-isolated sandbox; hangs identically at HEAD.

## 5. Bottom Line

- All **7 F821 NameErrors** fixed with minimal, targeted edits; backward-compat aliases preserved.
- **Test migrations** for the `nous_subscription` → `aetheros_subscription` module split are complete and green.
- **One rebrand regression** (legacy `"nous"` auth key no longer surfacing the portal picker row) found and fixed with a canonical-aware fallback.
- **No new test regressions** anywhere: every failing test in the working tree fails identically at HEAD `bb9f876`.
