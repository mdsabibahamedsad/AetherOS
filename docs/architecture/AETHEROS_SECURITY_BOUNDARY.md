# AetherOS Security Boundary

Implementation: `kernel/core/security_boundary.py`,
`kernel/core/policy_engine.py`, `kernel/core/governance_engine.py`,
`kernel/core/human_oversight_manager.py`, `kernel/core/network_manager.py`.

## Trust boundary (§59)

```text
UNTRUSTED: LLM outputs, plans, web content, tool results, external agents,
  sensor input, OCR, user files, ambient audio, remote nodes
TRUSTED: kernel policy, identity verification, authority evaluator,
  capability broker, audit engine, security boundary, resource manager
```

The model is never the authorization source — not the renderer, CLI,
agent, tool, or remote node either. Authorization happens kernel-side.

## Controls

- Fail-closed (§32) + `PolicyDecision` (`allow / deny / require_approval /
  quarantine / limit / escalate`).
- Prompt-injection defense (§35): regex + provenance gates; untrusted
  content cannot change intent/authority/policy/credentials/system
  instructions (`untrusted_no_authority` rule).
- Information flow control (§34): `PUBLIC → … → HIGHLY_SENSITIVE` with
  deny on `SECRET/HIGHLY_SENSITIVE → PUBLIC/INTERNAL/unverified`,
  redaction hooks, and network-egress checks (`NetworkManager`: allow/
  denylists, SSRF/DNS-rebinding defense, TLS, proxy, budgets).
- Human oversight (§30): `approval.request/grant/deny/expire/delegate/
  remember` with full action context (resource, data, destination, risk,
  reversibility, identity, parent task, policy, alternatives).
- Emergency stop (§31): `AgentKernel.emergency_stop()` pauses agents and
  denies invocations; it operates independently of the LLM.

## Threat model (§58)

Covered by `tests/kernel/test_agent_kernel_security.py`: prompt injection,
capability escalation, authority confusion, memory poisoning, malicious
MCP/A2A (untrusted providers denied by grant check), credential
exfiltration (grant credential gate), SSRF/DNS rebinding (network rules),
replay/TOCTOU/race (grant validity + idempotency flags), delegation abuse
(subset enforcement), swarm collusion (per-agent scopes), automation
recursion (depth limits), resource exhaustion (admission denial).
