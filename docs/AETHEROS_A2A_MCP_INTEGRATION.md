# A2A × MCP Integration (Master 46)

A2A and MCP are complementary, disjoint layers:

- **A2A** (`aetheros_network/`): which *agent* to talk to, how to trust
  it, how to delegate, how to verify results.
- **MCP** (`tools/registry.py`, `toolsets.py`): which *tools/data* the
  **local** agent may use.

## The only legal crossing

```
remote agent --(capability request)--> AetherOS policy
  --> approval if needed --> LOCAL MCP execution
    --> sanitized result --> A2A response
```

Concretely: a remote `mcp.request` / `browser.request` /
`computer.request` permission is evaluated by `authorize_action`
(high/critical risk, always-approval, high minimum trust), executed by
the existing local tool stack (`ComputerControlEngine`, browser infra,
toolsets) — never by the remote principal directly — and the result is
redacted/summarized before crossing back. Remote agents cannot enumerate
local MCP servers; no server list is ever sent. Tested: `mcp.request`
without grant is denied; `shell.execute`/`secrets.read` are denied at
every trust level.

## What we do NOT do

- Convert MCP servers into A2A agents (or vice versa).
- Duplicate MCP capability inside the A2A layer.
- Bypass MCP security, swarm controls, automation autonomy caps,
  extension permissions, or model/provider policies for remote work:
  Master 43 delegation inherits autonomy level (remote cannot elevate
  it); Master 42 swarms include remotes only within task/memory/
  permission/budget scope; Master 45 routing treats the remote as an
  independent security boundary.
