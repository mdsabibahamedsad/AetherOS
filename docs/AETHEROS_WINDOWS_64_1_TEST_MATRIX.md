# AetherOS Windows 64.1 Test Matrix

| Category | Command | Result |
|---|---|---|
| Electron unit (10 files) | `node --test electron/*.test.cjs` (8 prior + tray-menu + update-manifest) | 122 passed (110 prior + 12 new) |
| Python platform | `pytest tests/aetheros_platform/test_windows_capabilities.py test_toast_actions.py test_windows_native.py` | 28 passed |
| Python intelligence | `pytest tests/agent/test_operating_layer.py tests/agent_network tests/aetheros_automation/test_orchestrator.py tests/automation/test_automation_model.py` | 242 passed |
| Web typecheck | `npm run typecheck` (web/) | clean |
| CLI smoke | `python -m aetheros_cli.main --help` | boots, agent + agent-network coexist |
| Bench | `python scripts/windows_bench.py` | executed, real numbers |
| Installer/E2E/VM | — | BLOCKED — CLEAN WINDOWS VM |
| CI `windows-platform.yml` | — | UNVERIFIED (not run) |
| Signing/Store | — | BLOCKED — credentials/account |

Matrix total is reported per-run in certification; no totals fabricated.
