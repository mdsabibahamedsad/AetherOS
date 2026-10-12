# Marketplace Security

Status: IMPLEMENTED (controls below) / PARTIALLY (AV scanning, formal
injection proofs) / BLOCKED (live-network validation).

## Principles enforced in code

- Untrusted by default; explicit approval moves trust, never discovery.
- Trust ≠ capability ≠ authorization (identity + capability + policy +
  scope + task + risk, every time).
- No LLM in any approval/identity/settlement path (deterministic only).
- Remote content is DATA: injection screens both directions, audited.
- Secrets never cross: DLP ingest refusal, redaction, minimization,
  references/handles only.

## Listing security

Provenance on every listing; `verify_listing()` reconciles marketplace
identity vs live A2A card + network registry (hash/endpoint drift →
re-verify). States: verified/unverified/expired/revoked/unknown.
Scanner reports honest levels (scanned/partially_scanned/not_scanned)
and names what it does NOT cover (redirects, CVEs, malware).

## Network

Reuses `aetheros_network` URL policy (single source): SSRF/DNS-rebinding
guards, scheme allowlist, TLS validation, timeouts, size/connection
limits. No parallel implementation to drift.

## Artifacts & code

Untrusted: hashing, type detection, size limits, quarantine (network),
safe extraction, traversal/bomb defense, provenance. Remote code is
never executed on the host; sandbox execution marked unavailable unless
real isolation exists (it doesn't here — documented, not claimed).

## Economic abuse & recursion

Caps, velocity guards, flood guards, depth/agents/budget/time ceilings,
chain tracking with loop refusal, fallback re-authorization rules.

## Privacy & retention

Minimization, redaction, deletion of non-financial history, export,
per-agent memory provenance. Financial records are append-only; where
provider/org rules require immutable retention this is documented at
restore time (`check_restore_integrity` → safe mode on mismatch).
