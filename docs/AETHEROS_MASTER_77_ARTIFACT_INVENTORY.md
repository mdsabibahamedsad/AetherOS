# AetherOS Master 77 — Artifact Inventory (human-readable)

Source commit: `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` · Version `1.0.0`
Canonical output: `apps/desktop/dist-packaged/` · Machine source: `AETHEROS_MASTER_77_ARTIFACT_INVENTORY.json`

## Present (all IMPLEMENTED, integrity-verified 2026-09-13)

| Filename | Type | Size | SHA-256 (full in JSON) | Commit binding |
|---|---|---|---|---|
| AetherOS-1.0.0-win-x64.exe | NSIS installer | 195,739,994 | `87091be0…1f68` | VERIFIED-LOCAL (rebuilt 2026-09-13 from HEAD via `dist:win:nsis`) |
| AetherOS-1.0.0-win-x64.msi | MSI installer | 196,571,899 | `6fe65eb4…f2f3` | UNVERIFIED (2026-08-22; fresh MSI blocked by WiX MAX_PATH — see FINAL_STATUS) |
| AetherOS-1.0.0-win-x64-portable.exe | Portable | 187,240,131 | `cce16c07…c9cf` | UNVERIFIED (2026-08-22) |
| AetherOS-1.0.0-win-x64.exe.blockmap | Differential blockmap | 202,557 | `37c1e661…6a7e` | VERIFIED-LOCAL (same 2026-09-13 invocation) |

`release:validate-artifacts` → VALID (names, sizes > 0, versions == 1.0.0, hashes computed).

## Missing (BLOCKED, need Linux runner)

- `AetherOS-1.0.0-linux-x64.AppImage`
- `AetherOS-1.0.0-linux-x64.deb`
- `AetherOS-1.0.0-linux-x64.rpm`

## Stale (do not publish)

- `apps/desktop/release/` — previous-generation output (win-unpacked, July 2026 mtimes,
  effective-config `output: release`). The prompt's "missing installer in release/" observation is
  explained: the output directory moved to `dist-packaged/`; `release/` is archaeology, not product.
  Kept for evidence; archive before any deletion.

## Naming convention (existing, kept)

`AetherOS-${version}-${os}-${arch}.${ext}` with `${os}` ∈ {win, linux, macOS}, portable suffix
`-portable`. No misleading names found.
