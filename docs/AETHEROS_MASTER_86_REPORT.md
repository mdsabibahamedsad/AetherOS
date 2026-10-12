# AetherOS Master 86 Report — Production Credential, Signing, Provenance & Clean-Environment Certification

## 1. Executive Summary

Master 86 started from the Master 85 blocked-but-honest state and executed every production
control that can be executed without owner credentials, owner GitHub configuration changes,
or clean-room machines. No control was faked. The release pipeline is byte-identical to the
#16-certified state, release v1.0.0 assets were re-verified end-to-end (7 files, ~1.05 GB,
all hashes match), SBOMs were re-parsed from actual release bytes (SPDX-2.3, 232/291),
all three Windows executables were proven unsigned with platform-native tooling, and the
provenance 404 was re-executed. A new Desktop Build dispatch closed the Master 85 lint
blocker with CI evidence but exposed a second, pre-existing, non-production deficiency in
that secondary workflow. Final state:

**`AETHEROS_1_0_PRODUCTION_BLOCKED`** — blockers: `BLOCKED_BY_CREDENTIALS` (Windows/macOS
signing, notarization), `BLOCKED_BY_GITHUB_CONFIGURATION` (provenance), `BLOCKED_BY_ENVIRONMENT`
(clean VMs). No `RELEASE_ASSET_INTEGRITY_FAILURE`. No fake PASS anywhere.

## 2. Current Source Identity

- Branch: `release/aetheros-1.0.0-rc-84c`; local == `origin/...` == `287e8b3`.
- HEAD: `287e8b3bb9df2d273bf479b570598b24d34b1fe8`
  (`fix(desktop): resolve all eslint errors blocking Desktop Build lint`).
- Delta vs Master 85 workflow commit `c16d126`: 65 files — Master 85 evidence docs + 50
  renderer/lint-compliance files. **`.github/workflows/` is byte-identical** (`git diff
  c16d126..HEAD -- .github/workflows/` is empty). No packaging-config change.
- Evidence: `docs/AETHEROS_MASTER_86_EVIDENCE/01-preflight.json`,
  `02-source-binding.json`.

## 3. CI Run

- Decisive packaging run: **#16 `35186131800` (success, headSha == `c16d126`)** — still the
  newest Desktop Release run; the pipeline it certified is unchanged at HEAD.
- New validation run: **Desktop Build `35232901570`**, dispatched manually
  (`workflow_dispatch`, `build_type=beta`, `platform=all`) on the release branch with
  `headSha == 287e8b3` — no workflow file was modified to obtain it.
  - **Lint & TypeCheck: SUCCESS** — the Master 85 `no-control-regex` blocker is CLOSED.
  - **Test: SUCCESS.**
  - **Build (win/ubuntu/macos-14): FAILURE** at step `Build renderer` with
    `bundle-python.cjs: Cannot find a working virtual environment to bundle at
    .../aetheros/.venv` — the Build job has no `uv python install` / `uv sync` step
    (present in desktop-release.yml, absent in desktop-build.yml). Pre-existing structural
    gap, not caused by `287e8b3` (control: the same `npm run build` is green in #16 where
    the venv is provisioned). macos-13 was still queued at evidence time (non-decisive).
- Evidence: `03-ci-run.json`, `22-secondary-workflow.json`.

## 4. Artifact Inventory

Release `v1.0.0`: 14 assets, published `2026-09-17T04:08:32Z`, unchanged since Master 85
(no new release run, no replacement, no version bump). Sizes verified against the API
record. Evidence: `04-artifact-manifest.json`.

## 5. SHA-256 Integrity

Downloaded the exact release bytes (`gh release download`, sizes match API byte-for-byte)
and hashed locally: Linux 3/3 MATCH, Windows exe/blockmap/msi MATCH the release manifests,
portable.exe consistent across two independent downloads (`ab31ea89...`). A first
interrupted bulk download produced partial files whose hashes mismatched — those bytes were
deleted, re-downloaded completely, and never recorded as results. Evidence:
`05-artifact-sha256.json`, `20-release-asset-integrity.json`.

## 6. SBOM

PASS. Re-parsed from the actual release asset bytes: **SPDX-2.3, 232 packages (linux),
291 (windows)** — identical to Master 85. macOS SBOM: `NOT_APPLICABLE` (no SBOM step in
the macOS job; release policy unchanged, documented scope). Artifact binding is co-shipment
only — cryptographic binding stays BLOCKED behind the same private-repo attestation gate.
Evidence: `06-sbom-status.json`, `07-sbom-binding.json`.

## 7. Provenance

`PROVENANCE_ATTESTATION_BLOCKED_BY_GITHUB_CONFIGURATION` (unchanged). Wiring is valid and
untouched; repo is still PRIVATE (`gh repo view` 2026-09-17); the job correctly skips.
`gh attestation verify` against real release bytes re-executed → **HTTP 404, exit 1**.
No repo visibility change was made (no owner authorization). Evidence:
`08-provenance-status.json`, `09-attestation-verification.json`.

## 8. Windows Signing

`BLOCKED_BY_CREDENTIALS`. Config is unsigned-by-design (`signAndEditExecutable=false`, no
CSC secrets); `desktop-release.yml` references zero signing secrets; `gh secret list` is
empty; all 14 credential presence booleans are false (booleans only, nothing printed).
`sign-windows.mjs` (Azure Trusted Signing → signtool/PFX, fails closed) is present but
unwired. No self-signed/ad-hoc certificate was created. Evidence: `10-windows-signing.json`.

## 9. macOS Signing

`BLOCKED_BY_CREDENTIALS`. `CODE_SIGNING_ALLOWED=NO`, no `APPLE_*` env, no identity;
`hardenedRuntime=true` + entitlements + `afterSign=notarize.cjs` present but unconfigured.
electron-builder `^26.8.1`. Release scope stays dmg+zip (dead `pkg` config untouched).
Evidence: `12-macos-signing.json`.

## 10. macOS Notarization

`BLOCKED_BY_CREDENTIALS`. `notarize.cjs` supports keychain-profile or App Store Connect API
key; `verify-notarization.mjs` exists — none configured, nothing uploaded/stapled/claimed.
Evidence: `13-macos-notarization.json`, `14-macos-verification.json` (also
`BLOCKED_BY_ENVIRONMENT`: no macOS host for `codesign`/`spctl`/`stapler`).

## 11. Clean Windows Validation

`BLOCKED_BY_ENVIRONMENT`: BUILD=PASS, ARTIFACT=PASS, CLEAN-VM=BLOCKED. This host holds the
source repo, dev dependencies, and prior downloads — it cannot serve as a clean machine.
No SmartScreen/signature bypasses used. Evidence: `15-windows-clean-validation.json`.

## 12. Clean macOS Validation

`BLOCKED_BY_ENVIRONMENT`. No clean supported macOS environment; no Gatekeeper/quarantine
bypasses used. Evidence: `16-macos-clean-validation.json`.

## 13. Clean Linux Validation

`BLOCKED_BY_ENVIRONMENT`. No clean matrix environments for AppImage/deb/rpm
install-launch-uninstall sweeps; no universal-compatibility claim. Evidence:
`17-linux-clean-validation.json`.

## 14. Update Policy

`AETHEROS_1_0_UPDATE_MODEL = MANUAL_RELEASE_UPDATE`. No `electron-updater` dependency, no
publish/provider/channel config; `update-manifest.cjs` is a pure validator;
`src/updater/` adapters exist as unwired source (zero importers). No updater was built to
tick a checkbox. Evidence: `18-update-policy.json`.

## 15. Release Asset Verification

`PASS_WITH_DOCUMENTED_SCOPE`: 7 files end-to-end verified (Linux 3/3 + Windows 4/4
consistent), no mismatch → no `RELEASE_ASSET_INTEGRITY_FAILURE`. macOS bytes covered by
CI's `sha256sum -c` in #16. Version safety: `v1.0.0` unchanged, no bump, no replacement.
Evidence: `20-release-asset-integrity.json`.

## 16. Secondary Workflow Issue

Re-scoped, non-production. The Master 85 lint blocker is **CLOSED** (CI SUCCESS on the
fix commit). What remains is a pre-existing deficiency: desktop-build.yml's Build job lacks
Python venv provisioning, and its push path filter (`apps/desktop/**`) never matches the
real tree (`aetheros/apps/desktop/**`) — which is why the fix commit triggered no automatic
run. Neither affects the production release pipeline. Documented, not fixed (workflow
modification is owner follow-up, out of certification scope). Evidence:
`22-secondary-workflow.json`.

## 17. Remaining Blockers

1. `BLOCKED_BY_CREDENTIALS` — owner must provide Windows Authenticode (or Azure Trusted
   Signing) + Apple Developer ID/notarization credentials and wire them into
   `desktop-release.yml` (or environment).
2. `BLOCKED_BY_GITHUB_CONFIGURATION` — repo is private; make it public (or move releases
   to a public repo) and re-run to get real SLSA attestations.
3. `BLOCKED_BY_ENVIRONMENT` — clean Windows/macOS/Linux machines + full
   install-launch-uninstall sweeps per §22–25.
4. Owner follow-up (non-production): provision `uv sync` in desktop-build.yml Build job;
   fix its push path filter to `aetheros/apps/desktop/**`.

## 18. Certification Matrix

See `docs/AETHEROS_MASTER_86_EVIDENCE/21-final-certification.json` (PASS / BLOCKED /
NOT_APPLICABLE per control). Every value traces to executed commands in this evidence set.

## 19. Final Certification

**`AETHEROS_1_0_PRODUCTION_BLOCKED`** (packaging remains green; trust controls outstanding).

## 20. Exact Next Action

Release owner, in order: (1) configure Windows + Apple signing credentials as Actions
secrets and wire them into `desktop-release.yml`; (2) authorize the public-repo (or
release-relocation) change for provenance; (3) dispatch Desktop Release `v1.0.0` so signed
bytes are built, attested, and re-uploaded with a documented asset-replacement note;
(4) run clean-VM sweeps on all three platforms. Then a future master can certify READY.
