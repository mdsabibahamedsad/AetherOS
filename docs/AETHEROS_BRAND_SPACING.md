# AetherOS Brand Spacing System

8pt-based scale, centralized in `design-system/tokens/spacing.ts` (+ CSS
vars). Canonical steps (px): 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80,
96 — with 0/1/6/10/14/28/36 supported as named stops where the token file
already defines them. No off-scale values in new work; component padding
uses semantic stops (button/input/card/section/page), layout uses the
numeric scale. Density modes (`compact`/default/`cozy`) scale stops, never
redefine them.
