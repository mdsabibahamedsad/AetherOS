# Master 62 — Performance Report (2026-09-09)

Tool: `python -m aetheros_platform.bench` (in-process + loopback HTTP).
Env: Windows (nt), Python 3.12.13, run at 2026-09-09T13:54:31Z.
HTTP bench is sized under enforced rate-limit bursts so it measures
latency, not the limiter (limiter proven separately by
`test_rate_limit_enforced`: 80-burst trips 60-bucket with structured 429).

| metric | value |
|---|---|
| sdk_import_ms | 313.0 |
| cli_startup_ms | 106.7 |
| schema_validate_ms_per_op | 5.4862 |
| tool_invoke_ms_p50 | 0.523 |
| tool_invoke_ms_p95 | 0.645 |
| package_build_ms | 51.0 |
| http_health_ms_p50 | 1.01 |
| http_health_ms_p95 | 1.99 |
| http_task_create_ms_p50 | 198.65 |
| http_task_create_ms_p95 | 201.94 |
| concurrent_tasks (4 threads) | 4/4 ok, wall 799.7ms |

Notes: `http_task_create` (~200ms) covers auth+scope+policy+audit+
SQLite transitions+tool invoke over loopback — acceptable for a
governed path; no optimization claimed beyond measurement. macOS/Linux
numbers: NOT measured (no runners) — not invented. Bottleneck watch:
`schema_validate` (~5.5ms, `jsonschema` Draft 2020-12) dominates manifest
registration; catalog caching (§67) applies to Agent Cards/tool lists
with freshness + auth-validity respected.
