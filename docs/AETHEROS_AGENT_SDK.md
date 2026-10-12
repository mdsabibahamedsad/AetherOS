# Agent SDK

Manifest (`schemas.py::Agent`, `AgentManifest`): name (semver version),
description, capabilities (`area.action`, e.g. `artifact.create`),
inputs/outputs, tools, skills, models, memory/artifact/network/
filesystem/data/approval policies, resourceLimits, tenant.

Lifecycle (`agents.py::TRANSITIONS`) — enforced, illegal transitions
raise `CONFLICT`:

```
REGISTERED → CREATED → READY → RUNNING → WAITING | PAUSED
  → COMPLETED | FAILED | CANCELLED (+ QUARANTINED → TERMINATED/READY)
```

`register()` validates the manifest, persists idempotently
(`name:version`), and walks `REGISTERED→CREATED→READY`.
`run_task()` executes Intent→policy→capability→tool with least-privilege
delegation (tool runs with agent∩tool capabilities only) and returns the
agent to `READY` (or `FAILED`). `quarantine()` removes an agent from
scheduling. Malformed capabilities (`no dot`) and bad names/versions are
rejected with `INVALID_SCHEMA` (422).

Python: `Client.create_agent(manifest)` / `create_task(agent_id, input)`
/ `get_task` / `cancel_task`. TypeScript: same surface on `Client`.
Example: `aetheros_platform/examples/hello_agent.py` (executed in CI).
Scaffold: `python -m aetheros_platform.cli init agent <name>`.
