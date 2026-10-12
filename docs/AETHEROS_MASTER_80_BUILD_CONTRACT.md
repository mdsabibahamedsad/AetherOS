# AETHEROS Master 80 — Windows Build Contract (ONE source of truth, §73)

> "How do I produce the exact Windows release artifact?" — this document is the answer.

## Canonical commands (apps/desktop)

| Intent | Command | Gates |
|---|---|---|
| Developer build (dirty OK) | `npm run dist:win` (or `dist:win:nsis/msi`) | path-guard only |
| Release dry-run | `npm run desktop:preflight:windows` | A01–A12, no artifacts (§47) |
| Clean build output | `npm run desktop:clean:windows` | `assertOutputDirSafe()` (§71) |
| THE release build | `npm run desktop:release:windows` | everything below |
| Re-validate output | `npm run desktop:validate:windows` | B/C gates |
| Full pipeline + manifest file | `npm run desktop:release:windows:manifest` | + writes `docs/AETHEROS_MASTER_80_RELEASE_ARTIFACT_MANIFEST.json` |

`desktop:release:windows` stages: Node-major check → tree-clean check → full
preflight → clean+verify-empty output → `npm ci` (repo root) → lockfile-diff
check → path guard → `npm run build` → repo-local `electron-builder --win`
(NSIS+MSI+portable) → `validate-windows-release.mjs` → manifest+hashes+evidence.

## Contracts

- **Tree (§4):** release requires EMPTY `git status --porcelain` (untracked included).
  Else `RELEASE_BUILD_BLOCKED_DIRTY_TREE` with offenders. No auto-commit/stash/clean (§45).
- **Toolchain (§12):** Node major == `.nvmrc` major (22). npm = bundled. Else `NODE_MAJOR_MISMATCH`.
- **Deps (§13):** `npm ci` only; post-install `git diff -- <lockfiles>` must be empty else `LOCKFILE_MUTATED`.
- **Output (§6/§71):** `apps/desktop/dist-packaged/` is build-owned. Deletion only after
  inside-repo ∧ not-root ∧ not-home ∧ not-system ∧ exact-expected-path checks; must be empty before builder runs else `OUTPUT_DIRECTORY_NOT_CLEAN`.
- **Artifact set (§8/§9):** exactly `AetherOS-{version}-win-x64.{exe,msi,-portable.exe}`.
  Missing/unexpected/wrong-version/wrong-arch/wrong-product → FAIL. Other-platform
  files are noted `foreignPlatform` (their own platform gates own them). `.blockmap`+`latest.yml` are sidecars.
- **Source binding (§7/§10):** install-stamp commit == `git rev-parse HEAD` AND `dirty==false`,
  else `ARTIFACT_STALE` / `ARTIFACT_DIRTY_TREE`. Build ID `AETHEROS-{v}-windows-x64-{sha12}-{ts14}` distinguishes same-version rebuilds (§11).
- **Electron (§14):** packaged `40.9.3` pinned (`build.electronVersion`); dev `^40.10.6` intentional. Builder `26.8.1` repo-local (§15/§16).
- **Branding (§19):** source `<title>` must be `AetherOS`; packaged `dist/index.html` title must match; legacy tokens (`Hermes Agent`) fail anywhere → `PACKAGED_BRANDING_MISMATCH`.
- **MSI (§20/§21):** ProductName `AetherOS`, ProductVersion `1.0.0.x`, UpgradeCode pinned `{5A6B7C8D-…}` (never changes post-release), ProductCode GUID-shaped. MSI-built ≠ MSI-installed (separate CI job).
- **Hashes (§24):** SHA-256 post-build (post-sign for signed artifacts; current stage `post-build-pre-sign`, `signing.stage=unsigned`).
- **Manifest (§25–§27):** schema `aetheros-windows-release-manifest/1`, self-validated (§26: files+sizes+hashes+commit re-checked), content-hashed (`manifestSha256`), immutable per buildId; historical manifests never overwritten.
- **Path safety (§38/§39):** projected-path guard in preflight+build; developer-path screen classifies hits (sourcemap/binary-bundle = KNOWN_ACCEPTED_RISK; text-surface leak = `DEVELOPER_PATH_LEAK` FAIL).
- **Failure (§44):** first invalid state stops the pipeline. No fix-everything automation (§45).
- **Caching (§65):** npm cache keyed by OS/arch/Node/lockfile (setup-node default); build output/manifest never trusted from cache (clean-output guarantee).
- **Reproducibility (§63–§64):** claimed level = **Level 1** (source/toolchain identity recorded). Byte-for-bit (L4) NOT claimed: Electron/NSIS/MSI embed timestamps; no artificial hash-forcing. Deterministic: names, config, toolchain, manifest schema. Non-deterministic: embedded timestamps, compression ordering.
- **Status model (§35):** LOCAL_DEVELOPMENT / LOCAL_RELEASE_BUILD / CI_BUILD / CI_CERTIFICATION / CLEAN_VM_CERTIFICATION / SIGNED_RELEASE / PRODUCTION_RELEASE — never collapsed into one PASS.
- **Out of scope (§52):** auto-update platform (Master 70.5 owns it); packaging only guarantees updater-compatible artifact continuity.

## §82 historical-failure coverage (each = deterministic failure)

stale artifact→ARTIFACT_STALE; dirty tree→RELEASE_BUILD_BLOCKED_DIRTY_TREE/ARTIFACT_DIRTY_TREE;
wrong commit→ARTIFACT_STALE; wrong version→ARTIFACT_WRONG_VERSION; wrong arch→ARTIFACT_WRONG_ARCH;
wrong product→ARTIFACT_BAD_NAME/MSI_IDENTITY_MISMATCH; old branding→PACKAGED_BRANDING_MISMATCH;
unexpected artifact→ARTIFACT_UNEXPECTED/FOREIGN_FILE; missing→ARTIFACT_MISSING;
wrong Node→NODE_MAJOR_MISMATCH; lockfile mutation→LOCKFILE_MUTATED; path leak→DEVELOPER_PATH_LEAK;
manifest mismatch→MANIFEST_SELF_CHECK_FAIL; hash mismatch→round-trip HASH MISMATCH.
All regression-tested in `windows-release-guards.test.cjs` (19 tests).
