# AetherOS Master 76 Artifact Report (local build, 2026-09-12)

Built on win32-x64 via `npm run pack` equivalent (build + builder --dir +
NSIS/MSI/portable targets completed): tsc -b clean, vite 14.53s,
electron 40.9.3 fetched (138MB, 1m55s), asar packed, exe identity stamped,
blockmap generated. Statuses: Windows x64 NSIS ECO→ BUILT (unsigned);
MSI BUILT (unsigned); portable BUILT; unpacked BUILT+LAUNCHED. macOS/Linux/
mobile/web/server/CLI-installer: NOT BUILT here (no runners) → BLOCKED.

| File | MB | SHA-256 (see local-artifacts.json) | Signed |
|---|---|---|---|
| AetherOS-1.0.0-win-x64.exe | 178.7 | recorded | NO (NotSigned verified) |
| AetherOS-1.0.0-win-x64.msi | 187.5 | recorded | NO |
| AetherOS-1.0.0-win-x64-portable.exe | 178.6 | recorded | NO |

Immutability: outputs untouched since build; any rebuild gets new hashes
(recorded, never overwritten). Version consistency: desktop/root 1.0.0;
backend 0.16.0 independent (documented intent); artifact names match
`AetherOS-{version}-{platform}-{arch}` convention. Hermes legacy: no legacy
paths harmed; migration behavior unchanged (guide stands).
