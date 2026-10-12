# AetherOS Beta User Guide — 1.1.0-beta.1

Beta software may crash, change behavior, and require updates. Do not use it
as your only environment for critical work. Extra caution with computer-use,
filesystem access, browser automation, and autonomous agents.

## Installation

- **Windows x64**: run the signed `AetherOS-1.1.0-beta.1-win-x64.exe` (NSIS).
  Verify the publisher shows AetherOS before proceeding. Per-machine install
  prompts for admin (UAC) — this is expected, never bypassed.
- **Linux x64**: AppImage (mark executable, run), or deb/rpm via the beta
  repository. Privileged install asks for sudo/polkit approval.
- **macOS / iOS / Android / ARM64**: NOT in this beta (see Platform Matrix).

## Channels and updates

- Beta channel receives controlled rollouts (10% → 25% → 50% → 100%).
- Updates show version, size, release notes, and restart requirement.
  Security updates may be mandatory.
- Before restart the updater checkpoints active agent tasks and resumes after;
  if resuming is unsafe the update defers.
- If an update fails health checks, the app automatically rolls back to the
  previous version. You can also roll back manually from Settings → Updates.
- On metered connections, downloads follow your policy (allow / Wi-Fi-only /
  block). Updates never silently consume unbounded bandwidth or disk.

## Reporting bugs

Settings → Support → **Export support bundle**, then attach it to your report.
The bundle is privacy-redacted (tokens, keys, cookies replaced with
`[REDACTED]`) — review it before sending.

Include: what you did, what you expected, what happened, version
(`1.1.0-beta.1`), platform, and whether the issue survives a restart.

Severity: P0 (security/data-loss/system-wide), P1 (major beta feature broken),
P2 (normal bug), P3 (minor).

## Privacy

Beta telemetry is minimal and documented: install/launch/update outcomes,
crash counts, performance aggregates. No prompts, memory content, files, or
secrets. Opt out in Settings → Privacy. Data retention and deletion are
documented in the Admin Guide.

## Known limitations (this beta)

- Windows x64 and Linux x64 only; macOS/iOS/Android blocked (no signing/store infra).
- No real-device clean-machine validation yet; no store distribution.
- Telemetry pipeline is local-only; fleet metrics are UNVERIFIED.
