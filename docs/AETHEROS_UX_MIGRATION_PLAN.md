# AetherOS UX Migration Plan (Complete Redesign)

How the full vision lands without destroying working functionality.
Rule: preserve APIs and business logic; migrate screens incrementally;
never ship fabricated state.

## Phase 0 — Repair navigation truth (THIS PASS, done)
- `store/navigation.ts` routes corrected to registered paths; new
  `store/navigation-routes.test.ts` enforces every sidebar route resolves
  in `APP_ROUTES` (or is `/`, the chat root).
- TopBar: search commits to the real command palette; New Chat → `/`;
  Notifications → `/communications`.
- Sidebar gains wolf identity header (`BrandMark` + wordmark).

## Phase 1 — Intelligent Home (THIS PASS, done)
- Intent input ("Ask AetherOS…") → `stashSessionDraft(null, text, [])` +
  navigate `/`: real composer handoff, zero fake execution.
- Context sections (attention / active work / system+model / automations)
  stay live-backed (Master 63 rule); suggested actions derive from real
  state and navigate to real routes only.

## Phase 2 — Agent workspace language (THIS PASS, component + integration)
- New `components/agent/agent-card.tsx`: identity, goal, status summary
  (done/total across node tree), current tool, model, tokens, files,
  elapsed; Inspect/Stop actions; collapsed stream preview. Pure-props,
  no store coupling, tested.
- Integrated as the Agents overlay header for the active session
  (Stop → real `session.interrupt` via `$gateway`, disabled offline).
- Subagent rows untouched (working, tested behavior preserved).

## Phase 3 — Universal command layer (NEXT)
- Palette already real (sessions/config/MCP/archived/theme). Remaining:
  agent/task/approval/model actions, natural-language verb mapping
  (open/create/automate/research/explain…), voice entry point, contextual
  "this" resolution (current folder/session/scope passed as context).

## Phase 4 — Workspace system (NEXT)
- Workspace types (dev/research/writing/automation/personal/ops) as
  saved context bundles over existing profiles + projects + smart-workspace
  stores. No new state system per page; centralize in store.

## Phase 5 — Remaining fabrication removal (NEXT, in order)
1. Plugin marketplace → `/api/plugins/marketplace/*` (backend exists).
2. Sync dashboard → real sync/backup state (fake timer removed, honest
   `Unavailable` first).
3. Devices → registered-device source or honest empty state.
4. Computer view → IPC-backed or honest degraded mode.
5. Research/knowledge → gateway-backed or honest unavailable.
6. Dashboard activity → real stores or removal behind canonical Activity.

## Phase 6 — Consolidation (NEXT)
- One card/badge/dialog/tooltip system (`components/ui` wins); delete
  `design-system/components` legacy wrappers after codemod.
- Single automation surface (merge `/automation` into `/automation-center`
  as legacy alias); single workspace surface (profiles ⊕ workspace-manager).
- Settings: keep structure, add natural-language intent mapping as a
  translation layer over existing keys (never a parallel settings store).

## Non-goals / guardrails
- No new primary symbol; wolf only, used sparingly (chrome, boot, empty
  states, presence, about, notifications fallback).
- Dark-first, light-complete; no neon excess; motion short + reduced-motion
  safe; WCAG AA+; mobile adapts interaction model (not shrunk desktop).
- Performance: no new polling loops (this pass adds none); virtualize long
  lists before claiming scale.
