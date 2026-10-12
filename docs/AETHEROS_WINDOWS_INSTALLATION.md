# AetherOS Windows Installation

Channels built by CI (`desktop-release.yml`, `windows-latest`): NSIS
installer, MSI, portable — x64, artifacts `AetherOS-<version>-win-x64.*`
plus `windows-artifacts.sha256`.

Requirements: 64-bit Windows 10/11. Per the current NSIS config installs
are per-machine (`perMachine: true`, GUID
`{1A2B3C4D-...}`); P1 follow-up is moving to per-user to minimize
elevation per Microsoft best practices. Shortcuts: Start Menu + Desktop.
`deleteAppDataOnUninstall: false` — user data under `%LOCALAPPDATA%\
aetheros` is preserved; uninstall removes binaries, shortcuts, protocol
and association registrations.

Clean-machine install/uninstall/repair: BLOCKED — CLEAN VM (never claimed).
Silent install: `installer.exe /S` (NSIS default; unverified here).
Unsigned builds WILL trigger SmartScreen; see SIGNING doc. First launch
runs renderer onboarding; backend health is probed before agent use.
