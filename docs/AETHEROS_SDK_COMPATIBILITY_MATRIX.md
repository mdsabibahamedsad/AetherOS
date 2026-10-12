# SDK Compatibility Matrix

Only configurations actually executed are marked tested (2026-09-09).

| Component | Version | Supported | Tested |
|---|---|---|---|
| AetherOS Runtime (platform API) | 1.0.0 (registry/schema) | yes | yes — 50 pytest contracts live over HTTP |
| Python SDK (`aetheros-sdk`) | 1.0.0 | yes | yes — sync+async+resources vs live gateway |
| TypeScript SDK (`@aetheros/sdk`) | 1.0.0 | yes | yes — `npm test` (unit + live E2E vs gateway :8765) |
| MCP | `mcp==1.26.0` (protocol 2025-11-25) | stdio tools/resources/prompts subset | yes — scaffold→list→call over real stdio |
| A2A | `0.3.0-compat` (built-in, no external SDK) | card/discovery/tasks/idempotency | yes — over real HTTP |
| Node.js | v25.5.0 | >=18 | yes (TS SDK) |
| Python | 3.12.13 (repo supports >=3.11,<3.14) | yes | yes |
| Windows | 10+ (nt) | yes | yes — full platform suite + benches |
| macOS | — | code is platform-safe (`pathlib`, no hard `C:\`/`/home/`) | NOT_TESTED (no runner) |
| Linux | — | same as above | NOT_TESTED (no runner) |
| Rust / Go SDKs | — | boundaries only (`aetheros_developer_platform` stubs are NOT SDKs) | NOT_TESTED — honestly unimplemented |

Notes: MCP 2026-07-28 (stateless core, Tasks, extensions) is BLOCKED on
the installed `mcp` package — not claimed. OAuth/OIDC/mTLS: NOT
implemented. Remote registry/signing enforcement: NOT implemented.
