# AetherOS Beta Platform Matrix — 1.1.0-beta.1

Status values: BETA_READY · BETA_READY_WITH_LIMITATIONS · BLOCKED · NOT_APPLICABLE · UNVERIFIED.
Columns: build · sign · install · launch · login · agent · browser · computer · memory · automation · update · rollback · uninstall · status.

| Platform | build | sign | install | launch | login | agent | browser | computer | memory | automation | update | rollback | uninstall | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Windows x64 | BLOCKED¹ | BLOCKED² | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | TESTED³ | TESTED³ | UNVERIFIED | BETA_READY_WITH_LIMITATIONS |
| Windows ARM64 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no hardware |
| macOS x64 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no Apple runner/certs |
| macOS ARM64 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no Apple runner/certs |
| Linux x64 | BLOCKED¹ | BLOCKED² | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | TESTED³ | TESTED³ | UNVERIFIED | BETA_READY_WITH_LIMITATIONS |
| Linux ARM64 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no hardware |
| iOS / iPadOS | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no TestFlight |
| Android | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED — no Play track |
| Web | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | NOT_APPLICABLE | UNVERIFIED — no beta deployment |
| Server | TESTED⁴ | TESTED⁴ | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | TESTED³ | TESTED³ | UNVERIFIED | BETA_READY_WITH_LIMITATIONS |

Notes:
1. Packaged build BLOCKED by pre-existing `design-system` typecheck errors + no signing creds.
2. Signing BLOCKED: no EV cert / Apple ID (fail-closed, proven in evidence).
3. Update/rollback logic TESTED in harness + unit suites (46 tests); on-device drills UNVERIFIED.
4. Update-server manifest/artifact/rollout logic executed in-process via vitest.

Golden journeys B01–B25: B17/B18/B19 (update paths) partially executed in
harness; all device-dependent journeys UNVERIFIED or BLOCKED — see
`AETHEROS_MASTER_74_BETA_TEST_MATRIX.json`.
