# AetherOS Platform Architecture

Status: living document (Master Prompt 31). Facts below are grounded in the
repository as of this writing; anything NOT yet implemented is explicitly
marked `PLANNED` / `UNSUPPORTED`. Do not remove those markers until real,
executable evidence replaces them.

---

## 1. Product Model

ONE AetherOS product family sharing a single agent core and backend protocol,
with platform-appropriate UI, security, and distribution:

```
                     AETHEROS
                        |
        +---------------+----------------+
        |               |                |
   Windows/macOS    Linux Desktop    iOS App
     Desktop         (Electron)      (SwiftUI)
        |               |                |
        +---------------+----------------+
                        |
                  Shared Backend
       (agent core, gateway api_server REST,
            tui_gateway JSON-RPC, MCP, memory)
                        |
        Security / Policy / Confirmation
        (enforced server-side & in agent core,
             never in the client alone)
```

Principles:

1. The agent core (`run_agent.py`, `model_tools.py`, `tools/`) is shared and
   is never forked per platform.
2. Business logic lives in the backend/agent, not in any client UI.
3. UI and OS integration are platform-specific by design.
4. Clients are never the sole security boundary; authorization is enforced
   server-side.

---

## 2. CURRENT — Windows / macOS / Linux Desktop (canonical reference)

Location: `apps/desktop/` (Electron 40, React 19 renderer, Vite, TypeScript).

| Layer | Files | Notes |
|---|---|---|
| Electron main | `apps/desktop/electron/main.cjs` | Window/session management, backend lifecycle, deep links, updates |
| Preload bridge | `apps/desktop/electron/preload.cjs` | Context-isolated IPC surface |
| Hardening | `electron/hardening.cjs` (+ test) | CSP, navigation/permission guards, webSecurity enforcement |
| Platform quirks | `electron/bootstrap-platform.cjs` (+ test) | WSL detection, remote-display/GPU fallback, bundled-runtime import check |
| Backend bundling | `scripts/bundle-python.cjs`, `build/bundled-python/` | Ships Python runtime + backend into the package |
| Renderer | `apps/desktop/src/` (`app`, `components`, `hooks`, `i18n`, `lib`, `store`, `themes`) | React chat surface over `@aetheros/shared` JSON-RPC client |
| Shared TS types/client | `apps/shared/src/json-rpc-gateway.ts` | Typed JSON-RPC framing used by desktop/TUI-family surfaces |
| Packaging | `package.json` → `"build"` (electron-builder 26) | NSIS/MSI/portable (win), DMG/ZIP/PKG (mac), **AppImage/deb/rpm (linux)** |
| Release pipeline | `.github/workflows/desktop-release.yml` | TEST → BUILD → PACKAGE → SIGN(secret-gated) → HASH → SBOM → ATTEST → VERIFY → PUBLISH on native runners |

### Desktop user-data rules

- Electron-standard per-OS data dirs via `app.getPath('userData')`
  (`main.cjs:109`); connection/update/profile configs live there
  (`connection.json`, `updates.json`, `active-profile.json`).
- Agent state follows `AETHEROS_HOME` (`~/.aetheros` or profile dir);
  `main.cjs` resolves it relative to `app.getPath('home')` — never a
  Windows-only path.
- Uninstall preserves user data (`nsis.deleteAppDataOnUninstall: false`;
  `electron/desktop-uninstall.test.cjs` covers this contract).

### Deep links

- `aetheros://` scheme registered for Win/mac/Linux
  (`main.cjs:5917-5921`, plus electron-builder `protocols`).
- Delivery paths: macOS `open-url`; Win/Linux running instance via
  `second-instance` argv; Win/Linux cold start via argv.
- Malformed URLs are ignored and logged (`main.cjs:5869`). The renderer must
  opt in via `aetheros:deep-link-ready` before payloads are delivered.
- Single-instance lock guarantees one delivery target.

### Baseline (measured, this repository)

| Gate | Result |
|---|---|
| Renderer tests (`npm run test:ui`, vitest) | 688/688 pass |
| Electron unit tests (`node --test electron/*.test.cjs`) | 161/161 pass |
| Python security suite (`scripts/run_tests.sh tests/security`) | 351/351 pass |
| Typecheck (`npm run typecheck`) | clean |
| Lint (`npm run lint`) | 0 errors (warnings allowed) |
| Entry JS (`dist/assets/index-*.js`, last build) | ≈3.22 MB (budget ≤5 MB) |

---

## 3. CURRENT — Shared Backend (the narrow waist)

Two existing, tested transport layers. New platform clients MUST reuse them;
no new backend may be created.

### 3.1 HTTP/REST — gateway `api_server` platform

`gateway/platforms/api_server.py` (aiohttp, bearer-token auth via
`API_SERVER_KEY`, HMAC constant-time compare). Versioned surface already in
place:

- `/v1/*`: `health`, `models`, `capabilities`, `skills`, `toolsets`,
  `chat/completions`, `responses` (+GET/DELETE), `runs`
  (+`events`, `approval`, `stop`)
- `/api/*`: sessions CRUD + fork/chat/chat-stream, jobs CRUD +
  pause/resume/run
- Security middleware: body limit, security headers, CORS allowlist,
  request audit logging, replay-resistant request coalescing.

This is THE contract for iOS and any remote client. Full detail:
`docs/AETHEROS_CROSS_PLATFORM_API.md`.

### 3.2 Local JSON-RPC — `tui_gateway/server.py`

Newline-delimited JSON-RPC over stdio used by the Ink TUI (and available to
embedded surfaces): `session.*` (~20 methods), `prompt.submit`,
`tool.start/progress/complete`, `approval.request/respond`,
`slash.exec`/`command.dispatch`, `complete.*`, skin/theme bootstrap. This is
a same-machine transport; it is NOT exposed to network clients and MUST NOT
be used by iOS directly.

### 3.3 MCP layer

MCP servers/skills are reachable through the agent core's MCP client
regardless of which platform frontend originated the conversation. Mobile
clients reach MCP only through backend-mediated endpoints (runs/tools), never
directly.

---

## 4. CURRENT — Linux Desktop specifics

Packaging targets are already declared and CI-built on `ubuntu-latest`
(`desktop-release.yml` matrix: AppImage, deb, rpm; x64).

Known platform behavior already in-tree:

- WSL detection + Windows-binary-in-WSL guard (`bootstrap-platform.cjs`).
- Remote-display GPU fallback incl. X11-forwarding detection
  (`detectRemoteDisplay`, `bootstrap-platform.cjs`).
- Fontconfig user config handling (`main.cjs:781`).
- Linux artifact naming `AetherOS-${version}-linux-${arch}.${ext}`.

Added by Master Prompt 31:

- `apps/desktop/electron/linux-session.cjs` — pure, unit-tested session-type
  detection (X11 / Wayland / tty / SSH-forwarded) and an explicit capability
  table so unsupported features return structured errors instead of silently
  misbehaving. See §6.

WAYLAND status: **LIMITED**. Screen capture / global input synthesis depend on
X11 APIs or portal services that vary by compositor. Until portal-based paths
are validated on real compositors (GNOME/KDE/wlroots), capabilities that need
them report `unsupported-under-wayland` structured errors. We do not claim
Wayland parity we have not executed.

Distribution claims: packages build in CI (evidence: workflow), install/
launch/update/uninstall/reinstall verification requires execution on real
distros — see `docs/AETHEROS_LINUX_RELEASE.md` certification checklist.
Linux is **NOT certified production-ready** until that evidence exists.

---

## 5. PLANNED — iOS native app

Location (this expansion): `apps/ios/` — Swift/SwiftUI, Xcode-compatible
project generated from `project.yml` (XcodeGen spec), XCTest target included.

Role: secure mobile companion/control plane — authentication, task/job
creation + monitoring, plan review, confirmations, notifications,
conversation with the SAME agent through `api_server` REST. It is a CLIENT.
No shell, filesystem, browser automation, screen capture, or window control
is implemented or implied on-device; all privileged execution happens on the
user's own machine/backend and requires server-side authorization + the
existing confirmation policy.

Honest status: source + tests exist; **nothing about iOS is production-ready
until built and exercised in Xcode on simulator/device with real Apple
signing**. See `docs/AETHEROS_IOS_RELEASE.md`.

Explicitly NOT exposed to iOS:

- arbitrary shell execution (desktop `terminal` tool)
- unrestricted host filesystem access (desktop `file` tools)
- desktop window management / screen capture / input automation
  (computer-use tools)
- direct browser automation (desktop browser tools)
- local stdio MCP servers (backend mediates instead)

---

## 6. Capability boundary model

Every cross-platform feature resolves to one of:

| Level | Meaning | Client behavior |
|---|---|---|
| `native` | Fully supported on this platform | Use it |
| `backend-mediated` | Executed by the agent/backend on the host machine; client only submits/observes | REST calls; show host context |
| `limited` | Works under some conditions (e.g. X11 only) | Degrade gracefully; label limits |
| `unsupported` | Not available | Structured error; UI hides/disables; never fake success |

The Linux module implements this table in code
(`electron/linux-session.cjs`); the API doc defines it on the wire
(`capabilities` endpoint + typed error codes); the iOS app models it as
`CapabilityLevel` and renders accordingly.

Structured error shape (wire):

```json
{
  "error": {
    "code": "capability_unavailable",
    "message": "screen capture is unavailable under Wayland",
    "details": { "capability": "computer_use.capture", "reason": "wayland", "platform": "linux" }
  }
}
```

---

## 7. What each platform owns

| Concern | Desktop (Win/mac/Linux) | iOS |
|---|---|---|
| Chat/conversation | Embedded full session (local JSON-RPC) | REST sessions + SSE stream |
| Terminal/computer/browser | Native, local execution | Remote-control requests ONLY (backend-mediated), gated server-side |
| Filesystem | Local file tools | None directly; backend-mediated artifacts only |
| Confirmation UX | Native dialog flow | Native push + in-app approval; policy still enforced server-side |
| Secrets | OS keychain / .env of the agent host | iOS Keychain only; never desktop credential stores |
| Notifications | OS notifications | APNs (token-free payloads; content-safe only) |
| Updates | electron-builder + update feed | App Store/TestFlight mechanics |
| Telemetry | none without opt-in | none without opt-in (same policy gate) |
