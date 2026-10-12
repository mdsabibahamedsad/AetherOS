# AetherOS Master 74 Beta Defect Register

## B74-001 — Manifest signature canonicalization excluded nested fields (FIXED)
- Severity: P0 (release trust) · Component: update signing · Platforms: all
- Reproduction: sign manifest, tamper `artifacts[0].sha256`, re-verify with
  trusted key → old code returned VALID (replacer-array whitelist drops nested keys).
- Root cause: `JSON.stringify(obj, Object.keys(obj).sort())` at 5 sites.
- Fix: recursive `stableStringify` everywhere; red-team test asserts
  SIGNATURE_INVALID on tamper.
- Regression: `server-and-redteam.test.ts` → rejects tampered hashes. Status: FIXED, verified 2026-09-12.

## B74-002 — `.github/workflows/update-release.yml` was a markdown doc (FIXED)
- Severity: P1 · Component: release pipeline
- A 603-line markdown overview carried a `.yml` extension and never executed.
- Fix: real 9-job pipeline + 7 fail-closed release scripts. Status: FIXED, YAML parses (9 jobs).

## B74-003 — Linux adapter missing braces; adapters mis-wired (FIXED)
- Severity: P1 · Component: platform adapters
- 38 syntax errors (unclosed `if` blocks); all 5 adapters imported from
  nonexistent `../platform-adapter` with adapter types from `types`.
- Fix: braces restored, imports corrected, `getuid` guards, UpdateUI IPC
  bridge. Status: FIXED — `src/updater/` typecheck-clean.

## B74-004 — Packaged build blocked by pre-existing design-system errors (OPEN, P1)
- `tsc -b` fails on `design-system/patterns/ActionBar.tsx` et al.
  (missing `../components/Button`, `ActionItem` mismatches). Out of Master 74
  scope; blocks installer production. Status: OPEN → Master 75 prerequisite.

## B74-005 — No code-signing credentials (OPEN, P0 for production, accepted for beta)
- No EV cert / Apple ID / Play / TestFlight. All tooling fails closed
  (proven). Status: OPEN → blocks STABLE, not controlled beta.

## B74-006 — design-tokens.test.ts: 3 failures (OPEN, P3, unrelated)
- Theme value assertions (type ramp, motion durations, spacing). Pre-existing,
  untouched by this work. Status: OPEN, not a beta blocker.
