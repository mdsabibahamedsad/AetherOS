/**
 * AetherOS Design System — Border Radius Tokens
 * Consistent radius scale with semantic aliases.
 */

export const radius = {
  // Base scale
  none: '0',
  xs: '0.125rem',     // 2px
  sm: '0.25rem',      // 4px
  md: '0.375rem',     // 6px
  lg: '0.5rem',       // 8px
  xl: '0.75rem',      // 12px
  '2xl': '1rem',      // 16px
  '3xl': '1.5rem',    // 24px
  '4xl': '2rem',      // 32px
  full: '9999px',     // Pill/circle

  // Semantic aliases
  button: '0.375rem',     // 6px
  buttonSm: '0.25rem',    // 4px
  input: '0.375rem',      // 6px
  card: '0.75rem',        // 12px
  cardSm: '0.5rem',       // 8px
  dialog: '0.875rem',     // 14px
  popover: '0.75rem',     // 12px
  tooltip: '0.375rem',    // 6px
  badge: '9999px',        // Pill
  avatar: '9999px',       // Circle
  separator: '0',         // None
  focusRing: '0.125rem',  // 2px offset
} as const;

export type RadiusTokens = typeof radius;
export type RadiusKey = keyof RadiusTokens;