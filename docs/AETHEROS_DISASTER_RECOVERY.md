# AetherOS Disaster Recovery (§49-50, §89)

## Procedures (Detection → Containment → Recovery → Verification → Post-audit)

- DB corruption: integrity_check fails → contain (stop writers) → restore
  latest verified backup to a scratch HOME → integrity + app start + task/
  memory/audit checks → cut over. Evidence preserved (corrupt file kept).
- Deleted project: selective restore of task/artifact/configuration prefixes.
- Machine replacement: FULL backup → clean install → restore → re-issue
  authority per device (grants never carry over as valid automatically).
- Broken migration: migration lock owner record + preserved pre-migration
  safety snapshot → restore → report exact error; never delete/recreate blindly.
- Corrupted backup: verify fails → fall back to previous registry entry.
- Credential loss: re-issue; backups exclude secrets by default so there is
  nothing to "recover" from them (by design).
- Device loss: revoke device trust, rotate backup keys, restore to new device.

## Drills DR-01..DR-08

Reproducible via `tests/aetheros_data/test_backup_restore.py` (corruption, deletion,
migration breakage, corrupted backup, sync conflict, revoked device) plus
`test_failure_injection.py`. Outcomes recorded in the completion report.

## RPO / RTO (§50)

Targets are measured, not chosen: see completion report §RPO/§RTO with
TARGET / ACTUAL / ENVIRONMENT / LIMITATION. Snapshot cost scales with DB
size; restore cost scales with archive size (benchmarks in tests).
