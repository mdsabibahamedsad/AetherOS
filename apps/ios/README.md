# AetherOS iOS App

Native SwiftUI companion client for the AetherOS agent backend. It talks to
the SAME shared backend contract as every other platform — see
`docs/AETHEROS_CROSS_PLATFORM_API.md` (gateway `api_server` REST/SSE,
`gateway/platforms/api_server.py`).

## Honest status (read this)

| Claim | Status |
|---|---|
| Source + XCTest suite present in-repo | YES |
| Compiles / tests pass | **NOT VERIFIED** — requires macOS + Xcode 15.4+; this repo was authored on Windows |
| Simulator/device tested | **NO** |
| Signed/TestFlight/App Store ready | **NO** — placeholders only, see `Config.xcconfig` |

Nothing above may be upgraded to "ready" without executable evidence
(Xcode build logs, simulator screenshots, signed archive). This follows the
repo-wide rule: no production-readiness claims without evidence.

## What it is

A mobile **control plane**, not a second agent:

- connect to your own `api_server` instance (URL + bearer token)
- submit tasks (`POST /v1/runs`, idempotent + offline-queued)
- monitor runs and stream events (SSE)
- resolve approval requests through the backend policy engine
  (`once | session | always | deny`) — the app can never widen permissions
- honest connection states: `connected / connecting / offline / reconnecting / failed`
- typed error taxonomy (`authentication / authorization / network / timeout /
  server / validation / confirmation-required / unsupported-capability`) with
  safe user-facing messages — no stack traces, no secret leakage

### Screens

| Screen | Source of truth |
|---|---|
| Launch | system launch screen (`UILaunchScreen` in project.yml) |
| Authentication | `AuthGateView` — first-run server URL + Keychain token |
| Home + Agent status | `HomeView` — `/v1/capabilities` + `/health`, device capability model |
| Tasks | `RunsView` — `POST /v1/runs`, run list |
| Task details | `RunDetailView` — status, stop, approvals |
| Plan preview | `PlanPreviewView` — steps streamed from `GET /v1/runs/{id}/events`; never fabricated client-side |
| Approval / confirmation | `ConfirmationCard` — action, risk, target, scope, side effects; explicit user choice required |
| Activity / history | `ActivityView` + transcript — `GET /api/sessions[/{id}/messages]` |
| Settings | `SettingsView` |
| Connection status | `ConnectionStatusRow` / banner — five real states |

## What it deliberately does NOT do

No shell execution, host filesystem access, screen capture, window/input
control, or direct browser automation on-device. Those are desktop
capabilities; iOS reaches them only as backend-mediated requests that are
authorized server-side.

## Build & test (macOS required)

```bash
brew install xcodegen
cd apps/ios
xcodegen generate          # creates AetherOS.xcodeproj from project.yml
open AetherOS.xcodeproj    # select the AetherOS scheme
# Cmd+U  → unit tests (no network, no Keychain needed)
```

CLI:

```bash
xcodebuild -project AetherOS.xcodeproj -scheme AetherOS \
  -destination 'platform=iOS Simulator,name=iPhone 15' test
```

## Layout

```
project.yml                  XcodeGen spec (app target + unit-test target)
Config.xcconfig              signing placeholders — NEVER commit real values
AetherOS/Sources/
  App/                       @main entry, AppState (observable container)
  Models/                    wire models (tolerant Codable), capability levels
  Networking/                APIClient (+SSE), idempotency keys, offline queue
  Auth/                      Keychain-only token store
  DeepLink/                  validated aetheros:// parser
  Views/                     Home, Tasks, Plan preview, Approvals (confirmation
                              card), Activity/history, Auth gate, Settings,
                              connection status surfaces
AetherOSTests/               pure-logic XCTests (deep links, queue, API shapes)
```

## Security notes

- Tokens live only in the iOS Keychain (`kSecAttrAccessibleWhenUnlocked`);
  never UserDefaults/logs/notifications.
- Plain HTTP is refused except loopback (local testing).
- Deep links validate host allowlist + ID charset/length; a link can open a
  confirmation screen but can never itself approve anything.
- Notification permission is requested only when the user enables alerts;
  payloads carry event kinds and IDs only.
