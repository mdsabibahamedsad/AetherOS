# Tool SDK

Definition (`schemas.py::Tool`, `ToolManifest`): identity, version,
description, inputSchema/outputSchema, capabilities, riskLevel
(LOW/MEDIUM/HIGH/CRITICAL), sideEffects, idempotency, safety flags
(reads/writes/deletes data, sends messages, executes code, network,
credentials, external modification, financial/legal/physical,
reversible, idempotent), timeoutSeconds, resourceLimits, auditPolicy.

Execution pipeline (`tools.py::invoke`): schema validation → excess-grant
denial → per-capability policy (`require_allowed`; HIGH/CRITICAL need
approval) → rate limit + concurrency cap → idempotency → deadline-bounded
run (sync thread / async with timeout) → audit.

Safety rules:

- Sync, async, long-running (deadline), approval-gated, and
  artifact-producing tools supported; streaming surfaces via the event
  feed. Human approval stays possible for risky calls.
- Caller grants must be a subset of the tool's declared capabilities.
  Extra grants → `CAPABILITY_NOT_GRANTED` (never laundered).
- Tool output is untrusted data, never authority.
- Server-side code upload is disabled (`POST /api/v1/tools` → 403 after
  validating the manifest). Register tools in-process via the SDK.

Example: `aetheros_platform/examples/tool_agent.py` (executed in CI).
Scaffold: `python -m aetheros_platform.cli init tool <name>`.
