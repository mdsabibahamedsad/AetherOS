# AetherOS Windows Signing

Status: **BLOCKED — SIGNING CREDENTIALS.** No signing step exists in
`desktop-release.yml`; `win.signAndEditExecutable` is false. Nothing in
this repo is signed by us and no SmartScreen/Defender verdict is claimed.

Pipeline to implement (structural, ready to wire): publisher identity →
OV certificate or Azure Artifact Signing (per current Microsoft guidance,
EV is NOT a SmartScreen bypass) → CI secret → sign `.exe/.dll/.msi/
uninstallers`/helpers during `electron-builder` (`signAndEditExecutable`)
→ RFC3161 timestamp → verify (`signtool verify /pa`) → gate release on
verification → rotate/rotate-out procedure. Sign every executable
component, not just the top-level installer. Until then: expect
SmartScreen warnings on first release; publish SHA256 (`windows-
artifacts.sha256` already in CI) and keep publisher identity stable to
build reputation. Never claim "SmartScreen clean" without evidence.
