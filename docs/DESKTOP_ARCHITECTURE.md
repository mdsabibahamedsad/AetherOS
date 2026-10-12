# Desktop Application Architecture

## Overview

The Aetheros desktop app (`apps/desktop/`) is an **Electron + React + nanostores** renderer
that communicates with the Python backend (`tui_gateway`) over JSON-RPC. It is a **first-class
chat surface** — NOT an embedded TUI — with its own composer, transcript, slash-command pipeline,
and window management.

## Process Model

```
┌──────────────────────────────────────────────────┐
│                   Electron Main                  │
│  (electron/main.cjs — 6.3K LOC, 56 IPC handlers) │
│                                                   │
│  ┌─────────────┐  ┌─────────────────────────┐    │
│  │  Node.js     │  │  Python Backend (child)  │    │
│  │  Window Mgr  │  │  ─ tui_gateway/server.py │    │
│  │  Terminal    │  │  ─ AIAgent + tools       │    │
│  │  Updates     │  │  ─ session management    │    │
│  │  File I/O    │  │  ─ slash commands        │    │
│  └──────┬───────┘  └──────────┬──────────────┘    │
│         │                     │                    │
│         └──── preload.cjs ────┘                    │
│         │  contextBridge                          │
│         │  (30+ IPC methods exposed)              │
│  ┌──────┴──────────────────────────────────────┐  │
│  │           Renderer (React)                   │  │
│  │  apps/desktop/src/                           │  │
│  │  - React 18 + nanostores                    │  │
│  │  - @assistant-ui/react                       │  │
│  │  - HashRouter (react-router-dom)             │  │
│  │  - xterm.js (embedded terminal)              │  │
│  └─────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

- **Main process** (main.cjs): Window management, native menus, auto-updater, file system access,
  terminal (node-pty), desktop notifications, OS integration
- **Preload bridge** (preload.cjs): Context bridge exposing 30+ IPC methods via `window.aetherosDesktop`
  to the renderer
- **Renderer** (React SPA): Full chat UI, settings, onboarding, command palette, session management
- **Python child process**: Spawned by main process, runs the `tui_gateway` JSON-RPC server.
  Communicates with renderer via the main process IPC bridge

## IPC Bridge (56 handlers in main.cjs)

| Prefix | Count | Purpose |
|--------|-------|---------|
| `hermes:connection*` | 5 | Backend lifecycle (start, revalidate, touch, WS URL) |
| `hermes:bootstrap*` | 4 | First-run bootstrap state (reset, repair, cancel) |
| `hermes:boot-progress*` | 1 | Boot progress polling |
| `hermes:profile*` | 2 | Profile get/set |
| `hermes:api` | 1 | Universal JSON-RPC passthrough to Python backend |
| `hermes:window:*` | 1 | Open separate session window |
| `hermes:notify` | 1 | OS-level desktop notifications |
| `hermes:readFile*` | 2 | Read file as data URL or text |
| `hermes:selectPaths` | 1 | Native file/folder picker dialogs |
| `hermes:writeClipboard` | 1 | Clipboard write |
| `hermes:saveImage*` | 3 | Save image from URL, buffer, or clipboard |
| `hermes:preview*` | 3 | File preview watching/normalization |
| `hermes:openExternal` | 1 | Open URL in OS default browser |
| `hermes:setting*` | 3 | Default project dir get/set/pick |
| `hermes:fetchLinkTitle` | 1 | Extract title from URL |
| `hermes:logs*` | 2 | Reveal/read desktop logs |
| `hermes:fs:*` | 2 | Read directory, find git root |
| `hermes:terminal:*` | 4 | Start, write, resize, dispose terminal |
| `hermes:updates:*` | 4 | Check, apply, get/set update branch |
| `hermes:version` | 1 | Report app version + Git SHA |
| `hermes:uninstall:*` | 2 | Uninstall summary and execution |
| `hermes:vscode-theme:*` | 2 | VS Code marketplace theme search/fetch |
| `hermes:deep-link-ready` | 1 | Signal renderer is ready for deep links |
| `hermes:requestMicrophoneAccess` | 1 | Request mic permission |

### Key IPC Flow: Chat

```
Renderer                          Main Process                    Python Backend
   │                                    │                              │
   │── hermes:api (JSON-RPC request) ──►│                              │
   │                                    │── spawns/manages ──────────► │
   │                                    │   ─ tui_gateway/server.py    │
   │                                    │                              │
   │◄── IPC response ───────────────────│                              │
   │                                    │                              │
   │── hermes:gateway:ws-url ──────────►│                              │
   │                                    │── resolve ──────────────────►│
   │◄── ws://... ───────────────────────│                              │
   │                                    │                              │
   │── WebSocket to Python backend ──────────────────────────────────► │
   │◄── streaming events (message.delta, tool.start, etc.) ─────────── │
```

## React Architecture

### Entry Point (`src/main.tsx`)

```tsx
<StrictMode>
  <ErrorBoundary>
    <QueryClientProvider>
      <I18nProvider>
        <ThemeProvider>
          <HapticsProvider>
            <HashRouter>
              <App />
            </HashRouter>
          </HapticsProvider>
        </ThemeProvider>
      </I18nProvider>
    </QueryClientProvider>
  </ErrorBoundary>
</StrictMode>
```

Providers chain: Error tracking → React Query → i18n → Theme → Haptics → Routing.

### Routes (`src/app/routes.ts`)

| Route | View | Type |
|-------|------|------|
| `/` | Chat (new) | Main |
| `/:sessionId` | Chat (existing) | Main |
| `/settings` | Settings | Overlay |
| `/command-center` | Command Center | Overlay |
| `/agents` | Agents | Overlay |
| `/cron` | Cron | Overlay |
| `/profiles` | Profiles | Overlay |
| `/skills` | Skills | Page |
| `/messaging` | Messaging | Page |
| `/artifacts` | Artifacts | Page |

Views marked "Overlay" render as full-screen modal cards above the shell.
Views marked "Page" replace the main content area.

### Layout: AppShell + PaneShell

```
┌────────────────────────────────────────────────┐
│  TitlebarControls                              │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐   │
│  │ ⚙️ │ │ 📋 │ │ 💬 │ │ 👤 │ │ 📁 │ │ ⋮  │   │
│  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘   │
├──────┬──────────────────────────────────┬──────┤
│      │                                  │      │
│Side  │        Main Content              │Rail  │
│bar   │        (PaneMain)                │Pane  │
│(Chat │                                  │(File │
│Side- │                                  │Brwsr)│
│bar)  │                                  │      │
│      │                                  │      │
│      │  ┌──────────────────────────┐    │      │
│      │  │    Terminal (persistent)  │    │      │
│      │  └──────────────────────────┘    │      │
├──────┴──────────────────────────────────┴──────┤
│  StatusbarControls                             │
│  ┌──────────┐ ┌──────┐ ┌──────┐ ┌──────────┐  │
│  │ Model    │ │ Cwd  │ │ Btn1 │ │  Status  │  │
│  └──────────┘ └──────┘ └──────┘ └──────────┘  │
└────────────────────────────────────────────────┘
```

- **TitlebarControls**: System tools (settings, profiles, haptics, right-sidebar) + pane-supplied tools.
  Position adapts to window controls (macOS left, Windows right). Content inset clears OS traffic lights.
- **PaneShell**: Flex container that holds sidebar, main content, and rail panes.
  Resizable panes with drag handles, hover-reveal overlays on narrow viewports.
- **StatusbarControls**: Model name, current workspace, gateway status, inference status, log line count.
- **AppShell**: Top-level shell that wires titlebar + main + statusbar. Provides CSS variables for
  pane width, titlebar height, inset, and tool cluster anchoring.

### Pane System (`src/components/pane-shell/`)

The pane system enables a multi-pane layout with resizable side panels:

| Pane | ID | Default | Content |
|------|----|---------|---------|
| Chat Sidebar | `chat-sidebar` | Open (left) | Session list, pinned, cron jobs, messaging sections |
| File Browser | `file-browser` | Closed (right) | File tree, folder navigation |
| Preview Rail | `preview` | Closed (right) | Image/file preview, browser preview |
| Terminal | `terminal-sidebar` | Open (right) | Embedded xterm.js persistent terminal |

Pane features:
- **Resizable**: Drag handles between panes (z-20)
- **Hover-reveal**: Force-collapse to 0px track, appear on hover at narrow viewports
- **Flip support**: Mirror layout (sidebar right, rail left) via `$panesFlipped` store
- **Width override**: Per-session pane width persistence

### State Management (42 nanostores in `src/store/`)

| Store | Purpose |
|-------|---------|
| `session.ts` | Active session, messages, gateway connection, session list, CWD, model |
| `boot.ts` | Boot phase, progress %, error state |
| `onboarding.ts` | Provider selection, OAuth flow, API key config |
| `composer.ts` | Input value, attachments, submit state |
| `composer-queue.ts` | Queued messages for sequential send |
| `composer-input-history.ts` | Input history for up/down arrow navigation |
| `layout.ts` | Sidebar open, panes flipped, pinned sessions, session limit |
| `panes.ts` | Per-pane width overrides |
| `profile.ts` | Active profile, profile scope, profile list |
| `preview.ts` | File/image preview targets |
| `gateway.ts` | Gateway connection state |
| `theme/context.tsx` | Active skin, light/dark mode (per profile) |
| `windows.ts` | Secondary window tracking |
| `updates.ts` | Update check/poller state |
| `notifications.ts` | Toast notification queue |
| `keybinds.ts` | Rebindable keyboard shortcuts |
| `command-palette.ts` | Command palette open/close |
| `cron.ts` | Cron job list, focus job ID |
| `subagents.ts` | Subagent states |
| `tool-view.ts` | Tool call view state |
| `tool-diffs.ts` | File diff state |
| `clarify.ts` | Clarification/approval prompts |
| `activity.ts` | Agent activity indicators |
| `voice-playback.ts` | Voice recording/playback |
| `haptics.ts` | Haptic feedback state |
| `model-visibility.ts` | Model visibility toggles |

All stores use **nanostores** (`@nanostores/react` + `nanostores`). Components subscribe via `useStore()`.
Non-rendering code reads with `$atom.get()`. Persistence lives beside the owning atom.

### Chat Architecture (`src/app/chat/`)

The chat view uses **@assistant-ui/react** for the thread/composer primitives, overlaid with custom components:

- **Thread**: Virtualized message list (`thread-virtualizer.tsx`), streaming message rendering
- **Composer**: Rich input with slash-command autocomplete, file/image attachments, voice recording
- **Message rendering**: `markdown-text.tsx` (Markdown → Shiki-highlighted code blocks),
  `compact-markdown.tsx`, `directive-text.tsx`, `ansi-text.tsx`
- **Tool calls**: `tool-approval.tsx`, `todo-tool.tsx`, `clarify-tool.tsx`, tool-fallback components
- **Preview**: `zoomable-image.tsx`, `code-card.tsx`, `diff-lines.tsx`, `disclosure-row.tsx`

### Slash Commands

Desktop slash commands are **curated client-side** in `src/lib/desktop-slash-commands.ts`:

1. **Built-in commands** (~19): Handled locally or via `commands.catalog` (e.g., `/help`, `/new`, `/skin`)
2. **Extension commands**: Skill-derived + `quick_commands` routed through `slash.exec` → `command.dispatch`
3. **Curation**: Terminal-only and messaging-only commands are excluded from the desktop palette.
   Extension commands always pass through the suggestion filter.

Pipeline: Renderer → `slash.exec` (persistent `_SlashWorker` subprocess) → `command.dispatch` fallback.

### Theme System (`src/themes/`)

- **Dual-axis**: `skin` (accent) × `mode` (light/dark/system)
- **Per-profile persistence**: Each profile remembers its own skin + mode assignment
- **Boot-time paint**: Applied before React mounts using `document.documentElement.style.setProperty()`
  to eliminate flash
- **Built-in skins**: `nous` (default), `mono`, `slate`, + user-installed custom themes
- **Color derivation**: Dark-mode skins auto-synthesize light variants via `synthLightColors()`
- **VS Code theme import**: Users can import themes from the VS Code marketplace
- **CSS injection**: 30+ custom properties set on `:root` feed shadcn/Tailwind utilities via `color-mix()`

### Onboarding Flow (`DesktopOnboardingOverlay`)

Multi-step provider selection overlay:
1. **Picker**: Featured OAuth providers (AetherOS, OpenAI, Anthropic, etc.) + API key option
2. **OAuth flow**: Device code, browser redirect, or external CLI command flow
3. **Model confirm**: Shows connected provider, default model with pricing/tier, option to change
4. **Cinematic exit**: Scramble-text decode animation → Begin button

Provider catalog is dynamically populated from backend's `getGlobalModelOptions()` with curated defaults
at the top and auto-discovered `api_key` providers appended.

### Updates System

- **Electron auto-updater** with branch selection (stable/beta/canary)
- **Poll-based**: `startUpdatePoller()` runs on interval, checks for available updates
- **Overlay**: `UpdatesOverlay` shows download progress, changelog, restart prompt

### Installer Targets (6 platforms)

| Platform | Format | Builder |
|----------|--------|---------|
| macOS (ARM) | .dmg | electron-builder |
| macOS (x64) | .dmg | electron-builder |
| Windows (x64) | .exe (NSIS) | electron-builder |
| Windows (ARM) | .exe (NSIS) | electron-builder |
| Linux (x64) | .AppImage | electron-builder |
| Linux (ARM) | .AppImage | electron-builder |

### Bootstrap Installer (`apps/bootstrap-installer/`)

Tauri v2 app that handles first-launch installation:
- Profile creation
- Python runtime detection/installation
- Backend setup and validation
- Desktop app launch after setup

## Chat Backend Communication

```
Renderer (JS)                       Python Backend
    │                                      │
    │── requestGateway(method, params) ──► │
    │   (via hermes:api IPC)               │
    │                                      │
    │◄── response ─────────────────────────│
    │                                      │
    │── WebSocket (direct) ──────────────► │
    │   (gateway WS URL from IPC)          │
    │                                      │
    │◄── events (delta, complete, tool,    │
    │      approval, clarify, etc.) ───────│
    │                                      │
    │── model / provider changes ────────► │
    │   (config.set via API)               │
    │                                      │
    │── slash command ───────────────────► │
    │   (slash.exec / commands.catalog)    │
    │                                      │
    │◄── command result ───────────────────│
```

### Key Backend Methods (from tui_gateway)

| Method | Purpose |
|--------|---------|
| `model.list` | List available models per provider |
| `model.current` | Get current model selection |
| `model.switch` | Switch active model |
| `config.get` | Read config values |
| `config.set` | Write config values |
| `commands.catalog` | List available slash commands |
| `complete.slash` | Auto-complete slash commands |
| `prompt.submit` | Submit user message |
| `session.list` | List sessions |
| `session.resume` | Resume session by ID |
| `slash.exec` | Execute slash command |

## Desktop-Only Features

1. **Native window management**: Titlebar (macOS traffic lights, Windows overlay), fullscreen,
   secondary session windows
2. **Node-pty terminal**: Persistent xterm.js terminal with resize, CWD-aware
3. **File system access**: Native dialogs, file watching, drag-and-drop
4. **Desktop notifications**: OS-native notification API
5. **Auto-updater**: Electron built-in with update branch selection
6. **Global hotkeys**: Rebindable keyboard shortcuts (including profile switching)
7. **Tray icon**: Background operation, quick-access menu
8. **Deep links**: `hermes://` protocol handler for blueprints
9. **Haptics**: Haptic feedback on supported devices
10. **Voice**: Speech-to-text via Web Speech API or backend STT
11. **Uninstaller**: Self-contained uninstall with cleanup summary
12. **VS Code theme import**: Browse and import themes from marketplace
