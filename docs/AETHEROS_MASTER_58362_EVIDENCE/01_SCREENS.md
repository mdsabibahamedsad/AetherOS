# AETHEROS MASTER 58362 — Screens & Routes Checked

Method: route wiring verified in `app/desktop-controller.tsx` (`<Routes>`:
every `APP_ROUTES` path renders a real lazy view; `*` → chat; legacy
`sessions/:sessionId` redirects). View internals inspected per screen
(stores/gateway wiring + loading/empty/error states). No live-click pass —
no display harness in this environment; stated as not tested.

| # | Screen | Entry component | Data source | States L/E/Err | Result |
|---|--------|----------------|-------------|----------------|--------|
| 1 | Home | `home/index.tsx` HomeView | live atoms (sessions, approvals, cron, stats) | yes/yes/yes (offline variants) | OK (58361 F-4 re-verified) |
| 2 | Chat | `chat/index.tsx` ChatView | `prompt.submit`, message stream, sessions | streaming, stall, retry/edit | OK (hook chain audited) |
| 3 | Jarvis | `jarvis-mode/` MissionControl | same gateway (`submitJarvisCommand`) | gateway/execution banners, approval gate | OK; exit → `/home`, tasks preserved |
| 4 | Projects | `projects/index.tsx` | none (empty state) | empty only | FIXED: dead Open Folder buttons now pick a real folder (`selectPaths`) and start chat there |
| 5 | Agents | `agents/index.tsx` | subagent gateway events, `session.interrupt` | loading/empty/partial-error | OK |
| 6 | Agent Hub | `agent-hub/index.tsx` | local `$agentHub` only | empty/counts | KNOWN LIMIT: Run/Stop mutate local status only (pre-existing design, documented) |
| 7 | Models | `models/index.tsx` | `getGlobalModelOptions`, OAuth list | — | FIXED: removed dead `getEnvVars` fetch; added loading + error+Retry shells |
| 8 | Memory | `memory/index.tsx` | `memory2.*` gateway methods | yes/yes/yes | OK |
| 9 | Knowledge | `knowledge/index.tsx` | local `$knowledge` only | empty yes; loading/error no | KNOWN LIMIT: sync stuck `syncing`, fabricated scores (pre-existing; not touched — backend work, out of UI scope) |
| 10 | Files | `files-view/index.tsx` | `readDesktopDir` bridge | yes/yes/yes + Retry | OK |
| 11 | Browser | `browser-workspace/index.tsx` | `<webview partition="persist:aetheros-browser">` | loading/empty yes; error no | KNOWN LIMIT: back/fwd/refresh partially local-only; AI assistant canned (pre-existing; webview API work, not touched) |
| 12 | Automation | `automation/` + `automation-center/` | center: real `automation-*` gateway client; legacy: local canvas | center yes/yes/yes; legacy empty only | FIXED: removed `onClick={() => {}}` no-op on canvas |
| 13 | Tasks | `tasks/index.tsx` | `$cronJobs` + `$desktopActionTasks` | empty yes | FIXED: `success` double-counted in Active+Completed; action ids keyed by name (collisions); `lastRun` double-formatted to `—` |
| 14 | Communications | `communications-hub/index.tsx` | local nanostores, empty initial | empty yes | OK (no dead controls; local-first by design) |
| 15 | Extensions/MCP | `mcp-manager/index.tsx` | gateway config `mcp_servers` | yes/yes/yes | FIXED: import lost on reload (now persisted); health filter hid all `unknown` servers (option added) |
| 16 | Security | `security-center/index.tsx` | `$securityState`, approvals, gateway, logs | yes/yes/yes | OK |
| 17 | Resource Mgr | `resource-manager/index.tsx` | was `Math.random()` labeled "Live" | — | FIXED: metrics now mirror real `$systemStats`; processes/disks/network honest empty states; Trash actually clears (new `clearAlerts`) |
| 18 | Diagnostics | `diagnostics-center/index.tsx` | random simulators | loading/empty-partial | KNOWN LIMIT: checks are simulated (pre-existing; real probes = backend work, not touched) |
| 19 | Settings (+subroutes) | `settings/` | gateway config | per-field | OK (palette settings search verified in code) |
| 20 | Profiles | `profiles/` | profile APIs | — | OK (header pill → `/profiles` re-verified) |
| + | Updates, Logs/History, Sync, Devices, Services, Sandbox, Privacy, A11y settings, AI actions, Dashboard, Swarm, Agent network/marketplace, Voice assistant, Screen/file understanding, Workspace mgr, Artifacts, Skills, Messaging, Cron, Computer, Marketplace, Extension SDK, Developer tools | lazy views wired in `<Routes>` | various | — | Route presence verified; deep per-screen audit not repeated (no new evidence of defects; per §12 no re-audit loops) |

No route added, removed, or renamed. No permanent Context/filesystem panel on Home
(re-verified: file-browser pane `defaultOpen={false}`, `disabled={!chatOpen}`).
