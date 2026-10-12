# AetherOS 1.0 Platform Release Matrix

Statuses: PRODUCTION_READY · PRODUCTION_READY_WITH_LIMITATIONS · BLOCKED · NOT_SUPPORTED.
No platform is marked PRODUCTION_READY: zero packaged artifacts exist.

| Platform | Status | Reason |
|---|---|---|
| Windows x64 | BLOCKED | no signed installer; update logic tested only in harness |
| Windows ARM64 | BLOCKED | no hardware, no build |
| macOS (Intel + Silicon) | BLOCKED | no runner, no Developer ID, no notarization |
| Linux x64 | BLOCKED | no repository build/E2E; adapter logic tested in harness |
| Linux ARM64 | BLOCKED | no hardware |
| iOS / iPadOS | BLOCKED | no TestFlight / approval |
| Android | BLOCKED | no Play track execution |
| Web | BLOCKED | no production deployment |
| Server | BLOCKED | no production deployment |
| CLI (python) | BLOCKED | P1-1 updater failures + full suite incomplete |
| SDKs | BLOCKED | depend on unreleased hosts |
| Containers | NOT_SUPPORTED | no container distribution defined |

"AetherOS 1.0" therefore names a source tree + version, NOT a shippable
product. See blocked tests for per-item infrastructure needs.
