# AETHEROS MASTER 58361 — Design-System Summary

No new token system created; existing consolidated system verified and reused:
- Source: `apps/desktop/src/design-system/tokens/` (`color, spacing, typography,
  radius, elevation, motion, opacity, density, breakpoints, zIndex`) →
  `css-variables.css` (`--color-*`, light default + `.dark` overrides, density,
  reduced-motion zeroing) → `styles.css` Tailwind v4 `@theme inline` mapping.
- Public alias surface: `--aether-*` (bg, surface, border, text, accent, success,
  warning, danger, info, control metrics). Components consume `--aether-*` /
  `--ui-*` + Tailwind utilities; no one-off hex in edited files.
- Primitives reused by edits: `Button`, `Codicon`, existing sidebar/topbar classes.
  No new components added; no new animations (only existing `transition-colors`).
- Icons: single Codicon set (`codicon-*`). Brand: `BRAND_WORDMARK`/`BrandMark` once
  per surface; no new logo asset; no duplicated wordmark introduced.
- Typography/spacing: existing scale untouched; edits use current utility classes.
