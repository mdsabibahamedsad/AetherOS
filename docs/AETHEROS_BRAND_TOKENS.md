# AetherOS Design Tokens (Implementation Index)

Centralized, implementation-ready tokens. Single source:
`apps/desktop/src/design-system/tokens/` (+ `tokens/index.ts` aggregator).

| Domain | File | CSS |
|---|---|---|
| Colors | `color.ts` | `css-variables.css` (`--color-*`, `.dark`) |
| Canonical aliases | — | `--aether-*` (bg/surface/elevated/border/text/muted/accent/success/warning/danger/info) |
| Typography | `typography.ts` | `--font-*`, `--text-*` |
| Spacing (8pt) | `spacing.ts` | `--space-*` |
| Radius | `radius.ts` | `--radius-*` |
| Elevation | `elevation.ts` | `--shadow-*` (levels + semantic + glow) |
| Motion | `motion.ts` | `--duration-*`, `--ease-*` (+ reduced-motion) |
| Opacity | `opacity.ts` | `--opacity-*` |
| Breakpoints | `breakpoints.ts` | `--breakpoint-*`, `--container-*` |
| Z-index | `zIndex.ts` | `--z-*` |
| Density | `density.ts` | `[data-density]` overrides |

Brand constants (`lib/brand.ts`): `BRAND` (palette, gradients, radius),
`BRAND_DARK_LAYERS`, `BRAND_TAGLINE`, `BRAND_WORDMARK`, `BRAND_LOGO_RULES`,
`BRAND_SEMANTIC` (frozen meanings → `--aether-*` values).

Rules: no hardcoded visual values in new code; no new frameworks; themes
consume tokens; `themes/*` duplicate layers are grandfathered (see Theme
Foundation). Pre-existing type drift in `design-system/components/*` and
the `design-tokens.test.ts` failures from uncommitted themes changes are
recorded in the final report — untouched by this phase.
