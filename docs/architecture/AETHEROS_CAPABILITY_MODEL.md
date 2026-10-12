# AetherOS Capability Model

Source: `kernel/core/types.py` (`CapabilityDescriptor`, `CapabilityInvocation`,
`CapabilityRiskLevel`), `kernel/core/capability_manager.py`,
`kernel/core/capability_invoker.py`, `kernel/core/syscalls.py`.

## Capability Descriptor (Capability ABI)

Every capability exposes machine-readable metadata:

```text
CapabilityDescriptor {
    capability_id: str
    version: str
    provider: str
    description: str
    inputs: Dict (JSON Schema)
    outputs: Dict (JSON Schema)
    side_effects: List[CapabilityRiskLevel]
    required_authority: List[str]
    required_resources: ResourceBudget
    required_credentials: List[str]
    network_access: bool
    filesystem_access: bool
    device_access: bool
    data_classification: DataClassification
    reversibility: bool
    idempotency: bool
    latency_class: str  // fast, normal, slow
    cost_class: str     // free, low, medium, high
    sandbox_support: bool
    verification_strategy: str  // observe, verify, attest
    tags: List[str]
}
```

## Syscall Catalog (Master 57 §8)

`kernel/core/syscalls.py` maps canonical syscalls to existing AetherOS
tools (reused, not duplicated):

| Syscall | Backing tool(s) |
|---|---|
| `fs.read` | `read_file` |
| `fs.write` | `write_file` |
| `fs.delete` | `write_file` |
| `fs.list` | `search_files` |
| `fs.search` | `search_files` |
| `fs.patch` | `patch` |
| `process.execute` | `process`, `execute_code` |
| `terminal.execute` | `terminal` |
| `network.request` | `web_extract`, `web_search` |
| `research.search` | `web_search`, `session_search` |
| `research.fetch` | `web_extract`, `document_extract` |
| `browser.navigate` | `browser_navigate` |
| `browser.click` | `browser_click` |
| `browser.type` | `browser_type` |
| `browser.screenshot` | `browser_snapshot`, `screen_capture` |
| `browser.extract` | `browser_snapshot`, `web_extract` |
| `computer.observe` | `screen_capture`, `screen_understand`, `computer_use` |
| `computer.screenshot` | `screen_capture`, `computer_use` |
| `computer.click` | `computer_use` |
| `computer.type` | `computer_use` |
| `memory.read` | `memory`, `memory2_get`, `memory2_search` |
| `memory.write` | `memory`, `memory2_create` |
| `memory.search` | `memory2_search`, `memory` |
| `automation.create` | `automation_create`, `automation_build` |
| `automation.execute` | `automation_run` |
| `agent.delegate` | `delegate_task` |
| `message.send` | `discord`, `integration_webhook` |
| `vision.analyze` | `vision_analyze`, `screen_understand` |
| `audio.transcribe` | `text_to_speech` |

Hardware-gated (explicit BLOCKED stubs, fail-closed):
- `device.control`
- `robot.navigate`
- `robot.manipulate`
- `device.pair`

Kernel-native (no tool backing):
- `agent.spawn` / `agent.delegate` (spawn child agent with delegated grant)
- `memory.read` / `memory.write` (scoped memory access)
- `checkpoint.create` (full snapshot)

## Syscall Pipeline

`CapabilityInvoker.invoke(invocation)` — every call passes through:

```
CapabilityManager (descriptor lookup)
    → AuthorityManager (grant validity + capability subset)
    → PolicyEngine (ALLOW/DENY/REQUIRE_APPROVAL/LIMIT/ESCALATE)
    → SecurityBoundary (injection, IFC, emergency, quarantine)
    → ResourceManager (remaining budget vs required)
    → CapabilityInvoker (provider.invoke → verification → receipt)
    → AuditEngine (hash-chained log)
```

No bypasses. Every step can deny.

## Verification Strategies

| Strategy | Behavior |
|---|---|
| `observe` | result exists |
| `verify` | result exists + no error |
| `attest` | UNVERIFIED unless provider registers custom verifier with cryptographic proof |

## Risk Classification (CapabilityRiskLevel)

| Level | Meaning |
|---|---|
| `READ_ONLY` | no side effects |
| `REVERSIBLE` | undo possible |
| `IRREVERSIBLE` | permanent |
| `EXTERNAL_SIDE_EFFECT` | world changes |
| `FINANCIAL` | money moves |
| `COMMUNICATION` | messages sent |
| `PRIVACY_SENSITIVE` | private data |
| `PHYSICAL` | actuators move |
| `SECURITY_CRITICAL` | auth/keys/boundary |

Risk determines approval requirement, autonomy cap, blast radius.

## Side-effect classification (§29)

Every capability declares `side_effects: List[CapabilityRiskLevel]`. The
pipeline uses this for:
- Approval gating (high-risk → REQUIRE_APPROVAL)
- Blast radius calculation
- Replay mode (external effects BLOCKED_EXTERNAL in DRY_RUN)
- Audit tagging

## Capability Registration

`ToolManager.discover_tools()` discovers from `tools.registry` +
`model_tools.get_tool_definitions(None, None, True)` (72 tools → `tool.*`
capabilities). `syscalls.py` registers canonical syscalls as aliases to
first-available backing tool. Hardware-gated caps registered as BLOCKED
stubs (fail-closed, never fake success).

## Security Invariants (tested)

1. `capability_not_found` → denied
2. `grant_not_found` / `grant_invalid` / `capability_not_granted` → denied
3. `policy_denied` → denied
4. `security_denied` (injection, IFC, emergency, quarantine) → denied
5. `ifc_violation` (secret→public, etc.) → denied
6. Manifest integrity: sealed manifest; tampering → all calls denied
5. Revoked capability → denied
6. Expired grant → denied
7. Emergency stop → denied