# AetherOS Swarm — Security (Master 42)

## Model

Every agent: identity, least-privilege tools, permissions, scope
(project_id), tool policy, data policy. Enforced in
`aetheros_swarm/security.py::ToolAuthorizer` + orchestrator gates.

## Defenses (all tested)

- **Prompt injection across agents**: `scan_override_attempt` blocks
  "ignore the orchestrator…" style directives; blocked attempts audited
  (`override_attempt_blocked`). Agent output never becomes policy.
- **Privilege escalation**: agents cannot self-grant filesystem_write/
  terminal/email/deploy etc.; denials recorded (`authorizer.denials`).
- **Tool authorization**: every side-effecting call gated on
  (run, task, agent, tool, resource, policy); destructive tier forces an
  approval request first.
- **Data isolation**: project_id must match unless explicitly authorized
  (`check_data_isolation`); memory recall is task/project-scoped.
- **Secret isolation**: secret-shaped content refused in messages and
  context packages (`sanitize_for_agent` raises; quality_gate checks
  findings for secrets).
- **Approval fail-safe**: approval expiry resolves to denied; destructive
  tasks block without approval.
- **Audit**: append-only JSONL (`agent_spawned`, `task_result`,
  `override_attempt_blocked`, `run_completed`, …).

## Human-in-the-loop

ApprovalQueue payloads carry what/why/agent/data/risk; UI shows
approve/reject per request (`swarm.approve`, Swarm Center run tab).
Takeover ops: pause/resume/stop/stop-agent/replan/force-single —
all real backend operations.
