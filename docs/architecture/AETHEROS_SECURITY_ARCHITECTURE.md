# AetherOS Security Architecture

Source: `kernel/core/security_boundary.py`, `kernel/core/policy_engine.py`,
`kernel/core/governance_engine.py`, `kernel/core/audit_engine.py`,
`kernel/core/provenance_engine.py`, `kernel/core/human_oversight_manager.py`.

## Trust Boundary (§59)

```
UNTRUSTED
──────────────
LLM outputs, agent plans, web content, tool results, external agents,
sensor input, OCR, user files, ambient audio, remote nodes

TRUSTED
──────────────
Kernel policy, identity verification, authority evaluator,
capability broker, audit engine, security boundary, resource manager
```

The model is never the ultimate security authority.

## Threat Model (§58)

| Threat | Control | Test |
|---|---|---|
| Prompt injection | SecurityBoundary patterns + provenance gate | 5 payloads + tool-input test |
| Tool poisoning | Grant check + verification | ungranted tool denied |
| Memory poisoning | Scope isolation + provenance | cross-scope read denied |
| Agent impersonation | Identity verification + grant binding | revoked identity denied |
| Capability escalation | Authority subset + grant check | escalation denied |
| Authority confusion | Delegation subset + policy rule | child>parent denied |
| Credential theft | Grant credential gate, vault-only | missing-cred denied |
| Data exfiltration | IFC + network rules | secret→public denied |
| Malicious MCP | Untrusted provider, grant-mediated | denied without grant |
| Malicious A2A | Trust levels, contracts, budgets | direct privileged invoke denied |
| Supply-chain | Extension manifest/signature gates | unsigned quarantine |
| Model compromise | Verification + provenance | unverified quarantined |
| Browser compromise | Per-capsule isolation, redaction | screen data contained |
| Remote node compromise | Pairing, attestation, trust | unauthenticated pairing denied |
| Sensor/device spoof | Pairing, attestation, trust | unauthenticated pairing denied |
| Network interception | TLS, pinning | enforced |
| DNS rebinding | Resolution-time validation + pin | blocked |
| SSRF | Allow/deny lists, IP policy | blocked |
| Race/TOCTOU | Grant validity + idempotency | expired approval denied |
| Replay attacks | Receipt chain + nonces | expired grant denied |
| Delegation abuse | Subset + depth + cascade revoke | enforced |
| Swarm collusion | Per-agent scopes/quotas | enforced |
| Automation recursion | Depth + budget + policy re-eval | enforced |
| Resource exhaustion | Admission denial with cause | enforced |

## Fail-Closed (§32)

| Uncertainty | Verdict |
|---|---|
| Authorization uncertain | DENY |
| Identity uncertain | DENY |
| Capability uncertain | DENY |
| Provenance invalid | QUARANTINE |
| Resource state unknown | PAUSE |
| External side effect uncertain | VERIFY |
| Security boundary uncertain | STOP |

Never use "probably safe" as authorization.

## Controls

- Deterministic `PolicyDecision` (ALLOW/DENY/REQUIRE_APPROVAL/QUARANTINE/LIMIT/ESCALATE)
- `SecurityBoundary.check_invocation()` (7-stage pipeline)
- `HumanOversightManager` (approval.request/grant/deny/expire/delegate/remember)
- `SecurityBoundary.activate_emergency_stop()` (independent of LLM)
- `ProvenanceEngine` (hash-chained lineage)
- `AuditEngine` (hash-chained log)
- `SecretBroker` (capability-mediated, no plaintext in env)
- `NetworkManager` (allow/deny lists, SSRF/DNS-rebinding defense)

## Data Classification (§29)

```
PUBLIC < INTERNAL < PRIVATE < CONFIDENTIAL < SECRET < HIGHLY_SENSITIVE
```

Flow: `SECRET/HIGHLY_SENSITIVE` → `PUBLIC/INTERNAL/UNVERIFIED` = DENY.
Redaction hooks for screen data (passwords, cards, keys).

## Secrets (§30-32)

`SecretBroker` — capability-mediated, no plaintext in agent env.
Bindings scoped to agent/capsule/task/capability/destination/time.
`use_secret` returns fingerprint; `with_resolved` exposes plaintext
only to provider callback. Rotation, revocation, TTL GC, audit.

## Emergency Stop (§31)

`SecurityBoundary.activate_emergency_stop(scope="global")` —
independent of LLM; pauses all RUNNING/WAITING/READY/PAUSED agents;
denies all invocations. Cannot be overridden by agent output.

## Audit

`AuditEngine` — hash-chained log (`AuditEntry` with `previous_hash`,
`entry_hash`, `sequence_number`). `verify_chain()` validates integrity.
Retention configurable; immutable once written.