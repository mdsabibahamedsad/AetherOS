# AetherOS iOS Architecture / Security / Privacy

Layers: SwiftUI Presentation → ViewModel/State (AppState machine) →
Services → APIClient (bearer + idempotency keys, 30s timeout, no
logging) → gateway api_server. KeychainTokenStore for tokens (most
restrictive accessibility); no secrets in UserDefaults/files/logs.
Deep links (`aetheros://task|approval|session|notification/<id>`)
navigate-only: 128-char allowlisted IDs, never approve, never carry
tokens. Push: minimal-preview payloads (forbidden keys enforced in
contract tests); fetch content post-auth; actions re-authorize
server-side. Offline: classified queue (SAFE/QUEUEABLE/ONLINE/
HIGH_RISK), expiry enforced, idempotency keys prevent duplicates.
Biometrics/Hello-style step-up: designed, UNVERIFIED (no device).
Missing for production: entitlements file, PrivacyInfo.xcprivacy,
APNs capability, iPad target (family=1 iPhone-only, portrait-only),
TestFlight/App Store artifacts. Privacy: transcripts/research/voice/
camera stay server-side or user-invoked; no tracking; diagnostics
redacted.
