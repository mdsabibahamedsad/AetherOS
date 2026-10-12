/**
 * AetherOS Design System — Motion / Animation Tokens
 * Consistent timing, easing, and animation definitions.
 */

export const duration = {
  instant: '60ms',
  fast: '120ms',
  normal: '180ms',
  slow: '260ms',
  slower: '320ms',
  modal: '320ms',
  page: '400ms',
} as const;

export const easing = {
  // Standard Material-style curves
  standard: 'cubic-bezier(0.2, 0, 0, 1)',
  exit: 'cubic-bezier(0.4, 0, 1, 1)',
  enter: 'cubic-bezier(0, 0, 0.2, 1)',
  modal: 'cubic-bezier(0.0, 0, 0.2, 1)',

  // Spring-like
  spring: 'cubic-bezier(0.16, 1, 0.3, 1)',
  springGentle: 'cubic-bezier(0.25, 1, 0.5, 1)',

  // Sharp
  sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
} as const;

export const keyframes = {
  // Fade
  fadeIn: {
    from: { opacity: '0' },
    to: { opacity: '1' },
  },
  fadeOut: {
    from: { opacity: '1' },
    to: { opacity: '0' },
  },

  // Slide
  slideUp: {
    from: { opacity: '0', transform: 'translateY(8px)' },
    to: { opacity: '1', transform: 'translateY(0)' },
  },
  slideDown: {
    from: { opacity: '0', transform: 'translateY(-8px)' },
    to: { opacity: '1', transform: 'translateY(0)' },
  },
  slideLeft: {
    from: { opacity: '0', transform: 'translateX(8px)' },
    to: { opacity: '1', transform: 'translateX(0)' },
  },
  slideRight: {
    from: { opacity: '0', transform: 'translateX(-8px)' },
    to: { opacity: '1', transform: 'translateX(0)' },
  },

  // Scale
  scaleIn: {
    from: { opacity: '0', transform: 'scale(0.95)' },
    to: { opacity: '1', transform: 'scale(1)' },
  },
  scaleOut: {
    from: { opacity: '1', transform: 'scale(1)' },
    to: { opacity: '0', transform: 'scale(0.95)' },
  },

  // Blur
  blurIn: {
    from: { opacity: '0', filter: 'blur(4px)' },
    to: { opacity: '1', filter: 'blur(0)' },
  },

  // Pulse (for live indicators)
  pulse: {
    '0%, 100%': { opacity: '1' },
    '50%': { opacity: '0.5' },
  },
  pulseGlow: {
    '0%, 100%': { boxShadow: '0 0 20px rgba(0, 212, 255, 0.2)' },
    '50%': { boxShadow: '0 0 30px rgba(0, 212, 255, 0.4)' },
  },

  // Spin
  spin: {
    from: { transform: 'rotate(0deg)' },
    to: { transform: 'rotate(360deg)' },
  },

  // Shimmer (for skeletons)
  shimmer: {
    '0%': { backgroundPosition: '-200% 0' },
    '100%': { backgroundPosition: '200% 0' },
  },

  // Accent border animation
  accentBorder: {
    '0%': { backgroundPosition: '15% 15%' },
    '100%': { backgroundPosition: '75% 75%' },
  },
} as const;

// Semantic animation combinations
export const animation = {
  // Entrance
  enter: {
    fast: { duration: 'fast', easing: 'enter', keyframes: 'fadeIn' },
    normal: { duration: 'normal', easing: 'enter', keyframes: 'slideUp' },
    slow: { duration: 'slow', easing: 'spring', keyframes: 'scaleIn' },
    modal: { duration: 'modal', easing: 'modal', keyframes: 'scaleIn' },
  },

  // Exit
  exit: {
    fast: { duration: 'fast', easing: 'exit', keyframes: 'fadeOut' },
    normal: { duration: 'normal', easing: 'exit', keyframes: 'slideDown' },
    modal: { duration: 'modal', easing: 'exit', keyframes: 'scaleOut' },
  },

  // State transitions
  hover: { duration: 'fast', easing: 'standard' },
  active: { duration: 'instant', easing: 'sharp' },
  focus: { duration: 'fast', easing: 'standard' },

  // Loading
  skeleton: { duration: '1.5s', easing: 'linear', keyframes: 'shimmer', iterationCount: 'infinite' },
  spinner: { duration: '1s', easing: 'linear', keyframes: 'spin', iterationCount: 'infinite' },
  pulse: { duration: '2s', easing: 'ease-in-out', keyframes: 'pulse', iterationCount: 'infinite' },
  pulseGlow: { duration: '2s', easing: 'ease-in-out', keyframes: 'pulseGlow', iterationCount: 'infinite' },

  // Special
  accentBorder: { duration: '2.23s', easing: 'linear', keyframes: 'accentBorder', iterationCount: 'infinite' },
  questGlow: { duration: '1.8s', easing: 'ease-in-out', keyframes: 'pulseGlow', iterationCount: 'infinite' },
} as const;

// Reduced motion overrides (applied via media query)
export const reducedMotion = {
  durationScale: 0, // 0 = instant, 1 = normal
  disableAnimations: [
    'skeleton',
    'spinner',
    'pulse',
    'pulseGlow',
    'accentBorder',
    'questGlow',
  ],
  keepAnimations: [
    'enter',
    'exit',
    'hover',
    'active',
    'focus',
  ],
} as const;

export type DurationTokens = typeof duration;
export type EasingTokens = typeof easing;
export type KeyframesTokens = typeof keyframes;
export type AnimationTokens = typeof animation;
export type DurationKey = keyof DurationTokens;
export type EasingKey = keyof EasingTokens;