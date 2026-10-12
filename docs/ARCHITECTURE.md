# AetherOS Architecture

**Version:** 0.24.0  
**Last Updated:** July 21, 2026

---

## 1. System Overview

AetherOS is a cross-platform Desktop AI Operating System built around a Python agent core with multiple user interfaces. The architecture follows a **narrow-waist** design: a single `AIAgent` class powers the CLI, TUI, Desktop app, and 16+ messaging gateway platforms.

```
┌──────────────────────────────────────────────────────────────────┐
│                      USER INTERFACES                            │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  CLI    │  │   TUI    │  │ Desktop  │  │ 16+ Messaging    │  │
│  │ (Rich)  │  │  (Ink)   │  │(Electron)│  │ Gateway Platforms│  │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       └────────────┼──────────────┼──────────────────┘             │
│                    │              │                                │
│  ┌─────────────────▼──────────────▼──────────────────────────┐   │
│  │                    tui_gateway / API                       │   │
│  │          JSON-RPC over stdio / WebSocket / HTTP            │   │
│  └───────────────────────────┬──────────────────────────────┘   │
│                              │                                    │
│  ┌───────────────────────────▼──────────────────────────────┐   │
│  │                    AIAgent Core                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │   │
│  │  │  Prompt  │  │   Tool   │  │  Memory  │  │  Skills  │  │   │
│  │  │  Builder │  │  Dispatch│  │  Manager │  │  System  │  │   │
│  │  ├──────────┤  ├──────────┤  ├──────────┤  ├──────────┤  │   │
│  │  │  Context │  │  Plugin  │  │  Cron    │  │  Delegate│  │   │
│  │  │  Compress│  │  System  │  │  Sched.  │  │  Subagent│  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │   │
│  └───────────────────────────┬──────────────────────────────┘   │
│                              │                                    │
│  ┌───────────────────────────▼──────────────────────────────┐   │
│  │                    Tool Implementations                   │   │
│  │  Terminal │ File │ Web │ Browser │ Vision │ MCP │ Code   │   │
│  │  Delegate │ Cron │ Kanban │ HomeAsst │ VoIP │ TTS/STT   │   │
│  └───────────────────────────┬──────────────────────────────┘   │
│                              │                                    │
│  ┌───────────────────────────▼──────────────────────────────┐   │
│  │               Backend Infrastructure                      │   │
│  │  SQLite │ Docker │ SSH │ Modal │ s6-overlay │ Provider    │   │
│  │  Nix │ uv (package) │ FastAPI │ Node/Electron             │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Systems

### 2.1 Agent Core (`run_agent.py`)
- **`AIAgent` class** — Full conversation loop with tool dispatch (~12K LOC)
- **`run_conversation()`** — Synchronous loop with interrupt checks, budget tracking, grace calls
- **`chat()`** — Simple one-shot interface
- 60+ constructor parameters for credentials, routing, callbacks, session context
- OpenAI-compatible message format: `{"role": "system/user/assistant/tool", ...}`

### 2.2 Tool System (`tools/`)
- **Auto-discovery** via `tools/registry.py` — any `tools/*.py` with `registry.register()` is auto-imported
- **89 tool files** covering terminal, file, web, browser, vision, code, MCP, delegate, cron, kanban, homeassistant, TTS, voice, video, image gen, todo, memory, skills, and more
- 6 terminal backends: local, docker, ssh, modal, daytona, singularity
- 20+ toolsets defined in `toolsets.py`
- `check_fn` pattern for service-gated tools

### 2.3 Plugin System (`plugins/`)
- **PluginManager** (`aetheros_cli/plugins.py`) — discovers from `~/.aetheros/plugins/`, `./.aetheros/plugins/`, pip entry points
- Lifecycle hooks: `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`, `on_session_start`, `on_session_end`
- **Memory provider plugins** — 8 built-in (honcho, mem0, supermemory, byterover, hindsight, holographic, openviking, retaindb)
- **Model provider plugins** — 29 bundled (openrouter, anthropic, gemini, deepseek, openai-codex, etc.)
- **Context engine, image gen, video gen, dashboard auth** — plugin surfaces
- Closed policy on new in-tree memory providers (policy May 2026)

### 2.4 CLI (`cli.py` + `aetheros_cli/`)
- Interactive CLI with **Rich** formatting + **prompt_toolkit** input (~11K LOC)
- **Skin engine** — data-driven theming with 4 built-in skins (default, ares, mono, slate)
- **Slash command registry** — centralized `COMMAND_REGISTRY` in `aetheros_cli/commands.py`
- **KawaiiSpinner** — animated faces during API calls
- Setup wizard, provider/model selection, diagnostics (`aetheros doctor`)

### 2.5 TUI (`ui-tui/` + `tui_gateway/`)
- **Ink** (React for terminal) — TypeScript owns screen, Python owns logic
- Communication via **JSON-RPC over stdio**
- Full session management, streaming, completions, themes
- Dark/light mode auto-detection
- 6 packages: `aetheros-ink`, `ink-markdown`, `aetheros-highlight`, `aetheros-tooltip`, etc.

### 2.6 Desktop App (`apps/desktop/`)
- **Electron + React** with nanostore state management (51 stores)
- `@assistant-ui/react` compositor for rich chat with streaming
- **IPC Bridge**: 56 handlers in `electron/main.cjs` covering backend lifecycle,
  file I/O, terminal (node-pty), updates, OAuth, previews, deep links, VS Code
  theme import, and universal JSON-RPC passthrough (`hermes:api`)
- **Preload bridge** (`preload.cjs`): 30+ methods exposed via `window.aetherosDesktop`
- **PaneShell layout**: Resizable side panes (sidebar, file browser, preview, terminal)
  with hover-reveal, flip support, and width persistence
- **40 routes**: Chat (`/`, `/:sessionId`), Settings, Skills, Messaging, Artifacts,
  Cron, Profiles, Agents, Command Center, Home, Projects, Models, Memory,
  Knowledge, Files, Browser, Automation, Extensions, Services, Tasks, History,
  Logs, Help, Updates, Agent Hub, Provider Manager, Marketplace,
  MCP Manager, Extension SDK, Developer Tools, Updates Manager, Sync,
  Remote Agents (overlays or pages)
- **Service & Integration Hub**: Replaces simple service health monitor with a full
  5-tab management interface at `/services`. Tabs: Dashboard (stats, health, overview),
  Connected Services (enable/disable, status badges, search, detail dialog), Marketplace
  (20+ platform connectors with setup guides, auth type, category filters, connect wizard),
  Sync Status (job management, interval config, run history, global sync toggle),
  Settings (hub preferences, diagnostics). Built on 2 nanostores (`store/services.ts`,
  `store/service-sync.ts`) with 3 supporting page components.
- **Per-profile theme system**: Skin (accent) × mode (light/dark/system) with
  boot-time paint to eliminate flash
- **Multi-step onboarding**: OAuth provider selection, device-code flow,
  API key entry, model confirmation with cinematic exit animation
- **Slash commands**: Client-side curation (`desktop-slash-commands.ts`),
  built-in dispatch + extension passthrough to backend
- `electron/main.cjs` (6.3K LOC) — boot, backend resolution, IPC, self-update
- **Bootstrap installer** (`apps/bootstrap-installer/`) — Tauri v2 first-launch installer
- **Shared package** (`apps/shared/`) — common types and utilities
- **6 installer targets**: macOS (ARM/x64), Windows (x64/ARM), Linux (x64/ARM)
- **Auto-updater**: Electron built-in with stable/beta/canary branch selection

### 2.7 Messaging Gateway (`gateway/`)
- **16+ platform adapters** in `gateway/platforms/`
- Adapter pattern via `base.py` ABC
- Platforms: Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, DingTalk, Feishu, WeCom, Weixin, QQBot, Matrix, Mattermost, BlueBubbles, Home Assistant, Webhooks, Yuanbao
- Session management, slash command handling, channel directory
- Kanban watcher, pairing, sticker cache

### 2.8 Orchestrator (`aetheros_orchestrator/`)
- Process orchestration with internal message bus
- Service lifecycle management
- API gateway, config, daemon mode
- Logging coordination

### 2.9 Automation & Orchestration (`aetheros_automation/`)
- **Task Orchestrator** — Central `TaskOrchestrator` class managing full lifecycle: objective understanding, task decomposition, plan creation, agent/model selection, execution graph traversal, pause/resume/cancel/restart. Sub-agent creation/termination, agent messaging, human-in-the-loop approval callbacks.
- **Execution Engine** — Runs individual tasks with tool dispatch to registry and automation modules. Supports parallel execution, execution context tracking.
- **Checkpoint System** — JSON-based persistence of plan execution state. Supports save/load/list/delete. Enables pause/resume/restore workflows. Checkpoints capture completed/failed/pending tasks per plan.
- **Model Router** — Automatic model selection based on task type, reasoning requirements, cost, latency, privacy. Role-based preferences (developer→claude-sonnet, research→gpt-4o, etc.). Fallback chains per provider (openai→gpt-4o-mini→haiku).
- **Multi-Agent System** — Agent collaboration (start/end collaborations, send/broadcast, share results). Agent messaging (async send/receive, conversation history, send-and-wait). Sub-Agent manager (create/terminate with limited scope, permissions, execution limits).
- **Execution Graph** — Level-based graph with sequential, parallel, conditional, dependent, retry, fallback, and human-approval execution modes. Topological sort via Kahn's algorithm.
- **Failure Recovery** — RetryHandler with exponential backoff/jitter, failure classification (timeout, rate_limit, auth, provider, tool, permission, model, validation, unknown). FallbackHandler with primary+fallback operation chains.
- **Result Validation** — Completeness, relevance, file existence checks. Custom validator registration.
- **Task Templates** — 7 built-in templates (Research Report, Software Development, Data Analysis, Content Creation, Email Campaign, Business Automation, Personal Assistant).
- **Natural Language Automation** — Parses natural language requests into plans with schedule detection (weekly/daily/interval/oneshot).
- Agents, approvals, browser, calendar, code, computer, core, devops
- Documents, email, files, live, MCP, mobile, models, modes
- Permissions, plugins, security, tasks, terminal, undo, web
- CLI commands for run/task/automate/approvals/stop/resume/rollback

### 2.10 Security (`aetheros_security/`)
- AI security, audit trails, DLP, encryption
- Permissions system, rate limiting, sandbox, secrets management
- Threat detection

### 2.11 Intelligence (`aetheros_intelligence/`)
- Model routing, reasoning, planning, research
- Workflow AI, local AI, automation AI, developer AI
- Project understanding, explainability, learning

### 2.12 Knowledge (`aetheros_knowledge/`)
- Vector database, RAG, search, indexing
- Memory management, sharing, web integration
- Center for unified knowledge access

### 2.13 Cloud (`aetheros_cloud/`)
- Remote agent execution, collaboration, team/workspace
- Storage, sync, notifications, audit
- Plugin system for cloud extensions
- Sync engine with offline-first architecture
- Device management and multi-device support
- Remote agent platform with mTLS security

### 2.14 Voice (`aetheros_voice/`)
- STT/TTS engines, wake word detection, dictation
- Noise cancellation, personality, modes
- Accessibility, chat, automation, computer integration
- CLI commands for voice management

### 2.15 Memory (`memory/`)
- Short-term, episodic, semantic, procedural, long-term
- Embeddings, knowledge graph, entity/relationship indexing
- Consolidation, retrieval, ranking, reflection, summarization
- Project memory, workspace memory, garbage collection
- Import/export, retention policies

---

## 3. Data Flow

### 3.1 User Request Flow (CLI)
```
User Input → cli.py → AIAgent.run_conversation()
  → LLM API Call → Response Handler
    → Tool Call? → handle_function_call() → Tool Result
    → Text Response? → Display to User
```

### 3.2 Desktop Request Flow
```
Desktop UI → IPC → Electron Main (main.cjs)
  → JSON-RPC → tui_gateway → AIAgent
  → Response → IPC → Desktop UI
```

### 3.3 Gateway Message Flow
```
External Platform → Platform Adapter → Gateway Runner
  → Slash Commands / Message Processing → AIAgent
  → Response → Platform Adapter → External Platform
```

---

## 4. Storage

| Data | Store | Location |
|------|-------|----------|
| Sessions | SQLite (FTS5) | `~/.aetheros/state.db` |
| Config | YAML | `~/.aetheros/config.yaml` |
| Secrets | .env (+ encryption) | `~/.aetheros/.env` |
| Memory | Provider-specific | Various |
| Logs | Rotating files | `~/.aetheros/logs/` |
| Skills | Python files | `~/.aetheros/skills/` |
| Cron Jobs | SQLite | `~/.aetheros/cron/` |
| Kanban | SQLite | Board-specific |
| Sync State | SQLite | `~/.aetheros/sync/state.db` |
| Sync Cache | Filesystem | `~/.aetheros/sync/cache/` |
| Device Keys | Keychain | OS-specific secure storage |
| Remote Instances | SQLite | `~/.aetheros/remote/instances.db` |

---

## 5. Configuration

Three config loader paths:
1. **`load_cli_config()`** — CLI mode (cli.py)
2. **`load_config()`** — CLI subcommands (aetheros_cli/config.py)
3. **Direct YAML load** — Gateway runtime (gateway/run.py)

Config sections: `model`, `agent`, `terminal`, `compression`, `display`, `stt`, `tts`, `memory`, `security`, `delegation`, `smart_model_routing`, `checkpoints`, `auxiliary`, `curator`, `skills`, `gateway`, `logging`, `cron`, `profiles`, `plugins`, `honcho`

Profiles system with fully isolated `AETHEROS_HOME` directories.

### 2.16 Sync Architecture

The sync system provides offline-first, end-to-end encrypted synchronization across multiple devices.

- **Sync Engine** — Core orchestrator with session lifecycle, scope management (16 scopes), delta computation, conflict resolution, version history, and background sync scheduling.
- **Offline-First Model** — Local-first storage with outbox pattern. Writes succeed immediately offline; background processor syncs when connectivity returns.
- **Conflict Resolution** — 5 strategies per scope: latest (default), manual, keep-local, keep-remote, merge.
- **Version History** — Immutable version chain per scope with browse and restore (default: 100 versions, 90-day retention).
- **Cloud Provider Abstraction** — `CloudProviderBase` ABC with Local (filesystem) and Custom (HTTP/S) providers. Pluggable for future backends.
- **Encryption Layer** — AES-256-GCM for payload encryption, RSA-4096 for device identity, PBKDF2 for key derivation (600K iterations), E2EE preventing provider access to plaintext, digital signatures for non-repudiation.
- **Device Manager** — Device registration with RSA key pairs, secure keychain (Windows Credential Manager, macOS Keychain, Linux Secret Service), per-device permissions, device revocation.
- **Session Management** — JWT tokens (1h TTL), automatic background refresh, token blacklisting, scope-limited tokens.

### 2.17 Remote Agent Platform

The remote agent platform extends AetherOS to distributed deployments with secure remote control, monitoring, and workspace access.

- **Remote Instance Manager** — Instance registry with unique IDs, capability negotiation, mTLS + token authentication, health monitoring (30s heartbeat).
- **Connection Lifecycle** — Connect/disconnect/reconnect with exponential backoff (1s → 30s cap, ±25% jitter), graceful shutdown, stale detection.
- **Agent Control** — Remote start/stop/pause/resume/restart with status reporting, PID tracking, timeout handling.
- **Remote Monitoring** — Real-time log streaming (level-filtered), task tracking, memory/CPU/disk monitoring, usage statistics, error aggregation.
- **Workspace Bridge** — Remote file operations (list/read/write/delete/search), project management, agent inspection, automation control, knowledge base search.
- **Security** — Mutual TLS, token authentication, rate limiting (60 req/min, 10 burst), audit logging, never-log-credentials policy.
- **Collaboration Architecture (Future)** — Team workspaces, shared agents/knowledge, role-based access (Admin/Operator/Viewer).

### 2.18 Plugin Marketplace, MCP Manager & Extension SDK

The Plugin Marketplace, MCP Manager, and Extension SDK form the developer ecosystem layer of AetherOS, providing UI surfaces for discovering, installing, and managing extensions.

- **Plugin Marketplace** (`/marketplace`): Web and desktop routes for browsing and installing community and official plugins. Includes plugin detail pages (`/marketplace/plugin/:id`), installed plugins management (`/marketplace/installed`), and updates tracking (`/marketplace/updates`).
- **MCP Manager** (`/marketplace/mcp` in web, `/mcp-manager` in desktop): UI for configuring, enabling, disabling, and monitoring MCP servers. Supports stdio and SSE transport types with health checks and logging.
- **Extension SDK** (`/marketplace/sdk` in web, `/extension-sdk` in desktop): Developer portal with SDK documentation, API references, and plugin authoring tools.
- **Developer Tools** (`/marketplace/devtools` in web, `/developer-tools` in desktop): Sandbox and debugging tools for plugin development.
- **Documentation**: `PLUGIN_SDK.md` (comprehensive plugin authoring guide) and `MCP_GUIDE.md` (MCP configuration reference with 23 server examples) at the project root.

### 5.6 Security Center (Desktop App)

The Security Center provides enterprise-grade security management for the desktop app:

- **Route**: `/security` — registered in `NAV_SECTIONS` sidebar, lazy-loaded view
- **Store**: `src/store/security.ts` — nanostore atoms for all security state, 34 permission definitions, 20+ action functions
- **Views**: 8-tab layout in `src/app/security-center/`:
  - **Overview** — Security status dashboard with stats cards, active alerts, pending approvals, running sandboxes
  - **Permissions** — Granular per-agent/plugin/MCP/automation permissions with Allow/Deny/Ask Every Time/Ask Once policies
  - **Approvals** — Approval request management with risk level display, allow/deny/session/permanent options
  - **Sandbox** — Isolated execution environments with 5 modes, 7 types, filesystem/network controls, resource limits
  - **Audit Log** — Tamper-evident audit trail with 18 event types, search/filter/export (up to 10K entries)
  - **Alerts** — Security threat detection with 9 categories, 4 severity levels, acknowledge/resolve workflow
  - **Secrets** — Encrypted vault for API keys, passwords, tokens, certificates with masked display
  - **Privacy** — Privacy modes (Offline, Local-Only, No Telemetry, Private, Strict Sandbox), telemetry and offline toggles
- **Key design**: Zero Trust by default. Reuses existing Python `aetheros_security/` backend concepts. Follows same patterns as MCP Manager and Devices views (PageShell, nanostore atoms, Dialog components).

---

## 6. Key Design Decisions

1. **Prompt caching is sacred** — never mutate past context mid-conversation
2. **Narrow core waist** — most capability lives in plugins/skills, not core
3. **Extend, don't duplicate** — always prefer extending existing code
4. **Service-gated tools** — tools only appear when prerequisites are configured
5. **All deps upper-bounded** — supply chain security
6. **Self-registering tools** — auto-discovery with deliberate toolset wiring
7. **Plugin surface before core hack** — plugins never modify core files
8. **Profiles are islands** — no config inheritance between profiles
9. **Offline-first sync** — writes succeed locally, sync happens asynchronously
10. **End-to-end encryption** — provider cannot read payloads; only authorized devices
11. **Device identity via RSA** — hardware-backed key pairs for authentication
12. **Remote agents as peers** — distributed control with mutual TLS
13. **Zero Trust security** — every action is denied by default unless explicitly granted; permissions are granular, auditable, and user-controlled
