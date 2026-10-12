# AetherOS Platform Security Model

One security model, three platforms. Clients render and relay; the backend
and agent core decide. Nothing in this document may be satisfied by
client-side checks alone.

## 1. Invariants (all platforms)

| Invariant | Enforcement point |
|---|---|
| Authentication | `api_server` bearer token (HMAC constant-time compare); desktop local IPC via contextBridge only |
| Authorization | Server-side, per request/run; clients cannot grant themselves scope |
| Confirmation policy | Agent-core approval engine; mobile/desktop approval UIs can only resolve a PENDING request with `once/session/always/deny` — never create or widen permissions |
| Risk classification | Backend-owned, attached to approval payloads |
| Audit logging | `api_server` request audit context (redacted); gateway logs |
| Rate limiting / replay | Body limits, request coalescing/fingerprints; client adds idempotency keys for retryable submissions |
| Tool & network policy | Agent core toolsets + sandbox docs (`docs/PERMISSIONS.md`, `docs/SANDBOX.md`) |
| Data protection | Secrets only in OS keystores (Keychain / keyring / `.env` of the host); never in logs, notifications, or deep links |

## 2. Desktop (Windows/macOS/Linux) — identical controls everywhere

Enforced in `apps/desktop/electron/hardening.cjs` + covered by
`electron/hardening.test.cjs` (runs cross-platform in CI):

- context isolation ON, nodeIntegration OFF, webSecurity ON
- CSP on all surfaces
- navigation guards: no arbitrary remote navigation; external URLs via
  allowlisted shell-open path
- permission handlers deny-by-default
- preload boundary is the ONLY IPC surface (`aetheros:*` channels)
- deep links validated; malformed dropped (`main.cjs` deeplink block)
- single-instance lock prevents duplicate delivery targets

Linux adds no exceptions. The Wayland/X11 capability matrix
(`electron/linux-session.cjs`) returns structured errors instead of
degrading security to gain features.

## 3. iOS

Threat model: malicious client, stolen device, stolen session, replay,
MITM, token theft, API abuse, tampering, privilege escalation.

Controls implemented in `apps/ios/`:

- ATS default (TLS required); plain HTTP refused except loopback
  (`AppState.rebuildClient`)
- tokens in Keychain only, `kSecAttrAccessibleWhenUnlocked`; never logged,
  never in URL/query strings
- server-side authorization assumed for every privileged op; the app holds
  no capability of its own
- deep links: host allowlist (`task|approval|session|notification`), ID
  charset+length caps, navigation-only (cannot approve)
- notifications: permission requested on opt-in only; payloads carry event
  kinds/IDs, never secrets or content
- offline queue: bounded retries, 4xx never retried, honest state rendering
- minimal permission surface: no camera/mic/photos/contacts/location usage
  strings exist because nothing requests them

Known gaps (tracked honestly, do not ship around them):

1. **Short-lived access tokens / refresh rotation** — `api_server` currently
   accepts one operator bearer token; rotation requires backend work.
2. **Device binding** — not implemented anywhere yet.
3. **APNs bridge** — contract fixed, component missing.

## 4. Release security

- Desktop: secret-gated signing in `desktop-release.yml`; unsigned artifacts
  marked UNSIGNED and can never satisfy certification; SHA-256 manifest +
  CycloneDX SBOM + artifact attestation, verified before publish.
- Linux: CI attestation covers packages; repo-level GPG signing NOT claimed.
- iOS: Apple signing/provisioning BLOCKED until real credentials exist;
  placeholders only (`apps/ios/Config.xcconfig`).
- Signing material NEVER lives in source control; CI reads it from secrets.
