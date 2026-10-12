# AetherOS 1.0 Security Architecture (as implemented)

Zero-trust intent: every privileged action authorized (who/agent/task/tool/
resource/scope/purpose/policy/approval); deny by default (RBAC/ABAC/capability
gates in tree). AgentCapsule + approval gates + resource/tool/network/
filesystem budgets; runaway → budget/timeout/kill/takeover + audit.
Sandbox: Electron sandbox + context isolation; preload is the sole bridge
(allow-listed channels). Secrets: manager-only, redacted from logs/bundles/
telemetry (tested). Update trust: RSA manifest + artifact signatures, SHA-256,
HTTPS-only, anti-downgrade, revocation (tested). MCP/A2A: identity-gated, no
implicit trust; malicious-output handling in tree. Memory: provenance,
retraction, poisoning defenses, tenant isolation. Audit: actor/resource/
timestamp-aware; tamper-evidence is a deployment property (UNVERIFIED live).
