export const BRAND = {
  colors: {
    blue: '#0066FF',
    cyan: '#00D4FF',
    purple: '#9933FF',
    dark: '#060816',
    darkLight: '#0B1020',
    eyeGlowFrom: '#00D4FF',
    eyeGlowTo: '#00FFFF',
  },
  gradient: {
    from: '#0066FF',
    via: '#00D4FF',
    to: '#9933FF',
  },
  textGradient: 'bg-gradient-to-r from-[#0066FF] via-[#00D4FF] to-[#9933FF] bg-clip-text text-transparent',
  backgroundGradient: 'bg-gradient-to-br from-[#060816] to-[#0B1020]',
  cornerRadius: 'rounded-[12px]',
} as const

/**
 * Official dark environment layers (dark mode is primary). Surfaces step
 * L0→L3 with controlled contrast; never pure black everywhere.
 */
export const BRAND_DARK_LAYERS = {
  /** Layer 0 — app background (deep black-navy). */
  layer0: '#060816',
  /** Layer 1 — default surface. */
  layer1: '#0B1020',
  /** Layer 2 — raised cards, panels. */
  layer2: '#111831',
  /** Layer 3 — floating, modal, overlay. */
  layer3: '#1A2342',
} as const

/** Official tagline. Secondary — never competes with the wolf. */
export const BRAND_TAGLINE = 'AI Operating System' as const

/** Official wordmark text. */
export const BRAND_WORDMARK = 'AetherOS' as const

/**
 * Logo protection rules (see docs/AETHEROS_BRAND_LOGO_USAGE.md).
 * Ratios are relative to the wolf tile edge (size = 100%).
 */
export const BRAND_LOGO_RULES = {
  /** Minimum legible size, px. Below this use the mark only, no wordmark. */
  minSizePx: 16,
  /** Clear space on all sides, as a fraction of tile size. */
  clearSpaceRatio: 0.25,
  /** Favicon floor: geometry is validated recognizable at 16px. */
  faviconSizePx: 16,
} as const

/**
 * Semantic color contract. Values are CSS-variable references into the
 * centralized token layer (`design-system/tokens`), so themes stay the
 * single source of truth — this map only freezes the *meaning*.
 */
export const BRAND_SEMANTIC = {
  primary: 'var(--aether-accent)',
  secondary: 'var(--aether-surface-elevated)',
  accent: 'var(--aether-accent)',
  success: 'var(--aether-success)',
  warning: 'var(--aether-warning)',
  danger: 'var(--aether-danger)',
  info: 'var(--aether-info)',
  background: 'var(--aether-bg)',
  surface: 'var(--aether-surface)',
  elevatedSurface: 'var(--aether-surface-elevated)',
  border: 'var(--aether-border)',
  textPrimary: 'var(--aether-text)',
  textSecondary: 'var(--aether-text)',
  textMuted: 'var(--aether-text-muted)',
} as const
