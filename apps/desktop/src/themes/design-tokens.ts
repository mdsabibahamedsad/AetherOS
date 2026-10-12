/**
 * AetherOS Desktop — centralized design tokens (Master 36, Flagship Redesign).
 *
 * Single source of truth for ALL non-color primitives consumed by Tailwind
 * utilities and component variants. Additive only: existing `themes/`
 * color palettes remain authoritative for colors; these tokens formalize
 * spacing, radius, typography scale, shadows, z-index layers, motion, breakpoints,
 * accessibility, and motion preferences so future restyling iterates here —
 * never ad hoc in components.
 *
 * Every token has corresponding component states (default, hover, focus, active,
 * disabled, loading, error, success, warning) defined in the component library.
 */

export const spacing = {
  px: '1px',
  0.5: '0.125rem',
  1: '0.25rem',
  2: '0.5rem',
  3: '0.75rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  8: '2rem',
  10: '2.5rem',
  12: '3rem',
  16: '4rem',
  20: '5rem',
  24: '6rem',
  32: '8rem',
} as const;

export const radius = {
  none: '0',
  sm: '0.25rem',
  DEFAULT: '0.375rem',
  md: '0.5rem',
  lg: '0.75rem',
  xl: '1rem',
  panel: '0.75rem',
  dialog: '0.875rem',
  full: '9999px',
  pill: '100rem',
} as const;

export const fontSize = {
  display: ['2.5rem', { lineHeight: '1.1', fontWeight: '600' }],
  heading: ['1.25rem', { lineHeight: '1.35', fontWeight: '600' }],
  subheading: ['1rem', { lineHeight: '1.45', fontWeight: '500' }],
  body: ['0.875rem', { lineHeight: '1.6', fontWeight: '400' }],
  caption: ['0.75rem', { lineHeight: '1.5', fontWeight: '400' }],
  metadata: ['0.6875rem', { lineHeight: '1.4', fontWeight: '400' }],
  code: ['0.8125rem', { lineHeight: '1.55', fontWeight: '450' }],
  label: ['0.875rem', { lineHeight: '1.6', fontWeight: '500' }],
  button: ['0.875rem', { lineHeight: '1.25', fontWeight: '600' }],
} as const;

export const fontFamily = {
  sans: '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
  mono: '"JetBrains Mono", "SF Mono", "Cascadia Code", ui-monospace, Menlo, Consolas, monospace',
  display: '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, system-ui, sans-serif',
} as const;

export const boxShadow = {
  /** Calm, technical elevations — no glow, no glass bloom. */
  panel: '0 1px 2px rgb(0 0 0 / 0.28), 0 4px 16px rgb(0 0 0 / 0.18)',
  overlay: '0 4px 12px rgb(0 0 0 / 0.32), 0 16px 48px rgb(0 0 0 / 0.28)',
  focus: '0 0 0 1px var(--ring-color, transparent)',
  card: '0 1px 3px rgb(0 0 0 / 0.12), 0 1px 2px rgb(0 0 0 / 0.08)',
  elevated: '0 4px 12px rgb(0 0 0 / 0.25)',
  high: '0 8px 24px rgb(0 0 0 / 0.35)',
} as const;

/** Strict layering contract — prevents ad-hoc z-index races. */
export const zIndex = {
  base: 0,
  raised: 10,
  dropdown: 100,
  sticky: 200,
  overlay: 300,
  modal: 400,
  popover: 500,
  toast: 600,
  tooltip: 700,
  commandPalette: 800,
  agentWorking: 900,
  approvalOverlay: 1000,
} as const;

/** Consistent micro-transitions; respects reduced motion via CSS layer. */
export const duration = {
  instant: '60ms',
  fast: '120ms',
  normal: '180ms',
  slow: '260ms',
  modal: '320ms',
} as const;

export const easing = {
  standard: 'cubic-bezier(0.2, 0, 0, 1)',
  exit: 'cubic-bezier(0.4, 0, 1, 1)',
  modal: 'cubic-bezier(0.0, 0, 0.2, 1)',
} as const;

/** Desktop window breakpoints (P29 → P36 upgrade): small → standard → large → ultrawide. */
export const breakpoints = {
  'desktop-sm': '1024px',
  'desktop-md': '1440px',
  'desktop-lg': '1920px',
  ultrawide: '2560px',
} as const;

/** Accessibility: reduced motion preference. */
export const reducedMotion = {
  enabled: false,
  durationScale: 0, // 0 = disabled, 1 = normal
} as const;

/** Color tokens are defined in themes/presets.ts — this file is non-color primitives only. */
const tokens = {
  spacing,
  radius,
  fontSize,
  fontFamily,
  boxShadow,
  zIndex,
  duration,
  easing,
  breakpoints,
  reducedMotion,
} as const;

export default tokens;
