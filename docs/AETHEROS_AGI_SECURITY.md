# AGI Security Review (Master Prompt 4)

Verified this pass; enforcement is server-side (gateway owns config, env,
permissions, execution). The renderer cannot bypass authorization — every
mutation is a gateway RPC the backend re-checks.

- Secrets: masked (`redacted_value`) by default; reveal is an explicit
  per-key user click (`revealEnvVar`); delete requires `window.confirm`.
  No keys/tokens/passwords render unprompted; none in logs/notifications.
- Destructive actions: strong confirmation (confirm-dialog, tiered
  `confirmationForTier`); dangerous tools gate on approval policy with
  scope shown; YOLO bypass is explicit, visible (statusbar), reversible.
- Task/agent/tool scope: session-keyed prompts (no cross-session leaks);
  interrupt/resume target explicit session ids; STOP ALL enumerates live
  sessions and reports per-leg results.
- Audit trail: execution timeline (task/action/tool/timestamp/result),
  approvals history in Security, per-leg stop reporting. No private
  reasoning is logged or displayed anywhere in the new surfaces.
- Sandbox boundaries: terminal sandboxing, workspace-only file scope,
  MCP/A2A trust states are shown where the backend reports them; unknown
  renders as Unknown, never as safe.
- Hermes cleanup: zero user-facing Hermes strings in agent/AGI surfaces
  (agents, agent-hub, swarm-center verified); technical identifiers
  (`hermes.ts`, env vars) preserved for compatibility.
- No new network, storage, IPC, or credential surface was added by this
  phase (pure derivation + existing RPCs).
