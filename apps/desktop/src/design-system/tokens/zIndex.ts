/**
 * AetherOS Design System — Z-Index Tokens
 * Strict layering contract to prevent z-index wars.
 * Each layer has a specific purpose and fixed order.
 */

export const zIndex = {
  // Base layers
  base: 0,
  background: -1,

  // Content layers
  content: 10,
  raised: 20,           // Hovered cards, active nav items
  sticky: 100,          // Sticky headers, sidebar affix

  // Overlay layers (progressive)
  dropdown: 200,        // Select menus, dropdown menus
  popover: 300,         // Popovers, tooltips, hover cards
  tooltip: 400,         // Tooltips (above popovers)
  drawer: 500,          // Side drawers, slide-over panels
  modal: 600,           // Dialogs, modals
  modalOverlay: 550,    // Modal backdrop

  // Special system layers
  commandPalette: 700,  // Global command palette
  agentWorking: 800,    // Agent working indicator (top-right)
  approvalOverlay: 900, // Approval requests (must be above all)
  emergencyStop: 1000,  // Global emergency stop banner
  toast: 1100,          // Notifications/toasts (highest)
  tour: 1200,           // Onboarding tours

  // Developer/debug
  debug: 9999,          // Debug overlays, dev tools
} as const;

// Layer groups for easier reasoning
export const layerGroups = {
  base: ['base', 'background'] as const,
  content: ['content', 'raised', 'sticky'] as const,
  overlay: ['dropdown', 'popover', 'tooltip', 'drawer'] as const,
  modal: ['modalOverlay', 'modal'] as const,
  system: ['commandPalette', 'agentWorking', 'approvalOverlay', 'emergencyStop', 'toast', 'tour'] as const,
  debug: ['debug'] as const,
} as const;

export type ZIndexTokens = typeof zIndex;
export type ZIndexKey = keyof ZIndexTokens;
export type LayerGroup = keyof typeof layerGroups;