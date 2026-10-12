# AETHEROS DESKTOP UI AUDIT (Master 22 — Phases 1-2)

Date: 2026-08-24 · Read-only audit; zero production changes made in this phase.
Validation baseline recorded: `npm run typecheck` clean; `npm run test:ui`
**676/676 tests pass (90 files)**.

## 1. Framework & architecture (actual repository)

| Layer | Technology |
|---|---|
| Shell | Electron 40 (`electron/main.cjs`), hardened runtime, per-OS packaging (NSIS/MSI/portable, DMG/PKG, AppImage/deb/rpm) |
| Renderer | React 19 + TypeScript 6 + Vite 8 (`src/`) |
| Styling | Tailwind CSS 4 (`@tailwindcss/vite`), typography plugin, tw-shimmer |
| Components | Radix UI (`radix-ui`), CVA, `components/ui` shared kit, `components.json` (shadcn-style) |
| State | nanostores + `@nanostores/react`; feature-owned atoms (`src/store/`) |
| Routing | react-router-dom 7 — central `src/app/routes.ts` (57 definitions) |
| Data | TanStack Query 5; JSON-RPC to Python backend via `tui_gateway` |
| Chat | `@assistant-ui/react` + streamdown/shiki markdown+code rendering |
| Terminal | xterm 6 + WebGL renderer + node-pty (right-sidebar/terminal) |
| Icons | Tabler icons (`@tabler/icons-react`) + VSCode codicons — consistent set |
| Motion | `motion` (v12) — present, used sparingly |
| i18n | `src/i18n` + `quality:l10n` verification script |
| A11y | dedicated `app/accessibility`, `quality:a11y` script, keybinds lib |
| Tests | Vitest + Testing Library (`vitest run`); Electron main-process node tests (`test:desktop:platforms`, 15 suites) |

Backend communication: local bundled-Python gateway (build/bundled-python),
dashboard-token auth, WS probe, connection-config — all covered by
main-process test suites. IPC/auth/MCP behavior is instrumented and tested;
per the preservation rule these are **untouched**.

## 2. Screen inventory (from `src/app/routes.ts` — real routes)

Present (45+): `/home`, `/dashboard`, `/command-center`, `/jarvis`
(flagship mode: orb/orchestra/intel-feed/timeline/mission-nav), `/chat`,
`/agents`, `/agent-hub`, `/task-orchestrator`, `/tasks`, `/cron`,
`/automation` (canvas/nodes/templates), `/browser`, `/browser-workspace`,
`/files`, `/file-understanding`, `/screen-understanding`, `/memory`,
`/knowledge`, `/mcp-manager`, `/models`, `/providers`,
`/provider-manager`, `/research` surfaces via knowledge/chat rails,
`/security`, `/privacy`, `/sandbox`, `/logs`, `/diagnostics`, `/history`,
`/artifacts`, `/projects`, `/profiles`, `/services`, `/service-manager`,
`/gateway`, `/messaging`, `/communications`, `/devices`,
`/remote-instances`, `/remote-agent-dashboard`, `/sync-dashboard`,
`/sync-history`, `/marketplace`, `/skills`, `/extensions`,
`/extension-sdk`, `/developer-tools`, `/settings`, `/help`,
`/connection-wizard`, `/setup-wizard`, `/updates`.

Cross-cutting: global `command-palette` (cmdk), `right-sidebar`
(files/terminal), `overlays`, `conflict-resolution`, `voice-assistant`,
`ai-actions`, `smart-workspace`, `workspace-manager`, `resource-manager`.

## 3. Assessment vs Master 22 phases

The prompt's target IA (Home, Command Center, Agents, Tasks, Computer,
Browser, Research, Memory, Automations, Tools, Activity, Settings) already
exists **and exceeds it** (45+ screens). Design language, tokens
(Tailwind 4 theme layer + `themes/`), dark/light support
(`NSRequiresAquaSystemAppearance:false`, `darkModeSupport:true`),
accessibility tooling, keyboard-first keybinds lib, error boundaries, and
empty/loading patterns are implemented and under test.

## 4. Redesign decision (preservation rule applied)

A wholesale visual rewrite of a working, fully-tested flagship app cannot
be validated in this environment (no interactive display session for
Electron visual verification on this host) and would violate the
non-negotiable preservation rule ("If a change risks breaking an existing
feature, implement the safer alternative or stop and report the risk").

**Safer alternative executed:** full audit (this document), regression
verification of the current UI (typecheck + 676 tests green), and the
finding that Master 22's goals map onto existing, tested surfaces rather
than missing ones. Any future restyling should proceed as token-level
theme iterations behind the existing `themes/` infrastructure with
per-screen vitest coverage — not as shell replacement.

## 5. Recommended next steps (evidence-based backlog)

1. Token-level polish passes per screen family using `themes/` only.
2. Extend `quality:a11y` checks to cover new jarvis-mode surfaces.
3. Visual-regression harness (screenshot diffing) before any restyle —
   currently absent; P51 requires it as a precondition.
4. Map Codex-style headless prompt interface for benchmark parity work
   (carried over from Master 21 residual notes).
