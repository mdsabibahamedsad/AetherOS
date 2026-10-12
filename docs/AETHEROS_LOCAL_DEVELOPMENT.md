# Local Development

```bash
export PYTHONPATH=$PWD            # repo root (examples + SDKs resolve)
export AETHEROS_HOME=$PWD/.dev-home   # isolated state; NEVER production
python -m aetheros_platform.cli auth key-create --name dev \
  --scopes agents:write,tasks:write,tasks:read --owner me
python -m aetheros_platform.cli dev --port 8765   # LOCAL DEVELOPMENT ONLY
python -m aetheros_platform.cli init agent my-agent --dest .
python -m aetheros_platform.cli test --project my-agent
```

The local runtime provides: API server, agent runtime, in-process tools,
MCP stdio servers, A2A reference agent, labeled mock models
(`MockProvider` — outputs carry `[MOCK/SIMULATED/DEVELOPMENT ONLY]`,
never masquerade), isolated storage/secrets, SSE event stream, logs,
traces. Local development never silently connects to production:
state is HOME-anchored and the server binds loopback by default.

Sandbox vs production: `DevSandbox` = development only (filesystem
isolation, network policy flag, timeouts, cancellation). Production
runtime requires the gateway + policy + audit path; there is no
`--production` bypass.

IDE integration: project discovery via `init` scaffolds, logs/traces
via events + audit, schemas via `/api/v1/schemas`, generated TS types
via `cli schema --ts`. No deep VS Code/JetBrains plugins are claimed.
