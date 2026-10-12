# AetherOS Brand Theme Foundation

Dark-first, light-complete. Sources: `design-system/tokens/*`,
`css-variables.css` (`:root` light, `.dark` overrides, density,
reduced-motion), `themes/` (presets, user themes, skins, effects).

## Dark (primary)
Layered deep navy, never flat pure black: L0 `#060816` background → L1
`#0B1020` surface → L2 `#111831` raised → L3 `#1A2342` floating/modal.
Borders carry separation (subtle strokes over glow); text ramp
primary/secondary/muted holds contrast without excessive luminance.

## Light (complete)
Own hierarchy — surfaces step down from white through cool neutrals,
borders do more work, accents deepen for contrast. Same semantic names,
same wolf, same type: unmistakably AetherOS in both.

## Governance
- Themes consume tokens; nothing hardcodes theme values except
  grandfathered brand constants (`lib/brand.ts`).
- Duplicate theme layers (`themes/design-tokens.ts`, `themes/effects.ts`
  `--brand-*`/`--dt-*`) are documented tech debt: all new work uses
  `design-system/tokens` + `--aether-*`; consolidation is a tracked
  follow-up, not a silent rewrite.
- Density (`compact`/default/`cozy`), high-contrast, and reduced-motion
  are theme-level concerns, not per-component hacks.
