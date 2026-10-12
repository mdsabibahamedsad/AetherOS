export const JARVIS_THEME = {
  colors: {
    bg: {
      base: '#06060e',
      surface: '#0a0a18',
      elevated: '#0e0e20',
      overlay: 'rgba(6, 6, 14, 0.85)',
    },
    glass: {
      light: 'rgba(255, 255, 255, 0.03)',
      medium: 'rgba(255, 255, 255, 0.05)',
      heavy: 'rgba(255, 255, 255, 0.08)',
      border: 'rgba(255, 255, 255, 0.06)',
      borderHover: 'rgba(255, 255, 255, 0.12)',
    },
    accent: {
      cyan: '#00d4ff',
      cyanDark: '#0099cc',
      cyanGlow: 'rgba(0, 212, 255, 0.3)',
      blue: '#0066ff',
      blueDark: '#0044cc',
      blueGlow: 'rgba(0, 102, 255, 0.3)',
      purple: '#9933ff',
      purpleGlow: 'rgba(153, 51, 255, 0.2)',
      emerald: '#22c55e',
      emeraldGlow: 'rgba(34, 197, 94, 0.3)',
      amber: '#f59e0b',
      amberGlow: 'rgba(245, 158, 11, 0.3)',
      red: '#ef4444',
      redGlow: 'rgba(239, 68, 68, 0.3)',
    },
    text: {
      primary: 'rgba(255, 255, 255, 0.85)',
      secondary: 'rgba(255, 255, 255, 0.55)',
      tertiary: 'rgba(255, 255, 255, 0.25)',
      muted: 'rgba(255, 255, 255, 0.12)',
    },
  },
  blur: {
    sm: 'blur(8px)',
    md: 'blur(16px)',
    lg: 'blur(24px)',
    xl: 'blur(40px)',
  },
  radius: {
    sm: '6px',
    md: '10px',
    lg: '14px',
    xl: '20px',
    '2xl': '28px',
    full: '50%',
  },
  shadow: {
    sm: '0 1px 3px rgba(0,0,0,0.3)',
    md: '0 4px 12px rgba(0,0,0,0.4)',
    lg: '0 8px 32px rgba(0,0,0,0.5)',
    glow: {
      cyan: '0 0 20px rgba(0, 212, 255, 0.15), 0 0 60px rgba(0, 212, 255, 0.05)',
      blue: '0 0 20px rgba(0, 102, 255, 0.15), 0 0 60px rgba(0, 102, 255, 0.05)',
    },
  },
  animation: {
    spring: {
      fast: { type: 'spring' as const, stiffness: 400, damping: 25 },
      normal: { type: 'spring' as const, stiffness: 300, damping: 20 },
      slow: { type: 'spring' as const, stiffness: 200, damping: 18 },
    },
    duration: {
      fast: 0.15,
      normal: 0.3,
      slow: 0.5,
    },
  },
  typography: {
    font: {
      mono: "'SF Mono', 'Fira Code', 'JetBrains Mono', monospace",
      sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    size: {
      xs: '9px',
      sm: '11px',
      base: '13px',
      md: '15px',
      lg: '18px',
      xl: '24px',
      '2xl': '32px',
      '3xl': '48px',
    },
    weight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    tracking: {
      tight: '-0.01em',
      normal: '0',
      wide: '0.05em',
      wider: '0.1em',
      widest: '0.15em',
    },
  },
} as const

export type JarvisTheme = typeof JARVIS_THEME
