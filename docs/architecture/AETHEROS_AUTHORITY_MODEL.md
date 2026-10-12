# AetherOS Authority Model

Source: `kernel/core/authority_manager.py`, `kernel/core/types.py` (`AuthorityGrant`,
`AgentIdentity`), `kernel/core/authority_manager.py`.

## Authority Grant

The Kernel is the sole authority granter. All capability access is
mediated through an `AuthorityGrant`:

```text
AuthorityGrant {
    grant_id: str
    agent_id: str
    intent_id: str
    capabilities: List[str]
    resources: ResourceBudget
    data_scopes: List[str]
    network_scopes: List[str]
    filesystem_scopes: List[str]
    device_scopes: List[str]
    credentials: List[str]
    parent_grant_id: str | null   // delegation chain
    expires_at: float | null
    revocable: bool
    metadata: Dict
    created_at: float
}
```

- `is_valid()` checks `expires_at` and `revocable`.
- `check_capability(agent_id, cap)`, `check_data_scope()`, etc.

## Granting

`create_grant(intent, parent_grant_id=None)` derives from intent:
- Capabilities: requested ∩ policy-allowed (policy may strip)
- Resources: min(requested, available)
- Data scopes: derived from `privacy_class` (PUBLIC→SECRET ladder)
- Network scopes: `localhost` + explicit `authority_scope`
- Filesystem scopes: `workspace`, `scratch`
- Device scopes: `sensors` (+ `actuators` if physical caps)
- Credentials: inferred from capability names (github→GITHUB_TOKEN, etc.)

`grant_authority(agent_id, intent, parent_grant_id)` binds grant to
agent and indexes it.

## Delegation (§14)

```python
delegate_authority(parent_agent_id, child_agent_id, intent, parent_grant_id)
```

Enforces subset constraints:
- `child_caps = requested ∩ parent_caps` (denied logged)
- `child_resources = min(requested, parent_resources)`
- `child_scopes = requested_scopes ∩ parent_scopes`
- No credential inheritance (child gets empty list)
- Expiry = min(child_deadline, parent_expiry)
- Depth = parent.metadata.delegation_depth + 1 ≤ `max_agent_depth` (default 5)

Revocation cascades: `revoke_grant(grant_id)` → expires parent + all
descendants immediately.

## Authority Invariants (tested)

1. `ChildAuthority ⊆ ParentAuthority` always (enforced at delegation)
2. Child never inherits credentials
3. Revocation cascades recursively
4. Expired/revoked grant → `is_valid()` false → all invocations denied
5. Delegation depth capped by `max_agent_depth`