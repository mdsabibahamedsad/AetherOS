# AETHEROS MASTER 78A — Desktop Build Audit

Date (UTC): 2026-09-15
Auditor: Principal Electron Desktop Build Engineer (78A run)
Source commit (HEAD at audit): `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` (branch `main`, repo root `D:\hermes-agent-main`)
Working tree state: **DIRTY** — 1422 modified paths (`git diff --name-only`), largely CRLF/line-ending
noise plus real deltas listed below. HEAD binding of any artifact MUST record the dirty state.

## 1. Build configuration source of truth

- `apps/desktop/package.json` → `build.directories.output = "dist-packaged"` (line 182). **This is the
  current, canonical electron-builder output directory.**
- `build.artifactName = "AetherOS-${version}-${os}-${arch}.${ext}"` (NSIS/MSI), portable override
  `AetherOS-${version}-win-x64-portable.${ext}`.
- `build.win.target = [nsis(x64), msi(x64), portable(x64)]` — exactly the 78A matrix. No Squirrel/AppX/MSIX.
- `build.electronVersion = "40.9.3"` declared; actually installed Electron is **40.10.6** (minor drift, see §6).
- `extraResources` (current source): `install-stamp.json`, `native-deps`, `icon.ico`, `license.txt`,
  `build/bundled-python/py → py`, `build/bundled-python/backend → backend`.
- Hooks: `beforeBuild scripts/before-build.cjs`, `beforePack scripts/before-pack.cjs`,
  `afterPack scripts/after-pack.cjs` (rcedit identity stamp, best-effort), `afterSign scripts/notarize.cjs`.
- `asar: true`, `asarUnpack: **/*.node, **/prebuilds/**, dist/**`.

## 2. Real output directory verdict (§2)

| Directory | Status | Evidence |
|---|---|---|
| `apps/desktop/dist-packaged/` | **CURRENT / CANONICAL** | Matches `directories.output` in source config; CI reads/writes here; holds 2026-09-14 Linux artifacts |
| `apps/desktop/release/` | **LEGACY + STALE + CORRUPT** | Stale `builder-effective-config.yaml` inside it says `directories.output: release` (old config); blockmap dated 2026-07-27; `win-unpacked/` has **no exe at all** (interrupted-pack signature, see §3); extraResources used old `python` (not `py`) layout |

SOURCE DIRECTORY: `apps/desktop/` (renderer `src/`, main `electron/`, build scripts `scripts/`)
BUILD DIRECTORY: `apps/desktop/dist/` (renderer, currently ABSENT — not built) + `apps/desktop/build/` (bundled-python staging, currently ABSENT)
PACKAGING DIRECTORY: `apps/desktop/dist-packaged/` (+ transient `win-unpacked/`, `__msi-x64/` beneath it)
FINAL ARTIFACT DIRECTORY: `apps/desktop/dist-packaged/` — NOT `release/`. `release/` must not be treated as output.

## 3. Stale/corrupt output analysis (§3)

- `release/win-unpacked/` — Chromium payload + `resources/` present, but **no `AetherOS.exe`, no `electron.exe`**.
  This is the exact corrupted-partial-state signature documented in `scripts/before-pack.cjs`
  (interrupted pack: electron-binary rename never completed). Classification: **STALE + CORRUPT**. Safe to delete
  (pure generated artifact; `beforePack` hook wipes `appOutDir` on every run anyway).
- `release/__msi-x64/` — `project.wxs` (4.0 MB) + `project.wixobj` (30.5 MB), dated 2026-08-03. WiX harvest
  succeeded, link (`light.exe`) evidently did not produce an MSI (no `.msi` anywhere in `release/`).
  Classification: **STALE WiX staging**. Safe to delete.
- `release/AetherOS-1.0.0-win-x64.exe.blockmap` (2026-07-27) — orphan: its installer `.exe` is absent.
  Classification: **STALE ORPHAN**. Safe to delete.
- `release/builder-debug.yml`, `release/builder-effective-config.yaml` — evidence of the OLD config
  (`output: release`, `python` resource dir). Their content is preserved in this audit (§7); files are
  regenerable builder byproducts. Safe to delete after this audit.
- `dist-packaged/__msi-x64/` (`project.wxs` 4.4 MB, dated 2026-09-14) — WiX staging from a recent attempt;
  no MSI beside it. Classification: **STALE**. Safe to delete before a clean rebuild.
- `dist-packaged/AetherOS-1.0.0-linux-x64.{AppImage,deb,rpm}` (2026-09-14) — Linux artifacts from another
  machine/run, unrelated to Windows 78A. Classification: **CURRENT for Linux, out of scope** — leave alone.

## 4. Build scripts (§1 keyword sweep)

- `dist:win` = `npm run build && npm run dist:win:validate-paths && npm run builder -- --win` (working-tree
  addition of the `validate-paths` gate vs HEAD; correct per §36).
- `dist:win:nsis` / `dist:win:msi` dedicated scripts exist — use them, do not invent commands.
- `dist:win:validate-paths` → `scripts/release/check-packaging-path-lengths.mjs` (maxSafeLength 240,
  scans `build/bundled-python`, `dist-packaged/win-unpacked`, `dist-packaged/__msi-x64`). Real guard, tested
  (`check-packaging-path-lengths.test.mjs`).
- `scripts/bundle-python.cjs` — copies repo `.venv` → `build/bundled-python/py`, stages backend, smoke-tests
  (`import pydantic`). Requires host Python 3.11–3.13. `before-build.cjs`, `stage-native-deps.cjs`,
  `write-build-stamp.cjs`, `assert-dist-built.cjs`, `set-exe-identity.cjs` (rcedit) all present.
- `scripts/release/validate-artifacts.mjs` — deterministic validator (name/size/staleness/SHA-256,
  manifest cross-check). Use for §42.
- `scripts/release/build-all-installers.mjs`, `sign-windows.mjs`, `write-artifact-manifest.mjs`,
  `canary-install.mjs`, `test-desktop.mjs` (nsis/existing/fresh modes) present.
- `scripts/notarize.cjs` is wired as `afterSign` — macOS-oriented; on Windows unsigned builds it is a no-op
  path (signing BLOCKED, see §26 — no cert infrastructure in repo).

## 5. CI artifact paths (§43/44)

`.github/workflows/desktop-release.yml` (working tree; differs from HEAD):
- Windows job already uses `dist-packaged/` for verify/hash/upload of **all three** (`*.exe`, `*.msi`,
  `*-portable.exe`) — no stale `release/**` upload path. Correct.
- Working-tree improvements vs HEAD: split build→validate-paths→package steps, verify MSI+portable existence
  (HEAD only checked the NSIS exe), added Windows SBOM step. Sensible; uncommitted.
- Policy nit: SBOM step pins `anchore/sbom-action@v0` (mutable tag) while the Linux job uses a SHA —
  inconsistent with the repo's SHA-pinning policy. Flagged, not blocking for 78A.

## 6. MSI LGHT0103 root cause (§13) — CONFIRMED

Ran the repo's own guard against the staged tree: **4 offenders**, all `elevenlabs` SDK stubs:

1. `…\resources\python\Lib\site-packages\elevenlabs\text_to_speech\types\body_text_to_speech_streaming_with_timestamps_v_1_text_to_speech_voice_id_stream_with_timestamps_post_apply_text_normalization.py` — **LENGTH=260** (= MAX_PATH)
2. `…\pronunciation_dictionary\types\body_add_a_pronunciation_dictionary_v_1_pronunciation_dictionaries_add_from_rules_post_workspace_access.py` — LENGTH=247
3. `…\text_to_speech\types\body_text_to_speech_with_timestamps_v_1_text_to_speech_voice_id_with_timestamps_post_apply_text_normalization.py` — LENGTH=243
4. `…\pronunciation_dictionary\types\body_add_a_pronunciation_dictionary_v_1_pronunciation_dictionaries_add_from_rules_post_rules_item.py` — LENGTH=241

Checkout prefix `D:\hermes-agent-main\aetheros\apps\desktop\` is 44 chars. The guard's documented remediation
(shorter checkout root, e.g. `subst`) applies — no dependency may be renamed/deleted (elevenlabs eagerly
imports its `types/` tree). Fix doc: `docs/AETHEROS_MASTER_78A_MSI_PATH_FIX.md` (to be written after rebuild
attempt from a short path).

## 7. Preserved evidence from stale `release/` effective config (old source config)

Old config differences vs current source (proves `release/` is legacy): `directories.output: release`;
extraResources `build/bundled-python/python → python` (now `py → py`); no `win.portable.artifactName` override
detail changes; same appId `com.aetheros.aetheros`, productName `AetherOS`, nsis guid
`{1A2B3C4D-…}`, msi upgradeCode `{5A6B7C8D-…}`.

## 8. Audit conclusion

- Build system is coherent and current-config-correct; canonical output is `dist-packaged/`.
- `release/` is a legacy directory holding a corrupt partial unpack + orphan blockmap + old effective config.
- MSI blocker root cause is proven (elevenlabs long paths + long checkout prefix), fix path is the
  documented short-root rebuild — not exclusion/rename.
- Blockers entering the build phase: dirty working tree (HEAD binding caveat), Node 25 vs CI Node 22,
  missing `dist/` + `build/` (full `npm run build` required), empty electron-builder tool cache
  (NSIS/WiX download needed), no signing certs, no clean VM.
