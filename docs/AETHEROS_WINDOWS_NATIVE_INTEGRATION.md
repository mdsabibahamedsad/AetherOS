# AetherOS Windows Native Integration

Boundary (narrow, enforced): Renderer → typed preload → validated
`aetheros:*` IPC → main-process services → native APIs. Renderer never
touches child_process, filesystem, registry, or shell.

| Capability | Backend | Electron | Status |
|---|---|---|---|
| Notifications | `desktop/notifications.py` + action validation | `aetheros:notify` IPC | PARTIAL (actions UNVERIFIED live) |
| Tray | `desktop/tray.py` model | `tray-menu.cjs` (tested) + `tray.cjs` wiring | IMPLEMENTED — UNVERIFIED live |
| Startup | `desktop/startup.py` (HKCU Run, audited) | setting surface pending | IMPLEMENTED — UNVERIFIED live |
| Capabilities | `windows_capabilities.py` (+ `python -m` dump) | diagnostics wiring pending | AVAILABLE (backend) |
| Event Log | `observability/eventlog.py` (stable IDs, redacted) | n/a | IMPLEMENTED — UNVERIFIED live write |
| Hello | detection in registry | n/a | UNAVAILABLE (no fake prompt) |
| UIA | `aetheros_computer/uia.py` schema+scopes | n/a | schema AVAILABLE; tree UNVERIFIED |
| Update/rollback | `update-manifest.cjs` validator+recorder | apply flow missing | PARTIAL |

Every native capability maps to Master 60 authority
(`os.notification`, `os.tray`, `os.startup.persist`,
`ui.read/control.*`, `release.update/rollback`); no native API is a
privilege escape. Unavailable features surface as unavailable states,
never dead toggles.
