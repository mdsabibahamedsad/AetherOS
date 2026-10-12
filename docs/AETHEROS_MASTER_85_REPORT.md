# AetherOS Master 85 Report — Release Trust, Signing, Provenance & Clean-VM Certification

## Executive summary

Master 85 started from the 84D green state (`CI_PACKAGING_GREEN`, run #13 on `2d72b42`) and added a real
SLSA provenance job to `desktop-release.yml` (commits `c888871`/`505f1f1`/`c16d126`).
A NEW decisive CI run **#16 (`35186131800`) on `c16d126` is SUCCESS** — all five build/integrity jobs green,
`headSha == c16d126`, packaging behavior preserved. The provenance job **skips by design** because the
repository is user-owned **PRIVATE** (`gh repo view`: `visibility=PRIVATE`), where GitHub refuses to persist
attestations (proven by failed runs #14/#15 before the gate). No signing credentials exist anywhere in the
release path, and no clean VM is obtainable from this host. Nothing was faked. Final state:

**`AETHEROS_1_0_PRODUCTION_BLOCKED`** — blockers: `SIGNING_BLOCKED_BY_CONFIGURATION`,
`PROVENANCE_ATTESTATION_BLOCKED_BY_GITHUB_CONFIGURATION`, `CLEAN_VM_VALIDATION_BLOCKED`,
`UPDATE_VALIDATION_BLOCKED`. Secondary: `SECONDARY_WORKFLOW_BLOCKER` (Desktop Build lint, unrelated).

## Source identity

- Branch: `release/aetheros-1.0.0-rc-84c` (local == `origin/...` == `c16d126`)
- Commit: `c16d126aee55eff7d1667ca23f0bbde04f098df0` (contains 84D `2d72b42` as ancestor; delta is
  provenance-job workflow changes + evidence docs only — no product code touched)
- Workflow: `AetherOS Desktop Release` (`.github/workflows/desktop-release.yml`)
- Run: #16 `35186131800`, `https://github.com/sabib360/AetherOS/actions/runs/35186131800`, conclusion `success`

## Artifact inventory

Release `v1.0.0` (final, 14 assets). Run #16 rebuilt from `c16d126` and re-uploaded under the SAME tag
(sizes differ by bytes from the 84D record — documented, no version bump per tag-safety rule).
Current SHA-256 manifests were downloaded verbatim from the release; see `04-artifact-manifest.json` /
`05-sha256.json`. Pre-existing gap preserved: `windows-artifacts.sha256` still omits `-portable.exe`.

## SBOM status

PASS. SPDX-2.3, locally parsed from the actual release assets: 232 packages (linux), 291 (windows).
macOS SBOM is not generated (no SBOM step in the macOS job — same as 84D, documented scope gap).
Cryptographic artifact→SBOM binding is BLOCKED by the same private-repo attestation gate.

## Provenance status

`PROVENANCE_ATTESTATION_BLOCKED_BY_GITHUB_CONFIGURATION`. The workflow wiring is VALID
(`attest-build-provenance` pinned to verified v3 commit, correct `needs`/permissions/subjects), but the job
skips while the repo is private. `gh attestation verify` against the real release SBOM returns HTTP 404
(exit 1) — executed, recorded, not reinterpreted. Flipping the repo to public enables attestation with no
workflow change; then a re-run will produce verifiable attestations.

## Windows signing

`SIGNING_BLOCKED_BY_CONFIGURATION`. `desktop-release.yml` references no signing secret; env holds no
`WINDOWS_SIGN_CERT` / `AZURE_TRUSTED_SIGNING_*` (boolean presence check only, nothing printed).
`sign-windows.mjs` (Azure Trusted Signing → signtool/PFX, fails closed) is ready but unwired.
CI installers are UNSIGNED; nothing claims otherwise.

## macOS signing/notarization

BLOCKED. `CODE_SIGNING_ALLOWED=NO`, no `APPLE_*` env in the release workflow; `notarize.cjs` +
entitlements + `hardenedRuntime=true` exist but are unconfigured without Apple credentials.
`verify-notarization.mjs` requires a macOS runner + credentials — not executed (`BLOCKED_BY_ENVIRONMENT`).

## Clean-environment validation

`CLEAN_VM_VALIDATION_BLOCKED` (`BLOCKED_BY_ENVIRONMENT`): BUILD VALIDATION = PASS, ARTIFACT VALIDATION =
PASS, CLEAN-VM VALIDATION = BLOCKED — for Windows, macOS, and Linux alike. No bypasses used.

## Update validation

`UPDATE_VALIDATION_BLOCKED`. No production updater is configured (no `electron-updater`, no
auto-update module, no publish/provider config). `update-manifest.cjs` is a pure validator, not a channel.

## Outstanding blockers

1. `SIGNING_BLOCKED_BY_CONFIGURATION` — owner must configure Windows Authenticode (or Azure Trusted
   Signing) + Apple Developer signing/notarization credentials and wire them into `desktop-release.yml`.
2. `PROVENANCE_ATTESTATION_BLOCKED_BY_GITHUB_CONFIGURATION` — repo is private; make it public (or move
   releases to a public repo) and re-run to get real attestations.
3. `CLEAN_VM_VALIDATION_BLOCKED` — clean Windows/macOS/Linux environments + install/launch/uninstall sweeps.
4. `UPDATE_VALIDATION_BLOCKED` — only if a production updater is introduced (currently none exists).
5. `SECONDARY_WORKFLOW_BLOCKER` — Desktop Build lint `no-control-regex` in `electron/hardening.cjs:284`
   (+ warnings); proven unrelated to Desktop Release (same commit green in #16). Fix separately.

## Certification matrix

See `docs/AETHEROS_MASTER_85_EVIDENCE/14-final-certification.json` (PASS / BLOCKED per control).

## Final certification

**`AETHEROS_1_0_PRODUCTION_BLOCKED`** (packaging remains **`CI_PACKAGING_GREEN`**).
