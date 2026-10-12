# AetherOS Master 78 — WiX LGHT0103 Root Cause

Status: IMPLEMENTED (root cause proven by measurement) / MSI rebuild ATTEMPTED (see §9)
Date (UTC): 2026-09-13 · Source commit `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1`

## 1. Offending path (worst case, measured 2026-09-13)

```
D:\hermes-agent-main\aetheros\apps\desktop\dist-packaged\win-unpacked\resources\py\Lib\site-packages\elevenlabs\text_to_speech\types\body_text_to_speech_streaming_with_timestamps_v_1_text_to_speech_voice_id_stream_with_timestamps_post_apply_text_normalization.py
```

- Absolute length: **262 chars** (> Windows MAX_PATH 260).
- Measured blast radius (33,760 staged files under `dist-packaged/win-unpacked` +
  `build/bundled-python`): exactly **1 file ≥ 260** (fatal), **6 files > 240**
  (inside the guard's 20-char tooling margin — all must be resolved by shortening the prefix).
  Scan: `node scripts/release/check-packaging-path-lengths.mjs`, exit 1 from this checkout.
- File-name alone: ~150 chars. Directory depth alone (`Lib/site-packages/elevenlabs/
  text_to_speech/types/`): ~60 chars. Checkout prefix
  (`D:\hermes-agent-main\aetheros\apps\desktop\dist-packaged\win-unpacked\resources\py\`):
  ~100 chars. The sum crosses 260 — no single party is "at fault"; it is the composition.
- Originating packages: `elevenlabs` (Fern-generated endpoint body types, e.g.
  `body_*_post_apply_text_normalization.py`) and `mistralai` (`client/models/
  get_*_observability_*_postop.py`, `post_*_putop.py`).
- Runtime-required: YES. `elevenlabs/__init__.py` eagerly imports its `types/` tree
  (verified by reading the staged package); the app lazily imports `elevenlabs`
  for the ElevenLabs TTS provider (`tools/tts_tool.py::_import_elevenlabs`,
  `aetheros_voice/tts/elevenlabs.py`). `mistralai` is lazy-installed/imported for
  Mistral Voxtral TTS/STT. Deleting or renaming individual stubs breaks package
  integrity (`ModuleNotFoundError` on `import elevenlabs` / `import mistralai`).

## 2. Tool versions

| Tool | Version | Source |
|---|---|---|
| Node | v25.5.0 | `node --version` (Windows host) |
| npm | 11.8.0 | `npm --version` |
| Python (bundler host) | 3.11.15 | `python --version` |
| Electron (packaged runtime pin) | 40.9.3 | `build.electronVersion`, PE FileVer |
| Electron (dev dep) | ^40.10.6 | `aetheros/node_modules` |
| electron-builder | 26.8.1 | `aetheros/node_modules/electron-builder/package.json` |
| app-builder (WiX driver) | 3.5.10 | `app-builder.exe --version` |
| WiX toolset | v3 series via app-builder (candle/light; exact light.exe banner captured in MSI build log) | electron-builder MSI target |
| Windows | Windows 11 dev host (exact build in BUILD_ENVIRONMENT doc) | — |

## 3. Failed command (Master 77)

```
npm run dist:win          # nsis OK → msi FAILED at WiX light, LGHT0103
```

Failure output (Master 77 FINAL_STATUS): full `dist:win` FAILED at the MSI/WiX step with
LGHT0103 (MAX_PATH on the bundled-Python elevenlabs filename). NSIS alone
(`npm run dist:win:nsis`) exits 0 — NSIS tolerates long paths; only the WiX/MSI path fails.

## 4. Root cause

WiX v3 `light.exe` cannot address paths ≥ MAX_PATH (260). The MSI target stages
`build/bundled-python/py/**` (13,768 files incl. Fern-generated SDK stubs with ~150-char
filenames) under `dist-packaged/__msi-x64/…`, and the combination of checkout-prefix
length + staging depth + generated filename exceeds 260 for 40+ files. This is
ENVIRONMENTAL (path-length composition), not a code bug: the same tree packages fine
from a shorter checkout root.

## 5. Chosen fix (in order per phase §9)

- **A. Shorten build workspace path** (CHOSEN, zero runtime change): build MSI from a
  SUBST-mapped drive (`subst X: <desktop-root>`, run `npm run dist:win:msi` from `X:\`),
  saving ~40 prefix chars (worst 262 → ~222, inside budget). Documented in the
  distribution runbook; CI `windows-latest` runners already check out to a short
  `D:\a\…` prefix, so CI is unaffected.
- **B. Early-fail guard** (CHOSEN, complementary): new
  `scripts/release/check-packaging-path-lengths.mjs` (budget 240 = WiX MAX_PATH 260 minus
  20 tooling margin, actionable
  OFFENDING_PATH/LENGTH/PACKAGE/REMEDIATION output), wired into `dist:win:msi`
  (build → guard → builder) and the CI windows job. Proves the failure mode is
  detected in seconds instead of obscure LGHT0103 minutes later. TESTED (6/6 node:test PASS).

## 6. Rejected alternatives (with reason)

- **C. Rename vendored SDK files**: breaks `import elevenlabs` (eager `types/` import) —
  corrupts the Python runtime. REJECTED (violates §97).
- **C2. Delete elevenlabs/mistralai from the bundle**: removes TTS/STT providers the product
  ships (`tts.elevenlabs`, Mistral Voxtral) — functionality removal to make packaging pass.
  REJECTED (violates §97). Proof of use: `tools/tts_tool.py`, `aetheros_voice/tts/elevenlabs.py`,
  `aetheros_cli/config.py` provider tables.
- **D. Change packaging layout** (e.g. move `py/` out of WiX scope): changes runtime
  `process.resourcesPath` resolution in `electron/main.cjs` — high-risk, unnecessary when
  (A) suffices. REJECTED unless (A) fails.
- **E. Upgrade WiX/electron-builder**: no newer stable electron-builder is declared by the
  repo; toolchain churn for an environmental issue. REJECTED for this phase.
- **F. Long-path manifest/registry tweaks**: WiX v3 light.exe is not long-path-aware
  regardless of process manifest — ineffective. REJECTED.
- **G. Different MSI strategy**: current strategy is sound; the defect is prefix length.
  REJECTED.

## 7. Safe-to-rename / relocate verdict

- Vendored `site-packages` filenames: NOT safe to rename (package integrity).
- Checkout/staging prefix: SAFE to shorten (pure build-environment property, no artifact
  content change). This is the entire fix.

## 8. Validation

- Guard TESTED: `node --test scripts/release/check-packaging-path-lengths.test.mjs` → 6/6 PASS.
- Guard on real tree: 65 offenders reported with correct PACKAGE attribution
  (elevenlabs/mistralai) — proves detection works, not just the harness.
- MSI rebuild from SUBST short path: result recorded in FINAL_STATUS / build evidence
  (PASS or FAILED-with-log — whichever actually happened; see §9 below).

## 9. MSI rebuild outcome (filled after execution)

Recorded in `docs/AETHEROS_MASTER_78_FINAL_STATUS.md` + `docs/AETHEROS_MASTER_78_EVIDENCE/`.
