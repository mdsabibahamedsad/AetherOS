# AETHEROS Master 67 — iOS Audit

Host is Windows: Xcode/simulator/device/TestFlight/App Store claims are
BLOCKED unless source-verified. Nothing fabricated.

## Implementation (source-verified)

XcodeGen app (`apps/ios`, bundle `com.aetheros.mobile`, iOS 17+,
Swift 5.10): AppState/ConnectionState, KeychainTokenStore, DeepLink
(validated per shared rules), MobileCapability, APIClient (bearer +
`X-Aetheros-Request-Id` idempotency), APIError, OfflineQueue, SSE plan
preview, 6 SwiftUI views (AuthGate/Home/PlanPreview/Root/Runs/
Settings). Swift tests: APIClient, APIError, AppState, DeepLink,
OfflineQueue (exist; NOT runnable here — no Xcode).

## Architecture

Thin client over `gateway/platforms/api_server.py`: uses GET
/api/sessions, GET .../messages, POST .../chat[/stream], GET /api/jobs
— all four handlers verified present (`_handle_list_sessions`,
`_handle_session_messages`, `_handle_session_chat`,
`_handle_session_chat_stream`, `_handle_list_jobs`) + server-side
`_IdempotencyCache` matching the client's idempotency header.

## Gaps found (this phase)

- TARGETED_DEVICE_FAMILY = 1 (iPhone only) → iPad multitasking NOT
  READY (P1: enable + test).
- Portrait-only orientations → iPad landscape NOT READY.
- No `.entitlements` file, no `PrivacyInfo.xcprivacy`, no APNs
  capability → push/physical/security validation BLOCKED.
- No CI iOS job → added `ios-platform.yml` (contract tests; Xcode
  steps documented, UNVERIFIED).
- Camera/mic/speech: no usage strings (correct — unused), no code.

## Contract additions (tested here)

`aetheros_platform/mobile_contract.py`: canonical route table +
`verify_against_backend()` (imports api_server, asserts handlers),
deep-link rules mirroring Swift, push minimal-preview rules, offline
classification, device trust states.

## Security posture

Bearer tokens, Keychain storage design, no secrets in code (sweep),
deep links navigate-only (never approve/carry tokens), notification
payloads minimal-preview. Live audit: BLOCKED (device/simulator).
