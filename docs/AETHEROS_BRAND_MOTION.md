# AetherOS Brand Motion Foundation

Philosophy: fast, smooth, precise, calm, intentional. Motion communicates
state — never decoration. Tokens: `design-system/tokens/motion.ts` (+ CSS
durations, `prefers-reduced-motion` zeroing).

## Categories
- Fast 120ms (hover, focus, micro-interactions), Normal 180ms (entrances,
  panels), Slow 260–320ms (modals, pages), Instant 60ms (active press).
- Easings: standard/enter/exit/modal curves + spring pair for spatial
  movement; sharp for press states.

## Rules
- Subtle fade/scale/blur/morph/slide/depth/progress only; short and
  interruptible; animations never required to understand state.
- Reduced motion: durations zero, decorative loops (skeleton, pulse,
  glow, accent border) disabled; enter/exit/hover/active/focus preserved.
- AGI activity uses the pulse/breathe family at low amplitude — presence,
  not spectacle.
