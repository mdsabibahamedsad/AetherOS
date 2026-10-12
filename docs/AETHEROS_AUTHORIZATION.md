# Authorization

```
Identity (API key) → Credential (scopes) → Capability → Scope → Policy
→ Resource (tenant-owned) → Action
```

- No endpoint relies on authentication alone: every guarded route
  declares scopes (`registry.py`), enforced in `gateway.py::_guard`
  (401 without key, 403 `AUTHORIZATION_DENIED` without scope — both
  tested, incl. scope-confusion: a `memory:read`-only key cannot create
  agents or invoke tools).
- Capabilities (`area.action`, `schemas.py::Capability`) are granted in
  agent manifests/skills and evaluated per intent by `PolicyBridge`
  (deny-by-default; unknown capabilities resolve HIGH risk).
- Least privilege: tool invocation requires caller grants ⊆ tool
  capabilities; task delegation narrows to agent∩tool. Excess authority
  → `CAPABILITY_NOT_GRANTED`.
- Tenancy: `Organization → Workspace → Project → Agent → Task`.
  Requests carry `X-Tenant-Org`/`X-Tenant-Workspace`; listings filter by
  ownership and cross-tenant reads → 403 (tested:
  `test_tenant_escape_denied`).
- Risk handling: LOW/MEDIUM → allowed; HIGH/CRITICAL or irreversible
  side effects → `APPROVAL_REQUIRED` (surfaced, not auto-approved).
