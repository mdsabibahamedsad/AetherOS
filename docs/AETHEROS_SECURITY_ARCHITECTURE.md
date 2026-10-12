# AetherOS Security Architecture & Zero-Trust Map (Master Prompt 6)

## Architecture: identity → audit
HUMAN (operator, per-profile) → DEVICE (desktop host, main-process held)
→ SESSION (per-boot gateway token, drift-rejected; chat sessions with
explicit ids) → WORKSPACE (profile home isolation, per-profile sockets)
→ AGENT (goal/model/session-bound, no independent privilege) → TASK
(session/cron/action with owner) → PLAN → POLICY (approval gates) →
PERMISSION (server-side scopes) → CAPABILITY (registry-advisory,
backend-enforced) → TOOL → RESOURCE (scoped paths/domains) → ACTION →
OBSERVATION → VERIFICATION (tool signals) → ARTIFACT → AUDIT EVENT
(timeline, Security audit, run histories, stop legs).

## Trust boundaries (explicit)
1. User↔AetherOS: approval gates, YOLO explicitness, dismissal=refusal.
2. Renderer↔main: typed `invoke` IPC only; contextIsolation/sandbox/no-nodeIntegration/webSecurity verified in `main.cjs`.
3. Renderer↔gateway: per-boot session token, WS auth, reconnect hygiene.
4. Gateway↔workers: backend-owned execution, renderer never schedules.
5. AGI→tools: approval/policy/scope/risk gates; model output never authority.
6. Agent→user: session-keyed prompts, no cross-session leaks.
7. Plugin/MCP→core: untrusted-by-default, visible trust, scoped tools.
8. Browser→app: partitioned webview; site content untrusted; consequential submits confirm.
9. External content→system: data-only; never instructions.
10. Memory→context: retrieval never bypasses authorization; session vs saved separated.
11. Workspace↔services: per-profile homes/sockets; no cross-profile reads.
12. Host↔sandbox: backend workspaces/sandboxes; nothing weakened for UX.
13. Data↔telemetry: telemetry defaults OFF; drafts local-only; secrets masked.
14. Secrets↔processes: masked at rest, explicit reveal, redacted in errors.

## Zero-trust posture
Local, internal, authenticated, agent, MCP, plugin, or previously-approved
implies nothing. Every sensitive call re-evaluates identity + auth +
resource + action + scope + policy + context + risk. Least privilege,
deny-by-default at gates, short-lived session tokens, no inherited agent
privilege, no model-claimed authorization.

## Identity model
Human (operator/profile), device (host), session (chat id + gateway
token), agent (session-bound, attributed Human→Agent→Task→Tool→Resource→
Action), service/tool/plugin/workspace/task identities via backend
records. No generic "AI did something" — every row names the chain.

## Authorization
Server-side RBAC/ABAC/capability mix (toolsets, MCP scopes, A2A trust,
approval choices once/session/always/deny); renderer mirrors scope and
never decides. `confirmationForTier` documents the mirror law.

## Secrets, privacy, data
Masked at rest, explicit reveal, per-key scoping via settings; redaction
in error surfaces (new); drafts local-only (attachments memory-only);
telemetry off by default; retention/deletion/export via settings/memory
controls. Categories inventoried in §10 of the report.
