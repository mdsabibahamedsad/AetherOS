# AetherOS Data Portability (§69-74)

Export `AetherOSExport {format_version, created_at, source_version,
schema_versions, manifest, data, artifacts, integrity}` via
`PortabilityManager.export` (explicit scope; secrets never included).
Portable project state uses logical references (`project://...`) resolved by
`PlatformStorageAdapter`; no hardcoded `C:\Users`, `/Users`, `/home` in
business logic. Private local state (credentials, caches, browser profiles,
OS integration, machine metadata, execution leases) is separated and never
exported.

Import safety (§71, §98): schema + integrity validation, provenance
inspection, conflict detection, classification, migration, policy
authorization (`authorize=True` required). Authority/credentials never
imported; tasks enter RECOVERED_PENDING_RECONCILIATION; archives are data
only — scripts/binaries/macros/plugin code never executed.
