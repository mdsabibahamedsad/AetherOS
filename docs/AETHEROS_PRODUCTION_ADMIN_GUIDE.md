# AetherOS Production Admin Guide (1.0 — pre-launch)

Deployment: only from a verified RC (rc-manifest) through update-release.yml;
verify digest match post-deploy (§165) before any traffic. Configuration
boundaries dev/beta/production are explicit — production never loads
.dev/.test/.mock/.local. Monitoring/alerting/incident roles per runbook;
backup integrity + restore drill REQUIRED before launch (currently BLOCKED).
Updates: stable channel only for prod users; staged 1→5→10→25→50→100 with
health gates; kill-switch/revoke paths fail-closed (proven). Rollback:
application/config/feature via previous-known-good; data via controlled
Master 61 procedure. Secrets live in the secret manager — never in git, logs,
artifacts, or bundles (scan clean 2026-09-12).
