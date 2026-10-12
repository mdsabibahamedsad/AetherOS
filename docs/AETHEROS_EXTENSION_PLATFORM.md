# AetherOS Extension Platform (Master 44)

## Architecture

```
Renderer → Typed IPC (extension.*) → ExtensionService → Policy/Permission
engines → ExtensionHost → Capability runtime (PARTIAL OS sandbox)
```

One canonical registry, permission engine, publisher trust model, tool
registration path, MCP lifecycle, extension lifecycle, security policy —
shared by skills, MCP, tools, agents, automation, memory. No parallel
security systems.

## Package layout

`aetheros_extensions/`: manifest, package (.aetherext), trust
(Ed25519), permissions (R0–R5 + scopes), registry (states, deps,
compat, health), scanner (static + dynamic), sandbox (capabilities,
SecretBroker, host), sources (local/bundled/remote/git/private/org),
bridges (MCP/skill/tool/agent/automation/memory), service (18-stage
install flow, updates, rollback, quarantine).

## Extension API v1

Capability/Permission/MCP/Skill/Tool/UI APIs all at v1. Manifests
declaring another `apiVersion` fail closed. Engine gate: `engineVersion`
must be ≤ 44.

## Lifecycle

DISCOVERED → VALIDATING → VERIFIED → TRUST_PENDING → PERMISSION_PENDING
→ INSTALLING → INSTALLED → ENABLED → RUNNING → … → UNINSTALLED, with
failure states and quarantine. All transitions validated + persisted;
installed state is only entered after commit.

## Trust defaults

Third-party = untrusted. UNSIGNED never installs (except explicit dev
mode, visible + logged). Imports land UNTRUSTED/disabled.

## Integration map

- Tools: manifest tools → ToolRegistry with `ext:<id>` provider tag and
  risk/permission metadata; uninstalled/quarantined tools deregistered.
- Agents: specialist roles → swarm AgentRegistry (same permission/budget/
  audit path, cannot bypass orchestration).
- Automation: nodes gated by autonomy caps, never elevate Level 0.
- Memory: scoped recall only, never the full knowledge graph.
- MCP: servers adopted as MCPExtensions; descriptions scanned; invocation
  still passes policy/permission/approval/risk gates.
- Skills: SKILL.md frontmatter parsed; instructions flagged untrusted.

## Built-ins

Existing skills/MCP/tools represented as BUILT_IN records, never as fake
downloads. Migration is additive; nothing built-in was modified.
