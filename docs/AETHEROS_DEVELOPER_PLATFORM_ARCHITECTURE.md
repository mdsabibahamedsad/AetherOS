# AetherOS Developer Platform Architecture

```
Developer CLI (python -m aetheros_platform.cli)
  init agent|tool|skill|mcp|a2a|extension · dev/serve · schema · api list
  test · package build|publish|install · auth key-create|list|revoke
        │
SDKs (controlled interface — never a backdoor)
  aetheros-sdk (Python sync+async) · @aetheros/sdk (TS, Node+browser-safe)
        │  typed errors · bounded retries+jitter · timeouts · idempotency keys
        ▼
Capability / Intent ABI (aetheros_platform/schemas.py — 34 schemas, single source)
        ▼
API Gateway (gateway.py::create_app — /api/v1, /api/v2 alias)
  routing · API-key auth · scope authz · rate limits · quotas · validation
  request/trace IDs · pagination · SSE streams · versioning · audit
        ▼
Policy / Governance (policy.py::PolicyBridge)
  Intent → evaluate(grants) → allowed | denied | approval_required
  | sandbox_required | credential_required — every decision audited
        ▼
Agent Runtime (agents.py · tools.py · skills.py · mcp.py · a2a.py)
  11-state agent lifecycle enforced · least-privilege tool delegation
  skill dep graphs (cycles/missing/escalation rejected)
        ▼
Execution (tools in-process deadline-bounded · MCP stdio · A2A HTTP · cron)
        ▼
Storage / Audit / Artifacts / Events
  aetheros_data SQLite · content-addressed artifacts · EventBus + signed webhooks
```

## Layer rules

1. Developers never bypass identity, authorization, policy, approval,
   sandbox, audit, rate limits, or tenant boundaries. The SDK cannot
   reach raw privileged actions: every intent is evaluated first
   (`policy.py:100 require_allowed`).
2. Public vs internal: `registry.py::ENDPOINTS` is an explicit allow-list.
   Internal classes are never exposed merely because they exist.
3. Capability ladder for new features (per AGENTS.md): extend existing
   code → CLI+skill → service-gated tool → plugin → MCP catalog →
   new core tool (last resort).
4. Prompt caching / narrow waist: the developer platform adds zero model
   tools; it is HTTP + SDK surface, not prompt surface.
