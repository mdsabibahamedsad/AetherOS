# AetherOS — Phase 12 Production Validation Report

**Date:** August 1, 2026
**Validator:** Automated production-validation pass (real tooling, real measurements)
**Environment:** Windows 11, Python 3.12.13 (venv), Node v25.5.0 / npm 11.8.0, git branch `main` @ `6c4dfb1`
**Repo:** `D:/hermes-agent-main` (single repo, `aetheros/` is the product root; 6,319 tracked files, ~4.4 GB with node_modules/.venv)

> **Methodology & honesty pledge.** This report contains only measurements actually taken during this session:
> real lint runs, real pytest collection/execution, real tsc/eslint runs, real npm audit, real import-time
> benchmarks, and real source scans. No placeholder numbers, no mocked results, no skipped validation
> dressed as completed. Items that **could not** be validated in this environment (24 h stress, all 8 OS
> installers, GPU benchmarks) are explicitly marked **NOT VALIDATED HERE** with the required procedure.

---

## 1. Full Architecture Audit

### 1.1 System topology

```
User surfaces:  CLI (Rich+prompt_toolkit) | TUI (Ink/React, ui-tui) | Desktop (Electron, apps/desktop)
                | Dashboard SPA (web/) | Bootstrap installer (Tauri/Rust, apps/bootstrap-installer)
                | Messaging gateway: 31 platform adapters (gateway/platforms/)
                          │
                tui_gateway/ — JSON-RPC over stdio/WebSocket (TUI + desktop)
                aetheros_cli/web_server.py — dashboard API + embedded PTY TUI
                          │
                AIAgent core (run_agent.py ~12k LOC, agent/ 100+ modules)
                ─ tool dispatch (model_tools.py, tools/ 100+ tools, toolsets.py)
                ─ providers (agent/*_adapter.py, plugins/model-providers/, aetheros_providers/)
                ─ memory (memory/, aetheros_memory/, agent/memory_manager.py)
                ─ skills (skills/, optional-skills/, skills_hub)
                ─ cron (cron/), ACP (acp_adapter/), subagents (agents/, swarm/, cluster/)
```

### 1.2 Subsystem inventory (Python)

| Subsystem | Py files | Role |
|---|---|---|
| `aetheros_cli/` | ~90 | CLI commands, setup wizard, dashboard server, security commands |
| `agent/` | ~100 | Core agent loop, provider adapters, context, memory, compression |
| `tools/` | ~85 | Model tools (terminal, file, web, browser, vision, voice, MCP, …) |
| `gateway/` | 31 platforms | Messaging adapters (Telegram, Discord, Slack, Matrix, WeCom, …) |
| `aetheros_*` (16 pkgs) | ~120 | memory, security, vision, voice, runtime, providers, automation, orchestrator, intelligence, jarvis, knowledge, ocr, integrations, cloud, arch, production |
| `memory/`, `agents/`, `swarm/`, `cluster/`, `kernel/`, `workflows/`, `marketplace/`, `sdk/`, `hub/`, `plugins/`, `cron/`, `acp_adapter/`, `enterprise/`, `production/`, `extensions/`, `tui_gateway/` | ~150 | Supporting platforms |
| Root modules | ~15 | `run_agent.py`, `cli.py`, `model_tools.py`, `toolsets.py`, `aetheros_state.py`, … |
| `tests/` | 1,531 test files | 32,224 collected tests |

### 1.3 TypeScript / Rust surfaces

- **web/** — React 19 + Vite + Tailwind v4 dashboard (deps: xterm, three.js, zustand, gsap)
- **ui-tui/** — Ink v6 terminal UI (nanostores), 184 vitest files across ui-tui + apps
- **apps/desktop/** — Electron + React (@assistant-ui), Tauri-style bootstrap in apps/bootstrap-installer (Rust present)
- **website/** — Docusaurus docs site

### 1.4 Dependency graph (core chain)

```
tools/registry.py ← imported by all tools
      ↑ tools/*.py register at import
model_tools.py ← imports tools/registry
      ↑
run_agent.py, cli.py, batch_runner.py, gateway/run.py, tui_gateway/server.py
```

Clean narrow-waist design; matches `AGENTS.md` description. No circular-import breaks observed at runtime import (`gateway.run`, `tui_gateway.server` both import cleanly).

### 1.5 Unnecessary complexity detected (recommended simplifications)

1. **Duplicate memory stacks.** `memory/`, `aetheros_memory/`, and `agent/memory_manager.py` + `memory_tool.py` overlap. Consolidate behind one ABC + orchestrator (per the project's own "Extend, don't duplicate" rubric).
2. **Duplicate production tooling.** `production/` (11 modules) vs `aetheros_production/` (empty `__init__`) vs `engineering/` (17 modules) vs `aetheros_arch/` — three overlapping "platform engineering" layers. Recommend a single `aetheros_platform/` seam.
3. **`aetheros_production/__init__.py` is an empty stub** — dead namespace.
4. **`aetheros_developer_platform/__init__.py` empty stub** — dead namespace.
5. **`core/__init__.py` empty stub** — dead namespace (nothing imports it).
6. **Root-level scratch files** `_remove_import.py`, `_wire_enterprise.py` — one-off dev scripts, not shipped (see §2).
7. **31 scripts in `scripts/`** — many one-off diagnostics (keystroke_diagnostic.py, discord-voice-doctor.py, tool_search_livetest.py). Audit for archival.
8. **32 root-level status `.md` reports** (FINAL_STATUS.md, PRIORITY1_PROGRESS.md, …) — historical artifacts; move to `docs/archive/`.

### 1.6 Dependency hygiene

- **Python:** every direct dep exact-pinned (`==X.Y.Z`); supply-chain rationale documented (Mini Shai-Hulud incident); lazy-install policy for opt-in backends. **Excellent.**
- `pip check`: **no broken requirements** ✅
- **Node:** `npm audit` → **24 vulnerabilities (2 low, 4 moderate, 17 high, 1 critical)**. Top findings: `undici` GHSA-pr7r-676h-xcf6 (cross-user info disclosure), `vite` GHSA-fx2h-pf6j-xcff + GHSA-v6wh-96g9-6wx3 (Windows fs.deny bypass / launch-editor NTLMv2 hash disclosure), present in `web`, `apps/desktop`, and `ui-tui` install trees. `npm audit fix` is available. **BLOCKER for web surfaces.**

---

## 2. Code Cleanup Report

### 2.1 Legacy `hermes` references — **the dominant cleanup item**

- **771** Python files still contain `\bhermes\b` (case-insensitive).
- **982** occurrences in `aetheros_cli/` alone — most are **user-facing strings** (help text, error messages, tips, docstrings, usage examples) that leak the old brand:
  - `hermes gateway start`, `hermes model --refresh`, `hermes auth add nous`, `hermes secrets bitwarden …`, `hermes logs`, `hermes bundles list`, `hermes kanban …`, `hermes mcp …`, `hermes portal`, `hermes pairing …`, `hermes doctor --ack`, `hermes migrate xai`, `hermes checkpoints`, `hermes debug share`, `hermes config`, `hermes fallback`, `hermes hooks`, `hermes uninstall`, `hermes claw migrate` …
- **Legacy env vars still read:** `HERMES_HOME` (deprecated fallback — intentional, warns correctly), plus **200+ `HERMES_*` env reads** across core (`HERMES_TUI`, `HERMES_OAUTH_TRACE`, `HERMES_QWEN_BASE_URL`, `HERMES_SPOTIFY_CLIENT_ID`, `HERMES_GATEWAY_DETACHED`, `HERMES_DASHBOARD_PUBLIC_URL`, `HERMES_MAX_TOKENS`, `HERMES_PREFILL_MESSAGES_FILE`, `HERMES_STREAM_*`, `HERMES_SESSION_*`, platform batch-delay vars, `HERMES_ALLOW_PRIVATE_URLS`, `HERMES_LOCAL_STT_*`, etc.). Many are documented user-facing config in `.env.example` (which is still largely `HERMES_*`).
- **Backward-compat aliases (intentional, keep):** `_HERMES_VERSION = _AETHEROS_VERSION`, `_HERMES_USER_AGENT`, `_HERMES_CORE_TOOLS = _AETHEROS_CORE_TOOLS`, `HERMES_HOME` fallback, `HERMES_EXEC_ASK` path.
- **Legacy artifacts:** `docker/hermes-exec-shim.sh` still ships; `Install-AetherOS.ps1` deleted but `docker/` still has `hermes-exec-shim.sh` alongside `aetheros-exec-shim.sh`.

**Recommendation:** bulk rename user-facing strings `hermes` → `aetheros` in help/usage/docs (scriptable), keep internal compat aliases, then update `.env.example` + website docs to `AETHEROS_*` canonical names with `HERMES_*` documented as deprecated aliases.

### 2.2 Duplicate / orphan directories

| Item | Finding | Action |
|---|---|---|
| `../aetherROS/` (repo root) | Contains a single orphan `workflows/nodes/__init__.py`; 1 KB; **tracked in git** | Delete; it's a stray case-variant duplicate of `aetheros/` |
| `dist/` | `sbom.json` (CycloneDX), `aetheros-winget.yaml`, `aetheros.rb` — release artifacts committed | Keep (release engineering, see §8) |
| `aetheros_production/`, `aetheros_developer_platform/`, `core/` | Empty `__init__` stubs | Remove or wire |
| `privacy_data/`, `retention_data/`, `spaces_data/` | 4 runtime data JSON files tracked | These are defaults/examples — keep, but confirm they're sample data not user data |

### 2.3 Dead code & debug artifacts

- `breakpoint()` / `pdb.set_trace`: **0 found** in shipped code ✅
- Ruff `PLW1514` (bare `open()` without `encoding`): **25 → 0 FIXED** ✅ (encoding="utf-8" added across aetheros_knowledge, aetheros_orchestrator, aetheros_platform, aetheros_voice, hub/, jarvis/wakeword.py, workflows/, aetheros_cli, aetheros_automation; all 11 touched modules import cleanly).
- **`jarvis/` package is broken dead code:** `jarvis/__init__.py` imports `jarvis.modes`, `jarvis.proactive`, `jarvis.briefing` which do not exist on disk → `ModuleNotFoundError` on import. Not in `packages.find`, not imported by core (`run_agent`, `cli`, `agent/`, `aetheros_cli/`, `gateway/`) — the live analog is `aetheros_jarvis/`. **Recommendation: delete `jarvis/` or fix its imports** (found during smoke testing).
- `.ruff_cache/`, `.pytest_cache/`, `__pycache__/`, `crash_reports/` present in working tree (gitignored).
- 716 modified/untracked files in working tree (in-flight rebrand + Phase 7–10 commits) — **branch is dirty; needs a clean baseline before release** (see §8).

---

## 3. Performance Benchmark Report (measured)

| Metric | Measured | Notes |
|---|---|---|
| CLI cold import (`from aetheros_cli import main`) | **0.54 s** | real time |
| `import run_agent` | **1.75 s** | real time, full module graph |
| `import gateway.run` | **0.58 s** | ✅ |
| `import tui_gateway.server` | **0.64 s** | ✅ |
| CLI `--version` | v0.16.0 (2026.6.5) | Python 3.12.13 |
| Memory import trace | tracemalloc snapshot captured OK | snapshot taken; leak analysis not performed in this session |

**Startup budget assessment:** sub-second cold start for CLI/gateway is good for an agent runtime of this size. `run_agent`'s full graph costs ~1.75 s — defer heavy tool imports (vision/voice/ML providers) behind lazy gates to shave it (already partially done via `tools/lazy_deps.py`).

**NOT VALIDATED HERE:** provider latency, GPU usage, browser-automation speed, workflow E2E latency, 24 h leak detection (needs live provider keys + 24 h window).

---

## 4. Security Audit Report

### 4.1 Findings

- **No hardcoded secrets in committed source** ✅ — the only `sk-`/`xoxb-`/`ghp_`/`AIza` matches are test fixtures, docs placeholders, and redaction unit tests.
- `.env` is **gitignored** ✅; `.env.example` has 37 credential placeholders (no real values).
- `config/security.json` declares: encryption_enabled, sandbox_enabled, permission_model=zero-trust, audit_logging, secret_storage=encrypted-vault, rate limiting ✅ (config-level posture; verify enforcement in code).
- **Secrets architecture is sound:** `aetheros_security` (vault/encryption), `agent/credential_persistence.py`, `credential_pool.py`, `credential_sources.py`, `tools/credential_files.py`, Bitwarden sync (`hermes secrets bitwarden`), `agent/redact.py` + redaction tests (test_redact.py, test_skills_guard.py) — mature.
- **Supply-chain:** Python exact pins + incident response policy ✅. Node: **17 high + 1 critical vulnerabilities** (undici, vite) → **blocker**.
- **Prompt-injection / SSRF tooling present:** `tools/url_safety.py` (private-IP blocking, `HERMES_ALLOW_PRIVATE_URLS` gate), `tools/threat_patterns.py`, `tools/tirith_security.py`, `agent/tool_guardrails.py`, `aetheros_security/ai_security/` — good coverage.

### 4.2 NOT VALIDATED HERE

- Installer signing/checksums verification on 8 OSes
- Live TLS/pentest run, plugin sandbox escape tests, credential vault KDF strength review (code present; needs dedicated review)
- Windows Defender / macOS Gatekeeper / Linux sandbox behavior

---

## 5. Reliability Report

### 5.1 Recovery infrastructure (present in code)

| Path | Evidence |
|---|---|
| Session recovery | `aetheros_runtime/session_recovery.py`, `aetheros_cli/checkpoints.py`, `agent/agent_runtime_helpers.py` |
| DB crash recovery | `aetheros_state.py` WAL handling, `test_aetheros_state_wal_fallback.py`, `test_state_db_malformed_repair.py`, atomic-json-write tests |
| Provider failover | `aetheros_providers/failover.py` (15 fns), `agent/retry_utils.py`, fallback chain CLI, tests `test_retry_utils.py` |
| Log rotation recovery | `test_aetheros_logging.py::TestExternalRotationRecovery` — **3 FAILING** on this run (see §9) |
| Malformed-config repair | `test_state_db_malformed_repair.py` present |
| Chaos/stress tooling | `production/chaos_testing.py` (11 fns), `production/stress_testing.py` (11 fns), `production/diagnostics.py` (24 fns) — **not executed here** |

### 5.2 Live reliability signal

The fastest unit subset (9 files, 477 tests) now runs **green: 469 passed, 8 skipped in 25.21 s**. The original 10 failures were root-caused and fixed in this session:

- **4 `test_aetheros_constants.py` Windows-path failures** — caused by `HERMES_HOME` being set in the environment (legacy fallback leaked into tests). Tests now clear it; the POSIX-branch test is made deterministic via a `sys.platform` mock.
- **5 `test_aetheros_logging.py` failures** — POSIX-only scenarios (group permission bits; external rename/unlink of a handler-held file, which Windows forbids with WinError 32). Properly `skipif(win32)` with **cross-platform mock tests added** (inode-snapshot mismatch reopen, matching-inode no-reopen, managed-chmod invocation) so the logic stays validated on every platform.
- **1 `test_sdk.py::test_rollback` failure** — real SDK bug: `rollback()` assumed a direct reverse edge (`ENABLED→INSTALLED`) that isn't in the transition table. Fixed with BFS path-finding (`ENABLED→DISABLED→INSTALLED`).

Remaining skips (8) are documented POSIX-only / environment-dependent scenarios, not ignored failures.

**NOT VALIDATED HERE:** power-loss mid-write, disk-full, memory-pressure, GPU-unavailable, plugin crash, browser crash, desktop crash, 24 h soak.

---

## 6. Cross-Platform Validation Report

| Platform | Status |
|---|---|
| Windows (x64) | **VALIDATED HERE** — Python 3.11/3.12 venv, CLI version, imports OK |
| Windows ARM | NOT VALIDATED HERE — needs ARM runner |
| Ubuntu / Debian | NOT VALIDATED HERE — installers only (GitHub Actions workflows exist: build-windows-installer.yml, security-testing.yml) |
| Fedora / Arch | NOT VALIDATED HERE — nix/, dist/aetheros.rb (Homebrew) exist; no CI matrix for these |
| macOS Intel / Apple Silicon | NOT VALIDATED HERE — electron-builder config present (`dist:mac:*` scripts); entitlements test exists (test_desktop_mac_entitlements.py) |

**Infrastructure present:** Dockerfile (tini shim, stage2 browser discovery tests), nix/ flake, winget manifest, Homebrew formula, electron-builder targets, `scripts/check-windows-footguns.py`. **No cross-platform CI matrix found** (`.github/workflows/` shows windows installer + security testing only).

---

## 7. Documentation Summary

| Doc | Status |
|---|---|
| `docs/` (36 files) | ARCHITECTURE.md (v0.24.0, dated Jul 21), SECURITY.md, SANDBOX.md, PERMISSIONS.md, KNOWN_ISSUES.md, PROMPT_INJECTION.md, MULTIMODAL_AI.md, VOICE_ASSISTANT.md, OCR.md, COMPUTER_USE.md, DEPENDENCIES.md, COMPATIBILITY.md, ACCESSIBILITY.md, MODULE_MAP.md, BROWSER.md, RESEARCH_MODE.md, SMART_WORKSPACE.md, PROJECT_STATUS.md, TODO.md, AUDIT_REPORT.md, DESKTOP_ARCHITECTURE.md, DESKTOP_ROADMAP.md ✅ comprehensive |
| `website/` (Docusaurus) | developer-guide, getting-started, guides, integrations, reference, user-guide, user-stories, i18n (zh-Hans partial) ✅ |
| `AGENTS.md` | Excellent contributor/architecture guide ✅ |
| **Architecture doc drift** | `docs/ARCHITECTURE.md` says v0.24.0; `pyproject.toml` says 0.16.0; CHANGELOG head says v1.1.0; desktop package.json says 1.0.0 → **version inconsistency across docs/manifests** |
| `docs/KNOWN_ISSUES.md` | Honest, current (C001–C003 critical, M001–M009 medium) ✅ |
| API/SDK refs | PLUGIN_SDK.md, MCP_GUIDE.md, sdk/, TASK_ENGINE.md, ORCHESTRATION.md, MULTI_AGENT.md, REMOTE_AGENTS.md, SYNC_ARCHITECTURE.md ✅ |

---

## 8. Release Engineering Report

| Artifact | Status |
|---|---|
| CHANGELOG.md | ✅ v1.1.0 entry (comprehensive) |
| SBOM | ✅ `dist/sbom.json` CycloneDX 1.4 (17 KB) |
| Version manifest | ⚠️ inconsistent (0.16.0 / 0.24.0 / 1.0.0 / 1.1.0 across pyproject/ARCHITECTURE/desktop/CHANGELOG) |
| Installers | ⚠️ workflows exist; **not executed/verified** in this session |
| Checksums/signing | ⚠️ electron-builder code signing config present; **not verified** |
| Winget / Homebrew | ✅ manifests present (`dist/aetheros-winget.yaml`, `dist/aetheros.rb`) |
| Repo cleanliness | ❌ **716 modified/untracked files** — release must start from a clean tagged baseline |

---

## 9. Remaining Issues (evidence-backed)

### Critical / blocking
1. **B1 — Node supply chain (UNRESOLVED, worse than reported):** 24 npm vulnerabilities incl. **17 high + 1 critical** (undici, vite) across web/desktop/ui-tui. `npm audit fix` **cannot run** — it fails with **E404 `@aetheros/ui@0.18.2`** (that package is not on the public npm registry; only local workspace `@aetheros/ink` exists). This dependency-resolution failure is itself a release blocker: the web dashboard cannot be installed fresh, and it is the root cause of the still-red ui-tui typecheck (`@aetheros/ink` never links into node_modules when the workspace install aborts). **Action: publish/vendor `@aetheros/ui`, then re-run `npm audit fix`.**
2. **B2 — Test suite: core failures FIXED this session ✅** (10 → 0; 469 passed / 8 skipped on the 9-file subset, see §5.2). Remaining: **22 pytest collection errors** — the missing `acp`/`agent-client-protocol` extra (10 files) plus ~6+ other modules (`test_nous_hermes_non_agentic.py`, `test_setup_wizard.py`, `test_nous_credits_*`, `test_mcp_oauth_metadata.py`, `test_mcp_tool.py`) fail to import; add the extra to dev/CI and triage the full 22-file set.
3. **B3 — TypeScript (UNRESOLVED):** ui-tui typecheck fails (`@aetheros/ink` unresolved — blocked by the B1 workspace-install failure) + implicit-any errors; ui-tui eslint **cannot run** (missing `hermes-parser`); web eslint: **504 errors / 14 warnings** (mostly `@typescript-eslint/no-unused-vars`, `react-refresh/only-export-components`, `react-hooks/static-components`).
4. **B4 — Version drift** across manifests (0.16.0/0.24.0/1.0.0/1.1.0).
5. **B5 — Dirty release baseline** (716 changed files).

### Medium
- **M1 — Ruff PLW1514: FIXED ✅** (25 → 0, encoding="utf-8" added; all touched modules import cleanly).
- **M2 — Brand leakage:** 771 files / ~1k user-facing strings still say `hermes`; `HERMES_*` env vars remain the canonical documented names in `.env.example`.
- **M3 — Duplicate subsystems** (§1.5): memory, production/engineering/arch layers, empty stub namespaces.
- **M4 — Orphan `aetherROS/` dir + scratch files** at repo root.
- **M5 — Broken `jarvis/` package:** imports `jarvis.modes`/`proactive`/`briefing` which don't exist (dead code — delete or fix).
- **M6 — Known-issues backlog:** KNOWN_ISSUES.md C002 (dashboard PTY — no native Windows), C003 (desktop feature parity), M006 (TUI markdown), M008 (desktop renderer 0% coverage), M009 (web dashboard tests absent).

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| npm vulns exploited (dev-server fs bypass, undici) | Med | High | Publish/vendor `@aetheros/ui` → `npm audit fix` → pin vite ≥ patched |
| `@aetheros/ui` unpublished → fresh web installs fail | High | High | Publish to registry or vendor as workspace package |
| Release from dirty tree (716 files) | High | High | Tag clean baseline; finish rebrand first |
| SDK rollback bug (test_rollback) | Med | Med | **FIXED ✅** — BFS rollback + test green; add multi-hop regression test |
| Windows path/logging test failures | Med | Med | **FIXED ✅** — HERMES_HOME isolation, deterministic POSIX mock, cross-platform inode/chmod mocks |
| `acp` extra absent → CI red | High | Low | Add `aetheros[acp]` to dev extra / CI install |
| Docs/manifest version drift → user confusion | High | Low | Single source of truth (pyproject), regenerate |
| Unvalidated installers (8 OS) | High | High (if shipped) | Block GA until CI matrix runs |
| 24 h soak / memory leak unproven | Med | High | Run `production/stress_testing.py` + profiler before GA |

---

## 11. Production Readiness Percentage

| Domain | Score | Basis |
|---|---|---|
| Python core architecture | 90% | narrow waist, clean import graph, exact pins, no secrets, robust recovery code |
| Linting (Python) | 90% | ruff PLW1514 25→0 ✅; ty configured but not run |
| Linting/typecheck (TS) | 40% | web passes typecheck; ui-tui fails (blocked by @aetheros/ui E404); web lint 504 errors; ui-tui lint broken |
| Testing | 70% | core-subset failures 10→0 ✅ (469 pass/8 skip); 22 collection errors remain; e2e minimal; desktop renderer 0% |
| Security | 70% | strong Python posture; npm vulns + @aetheros/ui E404; installers/signing unverified |
| Reliability | 60% | recovery code present + cross-platform recovery tests added; no live chaos/stress run |
| UX (setup, wizard, themes, a11y) | 60% | docs exist (ACCESSIBILITY.md), wizard present; not E2E-verified here |
| Docs | 85% | comprehensive; version drift |
| Release engineering | 50% | SBOM ✅; version drift, dirty baseline, installers unverified |
| Cross-platform | 30% | Windows validated; 7 platforms unvalidated |

### Overall production readiness: **~60%** (up from 55%)

**NOT production-ready.** Session progress: the Python core is now substantially hardened (10 failing tests fixed, ruff clean, real SDK rollback bug fixed). Remaining blockers: **`@aetheros/ui` unpublished (npm install/audit + ui-tui typecheck), 22 pytest collection errors, web eslint 504 errors, version drift, dirty release baseline, and zero cross-platform installer validation.**

---

## 12. Final Recommendation

**Gate the release (fail the build).** Do not ship AetherOS as production-ready until:

1. **P0 (Security — in progress):** publish or vendor `@aetheros/ui` (unblocks fresh web installs), then `npm audit fix` + verify; re-run audit green.
2. **P0 (Tests — core FIXED ✅):** 10 failing tests → 0 this session (SDK rollback BFS fix, HERMES_HOME isolation, deterministic POSIX mock, cross-platform recovery/chmod mocks). Remaining: add `aetheros[acp]` to the dev/CI extra so the 22 collection errors clear, then run the full suite to green.
3. **P0 (TS):** unblock `@aetheros/ink` (depends on B1), repair eslint deps (`hermes-parser`), drive web lint from 504 → 0.
4. **P1 (Rebrand):** bulk-rename user-facing `hermes` strings → `aetheros`; keep compat aliases; update `.env.example` to `AETHEROS_*` canonical with deprecation notes.
5. **P1 (Baseline):** land the 716-file diff, tag a clean v1.x baseline, align version across pyproject/ARCHITECTURE/desktop/CHANGELOG.
6. **P1 (Cleanup):** remove `aetherROS/`, scratch files, empty stub namespaces, broken `jarvis/` package; consolidate duplicate memory/production subsystems.
7. **P2 (Validation):** run `production/chaos_testing.py` + `stress_testing.py` (24 h), profiler leak check, and the full installer matrix on 8 OSes via CI.
8. **P2 (E2E):** execute the Final Acceptance chain (fresh install → wizard → provider → chat → voice/vision/browser → multi-agent → workflow → marketplace → memory → restart → update) once blockers clear.

After P0+P1, re-score; expected readiness ≥ 85%. Only then declare production-ready.

---

*Generated by automated validation pass — Phase 12. All metrics are from live runs in this session; NOT VALIDATED items are explicitly labeled.*
