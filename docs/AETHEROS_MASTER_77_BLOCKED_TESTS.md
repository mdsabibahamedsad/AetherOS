# AetherOS Master 77 — Blocked Tests (exact reproduction commands)

Host limitation: Windows dev machine, no Linux runner, no clean VM, no signing certs.
Each item below is BLOCKED (not PASSED, not UNVERIFIED-as-pass).

## 1. Linux artifact production (CI, ubuntu-latest)

```bash
gh workflow run desktop-release.yml -f version=1.0.0 -f prerelease=true
# or push a tag workflow_dispatch manually; then:
gh run watch <run-id> --exit-status
```

What it proves: AppImage/deb/rpm exist, `file`/`dpkg-deb --info`/`rpm -qip` metadata,
SHA-256, SBOM, artifact upload. Workflow file: `.github/workflows/desktop-release.yml`
(job `build-linux`).

## 2. Windows clean-VM install matrix (VM: Windows 11 23H2+, snapshot before each case)

```powershell
# NSIS silent install + version check + uninstall
Start-Process .\AetherOS-1.0.0-win-x64.exe -ArgumentList "/S" -Wait
Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Where-Object DisplayName -Like "AetherOS*"
# launch GUI, smoke test, then:
& "$env:ProgramFiles\AetherOS\Uninstall AetherOS.exe" /S
# MSI equivalents:
msiexec /i AetherOS-1.0.0-win-x64.msi /qn
msiexec /x AetherOS-1.0.0-win-x64.msi /qn
```

## 3. Linux install matrix (VMs: Ubuntu 24.04 GNOME, Fedora 40 KDE, x64)

```bash
chmod +x AetherOS-1.0.0-linux-x64.AppImage
./AetherOS-1.0.0-linux-x64.AppImage --appimage-extract  # structure check
file AetherOS-1.0.0-linux-x64.AppImage
sudo dpkg -i AetherOS-1.0.0-linux-x64.deb
dpkg-deb --info AetherOS-1.0.0-linux-x64.deb
dpkg-deb --contents AetherOS-1.0.0-linux-x64.deb
sudo apt remove -y aetheros  # exact package name from --info
sudo dnf install -y ./AetherOS-1.0.0-linux-x64.rpm
rpm -qip ./AetherOS-1.0.0-linux-x64.rpm
rpm -qlp ./AetherOS-1.0.0-linux-x64.rpm
sudo dnf remove -y aetheros
```

## 4. Wayland session (GNOME Wayland + KDE Wayland VMs)

Launch under Wayland; verify documented matrix: notifications native; tray/clipboard limited;
screen_capture/input/window_management surface structured `capability_unavailable` errors
(never silent success). Screen-capture portal path stays UNSUPPORTED until implemented.

## 5. Signing + provenance (needs secrets, CI)

`WINDOWS_CSC_LINK`/`WINDOWS_CSC_PASSWORD` for NSIS/MSI Authenticode; GPG keys for Linux;
Sigstore/GitHub attestation via `desktop-release.yml` (`attestations: write` already granted).
Verify with `Get-AuthenticodeSignature` (win) / `rpm -K` / `dpkg-sig --verify` (linux).

## 6. Full renderer suite + packaging E2E in CI

```bash
npm ci
npm run test:ui -- --run
npm run test:desktop:platforms
npm run build && npm run dist:linux   # ubuntu-latest
npm run build && npm run dist:win     # windows-latest
```
