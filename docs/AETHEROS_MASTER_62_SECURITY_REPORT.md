# Master 62 — Security Report (2026-09-09)

Harness: `tests/aetheros_platform/test_security.py` (13 tests),
`test_fuzz.py` (4 tests / 870 cases), `test_package_signing.py`
(4 tests), `test_mcp_a2a.py` poison-card test. All pass.

## Adversarial results

| Attack | Expectation | Result |
|---|---|---|
| Privilege escalation (LOW agent → `email.send`) | 403 POLICY/APPROVAL | PASS |
| Scope confusion (mem-only key → agents/tools) | 403 | PASS |
| Tenant escape (cross-org read/list) | 403 / empty list | PASS |
| Malicious manifests (traversal agent, bad tool, SQL skill) | 422 | PASS (fixed: `POST /tools` validated) |
| Malicious tool schema executing via inflated grants | AetherError | PASS (fixed: excess-grant denial) |
| Prompt-injection metadata overriding policy | denied | PASS |
| Webhook forgery (wrong secret) / replay (old ts) | False | PASS |
| Package tamper (bit-flip registry bytes) | refuse install | PASS |
| Package traversal (`../../evil` name) | refuse build | PASS (fixed: strict identity) |
| Zip-slip (`../` arc on install) | refuse install | PASS (fixed: guard) |
| Secrets in logs/audit/redact | absent | PASS |
| Destructive retry (same Idempotency-Key) | same taskId | PASS |
| Skill cycle + missing dep | raise | PASS |
| Sandbox (print ok, network denied, timeout) | labeled `development` | PASS |
| Ed25519 roundtrip / tamper / wrong-key / missing-sig | verify/raise | PASS (fixed: stub → real verify) |
| Poisoned Agent Card auto-trust | never trusted | PASS |
| Fuzz 600 schema + 120 gateway + 100 tool-arg + 150 card/A2A cases | typed 4xx only, no traceback, no `aek_` echo | PASS |

## Failure policy (§104 gates)

No gate trips: no auth/authz bypass, no tenant escape, no secret leak,
no policy bypass (metadata never overrides), no blind signature trust,
no privilege laundering, no unbounded resources (rate + concurrency +
deadlines enforced). Destructive retries are idempotent where required.
Sandbox escape: N/A — production sandbox does not exist (dev-only
label enforced); untrusted code must not run outside `DevSandbox`.

## Residual risks

- OAuth/OIDC/mTLS absent: key theft = full scope compromise. Mitigate
  with short expiries, narrow scopes, rotation; tracked as NOT_IMPLEMENTED.
- Local registry is unsigned: `signature: none-available` disclosed;
  remote publishing must add provenance/signature enforcement first.
- `aetheros_developer_platform/` legacy mocks must never be mistaken for
  the production path (documented in audit §4).
