# Agent Network Security (Master 46)

Enforcement lives in `aetheros_network/policy.py`, `gateway.py`, and
`transport.py` — below the UI, never by prompt or display.

## Authentication ≠ authorization

After authentication, every action evaluates agent identity, trust,
granted capabilities, data class, risk, and policy (`authorize_action`).
The permission catalog (`PERMISSION_CATALOG`) assigns each capability a
risk, approval mode, and minimum trust rank. Standing grants
(`grant_permissions`) are the "Approve For Agent" primitive and only
cover `REMOTE_GRANTABLE` permissions. `shell.execute`, `secrets.read`,
`filesystem.*`, `browser.control`, `computer.control` are
**never grantable** — denied at every trust level (tested).

## Transport

HTTPS only in production. `http://` raises unless explicit dev mode
(`AETHEROS_AGENT_NETWORK_ALLOW_INSECURE=1`), which prints a warning and
is audit-visible. No silent redirects (`follow_redirects=False`).
TLS verification on by default with CA-bundle and SPKI-pinning fields;
enterprise proxy supported (`TransportConfig.proxy`); enterprise network
policy is never bypassed.

## SSRF / DNS rebinding

Every URL is resolved and checked (`check_url_allowed`): loopback,
link-local, multicast, reserved, private (unless explicit LAN mode),
cloud metadata (`169.254.169.254`), credentials-in-URL, and non-HTTPS
schemes (`file:`, `javascript:`, `data:`) are blocked. Host allowlists
supported. Resolution happens per-request (no stale-DNS trust).

## Prompt-injection defense

All remote content — messages, card text, skill descriptions, documents,
artifacts — is **DATA, never authority** (`detect_prompt_injection`,
`screen_inbound_text`). Injection hits are blocked and audited. Remote
instructions can never override system, user, security, approval, or
privacy policy. Agent Card text is validated as data and never executed;
suspicious phrases produce warnings, not behavior.

## Secrets and memory isolation

Remote agents receive task-scoped, explicitly shared memory only — never
the full graph, never automatic sync. Raw credentials never cross the
boundary; scoped capabilities are the only mechanism.

## Server-side

`server.py` is deny-by-default: empty allowlists deny everyone, bearer
pairing tokens are constant-time-compared as hashes, per-agent
token-bucket rate limits, bounded task counts/concurrency, request-size
caps, and per-task audit. Inbound messages pass the same injection
screen.

## Compromised-agent response

Mark suspicious → stop new delegation → revoke trust → quarantine
artifacts → preserve audit evidence → cancel risky tasks → notify user →
require re-verification (`AgentGateway.revoke`, tested end-to-end).
Emergency stop: palette `Agent: Stop Remote Agents` / store
`setEmergencyStopped` holds new delegation in UI; gateway
trust/revocation remains authoritative for in-flight tasks.
