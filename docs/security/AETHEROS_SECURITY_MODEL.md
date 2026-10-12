# AetherOS Security / Trust / Policy / Delegation / Data / Audit Models

## Security model
Deny-by-default. Every privileged action passes the §11 pipeline.
Private keys never enter prompts/logs/telemetry. Secrets are referenced
by finding spans, never logged. Emergency stop is authoritative state,
not model cooperation.

## Trust model
10 dimensions (identity, transport, organization, capability, behavior,
provenance, data_handling, execution, history, policy), each 0..1;
outcome from weighted floor + policy floors: ALLOW / ALLOW_WITH_LIMITS /
REQUIRE_APPROVAL / QUARANTINE / DENY, always with reasons. T0–T5 earned
via evidence; thresholds admin-customizable.

## Policy model
YAML allow/deny/requireApproval over capability/resource/tenant/trust
floor/risk ceiling. Precedence deny > approval > allow. Versioned,
hot-reloadable; history preserved, rollback supported.

## Delegation model
Child ⊆ parent enforced on scopes. Short-lived Ed25519-signed tokens
with audience/task/nonce/tenant binding; anti-replay, anti-confusion.
Authority expiry → PAUSE/REAUTHORIZE/CANCEL per policy.

## Data boundary model
PUBLIC → INTERNAL → CONFIDENTIAL → SENSITIVE → SECRET → RESTRICTED.
Flows evaluated source → transformation → destination: ALLOW / MASK /
REDACT / BLOCK / REQUIRE_APPROVAL. Capability-bound secret handles
preferred over raw secrets (execution layer resolves at final boundary).

## Audit model
Append-only JSONL with prev_hash → hash chaining + verifier. Threat
model documented: chaining detects tampering of retained records; it
does NOT prevent deletion by a storage administrator. No claim of
cryptographic immutability.

## Threat model (per threat: attack → mitigation → residual → test)
malicious model → pipeline ignores model claims → residual: model
finds allowed-but-harmful action → adversarial tests. malicious user →
authn + RBAC/ABAC → residual: credential theft → step-up + sessions.
compromised agent → quarantine + revocation propagation → residual:
pre-compromise actions → forensics. malicious remote agent → card
verify + trust + least-context → residual: behavior drift → monitoring.
malicious MCP → server trust + tool gate + quarantine → residual:
tool-output injection → sanitization envelope. malicious extension →
declared permissions + consent → residual: over-permission → health
check. malicious webpage/document → untrusted-data boundary →
residual: clever paraphrase → pattern + DLP defense in depth. stolen
credential → expiry + rotation + revocation → residual: use before
revocation → short TTLs. compromised device → device trust + step-up
→ residual: trusted-device abuse → budgets. network attacker → TLS +
SSRF guards → residual: DNS rebinding → TTL + re-resolve caution.
insider → RBAC + audit → residual: admin abuse → break-glass audit.
policy admin → versioning + audit → residual: malicious policy → review
+ rollback. supply-chain → provenance + signatures → residual:
compromised signer → key rotation.

## Incident response
Detect (security events) → Contain (quarantine + emergency stop) →
Eradicate (revoke + rotate) → Recover (resume + re-authorize) →
Learn (forensics timeline → policy update). All steps audited.
