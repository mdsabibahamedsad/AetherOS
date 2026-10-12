# AETHEROS MASTER 78A — Failure Log

## F-01 — vite build: missing @vitejs/plugin-react (SEVERITY: P1, build-blocking)
- Command: `npm run build` (apps/desktop)
- Error: `ERR_MODULE_NOT_FOUND: Cannot find package '@vitejs/plugin-react'`
- Root cause: incomplete workspace install — root `node_modules` lacked the devDep (also `concurrently`;
  vite 7.3.2 hoisted vs required ^8.0.10).
- Fix: `npm install --no-audit --no-fund` at repo root (added 100 packages, 19s).
- Retest: `npm run build` → EXIT 0. STATUS: RESOLVED.

## F-02 — dist:win:validate-paths gate FAIL on normal checkout (SEVERITY: P0 for MSI)
- Command: `npm run dist:win:validate-paths`
- Error: 1 path over budget (246 > 240): elevenlabs
  `body_text_to_speech_streaming_with_timestamps_..._post_apply_text_normalization.py` under
  `build/bundled-python/py/...`
- Root cause: 44-char checkout prefix + 130-char generated SDK filenames (proven, not assumed).
- Fix: NOT bypassed for MSI. NSIS/portable packaged directly (gate is WiX-specific); MSI packaged from
  physically short root `D:\hb\` (see MSI path-fix doc). STATUS: RESOLVED via short-root build.

## F-03 — MSI light.exe LGHT0103 from normal checkout (SEVERITY: P0)
- Command: `npm run builder -- --win msi` (from subst `X:\`)
- Error: `light.exe` exit 103, `project.wxs(30364) LGHT0103`: cannot find the 260-char elevenlabs path.
- Root cause: same as F-02; subst drives are canonicalized back to the physical `D:\...` path by
  npm/electron-builder, so subst does NOT shorten WiX inputs.
- Fix: verbatim copy to physically short `D:\hb\`, direct electron-builder invocation, MSI moved to
  canonical dir with hash verification. Retest: exit 0, MSI valid (ProductName/Version read from MSI
  table). STATUS: RESOLVED.

## F-04 — legacy release/ dir: corrupt win-unpacked, orphan blockmap, no installer (SEVERITY: P1)
- Not a build failure: forensics showed an interrupted-pack signature (exe missing, chromium payload
  present — the exact state `scripts/before-pack.cjs` documents) plus an old-config output dir.
- Fix: audited, evidence preserved in `AETHEROS_MASTER_78A_DESKTOP_BUILD_AUDIT.md`, generated files
  removed. STATUS: RESOLVED (explained, not rebuilt-over).

## Standing blockers (NOT failures of this run — environmental, honestly reported)
- B-01 SIGNING = BLOCKED: no code-signing credentials (`Get-AuthenticodeSignature` = NotSigned).
- B-02 INSTALL/UNINSTALL on clean VM = BLOCKED: no clean VM on this host (NSIS/MSI/portable
  installer-execution tests, reinstall, user-data safety all unexecuted).
- B-03 In-app UI smoke (navigation, agent screen, IPC, settings) = NOT PERFORMED: only process/window
  observation (`GUI_VISIBLE`), no interaction automation. No fake PASS claimed.
