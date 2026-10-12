export const GLASS_TOKENS = {
  '--glass-blur': '16px',
  '--glass-opacity': '0.88',
  '--glass-border-opacity': '0.10',
  '--glass-saturate': '1.5',
  // AetherOS Premium Glassmorphism
  '--glass-blur-heavy': '24px',
  '--glass-blur-light': '8px',
  '--glass-gradient': 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
  '--glass-border-gradient': 'linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.04) 100%)'
} as const

export const ANIMATION_TOKENS = {
  '--anim-duration-fast': '120ms',
  '--anim-duration-normal': '200ms',
  '--anim-duration-slow': '350ms',
  '--anim-ease-out': 'cubic-bezier(0.16, 1, 0.3, 1)',
  '--anim-ease-in-out': 'cubic-bezier(0.65, 0, 0.35, 1)',
  '--anim-ease-spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  // AetherOS Smooth Animations (60 FPS)
  '--anim-scale-hover': 'scale(1.02)',
  '--anim-scale-active': 'scale(0.98)',
  '--anim-fade-in': 'fadeIn 200ms ease-out',
  '--anim-slide-up': 'slideUp 250ms ease-out',
  '--anim-slide-down': 'slideDown 250ms ease-out',
  '--anim-blur-in': 'blurIn 300ms ease-out'
} as const

export const FOCUS_RING_TOKENS = {
  '--focus-ring-width': '2px',
  '--focus-ring-offset': '2px',
  '--focus-ring-color': 'rgba(0, 212, 255, 0.5)',
  '--focus-ring-shadow': '0 0 0 2px rgba(0, 212, 255, 0.3)'
} as const

export const SURFACE_TOKENS = {
  '--surface-raised': 'color-mix(in srgb, var(--theme-background-seed) 60%, var(--theme-primary) 2%)',
  '--surface-overlay': 'color-mix(in srgb, var(--theme-background-seed) 80%, var(--theme-primary) 1%)',
  '--surface-sunken': 'color-mix(in srgb, var(--theme-background-seed) 100%, #000 3%)',
  // AetherOS Surface Tokens
  '--surface-glass': 'rgba(255, 255, 255, 0.03)',
  '--surface-glass-hover': 'rgba(255, 255, 255, 0.06)',
  '--surface-glass-active': 'rgba(255, 255, 255, 0.08)',
  '--surface-elevated': 'rgba(255, 255, 255, 0.04)',
  '--surface-sunken-dark': 'rgba(0, 0, 0, 0.2)'
} as const

// AetherOS Brand-Specific Tokens
export const AETHEROS_BRAND_TOKENS = {
  '--brand-blue': '#0066FF',
  '--brand-cyan': '#00D4FF',
  '--brand-purple': '#9933FF',
  '--brand-gradient': 'linear-gradient(135deg, #0066FF 0%, #00D4FF 50%, #9933FF 100%)',
  '--brand-gradient-subtle': 'linear-gradient(135deg, rgba(0,102,255,0.1) 0%, rgba(0,212,255,0.05) 50%, rgba(153,51,255,0.1) 100%)',
  '--brand-glow-blue': '0 0 20px rgba(0, 102, 255, 0.3)',
  '--brand-glow-cyan': '0 0 20px rgba(0, 212, 255, 0.3)',
  '--brand-glow-purple': '0 0 20px rgba(153, 51, 255, 0.3)',
  // Border radius (16px, 20px, 24px)
  '--radius-premium-sm': '12px',
  '--radius-premium-md': '16px',
  '--radius-premium-lg': '20px',
  '--radius-premium-xl': '24px'
} as const

export function applyEnhancedTheme(root: HTMLElement) {
  const isDark = root.classList.contains('dark')

  for (const [key, value] of Object.entries(GLASS_TOKENS)) {
    root.style.setProperty(key, value)
  }

  for (const [key, value] of Object.entries(ANIMATION_TOKENS)) {
    root.style.setProperty(key, value)
  }

  for (const [key, value] of Object.entries(FOCUS_RING_TOKENS)) {
    root.style.setProperty(key, value)
  }

  for (const [key, value] of Object.entries(SURFACE_TOKENS)) {
    root.style.setProperty(key, value)
  }

  // Apply AetherOS brand tokens
  for (const [key, value] of Object.entries(AETHEROS_BRAND_TOKENS)) {
    root.style.setProperty(key, value)
  }

  root.style.setProperty('--glass-bg', isDark
    ? 'color-mix(in srgb, var(--theme-background-seed) 70%, transparent)'
    : 'color-mix(in srgb, var(--theme-background-seed) 80%, transparent)'
  )
  root.style.setProperty('--glass-border', isDark
    ? 'color-mix(in srgb, var(--theme-primary) 15%, transparent)'
    : 'color-mix(in srgb, var(--theme-primary) 10%, transparent)'
  )
  root.style.setProperty('--glass-shadow', isDark
    ? '0 8px 32px color-mix(in srgb, #000 30%, transparent)'
    : '0 4px 24px color-mix(in srgb, #000 8%, transparent)'
  )
}

export function setCustomAccentColor(root: HTMLElement, color: string) {
  root.style.setProperty('--accent-custom', color)
  root.style.setProperty('--theme-primary', color)
}

export function getAnimationDuration(name: 'fast' | 'normal' | 'slow'): string {
  const map = { fast: '--anim-duration-fast', normal: '--anim-duration-normal', slow: '--anim-duration-slow' }

  if (typeof document === 'undefined') {return map[name]}

  return getComputedStyle(document.documentElement).getPropertyValue(map[name]).trim() || '250ms'
}
