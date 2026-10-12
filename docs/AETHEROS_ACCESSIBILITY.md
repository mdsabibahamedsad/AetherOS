# AetherOS Accessibility

Target: strong, tested accessibility across the desktop shell. This page
records the standard, what Master 63 implements, and what remains.

## Standard (brief §72–§73)

Keyboard navigation and focus management; screen-reader semantic HTML +
ARIA where necessary; sufficient contrast in both modes; reduced motion;
scalable typography; visible focus; accessible dialogs, tables, charts,
command palette, and navigation.

## Implemented in Master 63

- New surfaces use native focusable controls (`button`), visible
  focus (`focus-visible:outline` on STOP ALL), `role="status"` for live
  regions (global status, active-work freshness, automation counts),
  `role="alert"` for the offline banner, `role="alertdialog"` for the
  stop confirm, `aria-label`s on icon-only/status controls, `aria-hidden`
  on decorative dots, `title` tooltips on state-dependent disabled
  buttons (Stop while offline, STOP ALL while offline).
- Token-level: `prefers-reduced-motion` zeroes all durations;
  focus-ring tokens in both color modes; density levels for zoom/scale
  needs; status never conveyed by color alone (dot + text label).
- Command palette: full keyboard operation (loop, nested pages with
  Back/Esc semantics, typed-query filtering), `sr-only` dialog title.

## Test evidence this phase

- `vitest`: canonical-nav + emergency-stop suites (7 tests) pass; full
  `tsc --noEmit` reports no errors in touched files (pre-existing errors
  in `design-system/components` and elsewhere on main are untouched and
  recorded in certification).
- `npm run quality:a11y` (`scripts/quality/verify-a11y.mjs`) was NOT run
  (requires a built app + tooling); no automated axe/contrast run is
  claimed. Manual screen-reader pass not performed.

## Remaining (explicit non-goals of this slice)

Automated a11y suite integration, contrast measurement per surface,
dialog/table/chart audit across all 60+ routes, keyboard-map
deconfliction (§48 shortcuts inventory), manual AT verification.
These are certification blockers for PRODUCTION_READY, not for the
BETA/DEVELOPMENT verdict issued here.
