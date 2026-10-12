# AetherOS Master 63 — UX Research Grounding

Why the Master 63 decisions are shaped the way they are. This note maps
the brief's required dimensions to concrete implementation choices. It
does not reproduce papers; it records the design stance taken.

## 1. Computer-use agent UX: explainability, control, mental models

Recent work identifies user prompts, explainability, user control, and
mental models as the major dimensions of computer-use-agent UX. Applied:

- Explainability → safe execution summaries and observable actions
  (goal/step/tool/observation/next-action), never hidden chain-of-thought
  (§14, §21). Computer view keeps its action-history/current-action/
  confidence/permission/takeover structure; its fabricated indicators are
  flagged, not shipped.
- Control → Inspect/Pause/Stop/Take Control on every live surface; STOP
  ALL with per-leg reporting (§56).
- Mental models → exact vocabulary everywhere (Agent ≠ Model, Tool ≠
  Skill ≠ Automation, Memory ≠ State, Backup ≠ Sync) (§171–§175).

## 2. Oversight timing: safety vs burden

CHI 2026 work on when users should check multi-step agent actions frames
the tradeoff directly. Applied: policy-driven checkpoints instead of
per-action interrupts; risk-proportioned UI; ranked attention rather than
an exhaustive event firehose (§23, §95, §117). Home's Needs Attention is
the minimal instance.

## 3. Agent-readable interfaces

Agent-mediated interaction needs semantic transparency, state
observability, interaction consistency, and reversibility — not
human-only visuals. Applied: stable nav ids, semantic roles/labels,
explicit component states as data (not just styling), typed IPC/API
contracts, deep links only where wired (`aetheros://…` stays a rule, not
a claim) (§70–§71, §89, §100).

## 4. Reversibility and safe takeover

Reversible where possible; destructive scope stated before acting;
takeover as a first-class, honest handoff (Take Control / Continue /
Cancel) at CAPTCHAs, logins, ambiguity, sensitive or physical-world
actions, and policy boundaries (§55, §92–§93).

## 5. Dark-pattern resistance

GUI agents are vulnerable to manipulative interfaces, and oversight
itself costs cognition — so the shell must neither manipulate nor nag.
Applied: no hidden permissions, misleading buttons, forced defaults,
deceptive urgency, or confusing opt-outs in AetherOS's own UI; approvals
show scope/reversibility/policy/expiry so the decision is real (§96).

## 6. Accessibility as interaction safety

Reduced motion, keyboard-first operation, visible focus, live-region
discipline, and color-plus-text status are safety features in an
agent-operating environment, not polish. See `AETHEROS_ACCESSIBILITY.md`.
