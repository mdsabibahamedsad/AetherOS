# AetherOS Capsule Network

Implementation: `kernel/core/hypervisor/{types,guards,hypervisor}.py`,
`kernel/core/network_manager.py`.

## Policy model (§20)

```text
NO_NETWORK  → all network-touching invocations denied
LOCAL_ONLY  → loopback/local targets only
ALLOWLIST   → suffix-matched domains (+ TLS, kernel re-check)
PRIVATE_NETWORK → RFC-1918 permitted, still guarded
FULL_NETWORK → allowed but flagged HIGH RISK + audited per call
```

`FULL_NETWORK` is treated as high risk by the risk engine (+15) and each
call emits a security event — it is available, never silent.

## Pre-connection screening (§21)

`check_egress_url()` is a pure function (unit-tested with 13 SSRF
probes): metadata endpoints, localhost/private/loopback/link-local/
reserved literals, numeric-IP obfuscation (decimal, octal, hex, 32-bit
int forms), IPv6 sensitive ranges, scheme allowlist (http/https only),
embedded credentials, internal DNS suffixes. Hostnames that are not
literals return "resolution-time validation required" — connectors must
resolve, re-screen every IP, and pin, because static checks cannot defeat
DNS rebinding.

## Attribution (§22)

`_egress_log[capsule_id]` records capability, destination, allowed,
reason, timestamp for every network-touching call; `invoke()` additionally
consults the kernel NetworkManager (grant scopes, budgets, global rules)
so capsule policy and host policy both apply (defense in depth).

## A2A and MCP (§34–§35, Master 46)

Remote A2A agents are external principals: they cannot create privileged
local capsules, mount host paths, request unrestricted network, read
local secrets, or drive local devices without independent authorization —
migration to non-local nodes returns REQUIRES_CONFIGURATION unless paired.
MCP servers execute under the capsule's tool policy (`sandboxed`,
per-capability approval lists); a malicious MCP server receives only the
capsule's declared capabilities, never host credentials or kernel
authority.

## Communication (§75)

Draft/preview/send are separate capabilities; send-class capabilities are
external side effects (approval-gated, replay-blocked, risk-weighted).
