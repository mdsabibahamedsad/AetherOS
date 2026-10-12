# AetherOS iOS/iPadOS Test Matrix (67)

| Category | Command | Result |
|---|---|---|
| Mobile contracts | `pytest test_mobile_contract.py` | 6 passed (incl. live backend-handler check) |
| Swift unit (5 files) | xcodebuild test | BLOCKED — Xcode/macOS |
| Simulator journeys 1–22 | — | BLOCKED — macOS |
| Physical device | — | BLOCKED — hardware |
| Push/APNs | — | BLOCKED — capability + device |
| Biometrics/Keychain live | — | BLOCKED — device |
| iPad multitasking | — | NOT READY (iPhone-only target) |
| TestFlight/App Store | — | BLOCKED — creds |
| CI `ios-platform.yml` | — | UNVERIFIED (not run) |
