# AetherOS Human–Agent Interaction

How humans and autonomous agents understand, supervise, delegate, inspect,
interrupt, approve, and collaborate — as implemented in the desktop shell.

## 1. Dual interface model (§3)

Human ↕ Interface ↕ Agent Runtime ↕ Capabilities. The interface is
simultaneously human-readable and agent-readable: stable identifiers
(`canonicalNavEntry` ids), semantic roles/labels, explicit component
states (default/hover/focus/active/disabled/loading/success/warning/
error/offline/permission-denied/approval-required) — not styling alone.

## 2. Agent lifecycle visibility (§12–§15)

Authoritative statuses: Idle, Planning, Running, Waiting, Awaiting
Approval, Paused, Recovering, Completed, Failed, Quarantined, Offline —
always from runtime state. Live view shows goal, current step, plan
progress, current tool/observation, next action, risk, approval state,
elapsed time, tokens, model. Plan visualization supports expand/collapse,
status, retry, inspect, pause, and failure reasons; skip/edit only where
the runtime honors them.

## 3. Tasks as first-class objects (§16–§18)

Intent → plan → execution → events → approvals → tools/models/memory →
artifacts → errors/recovery → audit. The execution timeline renders real
events only. Long-horizon tasks show started/elapsed/phase/remaining/
budget/approvals/errors; ETA appears only when computed from real data.

## 4. Approvals as a security surface (§22–§23)

Each request shows action, agent, capability, target, data, risk, reason,
scope, reversibility, policy, expiration. Choices: Approve Once / for Task
/ for Session / Deny / Edit Scope — risky actions never default to
approve. Parked gateway prompts (`$allApprovalRequests`, session-keyed)
feed both the overlay and the Security center; Home surfaces them with a
Review action.

## 5. Autonomy control (§24–§25)

Levels 0–5 (Suggest → Ask Before Actions → Approve Risky → Supervised →
High → Policy-Bounded), each mapped to real policy behavior with an
explanation of what runs automatically, what needs approval, what is
blocked, and what data/systems are reachable. The control is never
decorative. YOLO bypass paths (`yolo-session.ts`) stay explicit and
session-scoped unless the user opts into global.

## 6. Collaboration and takeover (§54–§55, §121, §126)

Chat + live workspace split: conversation beside observable work (sources,
evidence, artifacts). Delegation states who receives what, why, what data
is shared, and what is withheld (credentials, private memory, unrelated
files). Takeover triggers (CAPTCHA, login, ambiguity, sensitive or
physical-world action, policy boundary) show Human Takeover Required with
Take Control / Continue / Cancel — never faked.

## 7. Recovery and failure (§133–§135)

Checkpoints name the last confirmed state and unknown external outcomes,
then offer reconcile. Failures state cause + recovery path (e.g. session
expired → re-authenticate → retry/stop). Recovery complexity is not
hidden when it affects decisions.

## 8. Memory the user controls (§32–§33)

Saved, conversation-derived, project, and research memory with source,
timestamps, confidence, scope, rationale, and references. Inspect, edit,
delete, retract, forget, disable, scope. Provenance everywhere.

## 9. Research integrity (§29–§31)

Goal, plan, sources, evidence, claims, contradictions, confidence,
citations, artifacts. Each source shows title/domain/published/updated/
retrieved/authority/independence; contradictions and confidence are
visible. No fake metadata — the knowledge view's mock layer is a
documented gap, not a pattern to copy.

## 10. Research grounding (2026 literature, per brief §150)

Design decisions align with recent HAI findings: semantic transparency
and state observability over human-only visuals; explainability + user
control + mental models as the core computer-use UX dimensions;
oversight timing that trades safety against burden; reversibility where
possible; resistance to manipulative interfaces (our own UI included).
See `AETHEROS_MASTER_63_UX_RESEARCH.md`.
