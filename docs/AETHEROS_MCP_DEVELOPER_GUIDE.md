# MCP Developer Guide

Boundary: MCP = agent-to-tool/data/resource integration (A2A is for
agent-to-agent). Implemented against the protocol the environment
provides: **`mcp==1.26.0` (2025-11-25)**. The 2026-07-28 features
(stateless core, cacheable lists, Tasks, extensions) are NOT claimed —
see the compatibility matrix.

## What works (proven by `test_mcp_a2a.py` over real stdio)

- `aetheros_platform/mcp.py`: `mcp_init` scaffold (server.py, manifest,
  README, test), `validate_server_manifest`, `list_tools_stdio`,
  `call_tool_stdio` with structured input/output schemas, error shape
  (`isError` + content), audit on invocation.
- CLI: `init mcp`, plus `dev`/`test`/`validate`/`package` flows through
  the platform CLI + local registry publish.
- Trust: `is_trusted()` defaults False; MCP tool metadata stays
  untrusted unless the server is explicitly trusted; risky calls still
  route through policy/approval.

## Workflow

```bash
export PYTHONPATH=$PWD
python -m aetheros_platform.cli init mcp my-server --dest .
python -m aetheros_platform.cli test --project my-server
python -m aetheros_platform.cli package build --project my-server
```

Example: `aetheros_platform/examples/mcp_server.py` (scaffold → stdio
list → call, executed in CI). Human control: tool exposure and every
invocation are visible in events/audit; approval gates apply per tool
risk.
