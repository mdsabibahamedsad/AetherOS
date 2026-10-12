# AetherOS Trust Fabric 1.0 — Architecture (§240)

## Rule

MODEL proposes. Trusted runtime decides. System enforces. Reality verifies.

```
IDENTITY -> AUTHORITY -> POLICY -> RISK -> APPROVAL -> CAPABILITY
  -> ACTION -> VERIFICATION -> PROVENANCE -> AUDIT -> LEARNING
  -> GOVERNANCE UPDATE
```

## Layers

- **Master 50 (`aetheros_control_plane/`)**: identity plane, Ed25519
  keys, delegation engine, trust engine (T0-T5, 10 dimensions),
  policy registry/evaluator, approvals/sessions/JIT, audit hash-chain,
  network policy + SSRF guards, DLP, emergency stop, execution gate.
- **Master 55 (`trust/`)**: R0-R8 risk + escalation, extended policy
  decisions + versioned/canary/regression/replay, path governance,
  signed capability tokens, quorum approvals + self-approval ban,
  revocation propagation, layered kill machine, incidents +
  containment, signed receipts, secret/data/network boundaries,
  ActionFirewall orchestration, advisory trust scores + privilege
  graph, tool contracts, health/doctor, compliance packs, benchmarks.
- **`aetheros_security/`**: tool-authz service, sandbox, secrets,
  kill-switch registry, DLP/scanners — adapted, not duplicated.

## Trust boundaries

Model (untrusted proposer) | tool runtime (validates tokens
independently) | Trust Fabric (decides) | renderer/CLI (requests
only, never decides) | audit backend (append-only, hash-chained).
No `is_admin: skip_checks()` paths (§149). Development mode is
explicit and visible (§150); test fixtures are synthetic (§151).

## Fail-closed matrix (§40)

policy engine down -> deny high-risk; identity down -> deny
privileged; audit down -> deny mandatory-audit actions; approval
service down -> deny gated actions. Offline: cached authority +
expiry honored; network loss never upgrades permissions (§41).
