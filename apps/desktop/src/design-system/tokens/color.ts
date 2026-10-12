/**
 * AetherOS Design System — Color Tokens
 * Single source of truth for all color values.
 * Consumed by Tailwind config and component library.
 */

export const color = {
  // Brand Colors
  brand: {
    blue: '#0066FF',
    cyan: '#00D4FF',
    purple: '#9933FF',
    gradient: 'linear-gradient(135deg, #0066FF 0%, #00D4FF 50%, #9933FF 100%)',
    gradientSubtle: 'linear-gradient(135deg, rgba(0,102,255,0.1) 0%, rgba(0,212,255,0.05) 50%, rgba(153,51,255,0.1) 100%)',
  },

  // Semantic Colors (Light Mode)
  light: {
    // Backgrounds
    background: '#F8FAFF',
    surface: '#FFFFFF',
    surfaceElevated: '#FFFFFF',
    surfaceHover: '#F3F7FF',
    surfaceActive: '#EBF1FF',

    // Foregrounds
    foreground: '#17171A',
    foregroundMuted: '#71717A',
    foregroundSubtle: '#A1A1AA',

    // Borders
    border: '#E4E4E7',
    borderStrong: '#D4D4D8',
    borderFocus: '#0066FF',

    // Primary
    primary: '#0053FD',
    primaryHover: '#0045CC',
    primaryActive: '#0038A3',
    primaryForeground: '#FFFFFF',

    // Secondary
    secondary: '#F3F7FF',
    secondaryHover: '#EBF1FF',
    secondaryActive: '#D6E4FF',
    secondaryForeground: '#0053FD',

    // Accent
    accent: '#00D4FF',
    accentHover: '#00B8E6',
    accentActive: '#009CCC',
    accentForeground: '#17171A',

    // Destructive
    destructive: '#CF2D56',
    destructiveHover: '#B02548',
    destructiveActive: '#911D3B',
    destructiveForeground: '#FFFFFF',

    // Success
    success: '#1F8A65',
    successHover: '#1A7655',
    successActive: '#156245',
    successForeground: '#FFFFFF',
    successBackground: '#ECFDF3',

    // Warning
    warning: '#C08532',
    warningHover: '#A6732C',
    warningActive: '#8C6126',
    warningForeground: '#FFFFFF',
    warningBackground: '#FFFAEB',

    // Info
    info: '#0053FD',
    infoHover: '#0045CC',
    infoActive: '#0038A3',
    infoForeground: '#FFFFFF',
    infoBackground: '#EFF8FF',

    // Overlay
    overlay: 'rgba(0, 0, 0, 0.4)',
    overlayStrong: 'rgba(0, 0, 0, 0.6)',

    // Glass
    glassBg: 'rgba(255, 255, 255, 0.03)',
    glassBorder: 'rgba(255, 255, 255, 0.08)',

    // Sidebar
    sidebarBackground: '#F3F7FF',
    sidebarBorder: '#E4E4E7',
    sidebarForeground: '#17171A',

    // Chat
    chatBackground: '#F8FAFF',
    userBubbleBackground: '#EFF8FF',
    assistantBubbleBackground: '#FFFFFF',

    // Code
    codeBackground: '#F4F4F5',
    codeBorder: '#E4E4E7',
    codeForeground: '#18181B',

    // Selection
    selectionBackground: '#FFD24A',
    selectionForeground: '#17171A',

    // Focus
    focusRing: 'rgba(0, 102, 255, 0.5)',
    focusRingShadow: '0 0 0 2px rgba(0, 102, 255, 0.3)',
  },

  // Semantic Colors (Dark Mode)
  dark: {
    // Backgrounds
    background: '#0D0D0E',
    surface: '#161618',
    surfaceElevated: '#1C1C1F',
    surfaceHover: '#1A1A1D',
    surfaceActive: '#242427',

    // Foregrounds
    foreground: '#FAFAFA',
    foregroundMuted: '#A1A1AA',
    foregroundSubtle: '#71717A',

    // Borders
    border: '#27272A',
    borderStrong: '#3F3F46',
    borderFocus: '#0066FF',

    // Primary
    primary: '#4F8CFF',
    primaryHover: '#6BA3FF',
    primaryActive: '#3D7AE6',
    primaryForeground: '#FFFFFF',

    // Secondary
    secondary: '#1A1A1D',
    secondaryHover: '#242427',
    secondaryActive: '#2D2D30',
    secondaryForeground: '#4F8CFF',

    // Accent
    accent: '#00D4FF',
    accentHover: '#33DDFF',
    accentActive: '#00B8E6',
    accentForeground: '#0D0D0E',

    // Destructive
    destructive: '#E75E78',
    destructiveHover: '#ED7A8F',
    destructiveActive: '#D64A62',
    destructiveForeground: '#FFFFFF',

    // Success
    success: '#55A583',
    successHover: '#6BC097',
    successActive: '#488F71',
    successForeground: '#0D0D0E',
    successBackground: '#0A2D1F',

    // Warning
    warning: '#DB704B',
    warningHover: '#E18663',
    warningActive: '#D05C35',
    warningForeground: '#0D0D0E',
    warningBackground: '#3D2A0F',

    // Info
    info: '#4F8CFF',
    infoHover: '#6BA3FF',
    infoActive: '#3D7AE6',
    infoForeground: '#FFFFFF',
    infoBackground: '#0F1F3D',

    // Overlay
    overlay: 'rgba(0, 0, 0, 0.6)',
    overlayStrong: 'rgba(0, 0, 0, 0.8)',

    // Glass
    glassBg: 'rgba(0, 0, 0, 0.3)',
    glassBorder: 'rgba(255, 255, 255, 0.06)',

    // Sidebar
    sidebarBackground: '#0A0A0B',
    sidebarBorder: '#27272A',
    sidebarForeground: '#FAFAFA',

    // Chat
    chatBackground: '#0D0D0E',
    userBubbleBackground: '#1A1A1D',
    assistantBubbleBackground: '#161618',

    // Code
    codeBackground: '#1C1C1F',
    codeBorder: '#27272A',
    codeForeground: '#E4E4E7',

    // Selection
    selectionBackground: '#FFD24A',
    selectionForeground: '#0D0D0E',

    // Focus
    focusRing: 'rgba(0, 212, 255, 0.5)',
    focusRingShadow: '0 0 0 2px rgba(0, 212, 255, 0.3)',
  },

  // Status Colors (mode-agnostic)
  status: {
    running: '#4F8CFF',
    pending: '#DB704B',
    success: '#55A583',
    error: '#E75E78',
    warning: '#DB704B',
    idle: '#71717A',
    paused: '#C08532',
    blocked: '#E75E78',
    offline: '#52525B',
  },

  // Risk Levels
  risk: {
    low: '#55A583',
    medium: '#DB704B',
    high: '#E75E78',
    critical: '#CF2D56',
  },

  // Trust Levels
  trust: {
    verified: '#55A583',
    trusted: '#4F8CFF',
    pending: '#DB704B',
    untrusted: '#E75E78',
    blocked: '#CF2D56',
  },

  // Data Classification
  classification: {
    public: '#55A583',
    internal: '#4F8CFF',
    private: '#DB704B',
    sensitive: '#E75E78',
    restricted: '#CF2D56',
  },
} as const;

export type ColorTokens = typeof color;
export type ColorMode = 'light' | 'dark';
export type SemanticColor = keyof typeof color.light;