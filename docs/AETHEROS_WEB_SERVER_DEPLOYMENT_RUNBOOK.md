# AetherOS Web+Server Deployment Runbook

Environments: dev (loopback) → staging → production. Per env:
secrets (manager/env, never repo), origins allowlist, DB path/backups,
auth mode, model config. Deploy: build web → migrate (expand/contract)
→ health/live+ready → drain + rolling restart → verify (health,
auth smoke, task submit, SSE stream, artifact fetch) → rollback plan
(previous artifacts + migration-compat note). Rollback: web/API/workers
revert; DB via compatible migrations only (no destructive rollback).
Zero-downtime: claimed ONLY with rolling + compatible migrations +
verified probes — otherwise scheduled window. TLS/DNS/provisioning per
target env (BLOCKED here — no cloud executed).
