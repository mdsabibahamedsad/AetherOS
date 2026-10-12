# AETHEROS MASTER 58366 — Implementation H-2 & Verification (2026-10-12)

## Reproduction (pre-fix, code-path)
Tasks view (`app/tasks/index.tsx`) rendered lifecycle rows with a single
"view details" button. Runtime supports `pauseCronJob` / `resumeCronJob` /
`triggerCronJob` / `deleteCronJob` (proven by Cron overlay usage); the Tasks
list called none of them. No stop endpoint exists for desktop-action tasks
(status polling only) — so those rows must stay view-only.

## Root cause
Missing UI calls, not missing runtime: the list aggregated `$cronJobs` but
dropped the job handle and exposed no actions.

## Fix (renderer-only, established patterns reused)
- `TaskRow` carries `cronId` + `paused` (shared `jobState` rule); exported
  `getTaskRowActions` (cron-live → pause/trigger/view/delete; cron-terminal →
  view/delete; action → view) and `pauseResumeAction`.
- Handlers mirror Cron overlay: per-row busy lock, `updateCronJobs` apply,
  success notify, error notifyError with state preserved; delete confirmed
  via `window.confirm` (settings/sync precedent).
- Action buttons labeled (`Pause/Resume/Run now/View/Delete <title>`) with
  titles; busy row disables its own controls only.

## Regression tests
- `tasks-partition.test.ts` +4: full lifecycle set, terminal-only set,
  action view-only, pause/resume resolution. (Plus 58362's 2 partition tests.)
- Targeted: 6/6 pass. Full suite: **137 files / 908 tests pass, exit 0**
  (baseline 904 + 4 new). Typecheck clean (exit 0). Touched-file lint:
  0 errors (1 pre-existing-style blank-line warning fixed in-pass).

## Changed files
- `apps/desktop/src/app/tasks/index.tsx` (actions + handlers + TaskRow)
- `apps/desktop/src/app/tasks/tasks-partition.test.ts` (+4 tests)
- Docs: `AETHEROS_MASTER_58366_EVIDENCE/` (00–04), roadmap report, ledger.

## Environment blockers (unchanged, recorded once)
Live gateway/providers/mic, git provenance for packaging. No new blockers.
