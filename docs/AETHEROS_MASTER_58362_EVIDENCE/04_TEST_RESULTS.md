# AETHEROS MASTER 58362 — Regression-Test Results (executed 2026-10-12, Windows)

## Typecheck — PASS (exit 0, three runs)
- `npm run typecheck` (`tsc -p . --noEmit`): clean after baseline repro, after the
  fix batch, and after the lint-cleanup refactor. Zero errors every run.

## Vitest — PASS: 137 files / 900 tests (exit 0)
- Baseline repro (pre-edit): 134 files / 891 passed — matches 58361.
- Final (post-edit): `npx vitest run`: **137 passed / 900 passed, 0 failed** (54s).
  Delta = +3 files / +9 tests, all new:
  - `app/shell/left-sidebar.test.ts` — 5 tests (route→section mapping incl.
    session→chat, overlays). One mid-pass self-correction: initially asserted
    `/agents` → null, but `/agents` IS a registered nav section; expectation
    fixed to `'agents'` plus a dedicated overlay-with-entry case. Test bug, not
    source bug.
  - `app/tasks/tasks-partition.test.ts` — 2 tests (settled exclusion).
  - `store/resource-manager.test.ts` — 2 tests (`clearAlerts`, metric history).
- Targeted relevant suites also green: home, profile-theme (light contract
  preserved), presets, navigation-routes, navigation-groups, canonical,
  jarvis-lifecycle, use-jarvis-voice, composer, session, subagents,
  desktop-slash-commands.
- Classification: zero new regressions, zero pre-existing failures in scope,
  zero infra failures.

## Lint — changed files: no NEW errors; pre-existing debt unchanged
- `npx eslint` over all 22 touched/new files: remaining errors are all on
  untouched lines (jsx-prop sort, `curly` on old single-line `if`s, old import
  order, pre-existing unused `$gateway` in topbar). Own additions fixed in-pass:
  switch→`Record` lookup in sidebar (cleared ~20 padding warnings), `useRef`
  import, `persistServers` hook dep, blank-line warnings.
- Full `npm run lint` still not clean at baseline — pre-existing debt, recorded
  in 58361 and unchanged.

## Renderer production build — PASS
- `npx tsc -b` + `npx vite build` + `node scripts/assert-dist-built.cjs`:
  **PASS** — `✓ built in 26.41s`, `✓ assert-dist-built: dist/index.html +
  assets present` (exit 0). Current code bundles cleanly for packaging.

## Packaged build — BLOCKED (environmental, not a code failure)
- `npm run build` fails at `scripts/write-build-stamp.cjs`: requires a git ref
  (`$GITHUB_SHA` or `git rev-parse HEAD`); this tree is not a git checkout.
  Setting a fake SHA was refused (would fabricate release provenance).
- `dist-packaged/` contains only stale 1.0.0/1.1.0 artifacts from 2026-09-18/23
  (pre-change renderer); launching them would validate old code, so no launch
  was attempted. No install/publish actions taken.

## Not run
- Python backend suite (backend untouched), live-gateway E2E (no gateway in
  this environment), screen-reader run, manual resize pass — all recorded as
  not tested with exact reasons in the final report.
