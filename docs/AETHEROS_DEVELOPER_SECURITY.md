# Developer Security Model

## Error model (`errors.py::AetherError`)

`code · message · category · retryable · severity · requestId · traceId
· taskId · capability · policyDecision · remediation · metadata`.
No secrets, filesystem internals, credentials, or stack traces leak
(fuzz-asserted: no `traceback`, no `aek_` in error bodies).

Categories → HTTP: AUTHENTICATION_REQUIRED 401 · AUTHORIZATION_DENIED /
POLICY_DENIED / APPROVAL_REQUIRED 403 · INVALID_REQUEST 400 ·
INVALID_SCHEMA 422 · RATE_LIMITED / QUOTA_EXCEEDED 429 ·
RESOURCE/MODEL/TOOL/AGENT_UNAVAILABLE 503 · TIMEOUT 504 · CONFLICT /
IDEMPOTENCY_CONFLICT 409 · NETWORK_ERROR 502 · STORAGE_ERROR /
INTERNAL_ERROR 500 · SECURITY_VIOLATION / SANDBOX_VIOLATION /
DATA_EXFILTRATION_BLOCKED / CAPABILITY_NOT_GRANTED 403 ·
PROMPT_INJECTION_DETECTED / UNSUPPORTED_VERSION 400 · DEPRECATED_API 410.

## Rate limiting & quotas (`ratelimit.py`)

Per-(layer, identity, endpoint) token buckets: standard 60/s-burst,
agent 20, task 30, tool-invoke 10, memory 60 — plus
`MAX_CONCURRENT_TOOL=4`. 429s carry `retry_after` + `limit`.
Quotas integrate at the runtime layer (CPU/mem/disk/network/tokens/
tool calls/browser actions/automation runs/concurrent agents/storage/
API requests are tracked in `USAGE` ledger; monetary cost stays `None`
without a rate card — never fabricated).

## Webhooks (`events.py`)

HMAC-SHA256 signatures, timestamps, 5-minute replay window, endpoint
secrets, delivery IDs, filtered events, exp-backoff retry, dead-letter,
disable/re-enable, delivery history. SDK `verify_webhook()` helper.
Secrets never enter payloads; `redact()` scrubs logs/audit.

## Injection & supply chain

Tool/MCP/Agent-Card/skill metadata is untrusted: prompt-injection
probes are denied by policy (`test_prompt_injection_metadata...`),
poisoned cards never auto-trust, malicious manifests → 422, package
tamper/traversal/zip-slip → refusal. Secrets: env/credential-manager/
`cred://` references only — never hardcoded, logged, or memorized.
Sandbox: dev execution is isolated (scrubbed env, timeouts, labeled
`development`); production isolation (containers) is UNAVAILABLE —
do not run untrusted code outside the dev sandbox.

## Security center data

API keys, scopes, agent/tool/extension permissions, MCP/A2A trust sets,
package provenance, recent denials — all queryable via API/CLI
(`auth key-list`, `api list`, audit log); a graphical center is not
shipped (console: EXPERIMENTAL).
