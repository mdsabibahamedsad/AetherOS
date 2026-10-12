# Marketplace Threat Model

Status: living document. For each threat: attack → mitigation →
detection → recovery → residual risk.

| Threat | Mitigation (implemented) | Detection | Recovery | Residual |
|---|---|---|---|---|
| Malicious agent | deny-by-default, grants, approvals, revocation | audit, incidents | revoke+cancel+quarantine | Medium (operator review) |
| Compromised provider | trust signals, incident penalty, kill switch | anomaly flags | engage kill, disputes | Medium |
| Fake marketplace/registry | provenance, file-registry read-only + unverified | verify_listing | import-review flow | Low |
| Fake reviews / bombing | burst flags, verified weighting, min samples | flags | disregard low-conf | Low |
| Sybil identities | identity binding, tx weighting, org correlation | dominance flags | require verification | Medium |
| Payment fraud / double charge | idempotency, settled-refusal, ledger dedupe | reconcile | void/refund/dispute | Low |
| Replay | idempotency keys everywhere | same-key returns | none needed | Low |
| Prompt injection | bidirectional screens, DATA-only, approvals | audit events | block+reverify | Medium (heuristic) |
| Data exfiltration | DLP, minimization, redaction, scope gates | dlp_blocked audit | revoke, rotate | Medium |
| SSRF / DNS rebinding | network URL policy reuse | blocked-url audit | n/a (prevented) | Low |
| Credential theft | secret boundary, no raw secrets | DLP | rotate, revoke | Low |
| Malicious artifacts | quarantine, hash verify, traversal/bomb checks | verification fail | reject, dispute | Medium (no AV) |
| Supply-chain attack | pinned deps, no new network deps added | provenance | pin+rebuild | Low |
| Agent impersonation | A2A binding, card-hash/endpoint drift | reverify flags | block, re-pair | Low |
| Contract tampering | immutability, versions, ledger chain | chain verify | safe mode, dispute | Low |
| Reputation manipulation | weighted evidence, diversity, decay | flags | verified outcomes | Low |
| DoS / economic DoS | rate limits, budgets, circuit breaker, caps | velocity guards | kill switches | Medium |
| Budget exhaustion | multi-scope caps, velocity, approvals | usage views | dispute/adjust | Low |
| Infinite delegation loops | depth/agents/time ceilings, chain loop refusal | guard reason | cancel root | Low |

P0 release blockers (all gated by tests): payment idempotency,
identity binding, unauthorized data flow, double-spend, cross-tenant
leak. P1: delegation recovery, reputation accounting. P2: benchmark
gaps, UX. P3: polish.
