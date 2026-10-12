# AetherOS Capsule Threat Model

Threats, controls, and executable coverage
(`tests/kernel/test_agent_capsule_security.py`).

| Threat | Control | Test |
|---|---|---|
| Capsule exceeds authority | Manifest gate on every call | `test_capsule_cannot_exceed_authority` |
| Policy bypass | Admission + manifest + kernel policy | `test_capsule_cannot_bypass_policy` |
| Host file access | Guard + mount containment + virtualization | `test_capsule_cannot_access_unmounted_host_files` |
| Denied network | NO_NETWORK/allowlist + kernel re-check | `test_capsule_cannot_access_denied_network` |
| Secret theft | Broker scoping, no plaintext, revocation | `test_capsule_cannot_access_unauthorized_secrets` |
| Child exceeds parent | Subset delegation + quota + depth | `test_child_capsule_cannot_exceed_parent` |
| Remote impersonation | Kernel-assigned node_id; pairing-required migration | `test_remote_capsule_cannot_impersonate_local` |
| Revoked capability use | Manifest reseal; future calls blocked | `test_revoked_capability_cannot_execute` |
| Expired capsule execution | Expiry + authority-validity gates | `test_expired_capsule_cannot_execute` |
| Quarantined execution | Operability gate | `test_quarantined_capsule_cannot_execute_privileged` |
| Replay side effects | OBSERVE_ONLY default; external blocked | `test_replay_cannot_execute_external_side_effects` |
| Path traversal / symlink / junction / UNC / ADS / device paths | `validate_capsule_path` | 16 parametrized probes + live symlink test |
| SSRF / DNS rebinding / metadata / localhost / numeric-IP tricks | `check_egress_url` | 13 parametrized probes |
| Env secret leakage | Scrubbed environment block | `test_environment_secret_leakage_blocked` |
| Prompt injection (web/PDF/email/MCP/A2A/terminal/repo/OCR/audio/QR/device) | Payload grants nothing; caps ⊆ profile | 5 payload tests + tool-input test |
| Malicious escalation / exfiltration / spawn explosion / recursion / audit tamper | Manifest, quotas, depth, chained receipts | §114 tests |
| Resource exhaustion / policy update / credential expiry / crash | Capacity denial, re-evaluation, TTL, snapshot restore | §115 chaos tests |

Out of scope for 1.0 (stated, not hand-waved): hypervisor-escape via
kernel exploits, side channels, malicious container runtimes, compromised
hardware/firmware, remote-node compromise after pairing. LEVEL_3+,
GPU isolation, and secure remote migration are UNAVAILABLE/NOT_SUPPORTED
until implemented and tested.
