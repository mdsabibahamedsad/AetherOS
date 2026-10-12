# Agent Identity (Master 46 §5)

`AgentIdentity` (`aetheros_network/identity.py`) is the stable,
auditable principal for every remote agent:

`agent_id` (`aetheros:<org>:<12hex>`), `canonical_name`,
`display_name`, `instance_id`, `organization_id`, `owner`, `issuer`,
`public_keys` (fingerprints, `sha256:<hex>` of DER), `endpoints`,
`protocols` (e.g. `A2A/1.0`), `created_at`, `expires_at` (`0` = none),
`status`, `trust_level`, `revocation_status`.

Rules:

- Hostname, IP, URL, and display name are **endpoints/descriptions**,
  never identity. Two records may share a display name (spoof-tested);
  they never share an `agent_id` + key binding.
- Keys are Ed25519 via `cryptography` (stdlib never invents crypto).
  `sign_bytes` / `verify_signature` cover card/artifact provenance where
  publishers sign.
- `effective_status` folds revocation + expiry: `revoked > expired >
  status`. Expired or revoked identities fail verification and
  authorization.
- `audit_key()` (`agent_id` + key suffix) is the log correlation key.

Pairing flow: DISCOVER → IDENTIFY → VERIFY → DISPLAY → USER/ORG
APPROVAL → PAIR → AUTHORIZE → CONNECT. Pairing state persists in
`registry.json` + `trust.json`. Key rotation/expiration/revocation is
supported; `revoked` is terminal and requires fresh pairing.
Removal marks `REMOVED` and preserves history.
