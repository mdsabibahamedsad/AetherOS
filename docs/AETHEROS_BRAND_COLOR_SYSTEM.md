# AetherOS Brand Color System

Official palette. Implementation: `design-system/tokens/color.ts` +
`css-variables.css` (+ `--aether-*` aliases); constants: `lib/brand.ts`
(`BRAND`, `BRAND_DARK_LAYERS`, `BRAND_SEMANTIC`).

## Brand primaries
| Token | Hex | Use |
|---|---|---|
| Electric Blue | `#0066FF` | primary actions, focus, wolf fur start |
| Cyan | `#00D4FF` | accents, eye glow, live/AGI highlights |
| Violet | `#9933FF` | gradient end, premium moments |

## Dark environment (primary experience)
| Layer | Hex | Use |
|---|---|---|
| L0 background | `#060816` | app background |
| L1 surface | `#0B1020` | default surface / wolf tile |
| L2 raised | `#111831` | cards, panels |
| L3 floating | `#1A2342` | modals, overlays |

Avoid pure black everywhere; separate surfaces by layer steps, not glow.

## Semantics (names frozen in `BRAND_SEMANTIC`, values themed)
Primary, Secondary, Accent, Success, Warning, Danger, Info, Background,
Surface, Elevated Surface, Border (+Divider via border tokens), Text
Primary/Secondary/Muted, Disabled (opacity + muted), Focus (ring tokens),
Selection (selection tokens). Never color-alone: pair with icon + text.

## Gradient discipline
Gradients are reserved for: brand identity (wolf, wordmark hero),
hero moments (boot, onboarding, about), important system states, AGI
activity, selected/highlighted states. UI surfaces stay calm solid
layers. Counter-examples being retired: gradient button/checkbox/switch
variants predate this rule and are grandfathered pending component
migration — no NEW gradient UI outside the listed cases.

## Light mode
Complete, not inverted: own surface hierarchy, borders, text ramp, and
accent behavior from the same semantic names. Both themes must read as
unmistakably AetherOS.
