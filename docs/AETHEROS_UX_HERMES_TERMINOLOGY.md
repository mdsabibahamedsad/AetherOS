# Legacy Hermes UX Audit + Terminology + Consolidation (Phases 37–38, 41)

## Hermes audit: no user-facing legacy brand remains
Searched renderer, i18n (all locales), components, and app views:
- Zero "Hermes" logos, icons, favicons, splash, screenshots, or UI copy.
- Remaining references are TECHNICAL and preserved deliberately:
  `src/hermes.ts` (+ `@/hermes` imports, ~40 files), `use-hermes-config`
  hook filename, code comments citing the `hermes` CLI, `AETHEROS_HOME`,
  gateway env vars. Renaming any of these risks APIs, imports, CLI
  compat, and stored data for zero visual gain.
- Rule applied: user-facing brand vs technical backward compatibility —
  brand is 100% AetherOS; identifiers stay.

## Terminology (canonical, verified in use)
Agent (not bot/assistant/worker — "Bot token" appears ONLY as
messaging-platform credential labels, correct domain usage) · Task ·
Workspace (profile) · App (route view) · Automation (persistent
trigger→result) · Permission/Approval · Notification · Command (palette
entry) · Context (scoped chain) · Result/Artifact. Voice "assistant" is a
feature name, not a concept competitor. No renames needed; glossary
recorded here to block drift.

## Component consolidation
ONE SYSTEM direction: `components/ui` wins; legacy
`design-system/components` (type drift) is quarantined — new code
forbidden there, codemod + delete tracked. Single card/badge/dialog/
tooltip/toast/status/progress grammar already holds in touched surfaces;
`AgentCard`/`AgiActivityList` extend it, not duplicate it. No one-off UX
patterns added this pass. No files deleted (nothing proven safe to
delete — deletions require the codemod first).
