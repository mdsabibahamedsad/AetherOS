# AetherOS Windows Distribution Decision

Decision: **direct download (NSIS/MSI/portable) is the primary and only
supported model. Microsoft Store / MSIX is NOT pursued.**

Why: the Electron app is already packaged, signed-pipeline-ready, and
protocol/file-association complete via electron-builder; Store submission
requires a Partner Center account, certification passes, and MSIX
constraints that conflict with the bundled-Python architecture — none of
which exist here (BLOCKED — STORE ACCOUNT / CERTIFICATION ENVIRONMENT).
Per current Microsoft guidance, Store MSIX is re-signed by Microsoft
while direct distribution needs publisher signing (OV or Azure Artifact
Signing where eligible); our SIGNING doc follows exactly that path.

Security: signature + SHA256 per artifact, no silent downgrade (update
validator rejects), per-user install recommended (P1).
Update model: CI full installers + differential NSIS; signed-metadata
channel still MISSING (validator code exists, channel does not).
Cost: cert + CI minutes only; no Store fees or review latency.
CI: `desktop-release.yml` (existing) + `windows-platform.yml` (new).
Limitations: SmartScreen reputation must be earned post-signing; no
auto-update/rollback until the channel ships.
