# AetherOS Brand Foundation

The single visual-identity contract for the AetherOS ecosystem. All
screens, components, website, installer, and desktop surfaces build from
this system. Code: `apps/desktop/src/components/brand/` + `src/lib/brand.ts`.

## Brand core
AetherOS — AGI-Native Operating System. An OS built around intelligence:
intelligent, autonomous, powerful, precise, context-aware, fast, secure,
elegant, simple, future-facing. Serious technology platform, never a
chatbot skin or startup page.

## The wolf (primary and only symbol)
Master geometry: `WolfMark` (`components/brand/wolf-mark.tsx`,
`WOLF_VIEWBOX` 32×32, `WOLF_FUR_PATH`, `WOLF_CUTOUT_PATHS`). Geometric,
sharp, minimal, premium — shared angular DNA with the whole system.
Colorways: `brand` (blue→cyan→violet gradient, eye glow) and `mono`
(single currentColor silhouette; cutouts transparent). Gradient defs use
per-instance ids (no cross-instance collisions). Silhouette validated
standalone: mono reads at 16px with no effects, text, or background.

## Lockups (all cut from the master)
`BrandLockup`: `mark-only` (favicon/app icon/avatar/presence),
`horizontal` (wolf + AetherOS), `stacked` (wolf above wordmark),
optional `tagline` ("AI Operating System", muted, secondary), optional
hero-only `gradientWordmark`. White/Black/Monochrome = `mono` + text
color. Sizes are explicit px (16–1024). Legacy `BrandLogo`
(wolf+wordmark+tagline, sm/md/lg) and `BrandMark` (dark tile badge) now
delegate to the master with byte-identical output.

## Wordmark + tagline hierarchy
WOLF → AetherOS (Inter 700, −0.03em) → AI OPERATING SYSTEM (muted,
+0.2em tracking). Wordmark is secondary; tagline never competes.

## Color, type, theme (summaries — full docs linked)
- Color: Electric Blue `#0066FF`, Cyan `#00D4FF`, Violet `#9933FF`;
  dark layers L0 `#060816` → L3 `#1A2342`; semantics frozen in
  `BRAND_SEMANTIC` as `--aether-*` references. See
  `AETHEROS_BRAND_COLOR_SYSTEM.md`.
- Typography: Inter (UI/display) + JetBrains Mono (code/terminal) —
  already the repo standard; kept deliberately. See
  `AETHEROS_BRAND_TYPOGRAPHY.md`.
- Dark-first themes with complete light mode; tokens are the truth.
  See `AETHEROS_BRAND_THEME_FOUNDATION.md`.

## Rules that bind everything
Intelligence over decoration; calm surfaces; gradients reserved for brand,
hero, AGI activity, and selected states; motion communicates state;
reduced motion supported; user stays in control. Full protection rules:
`AETHEROS_BRAND_LOGO_USAGE.md`.
