# AetherOS Control Plane — Architecture (§101)

The Universal Agent Operating Fabric (`aetheros_control_plane/`) is the
central trust, governance, policy, identity, delegation, authorization,
execution-control, audit, and safety plane. It is a **facade + gap-fill**,
not a rewrite: it adapts existing `aetheros_security/*` modules (authz,
policy, tokens, dlp, kill_switch, approval, audit, network, sandbox)
per the migration strategy (§104 legacy path → adapter → control-plane
path) and implements what did not exist (T0–T5 trust, Ed25519 identity
keys, scope algebra, delegation tokens, manifests/receipts, provenance
graph, context firewall).

```
UI / CLI (`aetheros governance …`)
  → UniversalControlPlane.check(manifest)      # §11 pipeline, no shortcut
      identity → risk → trust → policy → scopes → delegation
      → network → DLP → approval → execute → receipt → provenance → audit
  → ExecutionGate                              # reusable primitive (§30)
  → agents / MCP / A2A                         # gated, never direct
```

Key files: `models.py` (types), `crypto_keys.py` (Ed25519),
`identity_plane.py`, `trust_engine.py`, `scopes.py`,
`policy_risk.py`, `delegation.py`, `approvals_sessions.py`,
`data_network.py`, `provenance_audit.py`, `emergency.py`,
`execution_gate.py`, `agent_cards.py`, `control_plane.py`, `cli.py`.
CLI bridge: `aetheros_cli/governance_cmd.py`.

## Honest status words (§103)

Implemented | Partially implemented | Protected by X |
Not protected against Y | Requires external infrastructure |
Not yet certified. No "secure / zero trust / production-ready" claims.
