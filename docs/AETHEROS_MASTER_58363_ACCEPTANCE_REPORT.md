# AETHEROS MASTER 58363 — Acceptance Report (2026-10-12)

## 1. What was actually changed
One root-cause fix (H-1 duplicate Jarvis execution), renderer-only, no API,
route, backend, security, or dependency changes:
- `store/jarvis-mode.ts`: `isJarvisExecutingState()` helper.
- `lib/jarvis/core/command-gateway.ts`: `JarvisBusyError` + central
  in-flight guard (nav/exit exempt, Allow-once bypasses).
- `app/jarvis-mode/layout/mission-control.tsx`: pre-reset duplicate check.
- `command-bar/command-bar.tsx`, `command-center/command-input.tsx`:
  submit guards (text preserved) + Send disabled with reason.
- `command-gateway.test.ts`: 4 new tests (+ state isolation in `beforeEach`).

## 2. Root causes fixed
- H-1: three stacked missing guards let one command spawn two gateway
  sessions, orphaning the first. Fixed at the single choke point every entry
  funnels through, plus UI-level guards. Chat/Home were audited and already
  duplicate-safe (queue / idempotent stash).

## 3. Workflow verdicts
- **Pass (live where possible, else code-traced + unit-tested):** C2 (Jarvis
  text incl. busy/approval paths), C3/C4 (voice gates), C5 (cancel/retry),
  D3 (duplicate prevention), E1–E5 (drafts, sidebar mapping, single palette,
  optional panels, task identity), F1–F4 (unavailable gateway, tool
  error/timeout, cancel vs reject, nav-during-task).
- **Partial (structure verified, live run blocked):** A (submit chain traced
  to `prompt.submit`; model/tool routing needs a gateway), B (tool cards +
  failure states verified; live invocation needs a gateway agent), C1/C6/C7
  (exit/no-teardown/drawer/approvals read-verified; live session needed),
  D1/D2/D4 (state machine + lifecycle tested; live multi-turn needed).
- **Could not test:** D5 (restart persistence — unsupported, no claim),
  packaged-app comparison, screen-reader run, continuous resize.
- **Failed:** none.

## 4. Commands executed (real results)
- `npm run typecheck` → clean, exit 0.
- `npx vitest run` (full) → 137 files / 904 tests pass, exit 0.
- `npx vitest run src/lib/jarvis/core/command-gateway.test.ts` (+ ai-core,
  task-state-machine, jarvis-lifecycle) → 26 + 14 pass.
- `npx eslint` (6 touched files) → 0 errors, 2 pre-existing warnings.
- Dev-server smoke was established in 58362 (HTTP 200); not re-run per §1.

## 5. Automated vs live coverage
Automated: submit routing, approval gates (both channels), busy guard,
state classification, drafts, sidebar mapping, voice-state helpers, theme
contract. Live integration (gateway sessions, model routing, STT/TTS audio,
packaged launch) is **uncovered here** — mocks prove behavior against the
mock contract only, as stated in every verdict above.

## 6. Installed-app validation
Not performed. Exact prerequisite: a git checkout (or `$GITHUB_SHA`) for
`write-build-stamp.cjs` provenance; tree has neither. Stale 1.0.0/1.1.0
artifacts predate all recent changes. No release/publish/signature actions.

## 7. Security and approval findings
No bypass found: all Jarvis entries funnel through the policy-gated
`submitJarvisCommand`; destructive actions need Allow-once on both channels;
reject runs nothing; cancel ≠ failure; renderer gains no privilege
(preload/IPC/Electron flags untouched; only existing narrow bridges used).

## 8. Closed issues / active blockers
- Permanently closed: 58361 F-1–F-5, 58362 G-1–G-7 (no contrary evidence).
- Newly closed: H-1.
- Active blockers: live gateway + provider credentials + mic session (for
  live A/B/D), git checkout (for packaged rebuild). Smallest next actions:
  run `scripts/run_tests.sh`-adjacent gateway session once in a credentialed
  dev environment and execute matrix rows A2/B/D-live; run the packaged
  build from a git checkout and compare behavior.

## Overall status
`AETHEROS_ACCEPTANCE_PARTIAL`
