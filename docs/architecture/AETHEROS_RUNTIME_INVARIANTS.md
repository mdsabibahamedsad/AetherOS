# AetherOS Runtime Invariants

Source: `docs/architecture/AETHEROS_RUNTIME_INVARIANTS.md` — architectural
guarantees enforced by code, not documentation.

## Invariant Catalog (tested)

1. **No privileged action without capability authorization**
   - `CapabilityInvoker.invoke()` requires valid grant + manifest
   - Test: `test_capsule_cannot_exceed_authority`

2. **No capability authorization without identity**
   - `AuthorityManager.create_grant` binds to agent
   - Test: `test_renderer_cannot_grant_backend_authority`

3. **No autonomous execution without policy evaluation**
   - `IntentManager.admit()` runs policy + resource + risk
   - Test: `test_intent_admission_and_validation`

4. **Model output never overrides deterministic policy**
   - `PolicyEngine` + `SecurityBoundary` gate all invocations
   - Test: `test_policy_denial_cannot_be_bypassed_by_model_output`

5. **Observation is not verification**
   - `_verify_observe` only checks result exists
   - Test: `test_verification_honesty` + `_verify_attest` UNVERIFIED

6. **Planning is not execution**
   - Intent → Admission → Plan → Schedule → Execute are distinct
   - Test: `test_intent_admission_and_validation` separates phases

7. **Prediction is not reality**
   - `ProvenanceType.PREDICTED` ≠ `OBSERVED`
   - World model outputs labeled PREDICTED/SIMULATED
   - Test: `test_simulation_cannot_be_reported_as_reality`

7. **Memory is not automatically truth**
   - `ProvenanceType` distinguishes `USER_PROVIDED` vs `MODEL_GENERATED`
   - Test: `test_untrusted_content_never_becomes_authority`

8. **Agent delegation cannot exceed parent authority**
   - `delegate_authority` enforces subset
   - Test: `test_child_capsule_cannot_exceed_parent`

10. **Background automation cannot silently escalate autonomy**
    - `reevaluate_policy()` on change; critical risk → RESTRICT/TERMINATE
    - Test: `test_chaos_policy_update_reevaluates`

11. **Remote agents are untrusted until verified**
    - Migration requires pairing + mTLS
    - Test: `test_remote_capsule_cannot_impersonate_local`

12. **Extensions are untrusted until policy-approved**
    - `ExtensionSDK` manifests + signatures + capability lists
    - Not yet wired (feature flag off)

13. **Security boundaries must be enforced outside the model**
    - `SecurityBoundary` runs before every invocation
    - Test: `test_emergency_stop_cannot_be_overridden_by_agent`

14. **Every consequential action must be auditable**
    - `AuditEngine` hash-chained + `CapabilityInvoker` receipts
    - Test: `test_malicious_agent_audit_tamper_evident`

## Enforcement Points

| Invariant | Enforcement |
|---|---|
| 1,2 | `CapabilityInvoker` grant + manifest |
| 3 | `IntentManager.admit()` |
| 4 | `PolicyEngine` + `SecurityBoundary` |
| 5,6 | `CapabilityInvoker` verification strategies |
| 7 | `ProvenanceEngine` + labeling |
| 8 | `MemoryManager` scope isolation + provenance |
| 9 | `AuthorityManager.delegate_authority()` subset |
| 10 | `reevaluate_policy()` + autonomy bands |
| 11 | `AgentHypervisor.migrate_capsule()` pairing |
| 12 | `ExtensionSDK` manifest + signature |
| 13 | `SecurityBoundary.activate_emergency_stop()` |
| 14 | `AuditEngine` + `CapabilityInvoker` receipts |

## Enforcement Location

All invariants enforced **kernel-side** — never in renderer, CLI,
agent, model, tool, or remote node. The kernel is the trusted control
boundary.