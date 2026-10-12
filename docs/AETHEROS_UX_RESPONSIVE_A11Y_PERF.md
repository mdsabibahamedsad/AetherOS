# Responsive, Accessibility, Performance Audits (Phases 31–32, 43)

## Responsive
- Viewport meta present; sidebar collapses under breakpoint
  (`SIDEBAR_COLLAPSE_MEDIA_QUERY`); overlay views cap width; Home grids
  collapse sm→lg. No mobile bottom-nav pattern; narrow windows reuse the
  collapsed rail + sheets. Gap (tracked): dedicated tablet/mobile
  interaction models, not shrunk desktop.
- This pass adds no fixed-width layouts; AgentCard/Home rows wrap.

## Accessibility (mandatory, audited)
- Global `:focus-visible` styles; Radix dialogs (focus trap, Esc);
  `role=status/alert/alertdialog/progressbar/list`, labeled live regions;
  notifications carry an aria region; status never color-alone
  (dot + text + counts); reduced-motion zeroes durations and decorative
  loops; density modes support zoom needs; touch targets use button
 /input minima.
- New surfaces (palette group, context line, AgentCard already covered)
  reuse these patterns. No automated axe run claimed; manual AT pass
  remains open (see report).

## Performance
- Virtualized: chat threads (`thread-virtualizer`), session sidebar
  lists. No `React.lazy` route splitting found — views load eagerly;
  recorded as the top perf follow-up (code-split by route group).
- No new polling/intervals in this pass (palette group is event-driven;
  context chain is computed); existing intervals (clocks, keepalive,
  cron ticks) untouched. No heavy effects/assets added.
- Full-suite timing: 102 files / 720 tests in ~43s (prior baseline run).
