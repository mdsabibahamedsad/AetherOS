# AetherOS Master 89 Report — E2E Release → Download → Auto-Update Rehearsal

> Controlled validation of the Master 88 architecture with real HTTP, real
> crypto, and real client verification. No redesign, no historical rework.

## 1. Master 88 inspection (actual state, not assumed)

- Committed at HEAD (`380197f`): website distribution (download page, manifest
  generator, verified 1.0.0 inputs, atomic publish script, 6 evidence files).
- Working-tree (Master 88 session, uncommitted): updater endpoint alignment
  (`update-manager.ts` → `https://releases.aetheros.com/updates/…`),
  version-consistency gate in `update-release.yml`, evidence 07–09.
- Pre-existing: `UpdateServer` + signed-manifest updater + `FakeUpdateServer`
  + red-team tests. All present and passing before this execution.

## 2. IMPLEMENTED

- **Stale-manifest fix** (`services/update/update-server.ts`, `getManifest`):
  the rehearsal proved the server returned the *oldest* published release
  (insertion order), so clients could never advance past the first release on
  a channel. Now selects the newest eligible release (semver-descending)
  before the rollout check. Small, surgical, covered by the existing suite.

## 3. VERIFIED

- Three-layer model: runtime updater uses only `https://releases.aetheros.com`;
  zero GitHub/token/electron-updater references in `src/updater/`; remaining
  `github.com` strings are legitimate git-remote helpers/docs links (untouched).
- Version binding: root 1.0.0 = desktop 1.0.0 = website stable 1.0.0; rehearsal
  manifests carried `commit == HEAD` (asserted, not invented).
- Rehearsal on test channel `beta` (stable 1.0.0 untouched):
  1.0.1-test.1 published → unauthenticated GET manifest + artifacts for
  win32-x64 / darwin-arm64 / linux-x64 → `verifyManifest` valid →
  sha256 + RSA signature verified per artifact.
- Update detection: 1.0.1-test.2 published → served as latest (post-fix) →
  `isVersionNewer` true → manifest valid against 1.0.1-test.1.
- Failure safety (all rejected, installed version untouched): tampered bytes
  (digest + RSA mismatch), forged manifest (`SIGNATURE_INVALID`), revoked
  release (withdrawn from channel), unreachable server (fetch fails, no install).
- Rollback: revoked B withdrawn, channel serves immutable A again, client on B
  rejects A with `DOWNGRADE_FORBIDDEN` — no silent downgrade, no overwritten bytes.
- Consistency: website stable 1.0.0 (8 artifacts, all https, all rooted at
  distribution base) unchanged by rehearsal; no website/updater/download skew.
- Security scan: no runtime secrets in updater, electron, website
  distribution surface, or update server.
- Regression: existing updater suite 6 files / 37 tests PASS after the fix.

## 4. PARTIALLY VERIFIED (environment-blocked, honestly bounded)

- Real signed installer builds, OS-level install/launch, and install→update→
  restart on Windows / macOS / Linux were NOT executed: the rehearsal used
  synthetic payload bytes through the real metadata→download→verify chain.
  No platform install PASS is claimed (§31 honored).

## 5. OWNER-BLOCKED

- Code signing (Windows/Apple), provisioned public bucket/CDN + publish
  identity, production-environment approvals, production release notes content,
  clean-VM install/update sweeps.

## 6. NOT IMPLEMENTED / NOT APPLICABLE

- `latest.yml` family: not applicable by design (no electron-updater; the
  signed `UpdateManifest` is the single metadata surface).
- No new staged-rollout machinery (existing percentage rollout + kill-switch
  verified as-is). No `installOnQuit` behavior change (no defect found).

## 7. REGRESSION

- One genuine flow defect found and fixed (§2). No closed functionality regressed.
