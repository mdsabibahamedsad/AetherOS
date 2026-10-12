# AetherOS Kernel Threat Model

Threats (§58) and where each is stopped:

| Threat | Control | Test |
|---|---|---|
| prompt injection | `SecurityBoundary` patterns + provenance gate | injection payload denied |
| tool poisoning | grant check + verification | ungranted tool denied |
| memory poisoning | scope isolation + provenance | cross-scope read denied |
| agent impersonation | identity verification + grant binding | revoked identity denied |
| capability escalation | authority subset + grant check | escalation denied |
| authority confusion | delegation subset + policy rule | child>parent denied |
| credential theft | grant credential gate, vault-only | missing-cred denied |
| data exfiltration | IFC + network rules | secret→public denied |
| malicious MCP | untrusted provider, grant-mediated | denied without grant |
| malicious A2A | trust levels, contracts, budgets | direct privileged invoke denied |
| supply-chain | extension manifest/signature gates | unsigned quarantine |
| model compromise | verification + provenance | unverified quarantined |
| sensor/device spoof | pairing, attestation, trust | unauthenticated pairing denied |
| network (SSRF/rebinding) | allow/denylists, IP policy | blocked domain denied |
| race/TOCTOU/replay | grant validity, idempotency, nonces | expired approval denied |
| delegation abuse | subset + depth + cascade revoke | enforced |
| swarm collusion | per-agent scopes/quotas | enforced |
| automation recursion | depth + budget + policy re-eval | enforced |
| resource exhaustion | admission denial with cause | enforced |

Fail-closed is the default verdict whenever state is uncertain.
