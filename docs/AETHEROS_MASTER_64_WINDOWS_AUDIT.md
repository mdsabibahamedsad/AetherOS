# AETHEROS Master 64 — Windows Audit

Date: 2026-09-11 · Scope: `apps/desktop`, `apps/shared`, Electron main/preload,
backend Windows paths, `aetheros_computer`, packaging, CI, docs.
Method: code inspection + executed unit tests. No values fabricated; anything
not executable here is marked BLOCKED — ENVIRONMENT or UNVERIFIED.

## 1. Current Windows architecture — PARTIAL

Electron 40 app (`apps/desktop`, `main: electron/main.cjs`) hosting the
renderer, spawning/managing a Python backend. Backend home resolves to
`%LOCALAPPDATA%\aetheros` on native Windows (`aetheros_constants.py`),
`~/.aetheros` on POSIX. No `platform/windows/` abstraction exists; Windows
behavior is spread across `electron/*.cjs`, backend `sys.platform` branches,
and `aetheros_computer/platform_caps.py`. Consolidation is deferred (no
duplication created by this phase).

## 2. Desktop architecture — COMPLETE (structure)

`electron/main.cjs` (main), `electron/preload.cjs` (single
`contextBridge.exposeInMainWorld` namespace), renderer (Vite React).
Python backend bundled via `scripts/bundle-python.cjs` into
`extraResources` (`py/`, `backend/`).

## 3. Electron architecture — PARTIAL

Versions: Electron ^40.10.6 (dep) / 40.9.3 (builder target). Three window
creations audited (`main.cjs` ~lines 2470, 3379, 4623) all enforce
`contextIsolation: true, nodeIntegration: false, sandbox: true,
webSecurity: true`. No `enableRemoteModule`; no `allowRunningInsecureContent`
found.

## 4. Main process — PARTIAL

Window/session registry, privileged `aetheros-media` protocol handler,
`aetheros://` protocol registration (`setAsDefaultProtocolClient`, ~line
5922), powerMonitor resume handling, hidden Windows consoles for backend
spawns (tested). MISSING: system tray, auto-start setting, crashReporter,
`second-instance`/`open-url` argv routing (protocol registered but inbound
URL dispatch unverified).

## 5. Preload — COMPLETE

Exactly one exposed namespace; 71 internal `ipcRenderer` call sites flow
through it. No direct `child_process`/`fs` in renderer found.

## 6. Renderer — COMPLETE (existing)

Unchanged by this phase; covered by Masters 7/9.

## 7. IPC — PARTIAL

Typed `aetheros:*` handlers (e.g. `aetheros:notify` with
`Notification.isSupported()` guard; `aetheros:readFileDataUrl` with
byte-capped, purpose-logged resolution). No wildcard IPC found in audit
sample. Full endpoint-by-endpoint schema catalog: UNVERIFIED (not enumerated
here; no new endpoints added).

## 8. Backend — COMPLETE (existing)

`aetheros` 0.16.0 editable install; CLI `--help` verified working in this
gate (post `agent-network` collision fix). Bundled-python script exists;
bundled-backend boot on a clean machine: UNVERIFIED here.

## 9. Python runtime — PARTIAL

`bundle-python.cjs` stages an embedded runtime into the package. Execution
of the bundled runtime: BLOCKED — ENVIRONMENT (no packaged build produced
here; Electron binary absent from `node_modules`).

## 10. Native process execution — PARTIAL

`windows-child-process.test.cjs` pins hidden consoles + documented
interactive spawns. `aetheros_computer` covers cmd/PowerShell via approval
gates. Job-object process-tree guarantees: MISSING (documented limitation).

## 11. Filesystem — COMPLETE

`%LOCALAPPDATA%`-anchored home; fs helpers cap reads (16MB data-URL,
64MB preview); sensitive extensions (`.kdbx/.p12/.pem/.pfx`) flagged;
symlink/junction-aware IPC resolution (tested); no `C:\Users\...` hardcodes
found in audited helpers.

## 12. Storage — COMPLETE (existing, Master 61)

Unchanged.

## 13. Secrets — PARTIAL

`encryptDesktopSecret` uses `safeStorage` (DPAPI on Windows) and THROWS when
encryption is unavailable (fail closed — verified in `hardening.cjs`).
Secret classes live in backend vault; renderer never holds raw secrets by
design. Windows Hello/passkeys: MISSING (not implemented).

## 14. Installer — PARTIAL

electron-builder targets: NSIS (per-machine! `perMachine: true`),
MSI, portable — x64. Config keeps user data on uninstall
(`deleteAppDataOnUninstall: false`). No installer artifact was produced in
this environment (BLOCKED — ENVIRONMENT: needs `electron-builder` run +
signing creds). `perMachine: true` conflicts with least-elevation guidance —
recorded as P1 follow-up (per-user recommended).

## 15. Updater — MISSING

No `electron-updater` integration. Updates = passive git-remote check
(`update-remote.cjs`, unit-tested, FIDO2-prompt-safe) + NSIS
`differentialPackage`. No signed-metadata channel, no rollback. Do not
represent in-product "updates" beyond what exists.

## 16. Crash recovery — PARTIAL

Backend task checkpoints/undo exist (Master 61/64 backend); Electron
`crashReporter` absent; renderer-crash task reconciliation: UNVERIFIED.

## 17. Windows integration — PARTIAL

Present: AppUserModel-aware `Notification` IPC, protocol registration,
file associations (`.aetheros/.aethskill/.aethcfg`), power resume hooks.
Missing: tray, login-item setting, jump lists, share contract.

## 18. Accessibility — PARTIAL

Renderer a11y from Master 9 (focus trap, ARIA, reduced motion,
forced-colors). Native UIA tree for computer-use: MISSING
(`platform_caps.py`: Windows = `ocr_fallback`, SendInput only).

## 19. Computer-use — PARTIAL

`aetheros_computer/` full pipeline (perception/approval/side-effects/
idempotency/supervision) with Win32 SendInput backend; semantic targeting
falls back to OCR (no UIA). Safe on paper; live desktop driving:
UNVERIFIED here.

## 20. Browser automation — COMPLETE (existing)

Playwright/CDP backend unchanged; profiles isolated per task/agent by
design.

## 21. Notifications — COMPLETE

Typed IPC, `isSupported` guard, no secrets policy documented. Toast action
buttons: MISSING.

## 22. Background execution — MISSING

No login-item/background mode; closing the app ends the runtime. No hidden
persistence (good); scheduled work relies on backend cron while running.

## 23. Startup — PARTIAL

`openAtLogin` absent (see §22). First-launch setup exists in renderer
onboarding. Clean-machine first launch: BLOCKED — CLEAN VM.

## 24. Security — PARTIAL

Strong defaults (sandbox, no node integration, safeStorage fail-closed,
capped file IPC, no wildcard IPC found). Gaps: no code signing executed,
no SmartScreen reputation, localhost service auth out of scope for this
doc (see backend Masters 60–62), update channel unsigned.

## 25. Observability — PARTIAL

Structured logs + diagnostics surfaces exist in backend; Windows Event Log
integration: MISSING (optional). Renderer diagnostics center: present.

## 26. Performance — UNVERIFIED

No benchmarks executed here (per no-cheating rule). Desktop unit tests run
in ~0.2s total. See PERFORMANCE doc for policy + how to measure.

## 27. CI — PARTIAL

`desktop-release.yml` builds Windows NSIS/MSI/portable on
`windows-latest` + SHA256 + release upload. No signing step, no E2E
Windows job, no clean-VM test. CI results: UNVERIFIED (not run here).

## 28. Release — PARTIAL

Artifact naming, GUID, license, shortcuts configured. Provenance/SBOM,
signing, Store: MISSING/BLOCKED.

## 29. Existing tests — COMPLETE (executed)

`node --test` on 8 electron unit files: **110 passed, 0 failed**
(session-windows, workspace-cwd, port-pool, desktop-uninstall,
hardening, windows-child-process, connection-config, bootstrap-platform).
Python: 242 passed (agent_network + operating layer + orchestrator +
automation). Web typecheck clean.

## 30. Existing failures — none in executed scope

Full `vite build` blocked pre-existing (partial `node_modules`, private
`@aetheros/ui` 404 on public registry). `npm run typecheck` passes.

## 31. Missing capabilities

Tray, login/background mode, electron-updater channel + rollback, UIA
tree, toast actions, Event Log, Windows Hello, MSIX/Store, signing
pipeline execution, clean-VM validation.

## 32. Technical debt

No `platform/windows/` abstraction (logic scattered); NSIS per-machine
default; update story is git-check + differential package without
integrity metadata; `agent`/`agents` CLI naming overlap (pre-existing,
untracked by this phase).

## 33. Blockers

- Signing credentials: BLOCKED — SIGNING CREDENTIALS
- Packaged installer/E2E/clean-VM: BLOCKED — ENVIRONMENT (no Electron
  binary, no VM, no cert)
- Store submission: BLOCKED — STORE ACCOUNT / CERTIFICATION ENVIRONMENT
- Benchmarks on hardware: BLOCKED — ENVIRONMENT (not executed; no values
  claimed)
