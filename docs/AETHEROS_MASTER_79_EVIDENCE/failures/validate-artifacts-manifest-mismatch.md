# release:validate-artifacts output (host, 2026-09-15) — W79-029 related

Command: `node scripts/release/validate-artifacts.mjs` in apps/desktop.

Result: INVALID — 11 failure(s). Per-file existence/size/sha "ok" lines
printed for all 7 dist entries, then manifest cross-check failures:

- FAIL: artifact missing from manifest: AetherOS-1.0.0-linux-x64.AppImage
- FAIL: artifact missing from manifest: AetherOS-1.0.0-linux-x64.deb
- FAIL: artifact missing from manifest: AetherOS-1.0.0-linux-x64.rpm
- FAIL: hash mismatch for AetherOS-1.0.0-win-x64-portable.exe
- FAIL: size mismatch for AetherOS-1.0.0-win-x64-portable.exe
- FAIL: hash mismatch for AetherOS-1.0.0-win-x64.exe
- FAIL: size mismatch for AetherOS-1.0.0-win-x64.exe
- FAIL: hash mismatch for AetherOS-1.0.0-win-x64.exe.blockmap
- FAIL: size mismatch for AetherOS-1.0.0-win-x64.exe.blockmap
- FAIL: hash mismatch for AetherOS-1.0.0-win-x64.msi
- FAIL: size mismatch for AetherOS-1.0.0-win-x64.msi

Interpretation: the checked-in Master 78 manifest
(docs/AETHEROS_MASTER_78_RELEASE_ARTIFACT_MANIFEST.json) is STALE relative
to the current dist-packaged outputs (artifacts were rebuilt from a dirty
tree after the manifest was written; manifest lacks the 3 Linux entries
entirely). This is a PROVENANCE/MANIFEST gap (P1), NOT artifact corruption:
the three Windows artifacts byte-match the Master 78A baseline hashes
quoted in the Master 79 prompt (see checksums/W79-001-host-hashes.md).
Validator NOT re-run with --manifest override; stale-manifest failure
preserved as evidence. Full log: this file + command log.
Exit code: 1.
