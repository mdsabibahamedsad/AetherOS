# Extension Threat Model (Master 44)

T1 malicious extension — impact: code exec/data theft. Mitigation:
untrusted default, scans, capability grants, quarantine. Residual:
in-process Python entrypoints (PARTIAL sandbox). Test: adversarial
fixtures blocked.

T2 compromised publisher — signatures + revocation + per-release
verify. Residual: stolen key valid until revoked. Test: revoked key
rejected.

T3 compromised registry — package digest + signature over digest;
index is discovery only. Residual: availability. Test: tampered file
hash mismatch.

T4 dependency attack — pinned/locked ranges, mismatch fail-closed,
confusion via exact-id registry (no namespace fallback). Test:
missing/mismatch/cycle.

T5 update attack — staged install, validate-before-replace, auto
rollback. Residual: none observed. Test: corrupt update rolls back.

T6/T7 signature theft/stolen key — expiry + revocation + rotation
(new key record). Residual: window before revocation. Test: expired
signature rejected.

T8 prompt injection — content scanned, policy never redefinable,
override phrases blocked. Test: injection fixtures.

T9 MCP tool poisoning — description gate + per-invocation policy.
Test: poisoned description denied.

T10 credential exfiltration — brokered scopes + approval; exfil
patterns BLOCK install. Test: harvest fixture blocked.

T11 filesystem escape — traversal/bomb/jail checks, scoped grants.
Test: traversal package + scope bypass denied.

T12 shell escape — shell.execute R4 + approval; smoke runs jailed,
no-shell. Test: shell fixture WARN-gated, capability denial.

T13 network exfiltration — domain allow-list, call logging, no raw
sockets granted. Test: exfil fixture flagged, off-list host denied.

T14 extension collusion — no direct comms; brokered messages carry
sender/permission (broker planned; direct channel absent by design).

T15 privilege escalation — self-grant denied, least-privilege
intersection. Test: escalation + wildcard-without-approval denied.

T16 malicious UI — controlled React points only; no DOM injection
surface added. Residual: review of future contributors. Test: n/a
(structural).

T17 resource exhaustion — timeouts, output caps, quotas, crash-loop
quarantine path, size/file/bomb limits. Test: timeout + quota + bomb.

T18 downgrade attack — version compare; downgrade installs as a new
staged version through full verification (no silent path). Residual:
policy pinning is org-config. Test: mismatch version rejected via deps.

T19 package tampering — integrity.json + signature digest. Test:
tamper mismatch.

T20 supply-chain compromise — provenance fields, publisher identity,
revocation, quarantine triggers. Test: revoked publisher blocked.
