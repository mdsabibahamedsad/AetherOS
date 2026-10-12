# AetherOS macOS Test Matrix (65)

| Category | Command | Result |
|---|---|---|
| Platform contracts | `pytest tests/aetheros_platform/test_macos_platform.py` | 11 passed |
| Entitlements audit | `python scripts/macos_entitlements_audit.py` | PASS |
| Electron unit (mac-relevant) | node --test (session-windows, tray-menu, update-manifest) | pass (in 122-file run) |
| Python regression | 64.1 battery (270) | 270 passed |
| Keychain/TCC/AX live | — | BLOCKED — MACOS ENVIRONMENT |
| DMG/PKG install, Gatekeeper, notarization | — | BLOCKED — creds/environment |
| Perf (Apple Silicon/Intel) | — | BLOCKED — hardware |
| CI `macos-platform.yml` | — | UNVERIFIED (not run) |
