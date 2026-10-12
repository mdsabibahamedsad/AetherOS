# Developer Guide: Building on Trust Fabric (§241-247)

## Register an identity

```python
from aetheros_control_plane.models import IdentityType
ident = plane.identities.create(IdentityType.AGENT, "my-agent",
                                scopes=["read:docs"])
```

## Define a capability + request approval

Capabilities are `action:resource` scope strings. High-risk work:
`orchestrator.request(ApprovalRequest(actor, action, resource,
purpose, risk, approver_policy="quorum:2"))`, collect votes, then
`consume()` binds approval to the exact triple.

## Authorize a tool call

```python
decision = fabric.propose(identity_id, capability, resource, ...)
token = fabric.authorize(...)   # raises unless unqualified ALLOW
tool_runtime.validate(token, audience="my-tool")
```

Tools validate tokens independently with `CapabilityAuthority`
— never trust `agent.is_admin` shortcuts (§149).

## Record provenance

`provenance.link_action(...)`, `link_result(...)`,
`issue_receipt(...)` (Ed25519-signed). Query with `explain()`.

## Handle revocation

`fabric.revoke(kind, id, reason)` propagates across the authority
graph and into M50 engines; subscribe via `on_revoke`.

## Integrate MCP / A2A / robotics

MCP servers pass identity+scope checks per tool call; remote
agents require explicit `delegation_id` (`check_remote`);
robot commands add workspace/collision/force/speed/human-proximity
context to the safety check. Marketplace extensions declare full
security metadata or registration is rejected
(`ToolContractValidator`).

## Contributor rule (§242)

New consequential capabilities MUST ship a `ToolManifest`
(identity, capabilities, permissions, risk R0-R8, side effects,
reversibility, data/network/secret access, audit level) or
registration fails validation.

## Maturity (§248)

S0 UNGOVERNED -> S1 IDENTIFIED -> S2 AUTHORIZED -> S3
POLICY-GOVERNED -> S4 FULLY AUDITED -> S5 HIGH-ASSURANCE, computed
from registry metadata — never self-declared S5.
