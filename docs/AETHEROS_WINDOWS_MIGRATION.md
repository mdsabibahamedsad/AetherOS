# AetherOS Windows Migration (Hermes → AetherOS)

Sources: `%LOCALAPPDATA%\hermes`, `%APPDATA%\hermes`, `HERMES_HOME` env,
old startup/scheduled-task/protocol/shortcut registrations. The backend
reads `HERMES_HOME` ONLY as a deprecated fallback with a warning
(`aetheros_constants.py`); canonical home is `%LOCALAPPDATA%\aetheros`.

Policy (idempotent, safe): detect → report plan → copy (never move)
→ verify → preserve permissions/timestamps → never overwrite newer
AetherOS state → keep rollback copy → mark complete with audit event.
Nothing migrates silently and nothing deletes legacy data. No automated
migration runner ships yet —until it does, migration is manual following
this policy, and the installer must not remove legacy state.
