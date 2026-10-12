# API Versioning

- URL versioning: `/api/v1/...`. `REGISTRY_VERSION` (`registry.py`) and
  `SCHEMA_VERSION` (`schemas.py`) are both `1.0.0`.
- `/api/v2` serves as an alias of v1 today (response headers
  `X-API-Version: v2-alias-of-v1`, `Sunset: not-planned`; see
  `V2_ALIAS`). New clients use v1.
- Compatibility contract (tested in `test_gateway_e2e.py` + SDK
  contracts): response headers `x-request-id`, `x-trace-id`,
  `x-api-version` on every response.
- Deprecation policy: breaking changes require a new registry version,
  `deprecated`/`sunset` metadata on the endpoint entry, a migration
  guide, and a minimum 6-month sunset. No silent breaks.
- Schema evolution: additive fields only on PUBLIC schemas; generated
  bindings (`tsgen.py`) keep old clients compiling.
- SDK compatibility matrix: `AETHEROS_SDK_COMPATIBILITY_MATRIX.md`
  (only configurations actually executed are marked tested).
