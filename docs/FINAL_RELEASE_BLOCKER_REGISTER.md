# FINAL RELEASE BLOCKER REGISTER

Date: 2026-08-24 · Baseline intact: 688/688 renderer · 161/161 Electron ·
351/351 Python security · entry JS 3.22MB PASS (no product code touched in
M29 — workflow + docs only, so regression baselines stand).

| # | Blocker | Sev | Status | Repository-side work done | External action required to close |
|---|---------|-----|--------|---------------------------|-----------------------------------|
| 1 | Code signing | P0 | **BLOCKED** | Signing stages wired into `desktop-release.yml`, secret-gated (`WINDOWS_SIGNING_PFX/PASSWORD`, `APPLE_ID/APP_SPECIFIC_PASSWORD/TEAM_ID`); native cryptographic verification jobs (`Get-AuthenticodeSignature`, `codesign --verify --strict`) gate publishing; unsigned artifacts can never pass to publish | Provision Windows EV cert + Apple Developer ID as GitHub Actions **environment secrets** (`production-release` environment). No cert names invented; none exist in repo |
| 2 | Release workflow | P0 | **IMPLEMENTED-AWAITING-RUN** | `.github/workflows/desktop-release.yml`: 3 native runners, least-privilege permissions (`contents:read` except attestation job: `id-token:write`+`attestations:write`; publish: env-gated `contents:write`), TEST→BUILD→PACKAGE→SIGN→HASH(manifest JSON)→SBOM(CycloneDX)→ATTEST→**VERIFY**(`gh attestation verify` per artifact)→PUBLISH behind manual approval environment | Merge + execute one full run; attach run ID to RC record |
| 3 | Provenance + SBOM | P1 | **BLOCKED** (verification half) | Attestation of every artifact+SBOM with digest subjects; explicit verify step that fails the job on any unverifiable subject | Same single workflow run as #2; then `gh attestation verify` against published release (executed inside pipeline) |
| 4 | Cross-platform interactive QA | P1 | **BLOCKED** | Critical-path checklist encoded in audit docs (M25 §38 matrix) | Human-executed install/update/E2E passes on Windows/macOS/Linux hosts using the RC from blocker #2's first run; Wayland stays UNSUPPORTED until claimed+tested |

## Regression gate
No application code changed in M29 → all Master 28 baselines carry forward
unchanged (verified earlier this session). Any future edit to signing/
workflow files re-runs: renderer 688 · electron 161 · python-security 351 ·
typecheck/lint clean · entry-chunk ≤5MB.

## Verdict logic
Per no-cheating rules ("workflow file exists" is not evidence), blockers
#1/#3-verify/#4 remain BLOCKED until executable evidence exists. Blocker #2
is code-complete and becomes PASS on its first successful pipeline run.
