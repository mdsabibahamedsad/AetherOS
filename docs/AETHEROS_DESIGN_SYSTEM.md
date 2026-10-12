# AetherOS Design System

Canonical token and component reference for the desktop renderer
(`apps/desktop/src`). Status: implemented for tokens + registry + global
status; component consolidation is incremental (see migration §).

## 1. Tokens — single source of truth

TypeScript: `src/design-system/tokens/` (`color`, `spacing`, `typography`,
`radius`, `elevation`, `motion`, `breakpoints`, `zIndex`, `opacity`,
`density`, aggregated in `tokens/index.ts`).
CSS: `src/design-system/tokens/css-variables.css` (light `:root`, `.dark`
overrides, `[data-density]`, `prefers-reduced-motion`).

### Canonical public names (Master 63 §4)

Components MUST consume `--aether-*`. Backing store `--color-*` remains.

| Token | Maps to | Use |
|---|---|---|
| `--aether-bg` | `--color-bg` | app background |
| `--aether-surface` | `--color-bg-surface` | cards, panels |
| `--aether-surface-elevated` | `--color-bg-surface-elevated` | popovers, dialogs |
| `--aether-border` | `--color-border` | all borders |
| `--aether-text` | `--color-fg` | primary text |
| `--aether-text-muted` | `--color-fg-muted` | secondary text |
| `--aether-accent` | `--color-primary` | actions, links, focus |
| `--aether-success` | `--color-success` | success states |
| `--aether-warning` | `--color-warning` | warnings, pending |
| `--aether-danger` | `--color-destructive` | destructive, critical |
| `--aether-info` | `--color-info` | informational |

Status/risk/trust/classification scales live in `tokens/color.ts`
(`status.*`, `risk.*`, `trust.*`, `classification.*`) with matching
`--color-status-*` / `--color-risk-*` / `--color-trust-*` /
`--color-class-*` CSS vars. Color is never the sole signal — pair with
icon + text (§83 of the brief).

### Rules

- No arbitrary hex in components; no new brand gradients (calm, minimal,
  precise — the existing blue/cyan/purple gradient is brand-reserved).
- Dark mode is designed, not inverted (independent surfaces, borders,
  shadows, focus rings in both modes).
- Motion: short, interruptible, purposeful; durations zero under
  `prefers-reduced-motion`. Motion never carries state by itself.
- Density via `[data-density]` (`compact` / default / `cozy`).

## 2. Typography scale

Display / h1–h6 / body(-lg,-sm,-xs) / label(-sm) / button(-sm) / caption(-sm)
/ metadata / code(-sm,-lg) — see `--text-*` vars. One hierarchy; metric and
code faces reserved for numbers and code respectively.

## 3. Components

Primitive library: `src/components/ui/` (Button, Dialog, Card, Table, Tabs,
Command, Switch, Select, Tooltip, EmptyState, ErrorState, Skeleton, …).
Product components added in Master 63:

- `src/components/system-status/global-status.tsx` —
  `useGlobalStatus()` / `GlobalStatusIndicator` / `StopAllAgentsButton`.
- Navigation registry `src/navigation/canonical.ts` (IA, not a visual).

Every component MUST expose: typed props, loading/disabled/error states
where relevant, keyboard behavior, and accessible names. New canonical
components (`AgentCard`, `TaskCard`, `ApprovalCard`, …) should be built on
the primitives + `--aether-*` tokens when their screens are rewired — not
as competing systems.

## 4. Icon system

Codicons (`@/components/ui/codicon`, `@vscode/codicons`) + curated
`@/lib/icons`. One library per surface; icons carry semantic meaning and
accessible labels/tooltips when ambiguous; never emoji as status.

## 5. Migration (§151–§152 of the brief)

`Old → New → Compat → Migrate → Remove`, one surface per release.
Known duplicates to consolidate next: legacy `src/design-system/components/`
(radix wrappers with pre-existing type drift — tsc reports errors there on
current main) vs `src/components/ui/`; dashboard simulated cards vs real
stores; `marketplace` sample views vs `/api/plugins/marketplace/*`.
Do not add a third button/modal/badge system.
