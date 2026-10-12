# AetherOS Master 77 — Build Matrix

Source commit: `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` · Version `1.0.0`

## Toolchain (verified)

| Component | Version | Source |
|---|---|---|
| Node (host) | v25.5.0 | `node --version` |
| npm (host) | 11.8.0 | `npm --version` |
| Node (CI) | 22 | all desktop workflows |
| Electron (dev dep) | 40.10.6 | `electron/package.json` |
| Electron (packaged runtime pin) | 40.9.3 | `build.electronVersion`, confirmed by exe FileVer |
| electron-builder | 26.8.1 | `electron-builder/package.json` |
| TypeScript | 6.0.3 | `typescript/package.json` |
| Vite | 8.0.10 | `vite/package.json` |
| Package manager | npm | `package-lock.json` + `npm ci` in CI |

## Architecture matrix

| Platform | x64 | ARM64 | Artifact | Build | Install | Launch | Update |
|---|---|---|---|---|---|---|---|
| Windows | IMPLEMENTED (exe/msi/portable) | NOT_APPLICABLE (not declared) | PASSED (validate-artifacts VALID) | BLOCKED (clean VM) | UNVERIFIED (spawn-only) | NOT_IMPLEMENTED |
| Linux | BLOCKED (no runner) | NOT_APPLICABLE (not declared) | BLOCKED | BLOCKED | BLOCKED | NOT_IMPLEMENTED |
| macOS | ABSENT (no runner) | ABSENT (no runner) | BLOCKED | BLOCKED | BLOCKED | NOT_IMPLEMENTED |

ARM64 is not declared for win/linux in `package.json` build targets and no ARM64 native
module evidence exists (`node-pty` staged copy is x64). No ARM64 claim is made.

## Reproducibility record

- Build command: `npm run dist:win` / `npm run dist:linux` (each = full `npm run build` + builder).
- Relevant env: `NODE_OPTIONS=--max-old-space-size=16384` (CI + local scripts).
- Existing Windows installers (2026-08-22) predate reproducible-build recording; per-artifact
  build environment was not captured at that time → provenance UNVERIFIED.
- CI (`desktop-release.yml`) captures runner OS, commit (`fetch-depth: 0`), SHA-256, SBOM per build.
  Next production build must run there so provenance is attested, not asserted.
