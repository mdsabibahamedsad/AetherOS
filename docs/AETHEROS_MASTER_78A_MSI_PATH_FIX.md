# AETHEROS MASTER 78A — MSI LGHT0103 Path Fix

## ROOT CAUSE

WiX `light.exe` (v4.0.0.5512, vendored by electron-builder 26.8.1) fails with `LGHT0103: The system
cannot find the file` when a harvested source path reaches Windows `MAX_PATH` (260 chars). The
bundled Python tree stages `Lib/site-packages/elevenlabs/**/types/*.py` files whose names alone
exceed 130 chars. Combined with this host's 44-char checkout prefix
(`D:\hermes-agent-main\aetheros\apps\desktop\`), the longest staged path hit exactly 260 chars:

## OFFENDING FILE

`dist-packaged\win-unpacked\resources\py\Lib\site-packages\elevenlabs\text_to_speech\types\body_text_to_speech_streaming_with_timestamps_v_1_text_to_speech_voice_id_stream_with_timestamps_post_apply_text_normalization.py`

- Absolute length from this checkout: **260 chars** (= MAX_PATH; WiX cannot open it)
- Package: `elevenlabs` (auto-generated SDK type stubs)
- WiX reference: `project.wxs(30364)`, `light.exe` exit code 103
- 3 further files at 241–247 chars (pronunciation_dictionary + text_to_speech stubs) — see build audit §6.

## PATH LENGTH

| File (tail) | Length |
|---|---|
| `..._stream_with_timestamps_post_apply_text_normalization.py` | 260 |
| `..._add_from_rules_post_workspace_access.py` | 247 |
| `..._with_timestamps_post_apply_text_normalization.py` | 243 |
| `..._add_from_rules_post_rules_item.py` | 241 |

Guard budget: 240 (`scripts/release/check-packaging-path-lengths.mjs`). Staged suffix below
`dist-packaged\win-unpacked\` is 216 chars, so any checkout prefix longer than 24 chars trips the
guard and any prefix at/over ~44 chars breaks WiX outright.

## FIX

Physically short, verbatim build root: `D:\hb\` (5-char prefix → longest staged path 221 chars).

- `D:\hb\` received verbatim `robocopy` copies of `package.json`, `dist/`, `build/`, `electron/`,
  `assets/`, `public/`, `scripts/` plus a `node_modules` junction to the repo install.
- No source file was renamed, moved, excluded, or edited; no dependency removed
  (elevenlabs is imported at runtime — renaming would break package integrity).
- `subst X:` was tried first and REJECTED: npm/electron-builder canonicalize the subst drive back to
  the physical `D:\...` path in the `light.exe` command line, so it does not shorten anything. Only a
  physically short path works.
- MSI was packaged from `D:\hb\` by invoking the repo's own electron-builder directly
  (`node <repo>/node_modules/electron-builder/out/cli/cli.js --win msi`), then MOVED (not copied) to
  canonical `apps/desktop/dist-packaged/` with SHA-256 verified identical before/after the move.

## WHY FIX IS SAFE

- Byte-identical inputs: same `dist/` renderer bundle, same `build/bundled-python/` runtime, same
  `electron/` main process, same `package.json` build config, same commit (`2bdfbfd8ebcf`, dirty-tree
  caveat recorded in build stamp).
- Application behavior untouched: fix changes only the filesystem location of the packaging operation.
- NSIS + portable artifacts were built from the normal checkout path and share the same payload.

## TEST RESULT

- `light.exe` exit code 0; `AetherOS-1.0.0-win-x64.msi` (203,137,784 bytes) produced 2026-09-15 09:39 UTC+2.
- MSI Property table: `ProductName=AetherOS`, `ProductVersion=1.0.0.0`.
- SHA-256 `1069FC6D…5B031B` identical before/after move to canonical dir.
- Permanent remediation: keep the `dist:win:validate-paths` gate (fails early with actionable output);
  document that Windows release packaging requires a short checkout path until the elevenlabs dependency
  shortens its generated filenames upstream.
