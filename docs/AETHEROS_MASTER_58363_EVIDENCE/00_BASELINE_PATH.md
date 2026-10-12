# AETHEROS MASTER 58363 — Baseline & Canonical Path (2026-10-12)

## Reports read (all exist)
- `docs/AETHEROS_MASTER_58361_UI_REDESIGN_REPORT.md` → `AETHEROS_UI_REDESIGN_PARTIAL`
- `docs/AETHEROS_MASTER_58362_UI_FINALIZATION_REPORT.md` → `AETHEROS_UI_FINALIZATION_PARTIAL`
- Evidence dirs `AETHEROS_MASTER_58361_EVIDENCE/` (00–05) and
  `AETHEROS_MASTER_58362_EVIDENCE/` (00–04) — read.
- Fix Ledger tail — 58362 entry present. Tree is not a git checkout (no git ops).

## Canonical execution path (traced, not assumed)
Single gateway-agent runtime; no second brain:
- Home composer → `stashSessionDraft(null, text, [])` → `/` → chat composer
  `takeSessionDraft(null)` → `submitText` → `submitPromptText` →
  gateway `prompt.submit` (`app/session/hooks/use-prompt-actions.ts`).
- Chat composer → same `submitText` path (slash vs text split; busy → queue,
  never duplicate-submit).
- Jarvis typed/voice/chips/palette → `submitJarvisCommand`
  (`lib/jarvis/core/command-gateway.ts`): conservative local intents
  (navigate, allowlisted apps/URLs, status) via validated `executeLocal`;
  everything else → `executePipeline` (`lib/jarvis/core/ai-core.ts`) via
  **`session.create` + `prompt.submit`** — the same gateway primitive as Chat.
- Automation Center → `automation-*` gateway methods; cron → scheduler backend.
- Voice LISTENING set only after real `getUserMedia` + level meter; SPEAKING
  only around real TTS playback (58362 audit, unchanged).

## New defect reproduced this pass (fresh evidence)
- **H-1 Duplicate Jarvis execution.** `command-bar handleSend` and
  `command-center handleSubmit` had no in-flight guard, and `mission-control
  runCommand` called `resetJarvisExecution()` BEFORE submitting — masking the
  in-flight state so a double-Enter/double-click spawned two gateway sessions
  for one command (first session orphaned, UI overwritten). Reproduction:
  code-path trace (no gateway needed): `handleSend` → `onCommand` →
  `runCommand` → reset → `submitJarvisCommand` → `executePipeline` creates
  session #2 while session #1 still streams.
