# Exact failed gate

A01 RELEASE_SOURCE_NOT_CLEAN: `git status --porcelain=v1` = 2786 non-empty lines.
Per §79: STOP before npm ci / build / CI / installer. No guard weakened (§86/§87:
zero changes to release-config/guards/preflight/validator/orchestrator; zero
SKIP/FORCE/ALLOW_DIRTY flags added anywhere).
Result: WINDOWS_RC_BLOCKED. Historical hashes remain HISTORICAL (§85).
