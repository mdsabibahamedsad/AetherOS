# AetherOS Brand Logo Usage Rules

All configurations originate from `WolfMark` (`WOLF_VIEWBOX`,
`WOLF_FUR_PATH`, `WOLF_CUTOUT_PATHS`) via `BrandLockup`. Constants:
`BRAND_LOGO_RULES` in `lib/brand.ts`.

## Official configurations
01 Wolf Only · 02 Wolf + AetherOS · 03 Wolf above AetherOS · 04 + tagline
"AI OPERATING SYSTEM" · 05 Monochrome (`mono` + tone color) · 06 White
(`mono` on dark) · 07 Black (`mono` on light) · 08 Dark background (brand
tile) · 09 Light background (brand tile, unchanged geometry) · 10
Transparent (`mono`, no tile) · 11 Favicon (`mark-only`, 16px) · 12 App
icon (tile + platform mask) · 13 Social avatar (`mark-only`) · 14
Installer icon (horizontal lockup).

## Protection
- Minimum 16px; clear space 25% of tile edge on all sides; never alter
  aspect ratio (square grid).
- Backgrounds: solid layers or photography with scrim; never place brand
  gradient wolf on clashing gradients.
- Mono on light must be Black; on dark, White; cutouts always transparent
  in mono (single silhouette).

## Forbidden
Stretch, squash, rotate, distort, recolor outside brand/mono/white/black,
random shadows/outlines, proportion changes, combining with unrelated
symbols, redrawing the wolf, "A"-letter substitutes, cartoon/mascot/
esports restyles, gradients on the mono mark.

## Known inconsistency (replacement required, not done here)
`apps/desktop/assets/icon.png` (+ derived `.ico`) is a different,
rounded wolf with an orbit ring — it does not match the master. It is
ACTIVE (electron-builder) so it is preserved; replacement must be cut
from `WOLF_*` geometry through the normal release pipeline (see final
report). In-app `BrandMark`/`BrandLockup` are already master-true.
