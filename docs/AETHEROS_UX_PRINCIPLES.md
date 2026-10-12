# AetherOS UX Principles

Product-level contract for the human-agent operating environment.
Derived from the Master 63 brief and the current desktop reality.

## 1. One environment, not a tool collection

Agents are processes, tasks are objects, memory is state, approvals are
permissions, artifacts are objects, models are resources. The IA
(`src/navigation/canonical.ts`) exposes this object model; chat is a
command surface plus collaboration, never the whole product (§120).

## 2. No fabricated state (§0)

Every UI state originates from application state. Missing backends render
`Unavailable` / `Not configured` / `Not supported` / `Blocked` — with an
explanation and a next action where one exists. Optimistic UI only where
rollback is safe; destructive or externally-consequential actions wait for
confirmation. This phase removed fabrication from Home and MCP; the audit
lists what remains (computer, research, marketplace, sync, devices,
dashboard) as explicit non-goals of this slice.

## 3. Oversight without exhaustion (§23, §95)

Minimum interruption, maximum meaningful control. Policy-driven approval
checkpoints, risk-proportioned UI (red reserved for high/critical), ranked
attention (Critical → Action Required → Important → Informational →
Background). Home's Needs Attention section implements the ranking in
miniature.

## 4. Every object is inspectable and stoppable (§98, §171–§175)

Identity, status, owner, scope, permissions, activity, actions, metadata —
the universal object pattern. Users can always pause, stop, inspect,
revoke, and disconnect. STOP ALL drives real cancellation legs and reports
per-leg results; it never hides UI. The vocabulary stays exact:
Agent ≠ Model, Tool ≠ Skill ≠ Automation, Task ≠ Agent, Memory ≠ State,
Backup ≠ Sync, Local ≠ Remote.

## 5. Explain, don't expose (§14, §21, §38)

Safe execution summaries and observable actions — never hidden
chain-of-thought, never proprietary routing internals. Model routing shows
requirement-level reasons (vision, context, privacy, latency). Data flow
for sensitive operations shows device → AetherOS → provider with
classification.

## 6. Trust comes from visibility (§97)

Visibility, control, predictability, reversibility, evidence, security —
never decoration, never vague safety claims. Trust calibration states show
current autonomy, what needs approval, what memory does, what leaves the
device. No dark patterns: no hidden permissions, misleading buttons,
forced defaults, or ambiguous destructive actions (§96).

## 7. Freshness is part of the UI (§91, §159)

Live panels indicate Live / Updated-ago / Paused / Disconnected. Cached
state is labeled and never authoritative. Stale data is never presented
as live.

## 8. Progressive disclosure (§68–§69)

Simple by default → Inspect → Developer/Debug. Runtime internals
(traces, tool calls, event streams, token usage) sit behind an explicit
advanced surface, not in every user's face.

## 9. Keyboard-first, accessible, responsive (§48, §72–§73)

Major workflows operable from keyboard; visible focus; semantic HTML +
ARIA where necessary; reduced-motion respected; no fixed-width layouts;
shared primitives stay Electron-decoupled for future web/mobile reuse.

## 10. Security is preserved by construction (§87–§90)

Context isolation, sandbox, preload boundary, typed IPC/API contracts,
sender validation, CSP, secure storage. Renderer never touches filesystem,
shell, secrets, or privileged Electron APIs except through approved
boundaries. UI work must not weaken the model — see `AETHEROS_UX_SECURITY`.
