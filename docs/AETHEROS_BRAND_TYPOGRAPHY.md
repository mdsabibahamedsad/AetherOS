# AetherOS Brand Typography System

Decision: **Inter** for UI/display, **JetBrains Mono** for code/terminal.
This keeps the existing repository standard (already in
`design-system/tokens/typography.ts`, `css-variables.css`,
`themes/presets.ts`, `themes/design-tokens.ts`) — no font migration, no
new downloads, no layout churn. Geist / Space Grotesk / Sora were
evaluated and rejected for this phase: Inter already carries the
technical-premium tone and full weight coverage.

## Scale (from `fontSize` tokens)
Display 40/32 → H1 30, H2 24, H3 20, H4 18, H5 16, H6 14 → Body
18/16/14/13 → Label 14/13, Button 14/13 → Caption 12/11, Metadata 11 →
Code 13/12/14 (weight 450). Weights 400/500/600/700 only.

## Rules
- Display/H1–H3: semibold, tight negative tracking (−0.02em → −0.005em).
- Body: regular, 1.55–1.6 line height. UI labels: medium 500.
- Terminal/code: JetBrains Mono, never proportional figures in metrics.
- Wordmark lockups: Inter 700, −0.03em (see Brand Foundation).
- No other families without a brand amendment. `Arial` fallback in
  `tooltip.tsx` is grandfathered, not a pattern.
