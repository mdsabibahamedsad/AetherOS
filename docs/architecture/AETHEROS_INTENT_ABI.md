# AetherOS Intent ABI

Source: `kernel/core/types.py` (`Intent`, `IntentEnvelope`), `kernel/core/intent_manager.py`.

## Intent

Structured Intent object — survives planning, delegation, tool calls, agent
handoffs, automation, A2A communication, recovery, checkpointing, and
audit. Never reduced to bare natural language after execution begins.

```text
Intent {
    intent_id: str           // new_id("intent")
    actor: str               // human, agent, automation, system
    objective: str           // verbatim normalized text
    constraints: List[str]   // hard constraints (e.g., "no network")
    requested_capabilities: List[str]  // explicit caps only; no guessing
    requested_resources: ResourceBudget
    authority_scope: List[str]
    data_scope: List[str]
    risk_level: CapabilityRiskLevel
    deadline: float | null
    budget: ResourceBudget
    privacy_class: DataClassification
    autonomy_level: float    // 0.0 = supervised, 1.0 = autonomous
    approval_requirement: str  // none / notify / require_approval / require_step_up
    provenance: ProvenanceType
    parent_intent_id: str | null
    correlation_id: str
    metadata: Dict
    created_at, updated_at: float
}
```

## IntentEnvelope

Versioned envelope with content-hash signature — travels the pipeline
unchanged:

```text
IntentEnvelope {
    version: "1.0"
    intent: Intent
    provenance: ProvenanceType
    signature: str  // SHA-256 of canonical payload
    timestamp: float
}
```

- `seal()` computes the hash
- `verify()` recomputes and compares — rejects tampering or version skew

## Normalization (§5)

Raw natural language → `IntentManager.normalize_natural_language()`
extracts ONLY explicit `cap:<id>` tokens from the text. No capability is
guessed from prose. The objective remains verbatim; all capability
resolution happens at admission time against the registry.

```python
intent = IntentManager.normalize_natural_language(
    "please delete the logs cap:fs.delete urgently")
# intent.requested_capabilities == ["fs.delete"]
# intent.objective == "please delete the logs cap:fs.delete urgently"
```

## Admission pipeline

```text
Natural Language
    ↓
Structured Intent (normalize)
    ↓
Validation (structure, deadlines, autonomy ∈ [0,1])
    ↓
Resource check (admission reserve)
    ↓
Risk evaluation (capabilities → risk escalation)
    ↓
Approval determination (risk + autonomy + privacy + constraints)
    ↓
Authority grant (subset of requested caps, resources, scopes, credentials)
    ↓
Execution environment (capsule + agent process)
```

The model never grants its own authority. The Kernel determines the
minimum authority required.

## Provenance

Every intent carries `provenance`:
- USER_PROVIDED
- MODEL_GENERATED
- TOOL_RETURNED
- WEB_DERIVED
- MEMORY_DERIVED
- SENSOR_DERIVED
- DEVICE_DERIVED
- AGENT_DERIVED
- HUMAN_APPROVED
- SYSTEM_DERIVED
- INFERRED
- SIMULATED
- PREDICTED
- VERIFIED
- UNVERIFIED

Policy rule `untrusted_no_authority` denies any escalation from
`web_derived`, `model_generated`, `unverified`, `simulated`, `predicted`.