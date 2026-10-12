---
id: security-control-plane
title: Zero-Trust Security Control Plane
sidebar_label: Security Control Plane
---

# Zero-Trust Security Control Plane

AetherOS runs its own zero-trust security control plane. Every sensitive
action — a tool call, a file write, an outbound message, a budget-spending
step — is evaluated deterministically *outside the model's reasoning loop*.
The model never decides whether an action is safe; the control plane does.

The plane is a **facade and extension of the existing AetherOS security
system** (`aetheros_security`). It composes the canonical identity,
authentication, authorization, session, policy, approval, audit, threat,
secrets, encryption, redaction, DLP, manifest, network, filesystem and
sandbox modules into a single stable public surface, and fills the gaps the
system did not yet cover — data classification and flow control, resource
budgets and recursion limits, named kill switches and safe shutdown, policy
priority hierarchy, the tool authorization boundary, the guarded-action
pipeline, and the security scorecard.

Two properties shape the design:

- **Fail closed.** Every boundary defaults to deny. An unknown principal is
  not active, an unknown tool is not allowed, an unknown host is not
  reachable, an unapproved high-risk action is not executed.
- **Deterministic.** All decisions come from audited state and policy —
  never from model output, tool descriptions, or memory.

## Architecture

```
aetheros_security/                 # canonical security package
├── identity/            principal registry, trust levels, quarantine
├── authentication/      credentials, MFA, session auth
├── authz/               AuthorizationEngine — the deterministic core
├── policy/              declarative policies (default deny)
├── approval/            single-use, exactly-bound human approvals
├── audit/               tamper-evident audit log
├── threat/              threat detection
├── secrets/             secret access broker + backend abstraction
├── encryption/          encryption manager
├── redaction/           secret redaction engine
├── dlp/                 data-loss-prevention manager
├── manifest/            per-tool permission manifests
├── network/             host/port/DNS policy (private-range blocking)
├── filesystem/          path checks, protected paths, symlink policy
├── sandbox/             command sandbox
├── mcp/                 MCP-server security
├── ai_security/         prompt-injection + output guardrails
├── response/            emergency stop / lockdown / incidents
├── rate_limit/          abuse prevention
├── classification/      DataClassification + DataFlowGuard  (new)
├── budget/              ResourceBudget + RecursionGuard       (new)
├── kill_switch/         named kill switches + SafeShutdownService (new)
├── policy_hierarchy/    PolicyLayer priority + safe explanations (new)
├── tool_authz/          ToolAuthorizationService boundary      (new)
├── action_guard/        RiskTier R0-R4 guarded-action pipeline (new)
└── scorecard/           SecurityScorecard (21-category posture) (new)
```

## Quick start

```python
from aetheros_security import get_security_manager

sm = get_security_manager()

print(sm.security_scorecard()["overall"])   # posture verdict
print(sm.classify_action_risk("filesystem:delete"))  # R4
decision = sm.check_data_flow(classification="secret",
                              source="memory",
                              destination="web:send")   # denied
```

## Classification and data flow

`classification/` labels data `PUBLIC → INTERNAL → PRIVATE → SENSITIVE →
HIGHLY_SENSITIVE → SECRET` by content (API keys, private keys, bearer
tokens, JWTs, SSNs, card numbers, passwords, emails) or explicit override.

`DataFlowGuard` enforces where each classification may go. Private and
above may not leave the system to external sinks (email, web, cloud)
without an explicit policy — and **secret data never leaves at all**, even
with policy and the global escape hatch both set.

```python
from aetheros_security.classification import classify_content, get_data_flow_guard

level = classify_content("key sk-1234567890abcdefghijklmnopqrstuv")  # SECRET
guard = get_data_flow_guard()
decision = guard.check_flow(classification=level,
                            source="memory", destination="web:send")
decision.allowed   # False
```

## Resource budgets and recursion limits

`budget/` provides per-mission `ResourceBudget`s (tool calls, cost USD,
wall time, tokens, network requests, storage, compute) and a thread-local
`RecursionGuard` with a hard absolute depth cap so runaway agent/tool
recursion is impossible.

```python
from aetheros_security.budget import BudgetLimits, register_budget, get_recursion_guard

budget = register_budget("mission-7", ResourceBudget(
    name="mission-7", limits=BudgetLimits(tool_calls=40, cost_usd=2.0)))
budget.spend_tool_call()
budget.can_tool_call()
```

## Kill switches and safe shutdown

`kill_switch/` implements six named, policy-controlled switches:

| Switch | Blocks |
|--------|--------|
| `disable_autonomous_actions` | autonomous / unattended missions |
| `disable_external_network` | outbound network access |
| `disable_tool_execution` | tool execution |
| `disable_agent_delegation` | spawning subagents |
| `disable_remote_control` | remote-control / gateway actions |
| `disable_model_provider` | model inference calls |

Only an **elevated principal** (`admin`, `system`, `security`, `root`) may
flip a switch; every transition is audited; switches **never auto-reset**.

`SafeShutdownService` performs a controlled shutdown: it activates the
switches that stop new privileged actions and signals the response layer's
emergency stop — and it **never deletes user data, memory, or session
history**.

```python
from aetheros_security.kill_switch import KillSwitch, get_kill_switch_registry

reg = get_kill_switch_registry()
reg.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, True,
               principal="admin", reason="incident-913")
reg.is_active(KillSwitch.DISABLE_TOOL_EXECUTION)  # True
```

## Policy priority hierarchy

`policy_hierarchy/` resolves layered decisions with a strict priority
order: **SYSTEM > ORGANIZATION > USER > MISSION > AGENT > TASK > MODEL
suggestion**. Lower layers can never override a higher layer; the model is
never a security authority. Explanations are **safe by default** — internal
reason strings never leak to users.

```python
from aetheros_security.policy_hierarchy import PolicyLayer, resolve_layer_decisions

resolve_layer_decisions([
    (PolicyLayer.SYSTEM, "DENY"),
    (PolicyLayer.AGENT, "ALLOW"),   # overridden — SYSTEM wins
])                                  # -> decision "deny"
```

## Tool authorization boundary

`tool_authz/` is the deterministic boundary every tool call should cross
before execution. It checks, in order (fail-closed): kill switch →
parameter validation (path traversal, UNC, absolute paths, encoded
separators, unsafe URL schemes) → manifest permission → the authorization
engine (principal, session, policy, risk, approval). Model-produced
parameters are validated *outside* the model.

```python
from aetheros_security.tool_authz import (
    ToolAuthOutcome, ToolAuthRequest, get_tool_authorization_service,
)

decision = get_tool_authorization_service().check(ToolAuthRequest(
    principal="research-agent", tool="filesystem_read_file",
    action="filesystem:read", resource="../../etc/passwd",
    parameters={"path": "../../etc/passwd"}))
decision.outcome   # DENY — traversal rejected before authorization
```

## The guarded-action pipeline

`action_guard/` runs every privileged action through a deterministic
pipeline:

```
intent validation → permission → parameters → risk (R0-R4) → approval →
irreversibility → bulk guard → dry-run → dual control → execute →
post-condition → audit
```

- **Risk tiers R0-R4** classify actions (`filesystem:delete` is R4,
  `search:query` R0).
- **Dry-run** previews high-risk actions without executing.
- **Irreversible** actions require approval.
- **Bulk protection** forces approval for actions touching more than
  `bulk_threshold` items.
- **Dual control** requires a second, independent authorization check for
  critical actions.
- **Post-condition validation** verifies the action actually achieved its
  declared effect.
- **Transactional actions** (`prepare → validate → commit/rollback`)
  provide safe, reversible multi-step operations.

```python
from aetheros_security.action_guard import GuardRequest, get_action_guard

guard = get_action_guard()
guard.register_executor("filesystem:delete", my_delete_fn)
result = guard.execute(GuardRequest(
    principal="agent-1", action="filesystem:delete",
    resource="/tmp/notes.md", dry_run=True))
result.decision  # approval_required / deny / dry_run / allow
```

## Security scorecard

`scorecard/` probes all 21 subsystems with fail-safe checks and produces a
PASS / PARTIAL / FAIL / NOT APPLICABLE posture report with an overall
readiness verdict.

```bash
aetheros security scorecard
# Security Scorecard:
#   Identity               PASS
#   Authentication         PASS
#   ... (21 categories)
#   Readiness: 100.0% (STRONG)
```

## Configuration

`security.control_plane` in `config.yaml` controls the plane (never new
env vars):

```yaml
security:
  control_plane:
    tool_authorization: true
    data_flow_guard: true
    allow_external_sensitive: false
    action_guard:
      require_approval_above: R3
      bulk_threshold: 100
    budgets:
      default:
        tool_calls: 40
        cost_usd: 2.0
    kill_switches:
      default: false
```

## CLI

`aetheros security <subcommand>` (also the `/security` slash command)
exposes the plane:

```
status  users  roles  sessions  audit  keys  mfa  providers
scorecard  kill-switch  shutdown  classify  flow  guard
```

Examples:

```bash
aetheros security status
aetheros security scorecard
aetheros security kill-switch disable_tool_execution on
aetheros security shutdown
aetheros security classify "the password is hunter2"
aetheros security flow --source memory --destination email:send
aetheros security guard --action filesystem:delete --source /tmp/x
```

Kill-switch toggles and shutdown are operator actions and run as an
elevated principal — agents and remote callers cannot flip switches.

## Red-team guarantees

The control plane is exercised by an adversarial test suite
(`tests/security/test_red_team.py`) that asserts the defenses hold against:

- prompt injection and jailbreak prompts
- approval replay (different resource / action / parameters) and
  single-use consumption
- bulk-abuse (mass delete) and recursion-depth runaway
- SSRF to metadata service and private ranges
- path traversal (plain, encoded, dot-dot-dot, UNC) and unsafe URL schemes
- secret exfiltration across the data-flow boundary
- kill-switch gating by unprivileged principals
- model output leaking sensitive data

## Related documentation

- [observability.md](observability.md) — the observability layer that
  records the audit trail these controls produce
- [agent-loop.md](agent-loop.md) — the conversation loop the controls gate