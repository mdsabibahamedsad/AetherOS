/**
 * AetherOS Design System — Breakpoint Tokens
 * Desktop-first breakpoints for responsive layouts.
 */

export const breakpoints = {
  // Desktop sizes
  desktopSm: '1024px',   // Small desktop / large tablet landscape
  desktopMd: '1440px',   // Standard desktop
  desktopLg: '1920px',   // Large desktop
  desktopXl: '2560px',   // Ultra-wide / 2K

  // Special
  ultrawide: '2560px',
  fullHd: '1920px',

  // Container max widths
  containerSm: '640px',
  containerMd: '768px',
  containerLg: '1024px',
  containerXl: '1280px',
  container2xl: '1440px',
  containerFull: '100%',

  // Sidebar breakpoints
  sidebarCollapse: '1024px',  // Below this, sidebar becomes hover-reveal
  sidebarNarrow: '768px',     // Below this, even hover-reveal is tight
} as const;

export const container = {
  // Max content widths
  content: '48.75rem',      // 780px - main reading width
  contentWide: '64rem',     // 1024px - wide content
  contentFull: '80rem',     // 1280px - full width content
  composer: '48.75rem',     // 780px - composer max width
  sidebar: '14.8125rem',    // 237px - default sidebar width
  sidebarMax: '22rem',      // 352px - max sidebar width
  sidebarMin: '12rem',      // 192px - min sidebar width
  previewRail: '28rem',     // 448px - preview rail width
  previewRailMax: '36rem',  // 576px - max preview rail
  previewRailMin: '20rem',  // 320px - min preview rail
  fileBrowser: '18rem',     // 288px - file browser width
  fileBrowserMax: '28rem',  // 448px - max file browser
  fileBrowserMin: '14rem',  // 224px - min file browser
  terminalSidebar: '42vw',  // 42% viewport width
  terminalSidebarMax: '80vw',
  terminalSidebarMin: '22vw',
} as const;

export type BreakpointTokens = typeof breakpoints;
export type ContainerTokens = typeof container;
export type BreakpointKey = keyof BreakpointTokens;