# AETHEROS MASTER 79 — Command Log (reproducible)

Workdir unless noted: `D:\hermes-agent-main\aetheros`. PowerShell 7 shell.

1. `git rev-parse HEAD` → `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1`
2. `git status --short` → ~2755 paths (dirty); `git diff --stat` → 1422 files
3. `Get-ChildItem apps\desktop\dist-packaged` → sizes (NSIS 195891460, MSI 203137784, portable 162205111, blockmap 202867, linux×3, yml×2, win-unpacked/)
4. `Get-FileHash <each win artifact> -Algorithm SHA256` → matches §2 baselines
5. `Get-AuthenticodeSignature <each win artifact>` → NotSigned ×3
6. `Get-ChildItem apps\desktop\dist-packaged\win-unpacked` + `(Get-Item ...\AetherOS.exe).VersionInfo` → ProductVersion 40.9.3
7. `Get-Content ...\resources\install-stamp.json` → commit==HEAD, dirty=true, source=local
8. `node -e` package.json reads → electron ^40.10.6, electron-builder ^26.8.1, build.electronVersion 40.9.3, nsis perMachine=true, deleteAppDataOnUninstall=false
9. `Select-String apps\desktop\electron\main.cjs -Pattern 'BrowserWindow|title'` → titles 'AetherOS' (lines ~4627/~4677); `Get-Content apps\desktop\index.html` → `<title>Aetheros</title>` line 11
10. `Select-String apps\desktop\electron\hardening.cjs -Pattern 'contextIsolation|nodeIntegration|sandbox'` → true/false/true
11. `Get-ItemProperty HKCU/HKLM ...\Uninstall\* | Where DisplayName -match 'Aether'` → none
12. `Test-Path $env:SystemRoot\System32\WindowsSandbox.exe` → False
13. `systeminfo | Select-String 'OS Name','OS Version','System Type'` → Win11 Pro, 10.0.26200, x64
14. `node scripts/release/validate-artifacts.mjs` (in apps/desktop) → exit 1, 11 manifest failures (stale M78 manifest)
15. `node scripts/release/check-packaging-path-lengths.mjs` → FAIL, 6 paths >240 (elevenlabs/mistralai)
16. `npm run test:desktop:platforms` (in apps/desktop) → 176/176 pass
17. MSI ProductCode via `WindowsInstaller.Installer` COM `OpenDatabase` read-only → `{77035F50-600E-49B1-851F-6E004FDBC134}`
18. `node --version` → v25.5.0; `npm --version` → 11.8.0; `.\.venv\Scripts\python.exe --version` → 3.12.13
19. `Get-Content .github\workflows\desktop-release.yml | Select -First 80` → setup-node node-version 22
20. `Get-Date -Format o` → 2026-09-15T10:12:06+06:00

NOT executed (no VM, non-admin dev host): installer runs, msiexec /i//x//qn,
GUI launches, screenshots, tasklist/process checks, Event Viewer, signtool,
uninstall/reinstall, Sandbox/VM operations. Nothing of the sort is claimed.
