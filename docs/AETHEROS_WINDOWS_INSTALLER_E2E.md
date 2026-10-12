# AetherOS Windows Installer E2E

Primary: NSIS (direct download). Secondary: MSI, portable. Matrix
(fresh/upgrade/repair/uninstall/reinstall, interrupted, low-permission,
low-disk, legacy-state, locked-files, per-user, silent): NOT EXECUTED —
BLOCKED — CLEAN WINDOWS VM. Harness direction: scripted VM snapshots
asserting installed files, shortcuts, protocol/file-association
registration, startup entries, uninstaller completeness, data-dir
preservation, version/publisher metadata. P1: flip NSIS to per-user
(`perMachine: false`) with migration handling for existing per-machine
installs — NOT changed untested. Uninstall contract (already
configured): binaries/shortcuts/registrations/startup/scheduled-tasks
removed; user data kept unless explicit Remove-data chosen.
