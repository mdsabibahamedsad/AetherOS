# AetherOS Restore Architecture (§45-48, §91-94)

Modes: FULL_RESTORE, SELECTIVE_RESTORE (per-domain prefixes). POINT_IN_TIME =
pick the backup by `created_at`. DISASTER_RECOVERY = procedure doc, not a
button.

Safety flow (§46): VALIDATE (verify) → PREVIEW → SAFETY SNAPSHOT (live state
backed up first) → RESTORE → MIGRATE (engine init) → INTEGRITY CHECK →
RECONCILE (UNKNOWN side effects → RECOVERED_PENDING_RECONCILIATION) → VERIFY.
Restore requires explicit confirmation (`assume_yes=True` / `--yes`); the
API raises `PermissionError` otherwise.

Preview (§47): records/files/tasks/memory/config/authority affected,
conflicts, schema delta, warnings.

Selective (§48): restore `task`, `memory`, `artifact`, `configuration`
prefixes without touching unrelated state.

Authority (§91): expired/revoked grants are never reactivated.
Tasks (§92): uncertain ⇒ RECOVERED_PENDING_RECONCILIATION, no auto-continue.
Memory (§93): provenance/version/trust/sensitivity preserved; imported old
memory stays CANDIDATE, never auto-current. Artifacts (§94): bytes re-hashed
before acceptance.
