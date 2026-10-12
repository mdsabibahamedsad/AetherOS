# AetherOS Master 76 Device Matrix (only actually accessible hardware)

| Device | OS/arch | AVAILABLE | TESTED | Result |
|---|---|---|---|---|
| DEV-HOST-01 (this machine) | Windows 11 x64 | AVAILABLE | TESTED (partial) | build+pack+hash+launch PASS; install/VM N/A |
| macOS Apple Silicon/Intel | — | NOT_AVAILABLE | — | BLOCKED (no hardware/runner/certs) |
| Linux x64/ARM64 | — | NOT_AVAILABLE | — | BLOCKED |
| Windows ARM64 | — | NOT_AVAILABLE | — | BLOCKED |
| iPhone/iPad | — | NOT_AVAILABLE | — | BLOCKED |
| Android phone/tablet | — | NOT_AVAILABLE | — | BLOCKED |

No platform behavior inferred from another. Clean-machine/VM validation:
BLOCKED (no VMs). Staging: BLOCKED (no infra). Installer execution on host:
NOT ATTEMPTED (would mutate dev host without elevation path; clean VM required).
