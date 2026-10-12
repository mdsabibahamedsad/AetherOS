# AETHEROS MASTER PROMPT 2 REPORT

## UX Architecture
- Audited repo-wide (routes, shell, palette, agents, tasks, composer, gateways, overlays, keybinds, i18n, terminal, files, settings, onboarding). Map: `AETHEROS_UX_ARCHITECTURE_MAP.md`. Fixed 7 dead nav destinations (prior pass); palette extended; no new top-level routes; duplicates tracked, not force-merged.

## Information Architecture
- Concept model fixed: HOME / AGI / WORKSPACE / TASKS / AGENTS / FILES / APPS / AUTOMATIONS / TERMINAL / SYSTEM over the existing 60+ routes via the canonical registry. Current→target migration documented; user always knows where they are (breadcrumbs via context chain), what the system is doing (live status), what needs attention (ranked), how to return (back/home/palette/drafts).

## OS Shell
- Persistent calm shell kept and repaired: truthful nav, intent topbar → real palette, statusbar truth, overlay cards, portal notifications, prompt overlays with refusal-on-dismiss. No new chrome weight.

## AGI Interaction
- The loop Ask→understand→plan→approve→execute→progress→result→continue runs on real plumbing: Home intent → composer draft → session → subagents → artifacts + deep-link notifications. New: transparent scope line ("Using context from: …"), no silent memory injection.

## Agents
- First-class entities: `AgentCard` header (status, done/total, tool, model, tokens, files, Inspect/Stop), subagent tree, delegation groups, 11-state mapping onto real states. No chain-of-thought anywhere.

## Tasks
- `/tasks` unifies scheduled + action tasks; palette adds Task Center entry; stop/approve/retry where the backend honors them. No fake progress.

## Workspaces
- Profiles (isolated, per-socket) + projects + draft restore = resume. One-surface merge tracked; both stay functional.

## Search & Command
- Search executes the real palette (sessions/config/MCP/settings/themes); new Tasks & Agents group (Task Center, Switch Model, Review Approvals, Stop Active Session — all real). Keyboard system audited, no conflicts, live combos in UI. Semantic search remains a stated gap, not a fake.

## Files & Apps
- Files native with honest states; AGI file actions route to the composer as suggestions; terminal keeps full power with shared context; all apps inherit shell + design language; no desktop simulation.

## Notifications
- Ranked kinds, error summarization (no stacks), deep-link actions, overflow grouping, sticky errors, haptics. Actionable, never spam.

## Permissions
- WHAT/WHY/SCOPE/RISK/CONSEQUENCE, scoped grants, dismissal = refusal, one approval truth (Security), palette + Home link to it. No dark patterns.

## Automation
- TRIGGER→CONDITIONS→ACTIONS→RESULT with history, failure/retry, and real STOP ALL leg. Depths documented, not simplified away.

## Responsive
- Viewport, collapsing rail, capping overlays, wrapping new surfaces. Tablet/mobile-dedicated models tracked as the gap.

## Accessibility
- Focus-visible globals, Radix dialogs, live regions, non-color status, reduced-motion, density modes. New code follows all patterns. No axe run / manual AT pass claimed.

## Performance
- Virtualized threads/sessions; zero new loops/effects/assets this pass; route-splitting recorded as top follow-up. Suite: 106 files, ~40s.

## Legacy Hermes Cleanup
- Zero user-facing Hermes strings found (all locales, all views). Technical identifiers (`hermes.ts`, env, CLI) preserved deliberately. Terminology verified canonical; "Bot" only where platforms require it.

## Files Changed
- Created: `lib/context-model.ts` (+test), `lib/session-actions.ts` (+test), 7 docs.
- Modified: `app/command-palette/index.tsx` (Tasks & Agents group), `app/home/index.tsx` (scope line).
- Deleted: none (nothing proven safe).
- Untouched by design: backends, brand modules, overlays, composer, themes, fabricated-surface gaps.

## Tests
- New: 8 tests (context chain/summary/scope, stop outcomes incl. offline propagation) — pass.
- Full `vitest run`: 734/737 pass; 3 failures are pre-existing `design-tokens.test.ts` themes-drift, unrelated and unmodified.
- `tsc --noEmit`: clean on all touched files. `eslint`: 0 errors on all touched files.

## Remaining Issues
1. Six fabricated surfaces (computer, research, marketplace, sync, devices, dashboard). 2. Route code-splitting. 3. Semantic search. 4. Workspace/profile surface merge. 5. Component-lib + icon + theme-layer consolidation. 6. Tablet/mobile models. 7. Axe + manual AT pass. 8. Pre-existing themes test drift + repo-wide lint backlog.

## Master Prompt 3 Recommendations
1. Wire the six fabricated surfaces to real backends (marketplace first — API exists). 2. Route-group code-splitting with measured budgets. 3. Semantic search over sessions/files/artifacts. 4. Merge automation + workspace surfaces. 5. Codemod legacy component lib, then delete. 6. Icon-family allowlist + lint. 7. A11y automation + AT pass. 8. Mobile navigation model.
