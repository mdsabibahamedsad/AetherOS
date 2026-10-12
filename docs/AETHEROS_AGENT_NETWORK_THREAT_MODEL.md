# Agent Network Threat Model (Master 46 §148)

For every threat: attack → impact → mitigation → test → residual risk.

| ID | Threat | Mitigation (implemented) | Test | Residual risk |
|---|---|---|---|---|
| T1 | Agent impersonation (name/domain/id collision, cert mismatch, endpoint substitution) | canonical id+key identity; endpoint-consistency warnings; TLS verify | `test_identity_spoof_same_display_name`, card validation tests | MEDIUM — no live CA/pinning deployment tested |
| T2 | Malicious agent | deny-by-default, capability grants, approvals, revocation cascade | adversarial suite, server tests | MEDIUM — depends on operator review |
| T3 | Compromised agent (post-pairing) | revoke → block + cancel + quarantine + audit | `test_compromised_agent_response` | LOW (local); MEDIUM for in-flight remote side effects |
| T4 | Malicious Agent Card | parse/validate, untrusted-data treatment, reverify flags | card + substitution tests | LOW |
| T5 | Credential theft | DLP block, secret isolation, redaction | DLP/adversarial tests | LOW locally; MEDIUM if user pastes secrets into approved tasks |
| T6 | Token replay | short-lived bearer design, hashed comparison, scoped pairing tokens | server auth tests | MEDIUM — rotation/expiry policy is deployment-configured |
| T7 | SSRF (localhost/private/metadata) | resolve-and-check per request, scheme/userinfo blocks | SSRF tests | LOW |
| T8 | DNS rebinding | per-request resolution, no stale-DNS trust | `_check_url` + policy tests | LOW–MEDIUM (no live rebinding rig) |
| T9 | Prompt injection (direct + cross-agent) | DATA-not-authority screens both directions, audit | injection tests | MEDIUM — heuristic patterns, not a formal guarantee |
| T10 | Tool poisoning | card skills never grant powers; catalog enforcement | capability-spoof test | LOW |
| T11 | Artifact malware | quarantine → validate → scan → verify → release; exe/macro/archive-bomb blocks | artifact tests | MEDIUM — no AV engine integration |
| T12 | Data exfiltration | classification + DLP + scope gates + approvals | DLP/delegation tests | MEDIUM — approved flows still move data by design |
| T13 | Privilege escalation | rank-gated catalog, never-grantable set, grant allowlist | authz matrix tests | LOW |
| T14 | Tenant escape | explicit tenant auth, allowlist isolation | cross-tenant test | LOW (single-tenant server scope) |
| T15 | Task duplication | idempotency keys + store lookup before resubmit | duplication test | LOW |
| T16 | Task flooding | bounded queue, token buckets, circuit breaker | flood/rate tests | LOW locally |
| T17 | Resource exhaustion | server caps (tasks, concurrency, sizes), timeouts | cap tests | LOW locally |
| T18 | Federation compromise | federation levels, strict public defaults | router mode tests | MEDIUM — no live federation tested |
| T19 | Publisher compromise | reverify-on-change, revocation, provenance | registry reverify tests | MEDIUM |
| T20 | Key compromise | rotation/expiry/revocation, terminal revoked | identity tests | MEDIUM — rotation UX is manual |
| T21 | Endpoint substitution | host-consistency check, no silent redirects | substitution tests | LOW |
| T22 | Downgrade attack | explicit version reject, no silent downgrade | protocol tests | LOW |
| T23 | Malicious dependency | exact-pinned deps only; **no new dependencies added** (httpx/PyJWT/cryptography already pinned) | n/a (policy) | LOW |
| T24 | Remote automation abuse | inherits autonomy level, cannot elevate; approvals preserved | pipeline tests | MEDIUM — host automation policy is operator-owned |
| T25 | Cross-agent data leakage | scope gates, `highly_sensitive`→`fully_trusted` rule, approvals | router privacy tests | MEDIUM |

**Explicit non-claims:** no production A2A interop against external
implementations (no fixtures available in this environment); no live
LAN/WAN measurements; injection defense is heuristic; OAuth2/OIDC and
mTLS are structurally supported, not deployment-validated.
