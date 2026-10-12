# AetherOS Capability ABI

Source of truth: `kernel/core/types.py` — `CapabilityDescriptor`,
`CapabilityInvocation`. Catalog: `kernel/core/syscalls.py`.

## Descriptor

`capability_id`, `version`, `provider`, `description`, `inputs`/`outputs`
(JSON Schema), `side_effects` (risk levels), `required_authority`,
`required_resources`, `required_credentials`, `network_access`,
`filesystem_access`, `device_access`, `data_classification`,
`reversibility`, `idempotency`, `latency_class`, `cost_class`,
`sandbox_support`, `verification_strategy`, `tags`.

## Syscall pipeline (§8)

```mermaid
flowchart LR
    CM[CapabilityManager] --> AM[AuthorityManager]
    AM --> PE[PolicyEngine]
    PE --> SB[SecurityBoundary]
    SB --> RM[ResourceManager]
    RM --> CI[CapabilityInvoker]
    CI --> V[Verification]
    V --> A[Audit]
```

```text
CapabilityManager → AuthorityManager → PolicyEngine → SecurityBoundary →
ResourceManager → CapabilityInvoker → Verification → Audit
```

No bypasses: `AgentKernel.invoke_capability()` is the only entry point.

## Canonical syscalls

`fs.read/write/delete/list/search/patch`, `process.execute`,
`terminal.execute`, `network.request`, `research.search/fetch`,
`browser.navigate/click/type/screenshot/extract`,
`computer.observe/screenshot/click/type`, `memory.read/write/search`,
`automation.create/execute`, `agent.spawn/delegate`, `message.send`,
`vision.analyze`, `checkpoint.create`, plus all `tool.*` capabilities
discovered from `tools/registry.py`.

Hardware-gated (`device.control`, `robot.navigate/manipulate`,
`device.pair`) is registered as BLOCKED stubs that raise
`REQUIRES_HARDWARE` — fail-closed, never faked.

## Side-effect classification (§29)

`READ_ONLY`, `REVERSIBLE`, `IRREVERSIBLE`, `EXTERNAL_SIDE_EFFECT`,
`FINANCIAL`, `COMMUNICATION`, `PRIVACY_SENSITIVE`, `PHYSICAL`,
`SECURITY_CRITICAL`. Risk determines approval (`PolicyEngine`,
`HumanOversightManager`) and the action transaction model
(`PREPARE → AUTHORIZE → EXECUTE → VERIFY → COMMIT`, with `ROLLBACK`
for reversible and explicit authorization + pre/post verification for
irreversible operations).
