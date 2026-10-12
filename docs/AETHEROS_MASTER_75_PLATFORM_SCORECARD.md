# AetherOS Master 75 Platform Scorecard — 1.0.0

| Platform | build | sign | install | launch | core | update | recovery | status |
|---|---|---|---|---|---|---|---|---|
| Windows x64 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | UNVERIFIED | TESTED* | TESTED* | BLOCKED |
| Windows ARM64 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no hardware |
| macOS arm64/x64 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no runner/certs |
| Linux x64 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | UNVERIFIED | TESTED* | TESTED* | BLOCKED |
| Linux ARM64 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no hardware |
| iOS / iPadOS | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no TestFlight |
| Android | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no Play track |
| Web | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED — no deployment |
| Server | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | TESTED* | UNVERIFIED | UNVERIFIED — no deployment |
| CLI | TESTED† | NOT_APPLICABLE | TESTED† | TESTED† | PARTIAL‡ | PARTIAL‡ | UNVERIFIED | PARTIAL — 22 updater-test failures |

\* update/rollback LOGIC tested in harness (Master 70.5), not on devices.
† Python CLI suite partially run via wrapper (security 351 pass); full suite time-boxed.
‡ P1-1: 22 failures in CLI self-update tests (pre-existing product bug).
