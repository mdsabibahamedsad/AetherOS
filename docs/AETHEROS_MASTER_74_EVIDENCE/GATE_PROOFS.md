# Master 74 — Gate Proofs (executed 2026-09-12, commit 2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1, Node v25.5.0, win32-x64)

## 1. RC freeze (PASS)
Command:
  RC_VERSION=1.1.0-beta.1 RC_CHANNEL=beta ARTIFACT_INDEX=%TEMP%\rc-test\artifact-index.json
  SBOM_PATH=%TEMP%\rc-test\sbom.spdx.json OUT_DIR=%TEMP%\rc-test\rc
  TEST_STATUS_JSON={"updater": "pass", "release": "pass"}
  node services/update/scripts/rc-manifest.mjs
Observed:
  RC frozen: aetheros-1.1.0-beta.1 commit=2bdfbfd8ebcf artifacts=1
  rc-sha256=f005fa1273e145263b2898292d5d62541ebf812856b633885b29413e781fdd00
Status: PASSED (receipt copied to rc-aetheros-1.1.0-beta.1.json)

## 2. RC immutability (PASS — overwrite refused)
Command: same as (1), re-run.
Observed: BLOCKED: RC already exists and is immutable (bump version for a new RC)
Status: PASSED (mutable-RC attack refused)

## 3. RC fail gate (PASS — failing suite blocks RC)
Command: RC_VERSION=1.1.0-beta.2 TEST_STATUS_JSON={"updater": "fail"} ...
Observed: BLOCKED: required suites failing: updater
Status: PASSED

## 4. Revoke without credentials (fail-closed)
Command: node services/update/scripts/revoke-release.mjs release
Observed: BLOCKED: UPDATE_ADMIN_URL, UPDATE_ADMIN_TOKEN and RELEASE_ID are required
Status: PASSED (fail-closed, no fake revocation)

## 5. Set-rollout without credentials (fail-closed)
Command: node services/update/scripts/set-rollout.mjs --percentage 100
Observed: BLOCKED: UPDATE_ADMIN_URL, UPDATE_ADMIN_TOKEN and RELEASE_VERSION are required
Status: PASSED (fail-closed)

## 6. Canary without manifest/key (fail-closed)
Command: node apps/desktop/scripts/release/canary-install.mjs
Observed: BLOCKED: UPDATE_MANIFEST_URL and UPDATE_PUBKEY_PEM are required
Status: PASSED (fail-closed, no fake canary)

## 7. Windows signing without credentials (fail-closed)
Command: node apps/desktop/scripts/release/sign-windows.mjs dist-packaged
Observed: SIGNING=BLOCKED: no Azure Trusted Signing or WINDOWS_SIGN_CERT configured
Status: PASSED (fail-closed; unsigned build never marked signed)

## 8. Unit suites (PASS)
Command: npm run test:ui -- --run src/release/__tests__ src/updater/__tests__
Observed: Test Files 7 passed (7); Tests 46 passed (46)
Full log: vitest-release-update.log

## 9. Packaged build (BLOCKED — honestly blocked, not attempted as fake)
`npm run build` runs `tsc -b`; repo typecheck fails on pre-existing
design-system errors (e.g. ActionBar.tsx: missing ../components/Button,
ActionItem property mismatches) untouched by this work. No signing
credentials exist. No installer was produced or claimed.
Status: BLOCKED — pre-existing tree typecheck errors + no signing creds.
