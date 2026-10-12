/**
 * Built-in desktop themes. Names match the CLI skins / dashboard presets.
 * Add new themes here — no code changes needed elsewhere.
 */

import type { DesktopTheme, DesktopThemeTypography } from './types'

// Color-emoji fonts to append to every stack as a last resort. None of the UI
// text/mono fonts carry emoji glyphs, so without this emoji render as tofu
// boxes on platforms whose default text font lacks them (e.g. Linux/#40364).
// Covers macOS, Windows, Linux, plus the `emoji` generic for anything else.
export const EMOJI_FALLBACK =
  '"Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji", emoji'

const SYSTEM_SANS =
  '"Segoe WPC", "Segoe UI", -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", system-ui, sans-serif, ' +
  EMOJI_FALLBACK

const SYSTEM_MONO =
  '"Cascadia Code", "JetBrains Mono", "SF Mono", ui-monospace, Menlo, Monaco, Consolas, monospace, ' + EMOJI_FALLBACK

export const DEFAULT_TYPOGRAPHY: DesktopThemeTypography = { fontSans: SYSTEM_SANS, fontMono: SYSTEM_MONO }

const AETHEROS_BLUE_LEGACY = '#0053FD'
const PSYCHE_BLUE = '#1540B1'
const PSYCHE_WARM = '#FFE6CB'

// AetherOS Brand Colors
const AETHEROS_BLUE = '#0066FF'
const AETHEROS_CYAN = '#00D4FF'
const AETHEROS_PURPLE = '#9933FF'
const AETHEROS_BG_DARK = '#060816'
const AETHEROS_BG_MID = '#0B1020'
const AETHEROS_BG_LIGHT = '#121826'

const aetherosTint = (pct: number) => `color-mix(in srgb, ${AETHEROS_BLUE_LEGACY} ${pct}%, #FFFFFF)`
const aetherosTintTransparent = (pct: number) => `color-mix(in srgb, ${AETHEROS_BLUE_LEGACY} ${pct}%, transparent)`

/**
 * AetherOS — canonical Aetheros desktop identity. The palette keeps the current
 * glass geometry neutral, then lets the old bb/gui blue and psyche cream
 * return as accent seeds.
 */
export const defaultDesktopTheme: DesktopTheme = {
  name: 'aetheros',
  label: 'AetherOS',
  description: 'Glass neutrals with AetherOS blue accents',
  colors: {
    background: '#F8FAFF',
    foreground: '#17171A',
    card: '#FFFFFF',
    cardForeground: '#17171A',
    muted: aetherosTint(5),
    mutedForeground: '#666678',
    popover: '#FFFFFF',
    popoverForeground: '#17171A',
    primary: AETHEROS_BLUE_LEGACY,
    primaryForeground: '#FCFCFC',
    secondary: aetherosTint(7),
    secondaryForeground: '#242432',
    accent: aetherosTint(10),
    accentForeground: '#202030',
    border: aetherosTintTransparent(22),
    input: aetherosTintTransparent(30),
    ring: AETHEROS_BLUE_LEGACY,
    midground: AETHEROS_BLUE_LEGACY,
    composerRing: AETHEROS_BLUE_LEGACY,
    destructive: '#C72E4D',
    destructiveForeground: '#FFFFFF',
    sidebarBackground: '#F3F7FF',
    sidebarBorder: aetherosTintTransparent(18),
    userBubble: aetherosTint(6),
    userBubbleBorder: aetherosTintTransparent(24)
  },
  darkColors: {
    background: '#0D2F86',
    foreground: PSYCHE_WARM,
    card: '#12378F',
    cardForeground: PSYCHE_WARM,
    muted: '#183F9A',
    mutedForeground: '#B5C7F3',
    popover: '#123A96',
    popoverForeground: PSYCHE_WARM,
    primary: PSYCHE_WARM,
    primaryForeground: '#0D2F86',
    secondary: '#1B45A4',
    secondaryForeground: '#E0E8FF',
    accent: PSYCHE_BLUE,
    accentForeground: '#F0F4FF',
    border: '#3158AD',
    input: '#0B2566',
    ring: PSYCHE_WARM,
    midground: AETHEROS_BLUE_LEGACY,
    composerRing: PSYCHE_WARM,
    destructive: '#C0473A',
    destructiveForeground: '#FEF2F2',
    sidebarBackground: '#09286F',
    sidebarBorder: '#234A9C',
    userBubble: '#143B91',
    userBubbleBorder: '#3A63BD'
  },
  typography: {
    fontSans: SYSTEM_SANS,
    fontMono: `"Courier Prime", ${SYSTEM_MONO}`,
    fontUrl: 'https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap'
  }
}

/** Deep blue-violet with cool accents. Matches the dashboard midnight theme. */
export const midnightTheme: DesktopTheme = {
  name: 'midnight',
  label: 'Midnight',
  description: 'Deep blue-violet with cool accents',
  colors: {
    background: '#08081c',
    foreground: '#ddd6ff',
    card: '#0d0d28',
    cardForeground: '#ddd6ff',
    muted: '#13133a',
    mutedForeground: '#7c7ab0',
    popover: '#0f0f2e',
    popoverForeground: '#ddd6ff',
    primary: '#ddd6ff',
    primaryForeground: '#08081c',
    secondary: '#1a1a4a',
    secondaryForeground: '#c4bff0',
    accent: '#1a1a44',
    accentForeground: '#d0c8ff',
    border: '#1e1e52',
    input: '#1e1e52',
    ring: '#8b80e8',
    midground: '#8b80e8',
    destructive: '#b03060',
    destructiveForeground: '#fef2f2',
    sidebarBackground: '#06061a',
    sidebarBorder: '#12123a',
    userBubble: '#14143a',
    userBubbleBorder: '#242466'
  },
  typography: {
    fontMono: `"JetBrains Mono", ${SYSTEM_MONO}`,
    fontUrl: 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap'
  }
}

/** Warm crimson and bronze — forge vibes. Matches the CLI ares skin. */
export const emberTheme: DesktopTheme = {
  name: 'ember',
  label: 'Ember',
  description: 'Warm crimson and bronze — forge vibes',
  colors: {
    background: '#160800',
    foreground: '#ffd8b0',
    card: '#1e0e04',
    cardForeground: '#ffd8b0',
    muted: '#2a1408',
    mutedForeground: '#aa7a56',
    popover: '#221008',
    popoverForeground: '#ffd8b0',
    primary: '#ffd8b0',
    primaryForeground: '#160800',
    secondary: '#341800',
    secondaryForeground: '#f0c090',
    accent: '#301600',
    accentForeground: '#e8c080',
    border: '#3a1c08',
    input: '#3a1c08',
    ring: '#d97316',
    midground: '#d97316',
    destructive: '#c43010',
    destructiveForeground: '#fef2f2',
    sidebarBackground: '#100600',
    sidebarBorder: '#2a1004',
    userBubble: '#2a1000',
    userBubbleBorder: '#4a2010'
  },
  typography: {
    fontMono: `"IBM Plex Mono", ${SYSTEM_MONO}`,
    fontUrl: 'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&display=swap'
  }
}

/** Clean grayscale. Matches the CLI mono skin and dashboard mono theme. */
export const monoTheme: DesktopTheme = {
  name: 'mono',
  label: 'Mono',
  description: 'Clean grayscale — minimal and focused',
  colors: {
    background: '#0e0e0e',
    foreground: '#eaeaea',
    card: '#141414',
    cardForeground: '#eaeaea',
    muted: '#1e1e1e',
    mutedForeground: '#808080',
    popover: '#181818',
    popoverForeground: '#eaeaea',
    primary: '#eaeaea',
    primaryForeground: '#0e0e0e',
    secondary: '#262626',
    secondaryForeground: '#c8c8c8',
    accent: '#222222',
    accentForeground: '#d8d8d8',
    border: '#2a2a2a',
    input: '#2a2a2a',
    ring: '#9a9a9a',
    midground: '#9a9a9a',
    destructive: '#a84040',
    destructiveForeground: '#fef2f2',
    sidebarBackground: '#0a0a0a',
    sidebarBorder: '#202020',
    userBubble: '#1a1a1a',
    userBubbleBorder: '#363636'
  }
}

/** Neon green on black. Matches the CLI cyberpunk skin and dashboard theme. */
export const cyberpunkTheme: DesktopTheme = {
  name: 'cyberpunk',
  label: 'Cyberpunk',
  description: 'Neon green on black — matrix terminal',
  colors: {
    background: '#000a00',
    foreground: '#00ff41',
    card: '#001200',
    cardForeground: '#00ff41',
    muted: '#001a00',
    mutedForeground: '#1a8a30',
    popover: '#001000',
    popoverForeground: '#00ff41',
    primary: '#00ff41',
    primaryForeground: '#000a00',
    secondary: '#002800',
    secondaryForeground: '#00cc34',
    accent: '#002000',
    accentForeground: '#00e038',
    border: '#003000',
    input: '#003000',
    ring: '#00ff41',
    midground: '#00ff41',
    destructive: '#ff003c',
    destructiveForeground: '#000a00',
    sidebarBackground: '#000600',
    sidebarBorder: '#001800',
    userBubble: '#001400',
    userBubbleBorder: '#004800'
  },
  typography: {
    fontMono: `"Courier New", Courier, monospace, ${EMOJI_FALLBACK}`,
    fontSans: `"Courier New", Courier, monospace, ${EMOJI_FALLBACK}`
  }
}

/** Cool slate blue for developers. Matches the CLI slate skin. */
export const slateTheme: DesktopTheme = {
  name: 'slate',
  label: 'Slate',
  description: 'Cool slate blue — focused developer theme',
  colors: {
    background: '#0d1117',
    foreground: '#c9d1d9',
    card: '#161b22',
    cardForeground: '#c9d1d9',
    muted: '#21262d',
    mutedForeground: '#8b949e',
    popover: '#1c2128',
    popoverForeground: '#c9d1d9',
    primary: '#c9d1d9',
    primaryForeground: '#0d1117',
    secondary: '#2a3038',
    secondaryForeground: '#adb5bf',
    accent: '#1e2530',
    accentForeground: '#c0c8d0',
    border: '#30363d',
    input: '#30363d',
    ring: '#58a6ff',
    midground: '#58a6ff',
    destructive: '#cf4848',
    destructiveForeground: '#fef2f2',
    sidebarBackground: '#090d13',
    sidebarBorder: '#1c2228',
    userBubble: '#1e2a38',
    userBubbleBorder: '#2e4060'
  },
  typography: {
    fontMono: `"JetBrains Mono", ${SYSTEM_MONO}`
  }
}

/**
 * AetherOS — Premium AI Operating System theme.
 * Dark-first design with Blue → Cyan → Purple gradient accents.
 * Glassmorphism with soft blur, 16-24px rounded corners.
 */
export const aetherosTheme: DesktopTheme = {
  name: 'aetheros',
  label: 'AetherOS',
  description: 'Premium AI Operating System — dark-first with blue/cyan/purple gradients',
  colors: {
    // Core surfaces
    background: AETHEROS_BG_DARK,
    foreground: '#E8ECF4',
    card: AETHEROS_BG_MID,
    cardForeground: '#E8ECF4',
    muted: AETHEROS_BG_LIGHT,
    mutedForeground: '#8B95A8',
    popover: AETHEROS_BG_LIGHT,
    popoverForeground: '#E8ECF4',
    
    // Brand accent colors
    primary: AETHEROS_BLUE,
    primaryForeground: '#FFFFFF',
    secondary: AETHEROS_CYAN,
    secondaryForeground: AETHEROS_BG_DARK,
    accent: AETHEROS_PURPLE,
    accentForeground: '#FFFFFF',
    
    // Borders and inputs
    border: 'rgba(255, 255, 255, 0.08)',
    input: 'rgba(255, 255, 255, 0.06)',
    ring: AETHEROS_CYAN,
    
    // Midground and composer
    midground: AETHEROS_BLUE,
    composerRing: AETHEROS_CYAN,
    
    // Destructive
    destructive: '#FF4D6A',
    destructiveForeground: '#FFFFFF',
    
    // Sidebar
    sidebarBackground: '#080C18',
    sidebarBorder: 'rgba(255, 255, 255, 0.06)',
    
    // User bubble
    userBubble: 'rgba(0, 102, 255, 0.12)',
    userBubbleBorder: 'rgba(0, 212, 255, 0.2)'
  },
  darkColors: {
    // Core surfaces - dark mode
    background: AETHEROS_BG_DARK,
    foreground: '#E8ECF4',
    card: AETHEROS_BG_MID,
    cardForeground: '#E8ECF4',
    muted: AETHEROS_BG_LIGHT,
    mutedForeground: '#8B95A8',
    popover: AETHEROS_BG_LIGHT,
    popoverForeground: '#E8ECF4',
    
    // Brand accent colors - dark mode
    primary: AETHEROS_CYAN,
    primaryForeground: AETHEROS_BG_DARK,
    secondary: AETHEROS_BLUE,
    secondaryForeground: '#FFFFFF',
    accent: AETHEROS_PURPLE,
    accentForeground: '#FFFFFF',
    
    // Borders and inputs - dark mode
    border: 'rgba(255, 255, 255, 0.08)',
    input: 'rgba(255, 255, 255, 0.06)',
    ring: AETHEROS_CYAN,
    
    // Midground and composer - dark mode
    midground: AETHEROS_CYAN,
    composerRing: AETHEROS_CYAN,
    
    // Destructive - dark mode
    destructive: '#FF4D6A',
    destructiveForeground: '#FFFFFF',
    
    // Sidebar - dark mode
    sidebarBackground: '#050810',
    sidebarBorder: 'rgba(255, 255, 255, 0.06)',
    
    // User bubble - dark mode
    userBubble: 'rgba(0, 212, 255, 0.08)',
    userBubbleBorder: 'rgba(153, 51, 255, 0.2)'
  },
  typography: {
    fontSans: `"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif, ${EMOJI_FALLBACK}`,
    fontMono: `"JetBrains Mono", "SF Mono", "Cascadia Code", ui-monospace, Menlo, Consolas, monospace, ${EMOJI_FALLBACK}`,
    fontDisplay: `"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, system-ui, sans-serif`,
    fontUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap'
  }
}

/**
 * High-contrast theme for accessibility. Pure black background with bright
 * white text and vivid accent colors for maximum readability. Meets WCAG AAA
 * contrast requirements.
 */
export const highContrastTheme: DesktopTheme = {
  name: 'high-contrast',
  label: 'High Contrast',
  description: 'Maximum contrast for accessibility — WCAG AAA compliant',
  colors: {
    background: '#000000',
    foreground: '#FFFFFF',
    card: '#0A0A0A',
    cardForeground: '#FFFFFF',
    popover: '#0A0A0A',
    popoverForeground: '#FFFFFF',
    primary: '#64C8FF',
    primaryForeground: '#000000',
    secondary: '#1A1A1A',
    secondaryForeground: '#FFFFFF',
    muted: '#1A1A1A',
    mutedForeground: '#B0B0B0',
    accent: '#64C8FF',
    accentForeground: '#000000',
    destructive: '#FF6B6B',
    destructiveForeground: '#000000',
    border: '#333333',
    input: '#333333',
    ring: '#64C8FF',
    success: '#69DB7C',
    warning: '#FFD43B',
    info: '#64C8FF',
    sidebarBackground: '#000000',
    sidebarBorder: '#333333',
    sidebarForeground: '#FFFFFF',
    sidebarAccent: '#64C8FF',
    sidebarAccentForeground: '#000000',
    sidebarMuted: '#1A1A1A',
    sidebarMutedForeground: '#B0B0B0',
    sidebarPrimary: '#64C8FF',
    sidebarPrimaryForeground: '#000000',
    sidebarDestructive: '#FF6B6B',
    sidebarDestructiveForeground: '#000000',
    sidebarRing: '#64C8FF',
    userBubble: 'rgba(100, 200, 255, 0.15)',
    userBubbleBorder: 'rgba(100, 200, 255, 0.3)'
  },
  darkColors: {
    background: '#000000',
    foreground: '#FFFFFF',
    card: '#0A0A0A',
    cardForeground: '#FFFFFF',
    popover: '#0A0A0A',
    popoverForeground: '#FFFFFF',
    primary: '#64C8FF',
    primaryForeground: '#000000',
    secondary: '#1A1A1A',
    secondaryForeground: '#FFFFFF',
    muted: '#1A1A1A',
    mutedForeground: '#B0B0B0',
    accent: '#64C8FF',
    accentForeground: '#000000',
    destructive: '#FF6B6B',
    destructiveForeground: '#000000',
    border: '#333333',
    input: '#333333',
    ring: '#64C8FF',
    success: '#69DB7C',
    warning: '#FFD43B',
    info: '#64C8FF',
    sidebarBackground: '#000000',
    sidebarBorder: '#333333',
    sidebarForeground: '#FFFFFF',
    sidebarAccent: '#64C8FF',
    sidebarAccentForeground: '#000000',
    sidebarMuted: '#1A1A1A',
    sidebarMutedForeground: '#B0B0B0',
    sidebarPrimary: '#64C8FF',
    sidebarPrimaryForeground: '#000000',
    sidebarDestructive: '#FF6B6B',
    sidebarDestructiveForeground: '#000000',
    sidebarRing: '#64C8FF',
    userBubble: 'rgba(100, 200, 255, 0.15)',
    userBubbleBorder: 'rgba(100, 200, 255, 0.3)'
  },
  typography: DEFAULT_TYPOGRAPHY
}

export const BUILTIN_THEMES: Record<string, DesktopTheme> = {
  aetheros: aetherosTheme,
  midnight: midnightTheme,
  ember: emberTheme,
  mono: monoTheme,
  cyberpunk: cyberpunkTheme,
  slate: slateTheme,
  'high-contrast': highContrastTheme
}

export const BUILTIN_THEME_LIST = Object.values(BUILTIN_THEMES)

/** Skin used when nothing is persisted or the persisted name is retired. */
export const DEFAULT_SKIN_NAME = 'aetheros'
