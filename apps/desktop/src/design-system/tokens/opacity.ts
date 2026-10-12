/**
 * AetherOS Design System — Opacity Tokens
 * Standardized opacity values for consistent transparency.
 */

export const opacity = {
  // Base scale (0-100)
  0: '0',
  5: '0.05',
  10: '0.1',
  15: '0.15',
  20: '0.2',
  25: '0.25',
  30: '0.3',
  35: '0.35',
  40: '0.4',
  45: '0.45',
  50: '0.5',
  55: '0.55',
  60: '0.6',
  65: '0.65',
  70: '0.7',
  75: '0.75',
  80: '0.8',
  85: '0.85',
  90: '0.9',
  95: '0.95',
  100: '1',

  // Semantic aliases
  transparent: '0',
  translucent: '0.15',
  semiTransparent: '0.5',
  opaque: '1',

  // State opacities
  disabled: '0.4',
  muted: '0.5',
  subtle: '0.6',
  hover: '0.8',
  active: '0.9',
  focus: '1',

  // Overlay opacities
  overlayLight: '0.3',
  overlay: '0.4',
  overlayStrong: '0.6',
  overlayModal: '0.5',
  overlayDrawer: '0.4',

  // Glass/border opacities
  glassBg: '0.03',
  glassBorder: '0.08',
  glassBorderStrong: '0.12',

  // Text opacities (for foreground on colored backgrounds)
  textPrimary: '0.94',
  textSecondary: '0.74',
  textTertiary: '0.54',
  textQuaternary: '0.36',
  textDisabled: '0.38',

  // Border opacities
  borderSubtle: '0.06',
  borderDefault: '0.12',
  borderStrong: '0.18',
  borderFocus: '0.5',

  // Shadow opacities
  shadowAmbient: '0.04',
  shadowDirect: '0.08',
  shadowStrong: '0.12',
  shadowModal: '0.25',
} as const;

export type OpacityTokens = typeof opacity;
export type OpacityKey = keyof OpacityTokens;