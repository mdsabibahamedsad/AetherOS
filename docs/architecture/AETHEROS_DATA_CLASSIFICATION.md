# AetherOS Data Classification

Source: `kernel/core/types.py` (`DataClassification`), `kernel/core/policy_engine.py`,
`kernel/core/security_boundary.py`, `kernel/core/network_manager.py`.

## Classification Hierarchy

```
PUBLIC < INTERNAL < PRIVATE < CONFIDENTIAL < SECRET < HIGHLY_SENSITIVE
```

## Usage

| Classification | Use Case | Flow Policy |
|---|---|---|
| `PUBLIC` | Public docs, open APIs | Any → Any |
| `INTERNAL` | Org-internal docs | Internal+ → Internal+ |
| `PRIVATE` | User personal data | Private+ → Private+ |
| `CONFIDENTIAL` | Business confidential | Confidential+ → Confidential+ |
| `SECRET` | API keys, tokens, PII | Secret+ → Secret+ |
| `HIGHLY_SENSITIVE` | Crypto keys, biometrics | Secret+ only |

## Enforcement

- `PolicyEngine.check_data_flow(src, dst)` → `DENY` if `src > dst`
- `SecurityBoundary._check_information_flow()` blocks egress of
  `SECRET/HIGHLY_SENSITIVE` without explicit `sensitive_data_access`
  capability in grant
- `NetworkManager` re-checks URL against grant `network_scopes`
- Screen data redaction (`redact_screen_text`) strips passwords,
  cards, keys before model input
- `SecretBroker` — raw secrets never in env/context; broker-mediated

## Provenance + Classification

Every memory write carries `classification`. Research downloads enter
as `WEB_DERIVED` (untrusted) before analysis. Explicit user data is
`USER_PROVIDED`. Model inferences are `MODEL_GENERATED` (never
authoritative).

## Scope

- Kernel namespaces (`agent:<id>:scope`) inherit agent's clearance
- Memory 2.0 `RecordScope` + `Sensitivity` (INTERNAL/SENSITIVE/SECRET)
- `SecretBroker` bindings carry classification