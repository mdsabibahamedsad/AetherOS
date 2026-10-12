# AetherOS Development Tasks

## Phase 4 — Universal AI Provider & Model Manager ✅ Complete

- [x] Provider store (nanostores with 30+ actions)
- [x] Provider Hub (categorized cloud/local/custom grid)
- [x] Provider Detail (auth, models, health, usage)
- [x] Model Manager (search, filter, favorite, pin, sort, hide)
- [x] Model Router (8 task types with provider/model assignment)
- [x] Health Monitor (per-provider status with check capability)
- [x] Model Tester (custom prompts, latency, tokens/s)
- [x] Usage Dashboard (daily/monthly stats, bar chart, top models)
- [x] Provider Settings (timeout, retries, fallback, features)
- [x] Route integration (`/providers` route with lazy loading)
- [x] Update routes.ts with new types

## Phase 3 — Setup Wizard ✅ Complete
- [x] (all 13 steps complete)

## Phase 6 — Agent & Automation Hub ✅ Complete

### Desktop App (apps/desktop/)
- [x] Agent Hub store (nanostores with 30+ actions, 16 template defaults)
- [x] Agent Hub shell with 6-tab navigation
- [x] Agent List (search, filter, create, duplicate, delete, run/stop/pause)
- [x] Agent Config panel (7-section: general, prompt, model, memory, tools, permissions, workspace)
- [x] Multi-Agent Workflows (sequential, parallel, coordinator with 8 roles)
- [x] Automation Builder (8 trigger types, workflow linking)
- [x] Task Manager (4 stat cards, status filter, expandable logs)
- [x] Monitoring Dashboard (4 stats, CPU/RAM/GPU gauges, agent status, recent activity)
- [x] Marketplace (agent templates grid, workflow templates, publish CTA)
- [x] Route integration (`/agent-hub` route with lazy loading, navigation entry)

### Web Dashboard (web/)
- [x] Agent Hub Zustand store with full CRUD and state management
- [x] Agent Hub API methods and types in lib/api.ts
- [x] Agent Hub desktop controller (lib/agent-controller.ts)
- [x] Agent Hub landing page with stats and quick actions
- [x] Agent List page (search, tag filters, grid cards with actions)
- [x] Agent Detail page (overview, config, tasks, memory, logs, permissions tabs)
- [x] Agent Templates page (browse, search, category filters, create from template)
- [x] Agent Configuration page (model, provider, system prompt, toolsets, memory, env vars)
- [x] Agent Orchestration page (sequential, parallel, fan-out, debate, voting, hierarchical)
- [x] Automation Builder page (triggers, conditions, actions, loops, retries, variables)
- [x] Task Manager page (stats, filters, search, create dialog, progress tracking)
- [x] Monitoring Dashboard page (CPU, RAM, GPU, running agents/tasks, provider/model status)
- [x] Marketplace page (agent templates, workflow templates, automation blueprints, toolset)
- [x] Workflow Runner page (visual pipeline, run controls, execution history)
- [x] Scheduler page (cron/interval/once jobs, enable/disable, run history)
- [x] Background Services page (start/stop/restart, auto-restart, resource usage)
- [x] Agent Logs page (level/agent/component filters, auto-refresh, search)
- [x] Notifications page (grouped by date, mark read, type filter, clear all)
- [x] Agent Permissions page (grant/revoke, agent/resource/effect filters, stats)
- [x] Agent Memory page (episodic/semantic/working tabs, semantic search)
- [x] Agent Search page (cross-agent search grouped by category)
- [x] Agent Tags page (create/edit/delete, color picker, usage stats)
- [x] Routing integration (19 routes in App.tsx)
- [x] Navigation integration (19 nav items in sidebar)
- [x] i18n translations (English nav labels)
- [x] Page title resolution (resolve-page-title.ts mappings)

## Phase 5 — Chat UI ✅ Complete (pre-existing)

- [x] Chat composer implementation (ChatBar with slash commands, @-mentions, attachments, voice, queue, drag-drop)
- [x] Message transcript rendering (Thread with virtualizer, markdown, directives, ANSI)
- [x] Tool call display (tool-approval, tool-fallback, todo-tool, clarify-tool)
- [x] Session management UI (sidebar with virtual list, CRUD, branch, search, cron jobs)

## Phase 7 — Service & Integration Hub ✅ Complete

### Desktop App (apps/desktop/)
- [x] Service Hub nanostore (`store/services.ts`) with connector catalog (20 entries), service state, patch API
- [x] Service Sync nanostore (`store/service-sync.ts`) with job configs, run lifecycle, history tracking
- [x] Service Hub 5-tab UI (Dashboard, Connected, Marketplace, Sync, Settings)
- [x] Dashboard tab with stats cards, backend health, platform overview, sync status
- [x] Connected Services tab with enable/disable toggles, status badges, search, detail dialog
- [x] Marketplace tab with category filters, color-coded connectors, setup guides, auth badges
- [x] Service Detail Dialog (`service-detail-dialog.tsx`) with status, error display, actions
- [x] Connect Wizard (`connect-wizard.tsx`) with setup guide, auth info, direct messaging link
- [x] Sync Manager (`sync-manager.tsx`) with job list, trigger, interval config, run history
- [x] Settings tab with hub preferences (sync display, auto health check, error notifications)
- [x] Auto-polling (10s refresh), refresh hotkey support, error notifications
- [x] Route integration (existing `/services` route, no navigation changes needed)
- [x] Documentation updated (CHANGELOG.md, PROJECT_STATUS.md, ARCHITECTURE.md, TODO.md)

## Phase 8 — Automation Builder ✅ Complete
- [x] Automation store (nanostores with 50+ action functions, 21 trigger types, 35 action types, 13 condition types)
- [x] Visual Canvas with zoom, pan, snap-to-grid, minimap
- [x] Drag & drop node palette (triggers/actions/conditions by category)
- [x] Node editor with configurable trigger/action/condition modals
- [x] Connection system with port-based wiring
- [x] Multi-select, copy, paste, duplicate, delete selections
- [x] Undo/redo (full history stack)
- [x] Auto-layout algorithm
- [x] Node keyboard shortcuts (zoom, undo/redo, select all, delete)
- [x] Variables panel (workflow/global/session/environment/secret/output/input scopes)
- [x] Secrets Manager (encrypted storage, masked display, CRUD)
- [x] Workflow Scheduler (once, daily, hourly, weekly, monthly, cron, manual)
- [x] Retry Policy configuration
- [x] Execution History (timeline, stats, logs, cost, retry count, model used)
- [x] Templates Gallery (15 built-in templates by category)
- [x] Marketplace UI (12 blueprints/templates/workflows with categories, ratings, install)
- [x] Workflow CRUD (create, enable/disable, duplicate, delete)
- [x] Route integration (`/automation` route)
- [x] Navigation entry (automation in sidebar)
- [x] Store integration with desktop-controller lazy loading

## Phase 9 — Communications Hub ✅ Complete

### Desktop App (apps/desktop/)
- [x] Communications Hub store (`store/communications.ts`) with 11 platform types, unified message model, AI/voice/media/notification/security configs, automation rules, templates, activity feed, 40+ action functions
- [x] Main Dashboard with 6-stat overview (Connected Accounts, Online, Messages Today, AI Replies, Queued, Failed), platform grid cards with live status dots, real-time activity feed
- [x] 9-tab hub navigation (Dashboard, Platforms, Inbox, AI Features, Automation, Voice, Media, Notifications, Settings)
- [x] Dashboard view with stats cards, platform connection grid, recent activity feed
- [x] Platform management tab preserves full existing credential UI with `getMessagingPlatforms`/`updateMessagingPlatform` API integration, per-platform env var editing (required/optional/advanced)
- [x] Unified Inbox (`unified-inbox.tsx`) with cross-platform message merge, 6 inbox filters (All, Unread, Important, Pinned, AI Only, Archived), platform filter, full-text search, split-pane conversation list + message detail
- [x] AI Features panel with 10 toggleable AI capabilities (Auto Reply, Smart Suggestions, Rewrite, Translate, Summarize, Sentiment, Priority, Spam, Meeting, Task)
- [x] Automation Rules panel with visual rule builder (4 trigger types, 5 action types, approval gates, platform targeting, inline CRUD)
- [x] Message Templates panel with cross-platform template storage, freeform content editor, create/delete
- [x] Voice panel with 4 provider selection (Whisper, Deepgram, OpenAI Voice, Local STT), Push-to-Talk, Voice Commands, Voice Reply
- [x] Media panel with OCR, Vision, Caption, Summarize, Auto-Download toggles + recent media grid
- [x] Notifications panel with Desktop Notifications, Sound, Silent Mode (time range), Priority Mode, DND toggles
- [x] Settings & Security panel with Encrypted Tokens, Local Storage, Credential Vault, Permission Manager, Audit Log toggles + Export/Import/Clear + Reconnect/Backup/Logs
- [x] Auto-polling (10s refresh) for live platform status, refresh hotkey support
- [x] Route integration: `communications` added to `NavSectionId` and `NAV_SECTIONS` (pointing to `/messaging`), `communications` added to `AppView`/`AppRouteId` in routes.ts, `COMMUNICATIONS_ROUTE = '/communications'` with route entry and lazy-loaded view in desktop-controller.tsx
- [x] All new code compiles with zero TypeScript errors
- [x] Documentation updated (CHANGELOG.md, TODO.md)

## Phase 12 — Plugin Marketplace, MCP Manager & Extension SDK ✅ Complete

### Web Dashboard (web/)
- [x] Marketplace, Plugin Detail, Installed Plugins, Updates page imports and routes
- [x] MCP Manager page route
- [x] Extension SDK page route
- [x] Developer Tools page route
- [x] Sidebar navigation items for all new marketplace pages
- [x] Icon map entries for Download and Plug

### Desktop App (apps/desktop/)
- [x] Route constants (`MARKETPLACE_ROUTE`, `MCP_MANAGER_ROUTE`, `EXTENSION_SDK_ROUTE`, `DEVELOPER_TOOLS_ROUTE`, `UPDATES_MANAGER_ROUTE`)
- [x] `AppView` / `AppRouteId` type union entries
- [x] `APP_ROUTES` array entries
- [x] Lazy-loaded view imports and Route elements in desktop-controller.tsx

### Documentation
- [x] `PLUGIN_SDK.md` — Comprehensive plugin SDK documentation
- [x] `MCP_GUIDE.md` — Complete MCP guide with 23 server examples
- [x] `PROJECT_STATUS.md` updated with Phase 12 completion
- [x] `CHANGELOG.md` updated with v0.22.0 entry
- [x] `TODO.md` demoting Phase 12 items
- [x] `ARCHITECTURE.md` updated with new components

## Phase 13 — Cloud Sync, Multi-Device & Remote Agent Platform ✅ Complete

### Sync Architecture
- [x] `SYNC_ARCHITECTURE.md` — Comprehensive sync architecture document
- [x] Offline-first storage model with outbox pattern
- [x] Sync engine design with session lifecycle and scope management
- [x] 16 sync scopes (settings, agents, configs, workflows, automations, provider_configs, model_preferences, knowledge_metadata, memory, chat_history, plugins, mcp_configs, workspace_metadata, themes, shortcuts, notifications)
- [x] Incremental sync and delta updates with version vectors
- [x] Conflict resolution (latest, manual, keep-local, keep-remote, merge)
- [x] Version history and restore (100 versions/scope, 90-day retention)
- [x] Cloud provider abstraction (`CloudProviderBase`) with Local and Custom providers
- [x] Encryption layer (AES-256-GCM, E2EE, RSA-4096, PBKDF2, digital signatures)
- [x] Performance: zstd compression, lazy loading, background sync, retry queue with exponential backoff
- [x] Security: device auth, session management (JWT, 1h TTL, auto-refresh), token rotation, audit logs

### Multi-Device
- [x] Device registration with RSA-4096 key pairs
- [x] Secure keychain integration (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- [x] Per-device permission sets
- [x] Device revocation with CRL
- [x] End-to-end encryption for secrets
- [x] Device authentication and session management

### Remote Agent Platform
- [x] `REMOTE_AGENTS.md` — Comprehensive remote agent platform document
- [x] Remote instance management with registry
- [x] Connection lifecycle (connect, disconnect, reconnect with exponential backoff)
- [x] Health monitoring with 30-second heartbeat
- [x] Agent control (start, stop, pause, resume, restart)
- [x] Remote monitoring (logs, tasks, memory, usage, errors)
- [x] Remote workspace access (files, projects, agents, automations, knowledge)
- [x] Security: mutual TLS, token auth, rate limiting (60 req/min), audit logging
- [x] Auto-reconnect with exponential backoff (1s → 30s cap, ±25% jitter)
- [x] Latency tracking via ping/pong RTT measurement
- [x] Collaboration architecture (future): team workspaces, shared agents, role-based access

### Security Documentation
- [x] `docs/SECURITY.md` — Comprehensive security overview
- [x] Device authentication and registration
- [x] Session management with token rotation
- [x] End-to-end encryption for secrets
- [x] AES-256-GCM sync encryption
- [x] RSA-4096 device identity keys
- [x] PBKDF2 key derivation (600K iterations)
- [x] Digital signatures for payload verification
- [x] Audit logging for all security events
- [x] Permission validation per device
- [x] Rate limiting for remote connections
- [x] Secure keychain integration
- [x] Never log credentials policy
- [x] Device revocation workflow

### Project Documentation Updates
- [x] `CHANGELOG.md` updated with v0.23.0 entry
- [x] `PROJECT_STATUS.md` bumped to 0.23.0, 94% overall
- [x] `TODO.md` demoting Phase 13 items
- [x] `ARCHITECTURE.md` updated with sync and remote agent sections

## Remaining
- [ ] Frontend unit test coverage
- [ ] Windows native PTY for dashboard chat
- [ ] Mobile companion app
