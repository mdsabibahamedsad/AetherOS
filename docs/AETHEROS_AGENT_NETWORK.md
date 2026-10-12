# aetheros agent-network Network — User Guide

The Agent Network lets your AetherOS instance delegate tasks to other
agents over the open A2A protocol: independent AetherOS instances,
organization agents, and compatible third-party agents.

Rule zero: **a discovered agent is not a trusted agent.** Everything you
discover lands in the directory as UNTRUSTED until it is verified and
you (or your organization) explicitly approve it.

## Quick start (CLI)

```bash
aetheros agent-network discover https://research.example.com/
aetheros agent-network list
aetheros agent-network verify <agent-id>
aetheros agent-network trust <agent-id> --level user_trusted
aetheros agent-network connect <agent-id>        # live HTTPS probe, real latency
aetheros agent-network delegate <agent-id> "Summarize Q3 solar papers" \
  --permission research.search --permission research.fetch
aetheros agent-network tasks
aetheros agent-network doctor <agent-id>
```

Pairing (discover + persist) is `aetheros agent-network pair <url>`.
Serving this instance to others: `aetheros agent-network serve --pair-token <tok>`.

## Desktop

Open **Agent Network** (`/agent-network`) or the command palette:
`Agent: Discover`, `Agent: Network`, `Agent: Trusted`, `Agent: Connect`,
`Agent: Delegate`, `Agent: Tasks`, `Agent: Security`, `Agent: Trust Center`,
`Agent: Stop Remote Agents`. Sections: Network, Discover, Trusted, Local,
Organization, Remote, Tasks, Trust, Security, Activity.

## Trust levels

`unknown → discovered → unverified → verified → user_trusted →
organization_trusted → fully_trusted`, plus terminal `blocked` / `revoked`.
Skipping levels is rejected. Revocation is terminal and cancels the
agent's pending tasks. Reputation/history never upgrades trust by itself.

## What remote agents can and cannot do

Remote agents receive **capabilities, not access**: `research.search`,
`agent.task.submit`, scoped memory reads — each with risk, scope,
approval, expiration, and audit. They can never receive raw API keys,
passwords, cookies, refresh tokens, or private key material, and they
never gain direct shell, filesystem, browser, computer, memory, or MCP
access. Such requests arrive as capability requests evaluated by local
policy, executed locally after approval, with sanitized results.

## Data sharing

Outbound payloads are classified (`public → highly_sensitive`).
Secret-like content is blocked (or requires approval) at `private` and
above. Inbound artifacts are quarantined, hash-verified, and scanned;
executables and macro documents are held for review, never auto-executed.

## Development / LAN mode

Insecure transports are off by default and always visible:

```bash
export AETHEROS_AGENT_NETWORK_ALLOW_INSECURE=1  # plain http, dev only (logged)
export AETHEROS_AGENT_NETWORK_ALLOW_LAN=1       # permit private/LAN targets
```

## Files

State lives under `<AETHEROS_HOME>/agent_network/`:
`registry.json`, `trust.json`, `tasks.sqlite`, `audit.jsonl`, `server/`.
