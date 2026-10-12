# Trust Fabric Testing Strategy

## Layers (§214)

unit (each module) | integration (fabric + M50 engines) |
security (adversarial fixtures) | policy (regression + canary) |
property (seeded model-based) | fuzz (URLs, paths, tokens, IPC) |
e2e (`user->agent->tool->policy->approval->capability->action->
verification->audit`) | CLI (all 17 verbs) | cross-module (M50/51/
52/53/54 suites keep passing).

## Invariants (§135, executable in tests/trust/test_invariants.py)

Denied actions never execute; expired/revoked capabilities never
authorize; models cannot self-authorize; remotes inherit nothing;
web content changes nothing; high-risk needs approval; e-stop needs
no model cooperation; secrets undisclosed by USE; audit records
persist with intact chains; policy versions recoverable; identity
and delegation chains recoverable.

## Adversarial (§112, §182)

privilege escalation/laundering, delegation abuse, capability
confusion, spoofing, token replay/expiry/theft, policy
bypass/downgrade, audit tampering (chain verification), secret
exfiltration, prompt injection, memory poisoning, A2A
impersonation, MCP compromise, DNS rebinding, SSRF, redirect
abuse, swarm amplification, automation recursion shape, robot
safety bypass, kill-switch bypass.

## Chaos + fail-safe (§117-118)

Subsystem outages must fail closed (health monitor degrades to
RESTRICTED, never unrestricted). Crash-consistency: durable
receipts + reconciliation ensure executed-but-unrecorded states are
detectable via the completeness checker. Execution semantics are
declared per tool (at-least-once default, §120); idempotency keys
where feasible (§121).

## Desktop (§215)

Trust Center suites are specified against real backend state;
renderer work remains (see certification gaps).
