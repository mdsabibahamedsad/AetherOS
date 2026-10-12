# Aetheros — Web UI

Browser-based dashboard for managing Aetheros configuration, API keys, and monitoring active sessions.

## Stack

- **Vite** + **React 19** + **TypeScript**
- **Tailwind CSS v4** with custom dark theme
- **shadcn/ui**-style components (hand-rolled, no CLI dependency)

## Development

```bash
# Start the backend API server
cd ../
python -m aetheros_cli.main web --no-open

# In another terminal, start the Vite dev server (with HMR + API proxy)
cd web/
npm install
npm run dev
```

Open the **Vite URL** printed in the terminal (usually `http://localhost:5173`). That is the live-reload UI.

`hermes dashboard` on port 9119 serves the **built** bundle from `aetheros_cli/web_dist/`, not the Vite dev server — changes in `web/src/` will not appear there until you run `npm run build` and restart the dashboard (or use `web --no-open` + Vite as above).

The Vite dev server proxies `/api` requests to `http://127.0.0.1:9119` (the FastAPI backend).

## Build

```bash
npm run build
```

This outputs to `../aetheros_cli/web_dist/`, which the FastAPI server serves as a static SPA. The built assets are included in the Python package via `pyproject.toml` package-data.

## Structure

```
src/
├── components/         # Reusable UI components
│   ├── AuthWidget, Backdrop, Sidebar*, LanguageSwitcher, ThemeSwitcher
│   └── ui/             # UI primitives (Card, Badge, Button, Input, etc.)
├── contexts/           # React context providers (PageHeader, Profile, SystemActions)
├── hooks/              # Custom React hooks (useSidebarStatus)
├── i18n/               # Internationalization
├── lib/
│   ├── api.ts          # API client — typed fetch wrappers for all backend endpoints
│   ├── utils.ts        # cn() helper for Tailwind class merging
│   └── dashboard-flags.ts
├── pages/
│   ├── agent-hub/      # Agent management hub (23 pages)
│   │   ├── AgentHubPage, AgentListPage, AgentDetailPage
│   │   ├── AgentConfigPage (11-tab editor)
│   │   ├── AgentTemplatesPage, AgentOrchestrationPage
│   │   ├── AgentKnowledgePage (8 source types)
│   │   ├── AgentSecurityPage, AgentAnalyticsPage
│   │   ├── AgentPermissionsPage, AgentMemoryPage
│   │   ├── AgentSearchPage, AgentTagsPage
│   │   ├── AgentLogsPage, NotificationsPage
│   │   ├── AutomationBuilderPage, TaskManagerPage
│   │   ├── MonitoringDashboardPage, MarketplacePage
│   │   ├── WorkflowRunnerPage, SchedulerPage
│   │   └── BackgroundServicesPage
│   ├── SecurityCenterPage, PermissionsPage, SecretsPage
│   ├── AuditLogPage, ThreatMonitorPage, SandboxManagerPage
│   ├── IntelligenceDashboardPage, AgentMonitorPage
│   ├── ConfigPage, EnvPage, DocsPage, FilesPage
│   ├── SessionsPage, LogsPage, AnalyticsPage
│   ├── ModelsPage, CronPage, SkillsPage, PluginsPage
│   ├── McpPage, PairingPage, ChannelsPage, WebhooksPage
│   ├── SystemPage, ProfilesPage, ProfileBuilderPage
│   ├── ChatPage, LiveChatPage, MemoryViewerPage
│   ├── KnowledgeGraphViewerPage, PlanningViewPage
│   └── agent-hub/index.ts  # Re-exports all agent-hub pages
├── plugins/            # Plugin system (discovery, slots, manifests)
├── store/              # Zustand state management
│   ├── agent-store.ts  # Server-backed agent CRUD, task, config, memory
│   └── agent-hub-local.ts  # Local (persisted) favorites, knowledge, security, analytics
├── themes/             # Theming system
├── App.tsx             # Main layout + sidebar + routing (55+ routes)
├── main.tsx            # React entry point
└── index.css           # Tailwind imports and theme variables
```

## Agent Hub Local Store

Persisted to localStorage (`aetheros-agent-hub-local`):

| Slice | Description |
|-------|-------------|
| `favorites` | Starred agents with `FavoriteAgent` entries |
| `knowledge` | Knowledge attachments per agent with 8 source types (pdf, markdown, word, text, website, git, folder, images) |
| `securitySettings` | Per-agent security config (sandbox, access control, resource limits, approval, audit) |
| `analytics` | Per-agent analytics (daily stats, top tools/models, costs, trends) |
| `exportQueue` | Pending export payloads |

## Key Pages

### Agent Config (`/agent-hub/config/:id`)
11-tab editor: General, Prompt, Memory, Knowledge, Tools, Models, Automation, Security, Permissions, Logs, Analytics.

### Agent Knowledge (`/agent-hub/knowledge`)
Add/manage knowledge sources of 8 types. Each source tracks status (indexing → ready/error), chunk count, and size.

### Agent Security (`/agent-hub/security`)
Per-agent sandbox configuration, network/filesystem access controls, domain allow/block lists, resource limits (memory, CPU, timeout), approval-required actions, audit logging, and secrets scope.

### Agent Analytics (`/agent-hub/analytics`)
Dashboard with metric cards (messages, response time, tool calls, sessions, cost), daily token usage bar chart, top tools/models with usage bars, and cost trend chart. Supports 7/14/30/90 day ranges.

### Templates (`/agent-hub/templates`)
15 built-in templates fallback when the API is unavailable (General Assistant, Research Analyst, Software Engineer, Content Writer, Data Analyst, DevOps Engineer, Security Analyst, Automation Engineer, Communications Agent, Web Browser Agent, Project Manager, Creative Writer, ML/AI Engineer, Customer Support Agent).

## Typography & contrast rules

Read before adding or editing UI styles. These rules keep the dashboard legible across all built-in themes and stop drift back into the patterns the design system was just refactored out of.

### Text size floor

- **Minimum body size: `text-xs` (12px / 0.75rem).** Do not use arbitrary `text-[0.6rem]`, `text-[0.65rem]`, `text-[9px]`, `text-[10px]`, or `text-[11px]` on copy, hints, labels, counts, or badges. Use the standard scale: `text-xs`, `text-sm`, `text-base`.
- Smaller sizes are only acceptable on **decorative overlays** (chart stripes, empty-state icons) — never on text the user is meant to read.

### Opacity floor on text

- **Never apply opacity below 0.7 to text.** No `opacity-30`, `opacity-50`, `opacity-60` on `<span>`s, `<p>`s, labels, etc.
- **Do not stack opacity tokens.** Patterns like `text-muted-foreground/60`, `text-midground/70`, `text-foreground/50` create unpredictable WCAG failures because the parent token already has alpha.
- Use the **semantic text tokens** from `@nous-research/ui`'s `globals.css`:
  - `text-text-primary` — default body text.
  - `text-text-secondary` — subtitles, meta, inactive nav.
  - `text-text-tertiary` — small chrome labels, counts, footnotes.
  - `text-text-disabled` — disabled states.
  - `text-text-on-accent` — text on filled accent surfaces.

### Brand uppercase via `text-display`, not raw `uppercase`

- The dashboard preserves the Nous brand uppercase aesthetic, but it is **opt-in per element, not global**.
- Apply uppercase via the DS utility `text-display` on **brand chrome only** — page titles, nav section headings, badges, brand wordmark. DS components (`Button`, `Badge`, `Tabs`, `Segmented`, etc.) already self-apply `text-display`.
- **Do not introduce new `uppercase`** (the literal Tailwind class) in `aetheros/web/src`. Prefer `text-display` for new brand chrome. Legacy `uppercase` call sites (e.g. `components/ui/label.tsx`, `card.tsx`) remain until migrated.
- The app shell no longer forces uppercase globally, so blanket `normal-case` opt-outs are unnecessary. Use `normal-case` only where a DS component applies `text-display` but the label should stay sentence case — e.g. dynamic user content (model slugs, theme names) **or** fixed UI copy that is not brand chrome (EnvPage “not configured” toggle, sidebar “New chat”).

### Fonts

Typography is **opt-in per surface**, not global on layout shells — the app shell and page header keep their original theme/expanded fonts; Mondwest applies only where explicitly set.

| Tier | Classes | Use for |
|------|---------|---------|
| Brand chrome | `font-mondwest text-display` (or `themedChrome`) | Sidebar nav, card section headers (`CardTitle`), Segmented filter buttons, filter panel headings |
| Themed body | `font-mondwest normal-case` (or `themedBody`) | Card content (`Card`, `CardDescription`), session/platform rows, analytics tables — **scoped to the component** |
| Page chrome | `font-expanded` | Page header h1 (`PageHeaderProvider`) — sentence case, not `text-display` |
| Wordmark | `Typography` + size/tracking only | Sidebar/mobile “Aetheros” — mixed case, no Mondwest, no `text-display` |
| Technical | `font-mono-ui` / `font-mono` / `font-courier` | Model slugs, env keys, schedules, YAML, repo URLs |

- Do **not** put `themedBody` or `themedFont` on `<main>`, `App`, or other layout wrappers — it overrides component-scoped styles.
- **`Card`** applies `themedBody`; **`CardTitle`** uses `text-display` (uppercase chrome); **`CardDescription`** uses `themedBody`.
- **`NouiTypography`** defaults to `font-sans` unless a font prop is passed.
- Do **not** use raw `font-sans` or `font-display` (theme sans variable) on new dashboard UI — prefer Mondwest tiers above where brand-appropriate.

### Color tokens

- Prefer **semantic tokens** (`text-text-*`, `bg-card`, `border-border`, `text-foreground`, `text-destructive`, `text-success`, `text-warning`) over raw layer references (`text-midground`, `text-foreground`).
- `text-muted-foreground` is now wired to `--color-text-secondary`, so existing call sites stay correct, but new code should prefer the semantic name.
- When you genuinely need a non-token color (icon de-emphasis on a chart, terminal foreground via inline style), keep alpha at `≥ 0.7` for any text.

