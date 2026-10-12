# AetherOS Screen Inventory (Complete Redesign — Audit Phase)

Source of truth for what exists in `apps/desktop/src/app` vs the route
table in `src/app/routes.ts` (`APP_ROUTES`) and the curated IA in
`src/navigation/canonical.ts`. Inspected 2026-09-10; statuses reflect
current source, not aspirations.

## Route-level defects found (fixed in this pass)

| # | Defect | File | Fix |
|---|---|---|---|
| 1 | Sidebar Home pointed at `/` (the chat view), so Home was unreachable from nav | `src/store/navigation.ts:45` | route → `/home` |
| 2 | Sidebar Chat pointed at `/chat`, which is NOT a registered route — `routeSessionId('/chat')` treats it as session id `"chat"` | `src/store/navigation.ts:47` | route → `/` (`NEW_CHAT_ROUTE`) |
| 3 | TopBar search committed to `/search`, unregistered → opened/broke into a bogus `search` session | `src/app/shell/topbar.tsx:27` | Enter opens the real command palette |
| 4 | TopBar "New Chat" → `/new`, unregistered → bogus `new` session | `src/app/shell/topbar.tsx:67` | → `/` |
| 5 | TopBar Notifications → `/notifications`, unregistered → bogus session | `src/app/shell/topbar.tsx:68` | → `/communications` (real hub) |
| 6 | Sidebar Extensions children → `/extensions/marketplace`, `/extensions/mcp`, both unregistered | `src/store/navigation.ts:64-65` | → `/marketplace`, `/mcp-manager` |
| 7 | No wolf identity in the primary chrome (sidebar/topbar); BrandMark only in loader/onboarding/about/updates | various | wolf header added to `left-sidebar.tsx` |

## Screen inventory (by canonical group)

### Workspace
| Screen | Route | Purpose | Problems | New experience | Migration |
|---|---|---|---|---|---|
| Home | `/home` | Live operational state | Was dashboard-like card grid; now intent-led workspace (this pass) | Intent input + context sections + suggested actions, all live-backed | REDESIGNED |
| Chat (new/session) | `/`, `/:id` | Agent collaboration | Fine; composer draft handoff now used by Home intent input | Unchanged this pass | KEPT |
| Tasks | `/tasks` | Task objects | Functional | Unchanged | KEPT |
| Activity (Command Center) | `/command-center` | Unified activity | Overlay view; functional | Unchanged | KEPT |

### Execute
| Screen | Route | Purpose | Problems | Migration |
|---|---|---|---|---|
| Computer | `/computer` | Computer-use sessions | Decorative controls, no IPC (known gap, Master 63) | DOCUMENTED, not redesigned |
| Browser | `/browser` | Shared browser workspace | Functional webview | KEPT |
| Research/Knowledge | `/knowledge` | Research jobs | Local mock layer (known gap) | DOCUMENTED |
| Automations | `/automation-center`, `/automation` (legacy), `/cron` | Schedules/triggers/history | Two automation surfaces overlap | DOCUMENTED; canonical nav prefers `/automation-center` |
| Swarm | `/swarm` | Multi-agent runs | Functional | AgentCard pattern available for future rows |

### System
| Screen | Route | Purpose | Problems | Migration |
|---|---|---|---|---|
| Memory | `/memory` | Inspectable memory | Functional | KEPT |
| Models | `/models` | Model resources | Functional | KEPT |
| Artifacts | `/artifacts` | Artifact browser | Functional | KEPT |
| MCP | `/mcp-manager` | Servers/trust/health | Fixed in Master 63 (real config) | KEPT |
| A2A | `/agent-network` | Remote agents/trust | Functional | KEPT |
| Security | `/security` | Approvals/policies/audit | Functional shell | KEPT |

### Build
| Screen | Route | Purpose | Problems | Migration |
|---|---|---|---|---|
| Marketplace | `/marketplace` | Extensions | Sample catalog + fake install (known gap) | DOCUMENTED |
| Agent marketplace | `/agent-marketplace` | Agent services | Functional | KEPT |
| Developer tools | `/developer-tools` | SDK/API/logs | Functional | KEPT |
| Extension SDK | `/extension-sdk` | Authoring | Functional | KEPT |
| History | `/history` | Run history | Functional | KEPT |

### Manage
| Screen | Route | Purpose | Problems | Migration |
|---|---|---|---|---|
| Devices | `/devices` | Registered devices | Hardcoded device (known gap) | DOCUMENTED |
| Sync | `/sync` | Backup/sync/conflicts | Simulated sync (known gap) | DOCUMENTED |
| Workspaces/Profiles | `/profiles`, `/workspace-manager` | Project context | Two overlapping surfaces | DOCUMENTED |
| Settings (+developer/advanced/multimodal/accessibility) | `/settings*` | Configuration | Large but functional, searchable | KEPT |

### Duplicates / legacy
- `design-system/components/*` (legacy radix wrappers, type drift) vs `components/ui/*` (canonical). Rule: all new work uses `components/ui`; legacy removal is a tracked task, not done here.
- `COMMAND_CENTER` vs `dashboard` vs `activity` overlap: canonical nav exposes one (Activity).
- `hermes.ts` is the gateway API layer, not UI — kept. No other "Hermes UI" skin remains; remaining legacy is structural (above), not branding.

## Component inventory (reused, not reinvented)
`components/ui/*` (~50 primitives incl. Button, Card, Dialog, Command,
EmptyState, ErrorState, Skeleton, StatusDot, Kbd), `design-system/tokens/*`
+ `--aether-*` CSS aliases, `BrandMark` (wolf SVG), `GlobalStatusIndicator`
/ `StopAllAgentsButton`, new `AgentCard` (this pass), `EmptyState`
(canonical "never bare No data" pattern — extended with wolf option).
