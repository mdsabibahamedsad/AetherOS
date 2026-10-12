# AETHEROS MASTER 58363 — Changed Files & Fix H-1

## Root cause (H-1 duplicate Jarvis execution)
Three missing guards stacked: (1) both Jarvis composers submitted
unconditionally; (2) `runCommand` reset execution state BEFORE submitting,
masking in-flight status; (3) `executePipeline` creates a fresh gateway
session per call — so the duplicate orphaned the first session instead of
colliding safely. Chat/Home were already safe (busy→queue; idempotent stash).

## Fix (smallest durable, renderer-only, no API/route changes)
1. `store/jarvis-mode.ts` — new `isJarvisExecutingState()`:
   in-flight = SUBMITTED/PARSING/PLANNING/EXECUTING/STREAMING.
2. `lib/jarvis/core/command-gateway.ts` — new `JarvisBusyError`; central guard
   in `submitJarvisCommand` (covers typed, voice, palette, chips): rejects
   while in-flight unless Allow-once resubmit; `system.navigate` intents
   (exit/nav) always pass so leaving Jarvis is never blocked.
3. `app/jarvis-mode/layout/mission-control.tsx` — `runCommand` checks BEFORE
   resetting; duplicates get an info notification, running task untouched.
4. `app/jarvis-mode/command-bar/command-bar.tsx` + `command-center/command-input.tsx`
   — submit handlers ignore while executing (text preserved); Send disabled
   with explanatory title.

## Regression tests (all passing)
- `command-gateway.test.ts` +4: state classification; duplicate rejected +
  pipeline not called; exit allowed mid-flight; Allow-once bypasses.
  (`beforeEach` now also calls `resetJarvisExecution()` — required isolation
  for the new stateful tests; existing expectations unchanged.)
- Existing suites re-verified: ai-core, task-state-machine, jarvis-lifecycle,
  use-jarvis-voice, composer, session, navigation, palette/slash, themes.

## Untouched
Backend, preload/IPC, Electron security flags, signing/updater/release,
theme default, routes, dependencies. Chat/Home submit paths unchanged
(already duplicate-safe).
