# AetherOS Cross-Platform API Contract

Audience: any client surface (Windows/macOS/Linux desktop, Linux packages,
iOS app, scripts) that talks to an AetherOS backend.

Rule zero: **clients reuse the existing backend transports. No new backend,
no forked protocol.** What is documented here already exists in
`gateway/platforms/api_server.py` (network) and `tui_gateway/server.py`
(local stdio).

---

## 1. Transports

| Transport | Where | Auth | Used by |
|---|---|---|---|
| REST + SSE over HTTP(S), versioned `/v1/*` + `/api/*` | gateway `api_server` platform (`gateway/platforms/api_server.py`) | `Authorization: Bearer <API_SERVER_KEY>` (constant-time compare) | iOS app, remote clients, dashboards |
| JSON-RPC over stdio (newline-delimited) | `tui_gateway/server.py` | same-process trust; NOT network-exposed | Ink TUI, embedded desktop surfaces |

iOS NEVER speaks stdio JSON-RPC and NEVER connects to a user's machine
directly except through the api_server contract.

## 2. Versioning policy

- Network routes are path-versioned (`/v1/...`). Additive changes (new
  optional fields, new endpoints, new event names) do NOT bump the version.
- Breaking changes require `/v2/...` to be added alongside `/v1/...` for at
  least one release cycle. Existing clients must keep working.
- Clients MUST discover optional surface via `GET /v1/capabilities` instead
  of hard-coding feature presence (see §4).
- The local stdio JSON-RPC follows the same rule: new methods are additive;
  unknown methods return `-32601` so old clients degrade gracefully.
- Deprecation: endpoints/features are marked in `capabilities.features`
  (e.g. `"audio_api": false`) before removal; removal happens only in a new
  major path version.

## 3. Authentication & session continuity

- Every protected route requires the bearer token issued by the operator
  (`API_SERVER_KEY`). 401 with `_openai_error(...)` shape on failure.
- Session continuity headers:
  - `X-Aetheros-Session-Id` — continue an existing session.
  - `X-Aetheros-Session-Key` — scope memory/session keys; requires API-key
    auth (never accepted from unauthenticated callers).
- Tokens are secrets. They live in iOS Keychain / OS keyring on desktop;
  they are never logged (server audit logging redacts them) and never
  embedded in notification payloads or deep links.

### Mobile hardening requirements (iOS)

Short-lived access tokens + rotation REQUIRE server support that does not
exist yet in `api_server.py`; until that lands, iOS uses the single operator
bearer token scoped per-server and treats it as a long-lived secret in
Keychain. This is recorded honestly as a gap in
`docs/AETHEROS_PLATFORM_SECURITY.md`, not papered over.

## 4. Capability discovery

`GET /v1/capabilities` → self-describing contract:

```json
{
  "object": "aetheros.api_server.capabilities",
  "auth": { "type": "bearer", "required": true },
  "runtime": { "mode": "server_agent", "tool_execution": "server" },
  "features": {
    "chat_completions_streaming": true,
    "run_submission": true,
    "run_events_sse": true,
    "run_approval_response": true,
    "session_chat_streaming": true,
    "memory_write_api": false,
    "...": "..."
  },
  "endpoints": { "models": {"method": "GET", "path": "/v1/models"}, "...": "..." }
}
```

Clients render/hide features strictly by this document plus the platform
capability table (`docs/AETHEROS_PLATFORM_ARCHITECTURE.md` §6).

## 5. Core resource contracts

All error bodies use the OpenAI-style envelope produced by `_openai_error`:

```json
{ "error": { "message": "...", "type": "invalid_request_error", "param": null, "code": "run_not_found" } }
```

### Sessions (`/api/sessions`)
- `GET /api/sessions` — list; `POST` — create.
- `GET/PATCH/DELETE /api/sessions/{id}` — inspect/rename-patch/delete.
- `GET /api/sessions/{id}/messages` — transcript.
- `POST /api/sessions/{id}/fork` — branch a session.
- `POST /api/sessions/{id}/chat` — synchronous turn.
- `POST /api/sessions/{id}/chat/stream` — SSE turn
  (`text/event-stream`; `event: <name>\ndata: <json>\n\n` frames).

### Runs (task execution + approvals)
- `POST /v1/runs` — submit a run.
- `GET /v1/runs/{run_id}` — status.
- `GET /v1/runs/{run_id}/events` — SSE event stream (tool progress,
  approval requests, completion).
- `POST /v1/runs/{run_id}/approval` — resolve a pending approval.
  Body: `{"choice": "once" | "session" | "always" | "deny"}`
  (`approve/approved/allow` normalize to `once`). Errors:
  `run_not_found` (404), `approval_not_active` (409),
  `invalid_approval_choice` (400).
- `POST /v1/runs/{run_id}/stop` — cooperative stop.

**Confirmation invariant:** an approval chosen on ANY client only resolves a
pending approval created by the SERVER-side agent policy. The mobile client
cannot create, widen, or pre-authorize permissions; risk classification and
scope remain backend-owned.

### Jobs (scheduled work)
`GET/POST /api/jobs`, `GET/PATCH/DELETE /api/jobs/{id}`,
`POST /api/jobs/{id}/pause|resume|run`. These are admin-flavored; exposure is
gated by the api_server config exactly as today.

### Model/chat compatibility surface
- `GET /v1/models`, `GET /v1/skills`, `GET /v1/toolsets`.
- `POST /v1/chat/completions` (+stream) and `POST /v1/responses`
  (+GET/DELETE) — OpenAI-compatible shapes for generic clients.

### Health
`GET /health` (unauthenticated, liveness), `GET /health/detailed`
(unauthenticated, no `/proc` dependency).

## 6. Offline / retry semantics (clients)

- Requests that create resources SHOULD carry a client-generated idempotency
  key where the endpoint accepts one; otherwise clients deduplicate locally
  by request ID before retrying.
- Client states shown to users MUST map to reality: `offline`, `pending`,
  `retrying`, `failed`, `succeeded`. A client never renders success without
  a server acknowledgment.
- Retries: exponential backoff with jitter; never retry 4xx validation
  errors; retry 5xx/network/timeouts bounded.
- SSE consumers reconnect with last-event resync where the endpoint provides
  it; otherwise re-fetch run status after reconnect.

## 7. Notification payloads (planned for APNs bridge)

Only content-safe fields: run id, job name, event kind
(`approval_required | task_completed | task_failed | security_event |
attention_required`). No secrets, tokens, message bodies, or file contents.
The device fetches details over authenticated TLS on tap-through.

## 8. Deep links

Desktop registers `aetheros://` (validated, malformed URLs dropped,
single-instance delivery — see `main.cjs:5849+`). iOS registers the same
scheme for its own app-scoped links (task/approval/session). Rules:

- Deep links may carry ONLY non-privileged navigation parameters.
- Incoming parameters are validated and length-capped; unknown hosts are
  ignored.
- Privileged actions (approvals) always re-authenticate in-app; a link can
  navigate to a confirmation screen but can never itself approve anything.

## 9. Local desktop IPC boundary (for completeness)

Electron renderer ↔ main communication goes exclusively through
`preload.cjs` contextBridge APIs under `aetheros:*` channels; webSecurity,
CSP, navigation guards, and permission handlers are enforced in
`electron/hardening.cjs` and covered by `electron/hardening.test.cjs`. The
same boundaries apply identically on Linux builds — no platform weakens them
(verified by the shared test suite running cross-platform in CI).
