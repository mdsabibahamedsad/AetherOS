# AetherOS Master 84B — CI Execution & Windows RC Validation Report

Date (UTC): 2026-09-16
Repair commit: `ed02700` (`ed0270022fd1bfc141052eb0c231bb77a968bd5b`)
Repository: `sabib360/AetherOS`
Workflow: `AetherOS Desktop Release` (`.github/workflows/desktop-release.yml`)

## Phase 1 — Local release commit: PASS

- `git rev-parse HEAD` → `ed0270022fd1bfc141052eb0c231bb77a968bd5b`
- `git status --short` → clean
- `git show --stat ed02700` → 5 files, +85/−10, all repair surfaces present
  (vitest config, platform-capability tests, design-token test + fix,
  workflow SBOM pin + shared build steps).

## Phase 2 — Remote state: ed02700 NOT on origin

- `git ls-remote origin` succeeds (read access OK).
- `origin/main` = `e3e9746` ("fix(ci): use only UDID in iOS simulator destination"),
  which is an **ancestor** of the local line — local is ahead.
- `git branch -r --contains ed02700` → empty. **The repair commit exists
  only locally; it has never been pushed.**

## Phase 3 — GitHub authentication: GITHUB_AUTH_REQUIRED

```
gh auth status →
  X Failed to log in to github.com account sabib360 (default)
  - The token in default is invalid.
  - To re-authenticate, run: gh auth login -h github.com
```

No credential modification was attempted. No `gh repo view` possible.

## Phase 4 — Workflow definition (verified at ed02700): PASS

- Trigger `workflow_dispatch` with inputs `version` (required string) and
  `prerelease` (boolean, default false).
- Jobs: `validate-linux-config` (ubuntu), `build-linux` (ubuntu),
  `build-windows` (windows-latest), `build-macos` (macos-latest).
- Node 22 + `npm ci` in all jobs; `npm run build --workspace @aetheros/shared`
  after every install; `npm run test:ui -- --run` + `npm run test:desktop:platforms`
  in all three build jobs; `dist:linux` / `dist:win` / `dist:mac` packaging.
- SBOM: `anchore/sbom-action@7b9c33f0… # v0.20.7` (matches `update-release.yml`).
- Uploads: `actions/upload-artifact@043fb46d… # v7.0.1` (verified genuine) +
  `softprops/action-gh-release@c95fe14… # v2` on dispatch events.
- Recorded gaps (not modified): no `tsc` typecheck step; attestation
  permissions exist but no attest step executes; no signing step
  (mac `CODE_SIGNING_ALLOWED=NO`, win `signAndEditExecutable=false`).

## Phases 5–6 — Dispatch & monitor: CI_DISPATCH_BLOCKED

No new run was dispatched: `gh` auth invalid **and** `ed02700` is not on the
remote (a dispatch ref must be a branch/tag containing the commit).
Historical run #8 is pre-repair and is not treated as evidence.

## Phases 7–16 — No CI failures to iterate on; nothing to compare

No CI artifacts, hashes, signatures, SBOMs, attestations, or clean-VM results
exist. Local 84A evidence (vitest 814/814 incl. clean checkout, typecheck,
electron 176/176, guards) stands but is explicitly **not** CI evidence.

## Required user actions (in order)

1. `gh auth login -h github.com` (as an account with write access to
   `sabib360/AetherOS`).
2. Push the repair commit, e.g.
   `git push origin ed02700:main` (or to a release branch; `--ref` needs a
   branch/tag — a raw SHA is not accepted by `gh workflow run --ref`).
3. Dispatch a NEW run (never rerun #8), e.g.
   `gh workflow run "AetherOS Desktop Release" --ref main -f version=1.0.0 -f prerelease=false`
   and confirm the run's head SHA equals the repair commit.
