# AETHEROS MASTER 78A — Release Artifact Inventory

Canonical dir: `apps/desktop/dist-packaged/` (commit `2bdfbfd8ebcf`, dirty-tree caveat applies).
Created times are 2026-09-15 ~09:21–09:39 (+02:00) except Linux artifacts (2026-09-14, prior run).

| Filename | Type | Version | Size (bytes) | SHA-256 (prefix) | Source commit | Status |
|---|---|---|---|---|---|---|
| AetherOS-1.0.0-win-x64.exe | nsis | 1.0.0 | 195891460 | b86b22f7… | 2bdfbfd8 | CURRENT_HEAD_BOUND |
| AetherOS-1.0.0-win-x64.exe.blockmap | nsis-blockmap | 1.0.0 | 202867 | d365386b… | 2bdfbfd8 | CURRENT_HEAD_BOUND |
| AetherOS-1.0.0-win-x64.msi | msi | 1.0.0 (table 1.0.0.0) | 203137784 | 1069fc6d… | 2bdfbfd8 | CURRENT_HEAD_BOUND |
| AetherOS-1.0.0-win-x64-portable.exe | portable | 1.0.0 | 162205111 | 214d4255… | 2bdfbfd8 | CURRENT_HEAD_BOUND |
| AetherOS-1.0.0-linux-x64.AppImage | linux | 1.0.0 | 176855362 | 20093a08… | unknown | LEGACY_NON_HEAD_BOUND |
| AetherOS-1.0.0-linux-x64.deb | linux | 1.0.0 | 140407144 | 939fb248… | unknown | LEGACY_NON_HEAD_BOUND |
| AetherOS-1.0.0-linux-x64.rpm | linux | 1.0.0 | 121074205 | 820c4d8d… | unknown | LEGACY_NON_HEAD_BOUND |
| latest.yml | updater metadata | 1.0.0 | 349 | (byproduct) | 2bdfbfd8 | CURRENT (auto-generated; update NOT_IMPLEMENTED) |
| builder-debug.yml | builder byproduct | — | 826 | (byproduct) | 2bdfbfd8 | CURRENT (auto-generated) |
| win-unpacked/ | staged app | 1.0.0 | — | — | 2bdfbfd8 | CURRENT (retained: runtime-probe evidence) |

Full hashes: `docs/AETHEROS_MASTER_78A_WINDOWS_ARTIFACT_CHECKSUMS.txt`.
Machine-readable: `docs/AETHEROS_MASTER_78A_WINDOWS_RELEASE_MANIFEST.json`.
Removed this run (all generated, documented in build audit §3): legacy `apps/desktop/release/`
(corrupt win-unpacked, orphan blockmap, old effective config), stale `__msi-x64/` WiX staging,
temporary short-path root `D:\hb\` (after MSI move with hash verification).
