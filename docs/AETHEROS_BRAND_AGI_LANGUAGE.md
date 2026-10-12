# AetherOS AGI Visual Language Foundation

How the system will visually communicate machine activity — one reusable
language for thinking, working, tool execution, file ops, research,
automation, agents, approvals, background tasks, success, and failure.
Component: `components/agi/agi-activity.tsx` (`AgiActivityList`, tested).

## Vocabulary
- ✓ emerald — done (with optional detail: counts, paths, durations)
- ● cyan pulse — active (exactly one per list; the current step)
- ○ muted — pending (upcoming, in order)
- ✕ red — failed (with cause + next action, never bare)
- Header: system label ("AetherOS") + one-line status ("Working on your
  request"); caption scale, muted, calm.

## Laws
1. Summaries and observable actions only — never private chain-of-thought.
2. Rows are data (props), never inferred or fabricated; empty states say
   what would appear and what to do.
3. One active row at a time; progress is real counts, never animated filler.
4. Waiting-for-approval rows route to the approval surface (amber, with
   scope + reversibility note at the destination).
5. Color + glyph + text always; reduced-motion keeps meaning without pulse.

## Example
AETHEROS — Working on your request
✓ Analyzed project · ✓ Located relevant files · ● Preparing changes ·
○ Validation

## Adoption path (not this phase)
Wire `AgiActivityList` into agent surfaces as the shared renderer behind
existing stores (subagents, swarm, automation runs) — same data, one
visual language. No screen was rewired here by design (foundation first).
