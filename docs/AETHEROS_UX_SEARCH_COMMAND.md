# Universal Search & Command (Phases 5–6)

## Search model
Topbar intent field is an affordance, not a route: Enter opens the
command palette (prior fake `/search` navigation removed). Palette
searches live sources — sessions (active + archived), config fields,
API keys surface, MCP servers, settings sections, themes — with
multi-term substring matching (no fuzzy noise). Semantic queries
("presentation edited last week") remain a documented gap: no fake
semantic ranking added.

## Command model (new this pass: Tasks & Agents group)
Every command shows action + context; results are navigations to
registered routes or real gateway calls:
- Open Task Center → `/tasks` (task/create/jobs keywords)
- Switch Model → `/models`
- Review Approvals → `/security` (approval/permission keywords)
- Stop Active Session → real `session.interrupt` via
  `lib/session-actions.ts` (`stopActiveSession`); reports
  no-active-session / offline honestly; gateway errors propagate to a
  truthful notification. Never silent, never ambiguous: stop targets
  the one active session id shown in context.

## Keyboard-first (Phase 29 audit)
Existing system (`lib/keybinds/actions` + `store/keybinds`): persisted
overrides, conflict surfacing in the keybind panel, canonical combos.
Coverage: ⌘K palette, ⌘N session, ⌘B/J panes, ⌘, settings, ⌘.
command center, ⌘/ shortcuts, composer keys, profile/session switching,
terminal toggle. No conflicts introduced; palette renders live combos
per item. Voice exists as recorder input to the same composer — one
intent system, not a parallel product.
