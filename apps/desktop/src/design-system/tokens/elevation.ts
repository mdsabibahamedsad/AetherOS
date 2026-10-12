/**
 * AetherOS Design System — Elevation / Shadow Tokens
 * Layered elevation system for consistent depth perception.
 */

export const elevation = {
  // Light mode shadows
  light: {
    // Flat / no elevation
    level0: 'none',

    // Subtle - for cards, panels at rest
    level1: '0 1px 2px rgb(0 0 0 / 0.05), 0 1px 3px rgb(0 0 0 / 0.1)',

    // Raised - for hovered cards, dropdowns
    level2: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',

    // Floating - for modals, popovers, tooltips
    level3: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',

    // Overlay - for drawers, sidebars
    level4: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',

    // Modal - for dialogs, full-screen overlays
    level5: '0 25px 50px -12px rgb(0 0 0 / 0.25)',

    // Special: Focus ring (not elevation but related)
    focusRing: '0 0 0 2px rgb(0 102 255 / 0.5)',

    // Special: Glass/borderless overlay
    glass: '0 8px 32px rgba(0, 0, 0, 0.12)',
  },

  // Dark mode shadows (stronger for visibility)
  dark: {
    level0: 'none',

    level1: '0 1px 2px rgb(0 0 0 / 0.3), 0 1px 3px rgb(0 0 0 / 0.4)',

    level2: '0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.3)',

    level3: '0 10px 15px -3px rgb(0 0 0 / 0.4), 0 4px 6px -4px rgb(0 0 0 / 0.3)',

    level4: '0 20px 25px -5px rgb(0 0 0 / 0.4), 0 8px 10px -6px rgb(0 0 0 / 0.3)',

    level5: '0 25px 50px -12px rgb(0 0 0 / 0.5)',

    focusRing: '0 0 0 2px rgb(0 212 255 / 0.5)',

    glass: '0 8px 32px rgba(0, 0, 0, 0.5)',
  },

  // Semantic elevation aliases (mode-agnostic, resolve via CSS variables)
  semantic: {
    card: 'level1',
    cardHover: 'level2',
    cardActive: 'level2',
    dropdown: 'level3',
    popover: 'level3',
    tooltip: 'level2',
    modal: 'level5',
    drawer: 'level4',
    sidebar: 'level2',
    header: 'level1',
    composer: 'level2',
    notification: 'level4',
    commandPalette: 'level5',
    approvalOverlay: 'level5',
    agentWorking: 'level3',
  },

  // Glow shadows for special states
  glow: {
    blue: '0 0 20px rgba(0, 102, 255, 0.3)',
    cyan: '0 0 20px rgba(0, 212, 255, 0.3)',
    purple: '0 0 20px rgba(153, 51, 255, 0.3)',
    success: '0 0 20px rgba(85, 165, 131, 0.3)',
    warning: '0 0 20px rgba(219, 112, 75, 0.3)',
    error: '0 0 20px rgba(231, 94, 120, 0.3)',
  },
} as const;

export type ElevationTokens = typeof elevation;
export type ElevationLevel = keyof typeof elevation.light;
export type SemanticElevation = keyof typeof elevation.semantic;