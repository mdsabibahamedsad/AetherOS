# AetherOS Policy Engine

Source: `kernel/core/policy_engine.py`, `kernel/core/security_boundary.py`,
`kernel/core/governance_engine.py`.

## PolicyEngine

Deterministic rule evaluation with caching (5s TTL). Rules have priority
(higher = evaluated first). Deny is final; REQUIRE_APPROVAL accumulates;
QUARANTINE/LIMIT/ESCALATE modify outcome.

```text
PolicyRule {
    rule_id: str
    name: str
    description: str
    condition: Callable[[Dict], bool]
    action: PolicyDecision
    priority: int
    metadata: Dict
    enabled: bool
}
```

```text
PolicyDecision { ALLOW, DENY, REQUIRE_APPROVAL, QUARANTINE, LIMIT, ESCALATE }
PolicyEvaluationResult { decision, matched_rules, denied_rules, required_scopes,
                         required_approvals, risk_level, explanation,
                         obligations, resource_limits }
```

### Default Rules (registered at boot)

| rule_id | action | priority | condition |
|---|---|---|---|
| `high_risk_approval` | REQUIRE_APPROVAL | 100 | risk ∈ {financial, physical, security_critical} |
| `untrusted_no_authority` | DENY | 200 | provenance ∈ {web, model, unverified, simulated, predicted} ∧ request ∈ {grant_cap, grant_auth, escalate} |
| `child_authority_subset` | DENY | 150 | action=delegate ∧ ¬(child_caps ⊆ parent_caps) |
| `sensitive_data_flow` | DENY | 180 | source ∈ {secret, highly_sensitive} ∧ dest ∈ {public, internal, unverified} |
| `resource_quota` | DENY | 120 | action=allocate ∧ requested > quota |
| `delegation_depth` | DENY | 130 | action=delegate ∧ depth > max_depth |

### Evaluation

```python
result = policy_engine.evaluate_intent(intent)      # for admission
result = policy_engine.check_capability(agent, cap)  # for invocation
result = policy_engine.check_data_flow(src, dst)     # for IFC
```

Cache key = sorted context items; TTL 5s; max 1000 entries.

## SecurityBoundary

All invocations pass through `SecurityBoundary.check_invocation()`:

1. Emergency stop check (global or agent-scoped)
2. Quarantine check (agent/capability)
3. Authorization (grant validity, capability subset, credentials)
4. Prompt injection scan (input regex patterns)
5. Information flow control (data classification → destination)
6. Side-effect risk (high risks → REQUIRE_APPROVAL)
7. Custom checks (registered callbacks)

### Emergency Stop (§31)

`SecurityBoundary.activate_emergency_stop(scope="global")` — independent
of any model; pauses all RUNNING/WAITING/READY/PAUSED agents; denies
all invocations with `"Emergency stop active"`. Cannot be overridden by
agent output.

### Quarantine

`quarantine_agent(agent_id, reason)` → marks agent, pauses, emits
`security.violation`. `release_quarantine(agent_id)` → authority
revalidation + manifest verification.

### Prompt Injection

Regex patterns (case-insensitive) for:
- Instruction override ("ignore previous instructions", "new instructions:")
- Authority escalation ("you have full/admin/root access", "bypass security")
- Data exfiltration ("send/print env/secrets/keys/tokens")
- Tool manipulation ("call tool", "execute code/shell")
- Identity manipulation ("you are admin/root/system")

Denied with `requires_human=True` — logged, not silently dropped.

## GovernanceEngine

Compliance checks for domain-specific policies (security, privacy,
financial, operational). Evaluates conditions against context, calls
registered violation handlers. Tracks compliance history.

## Information Flow Control (§34)

DataClassification hierarchy:
```
PUBLIC < INTERNAL < PRIVATE < CONFIDENTIAL < SECRET < HIGHLY_SENSITIVE
```

Policy: `SECRET/HIGHLY_SENSITIVE` cannot flow to `PUBLIC/INTERNAL/UNVERIFIED`.
`SecurityBoundary._check_information_flow` enforces at capability invoke
(egress check); `NetworkManager` re-checks URL against grant scopes +
deny/allow lists + SSRF/DNS-rebinding defense.

## Governance domains

```text
GovernanceDomain: SECURITY | PRIVACY | FINANCIAL | OPERATIONAL | COMPLIANCE
```

`GovernanceEngine.check_compliance(domain, context)` → `ComplianceCheck`
with `status: COMPLIANT | VIOLATION | REQUIRES_REVIEW`.