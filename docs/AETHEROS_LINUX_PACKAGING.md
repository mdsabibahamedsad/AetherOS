# AetherOS Linux Packaging / Installation / Updates / Troubleshooting

Formats: AppImage (primary), deb (secondary), rpm (secondary) × x64 —
all CONFIG-VERIFIED via builder config + CI validate job + structural
check script. Flatpak NOT SUPPORTED. No package BUILT here (needs
Linux runner with system deps). Per-user install preferred; verify
permissions post-install; preserve `~/.aetheros` + XDG state on
upgrade/remove.

Updates: no live channel; reuse manifest validator discipline
(https/hash/version/publisher, anti-downgrade); rollback = previous
package + state/schema compatibility planning. Troubleshooting:
`~/.local/state/aetheros/logs`, diagnostics bundle (redacted), portal
errors surfaced with DE name/version, sandbox denials diagnosed not
disabled. Migration: `detect_legacy` + copy-plan (never delete);
Hermes paths (`~/.hermes`, `~/.config/hermes`, …) preserved.
E2E journeys A–R: defined, UNEXECUTED (need Linux VM).
