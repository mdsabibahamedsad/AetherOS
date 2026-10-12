# AetherOS Windows Background Runtime

Modes: DISABLED, START_ON_LOGIN, START_MINIMIZED,
BACKGROUND_AGENT_RUNTIME, FULL_UI_START (`desktop/startup.py`).
Mechanism: per-user HKCU Run key only — no Windows Service, no hidden
persistence, every registration audited (mode, mechanism, owner, time)
with repair/remove paths. Run values carry flags only (`--minimized`,
`--background`), never secrets.

Runtime contract: approved automations, scheduled tasks, agent-state
monitoring, notifications, durable-task recovery — under unchanged
Master 57/58/60/61 mediation (policy, scheduler, durable state). No
extra privileges, no arbitrary code, no silent dangerous actions.
Power behavior (AC/battery/sleep/resume, no duplicate or lost durable
jobs): UNVERIFIED live. Settings must show current mode, mechanism,
owner, and diagnostics from the capability registry.
