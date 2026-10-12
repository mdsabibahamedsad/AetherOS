# AetherOS Web Security / Auth / ASVS-5 Mapping (Master 69)

Verified in code: explicit-origin CORS (both servers, no wildcard),
loopback session-token gate, bearer API auth, idempotency keys,
SSRF private-net block + redirect re-validation (documented
DNS-rebinding limit), canonical error model with leak-guard,
security-headers + config-validator contracts (wiring follow-up).

ASVS 5.0.0 (honest): V2 auth IMPLEMENTED (session/bearer, rotation
designed); V3 session PARTIAL; V4 access control IMPLEMENTED
(tenant/policy server-side); V5 validation PARTIAL (contracts tested,
fuzzing absent); V6 crypto NOT AUDITED here; V7 errors IMPLEMENTED
(leak-guard tested); V8 data protection PARTIAL; V9 comms PARTIAL
(TLS/deployment BLOCKED); V10 malicious code PARTIAL (upload/content
rules documented); V11 business logic PARTIAL; V12 files PARTIAL;
V13 API PARTIAL (versioning/deprecation policy documented, not
enforced); V14 config IMPLEMENTED (validator tested). Pen-test: NOT
RUN. Passkeys/WebAuthn: NOT IMPLEMENTED (no fake flow).
