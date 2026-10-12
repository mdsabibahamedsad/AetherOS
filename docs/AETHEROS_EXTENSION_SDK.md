# Extension SDK

Two surfaces, different jobs:

1. **Installed extensions** (`sdk/` — plugin API, validator, packaging
   `.aep`, Ed25519/HMAC signing with real verification, permissions,
   lifecycle state machine with rollback, SemVer/version ranges,
   compatibility checks, sandboxed `ExtensionContext`, 8 scaffolds in
   `sdk/templates.py`). Tests: `tests/test_sdk.py` (30 tests).
2. **Developer packages** (`aetheros_platform/packages.py` — `.aether-agent`
   / `.aether-skill` / `.aether-tool` / `.aether-extension` / `.aether-mcp`
   zips with manifest/metadata/schemas/permissions/dependencies/
   provenance/version/compatibility; local/test registry with hash
   verification, rollback records, never-executes-on-install).

Extension manifest (`schemas.py::Extension`): name, semver version,
entrypoint, permissions, dependencies — plus migrations, uninstall,
rollback, and provenance in the package format.

Supply-chain rules: strict name/version identity (traversal rejected),
zip-slip guard on install, tamper → `SECURITY_VIOLATION`, registry
entries disclose `signature: none-available` + "listing never implies
safety". Remote registry and signature enforcement: UNAVAILABLE
(local/test only). Scaffold: `init extension`.
