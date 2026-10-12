# AETHEROS MASTER PROMPT 4 — AGI OPERATING LAYER REPORT

## AGI Architecture
- Mapped to reality: composer → intent → context chain → task (session/cron/action) → delegation → approval gates → tools → streaming execution → tool-signal verification → artifacts → result → continuation. Doc: `AETHEROS_AGI_ARCHITECTURE.md`. No fake layers; unknown renders Unknown.

## Intent Model
- Text/voice/draft/file/app/workspace/task/terminal inputs converge on the composer; scope line states what "this" means. No restated context, no silent injection.

## Context Model
- `lib/context-model.ts` (tested): GLOBAL→WORKSPACE→APP→TASK→AGENT→ACTION; Home scope line + palette stop target consume it.

## Task Model
- Canonical 12-state vocabulary (`lib/agi-states.ts`, tested) mapped from cron/action/subagent signals. Conversation ≠ task ≠ agent ≠ result, enforced in UI structure.

## Planning
- Delegation tree + concise goal/summary display; approve/edit/cancel where backends honor; no trivial-action approval spam; no CoT.

## Autonomy
- Only implemented controls claimed: supervised default, session/global YOLO, statusbar indicator, `/yolo`. Tiered confirmation tested.

## Agent System
- Identity/purpose/tools/permissions/context/task/status/output via `AgentCard`; lifecycle mapped 1:1; "Researching documentation"-grade labels, no theater.

## Multi-Agent
- Tree + grouping + rollup (done/total, tool, tokens, files); WHO/WHAT/STATUS/RESULT visible, internals hidden.

## Tool System
- First-class summary-level activity (current tool + counts), raw output behind inspect. MCP/terminal/browser/search covered by existing real clients.

## Permissions
- WHAT/WHY/SCOPE/RISK gates; session-keyed; server-enforced.

## Approvals
- Once/for-task/session/always/deny per contract; dismissal = refusal; destructive = strong confirm. Palette + Home link to the single Security truth.

## Execution Timeline
- NEW `ExecutionTimeline` (tested): node-lifecycle history in the Agents overlay; timestamp-less events dropped; empty renders nothing.

## Verification
- Produced ≠ verified; only tool-reported signals count. Missing backend verified-flag recorded as gap, not faked.

## Artifacts
- Real collection with type/location/creator/filters/preview/download/open; result view separates activity/result/next-actions.

## Results
- Clean completion summaries with counts + artifacts + continue actions, all data-backed.

## Error Recovery
- WHAT/WHERE/WHY + real paths (resume, cron trigger, new draft, Security, logs). Failure matrix covered by existing handlers + honest messaging.

## Human Takeover
- Parked clarify with choices, sudo/secret modals, approval cards; choose/instruct/cancel on ambiguity; never guesses on consequences.

## Memory / Context
- Session scope vs saved preferences visually and mechanically separate; continuation states its context; Memory center controls intact.

## Terminal Integration
- Shared cwd/session context; agent terminal use summarized; raw output inspectable; conventions preserved.

## File Integration
- Attachments + views + composer-routed AGI suggestions; select→summarize/explain patterns without fake execution.

## Workspace Integration
- Profiles/projects/drafts resume; palette + Home deep-links; merge tracked.

## Automation Integration
- Trigger→actions→permissions→result; history + real stop leg; reps verifiable in automation-center/cron.

## Notifications
- Completion/approval/failure all deep-link; ranked, summarized, grouped. Verified unchanged and conformant.

## Security
- Server-side enforcement; masked secrets with explicit reveal; confirmations tiered; session-keyed isolation; per-leg stop audit; no CoT logged; no new attack surface. Doc: `AETHEROS_AGI_SECURITY.md`.

## Accessibility
- Timeline has labeled section; states are text + tone; live-region and reduced-motion rules hold. No new AT gaps introduced.

## Performance
- Timeline memoized, capped by node count; no new loops/assets; virtualization retained.

## Legacy Hermes Cleanup
- agents, agent-hub, swarm-center: zero Hermes strings. Technical identifiers preserved.

## Files Created
- `lib/agi-states.ts` (+test), `components/agi/execution-timeline.tsx` (+test), 4 docs.

## Files Modified
- `app/agents/index.tsx` (timeline integration).

## Tests
- New: 12 (states, lifecycle, cron/action mapping, autonomy, confirmation tiers, timeline events/ordering/honesty/rendering).

## Test Results
- Full suite: 746/749 pass; 3 failures pre-existing `design-tokens.test.ts` themes drift (untouched). `tsc` + `eslint`: clean on all touched files.

## Remaining Issues
1. No backend verified-flag (documented gap). 2. No session pause primitive (labeled honestly). 3. Six fabricated surfaces (prior phases). 4. Semantic search, route-splitting, surface merges. 5. Repo lint/themes backlog.

## Recommended Master Prompt 5
1. Backend verified-signal + surface it. 2. Wire the six surfaces (marketplace API ready). 3. Semantic search + route-splitting budgets. 4. Execute automation/workspace merges. 5. Visual regression baselines + AT pass. 6. Plan-mode approval UX if backend adds it.
