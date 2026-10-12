# AetherOS — Task List

**Generated:** July 14, 2026

---

## PRIORITY 1 — Critical (Must Fix Before Next Release)

- [ ] **C1: Complete dashboard auth confidential OAuth** — `plugins/dashboard_auth/self_hosted/__init__.py` has 3 `TODO(confidential-client)` markers (lines 36, 248, 268). Required for production self-hosted deployments.
- [ ] **C2: Desktop app onboarding polish** — First-run wizard should guide through provider selection → API key setup → model selection → first chat in a seamless flow.
- [ ] **C3: Desktop chat PTY for Windows** — `web/src/pages/ChatPage.tsx` embedded TUI only works on POSIX/WSL. Native Windows PTY bridge needed.

---

## PRIORITY 2 — Important (Next Sprint)

- [ ] **M1: Refactor `run_agent.py`** (~12K LOC) into focused modules. Extract conversation loop, agent initialization, tool dispatch into separate files.
- [ ] **M2: Refactor `cli.py`** (~11K LOC) into focused modules. Continue the mixin extraction pattern already started.
- [ ] **M3: Per-board dispatcher owner tracking** — `gateway/kanban_watchers.py` TODO for dispatcher_owner tracking.
- [ ] **M4: Yuanbao API chat metadata** — `gateway/platforms/yuanbao.py` TODO for real chat name/member-count.
- [ ] **M5: TUI markdown-to-ANSI soft-wrapping** — `ui-tui/src/components/markdown.tsx` TODO for inline markdown preservation.
- [ ] **M6: TUI Ink screen cell wrapping** — `ui-tui/packages/hermes-ink/src/ink/screen.ts` TODO for soft-wrapping SpacerHead cells.
- [x] **M7: Dashboard analytics page** — Built full analytics chart UI (`AgentAnalyticsPage.tsx`) with token/cost trends, top tools/models, configurable date ranges.

---

## PRIORITY 3 — Enhancement (Backlog)

- [ ] **E1: Desktop frontend tests** — Add Vitest + Playwright E2E tests for desktop renderer.
- [ ] **E2: Web dashboard tests** — Add component tests for 20+ dashboard pages.
- [ ] **E3: Plugin marketplace** — Create centralized registry/index for community plugins.
- [ ] **E4: VS Code extension** — Package ACP adapter as published VS Code extension.
- [ ] **E5: More CLI/TUI skins** — Add community-contributed themes.
- [ ] **E6: Performance benchmarks** — Create benchmark suite for agent loop latency.
- [ ] **E7: Desktop system tray** — Minimize to tray with quick access menu.
- [ ] **E8: Desktop global shortcut** — Configurable hotkey to summon app.
- [ ] **E9: Mobile companion app** — iOS/Android frontend.

---

## Phase 16 — Advanced Agent Intelligence & Autonomous Task Orchestration

- [x] **O1: Task Orchestrator Core** — Created TaskOrchestrator with full lifecycle management, plan creation, agent selection, sub-agent management, agent messaging, approval system
- [x] **O2: Execution Engine** — Created ExecutionEngine for task execution with tool dispatch
- [x] **O3: Checkpoint System** — Created CheckpointManager with save/load/list/delete operations
- [x] **O4: Model Router** — Created ModelRouter with 8 models, role-based preferences, fallback chains
- [x] **O5: Multi-Agent System** — Created AgentCollaborationManager, AgentMessaging, SubAgentManager
- [x] **O6: Specialized Agents** — Added CreativeAgent, DataAgent, CommunicationAgent, ReviewAgent (4 new roles)
- [x] **O7: Execution Graph** — Level-based execution with sequential/parallel/conditional/dependent/retry/fallback/human-approval modes
- [x] **O8: Failure Recovery** — RetryHandler (exponential backoff, failure classification), FallbackHandler (fallback chains)
- [x] **O9: Result Validation** — ResultValidator with completeness, relevance, file existence checks
- [x] **O10: Task Templates** — 7 built-in templates (Research Report, Software Development, Data Analysis, Content Creation, Email Campaign, Business Automation, Personal Assistant)
- [x] **O11: Natural Language Automation** — NLPAutomationEngine parsing requests into plans with schedule detection
- [x] **O12: Desktop Orchestrator UI** — 6 views (Main Workspace, Plan View, Execution Graph, Agent Activity, Checkpoints, Approvals), nanostore, route registration
- [x] **O13: Documentation** — ORCHESTRATION.md, TASK_ENGINE.md, MULTI_AGENT.md, EXECUTION_GRAPH.md
- [x] **O14: Tests** — 50+ tests across all new subsystems

## PRIORITY 4 — Technical Debt

- [ ] **T1: Remove `HERMES_*` env var references** — Rename remaining `HERMES_*` env vars to `AETHEROS_*` for complete rebrand consistency.
- [ ] **T2: Remove `hermes` CLI entry point** if it still exists as legacy fallback.
- [ ] **T3: Audit `~/.aetheros` hardcoded paths** — Ensure all paths use `get_aetheros_home()` for profile safety.
- [ ] **T4: Reduce gateway platform adapter LOC** — Some adapters (yuanbao.py at 4.8K LOC) are oversized.

---

## TODO Comments in Code

| File | Line | Note |
|------|------|------|
| `plugins/dashboard_auth/self_hosted/__init__.py` | 36, 248, 268 | `TODO(confidential-client)` |
| `gateway/kanban_watchers.py` | - | `# TODO` per-board dispatcher |
| `gateway/platforms/yuanbao.py` | - | `# TODO` chat metadata |
| `ui-tui/src/components/markdown.tsx` | - | `# TODO` ANSI wrapping |
| `ui-tui/packages/hermes-ink/src/ink/screen.ts` | - | `# TODO` cell wrapping |
| `optional-skills/research/darwinian-evolver/templates/` | - | `# TODO` template placeholders |

---

## Recently Fixed / No Longer Applicable

## Phase 14 — Advanced Security, Sandbox & Permission System

- [x] **S1: Security Store** — Created `src/store/security.ts` with comprehensive nanostore atoms for all security state, 34 permission definitions, 20+ action functions
- [x] **S2: Security Center Main View** — Created 8-tab layout (Overview, Permissions, Approvals, Sandbox, Audit Log, Alerts, Secrets, Privacy)
- [x] **S3: Overview Dashboard** — Security status, active permissions, blocked actions, recent approvals, running sandboxes, active alerts, pending approvals
- [x] **S4: Permission Manager** — Per-agent/plugin/MCP/automation permissions with Allow/Deny/Ask Every Time/Ask Once policies, 34 granular permissions across 10 categories
- [x] **S5: Approval Center** — Clear approval dialogs with risk levels, affected files, command display, network destination. Allow Once/Session/Always/Deny options
- [x] **S6: Sandbox Manager** — 5 sandbox modes, 7 types, filesystem sandbox with allowed/blocked/read-only folders, network security, resource limits, cross-platform
- [x] **S7: Audit Log** — Tamper-evident audit trail, 18 event types, search/filter/export, 500 sample entries
- [x] **S8: Security Alerts** — 9 alert categories, 4 severity levels, acknowledge/resolve workflow, alert aggregation
- [x] **S9: Secrets Manager** — Encrypted vault display, masked values, category organization, add/remove workflow
- [x] **S10: Privacy Settings** — 5 privacy modes, offline mode, telemetry toggle, data handling policy
- [x] **S11: Route Registration** — Route constant, AppView/AppRouteId types, APP_ROUTES entry, NAV_SECTIONS entry, lazy-loaded in desktop-controller
- [x] **S12: Documentation** — Created PERMISSIONS.md, SANDBOX.md, updated SECURITY.md, CHANGELOG.md, PROJECT_STATUS.md, TODO.md, ARCHITECTURE.md

## Phase 15 — Advanced Multimodal AI System

- [x] **M1: Multimodal Store** — Created `src/store/multimodal.ts` with comprehensive nanostore for cameras, screen capture, privacy indicators, processing status, model routing, TTS/STT/vision toggles, local mode
- [x] **M2: Model Capability Router** — Created `src/lib/model-router.ts` for automatic input type detection (text/code/image/audio/video/document/mixed), required capability matching, best model selection based on roles and user routing rules
- [x] **M3: Camera Capture System** — Created `src/components/ui/camera-capture.tsx` with camera enumeration, preview, capture button, camera switching, permission integration through Electron API
- [x] **M4: Screen Capture System** — Created `src/lib/screen-capture.ts` and `src/components/ui/screen-capture.tsx` with full screen/window/region capture, display media API, privacy indicator integration
- [x] **M5: Document Intelligence** — Created `src/lib/document-intelligence.ts` with text extraction for text-based files (txt/md/code), basic PDF parsing, office document metadata extraction, file type detection (text/office/code)
- [x] **M6: Audio Player** — Created `src/components/ui/audio-player.tsx` with waveform visualization, play/pause/seek, volume control, speed control (0.25x–4x), time display, error handling
- [x] **M7: Video Player** — Created `src/components/ui/video-player.tsx` with play/pause/seek, volume control, fullscreen toggle, progress bar, poster support, auto-play, HUD overlay
- [x] **M8: Document Preview** — Created `src/components/ui/document-preview.tsx` with text extraction display, confidence indicators, expandable content, loading/spinner, inline text preview
- [x] **M9: Multimodal Message Rendering** — Created `src/components/assistant-ui/multimodal-message.tsx` with MediaAttachment (auto-detects audio/video/image/file), AttachmentGallery (grid with overflow), ProcessingBadge, ModelTag
- [x] **M10: Privacy Indicators** — Created `src/components/ui/privacy-indicator.tsx` with PrivacyIndicators (mic/camera/screen/cloud active dots with pulse animation) and PrivacyBanner (warning bar). Wired into desktop-controller overlays
- [x] **M11: Composer Integration** — Added Camera and Screen Capture items to the composer's context menu (`context-menu.tsx`). Camera and Monitor icons added to icon library
- [x] **M12: Multimodal Settings View** — Created `src/app/settings/multimodal.tsx` with voice controls (STT/TTS toggles, voice selection, audio input/output device), vision settings (image toggle, camera scanning), local processing mode
- [x] **M13: Route Registration** — Added `MULTIMODAL_ROUTE = '/settings/multimodal'` route constant, updated AppView/AppRouteId types, APP_ROUTES entry, lazy-loaded MultimodalSettingsView in desktop-controller
- [x] **M14: Clipboard Utilities** — Created `src/lib/clipboard-utils.ts` with clipboard image read, text read/write, file read, data URL ↔ Blob conversion utilities
- [x] **M15: Icon Library Updates** — Added Camera icon export to `src/lib/icons.ts`

- Desktop Service & Integration Hub implemented (replaced simple health monitor with full 5-tab management UI, connection wizard, sync engine, marketplace, detail dialogs)
- PTY bridge POSIX-only limitation (tracked as C3, not removed)
- Dashboard analytics hidden (tracked as M7, not removed)
- Legacy HERMES_* env vars (tracked as T1)
