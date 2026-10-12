# AetherOS Windows Architecture

App ID `com.aetheros.aetheros` · Product `AetherOS` · Electron 40.

```
Renderer (Vite React, sandboxed, no Node)
   ↓  single contextBridge namespace
Typed preload (preload.cjs)
   ↓  validated aetheros:* IPC
Main process (main.cjs)
   ├─ windows, sessions, protocol, power, notifications
   └─ Python backend (bundled py/ + backend/ extraResources)
```

Security invariants: `contextIsolation/nodeIntegration=false/sandbox/
webSecurity` on every window; no wildcard IPC found; file IPC byte-capped
with purpose logging; secrets via `safeStorage` (DPAPI) with fail-closed
when unavailable. Renderer never spawns processes.

Paths: `%LOCALAPPDATA%\aetheros` home (native Windows), `HERMES_HOME`
deprecated fallback (compat only). No `C:\Users\...` hardcodes in helpers.

Integration present: `aetheros://` protocol registration, `.aetheros/
.aethskill/.aethcfg` associations, AppUserModel notifications,
power-resume hooks, hidden consoles for backend children.
Deliberately absent: tray, login-item background mode, updater channel
(see UPDATE doc), UIA tree (OCR fallback, see COMPUTER_USE doc).
