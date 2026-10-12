/**
 * AetherOS Design System — Spacing Tokens
 * 8pt base grid system.
 */

export const spacing = {
  // Base units (8pt grid)
  0: '0',
  px: '1px',
  0.5: '0.125rem', // 2px
  1: '0.25rem',    // 4px
  1.5: '0.375rem', // 6px
  2: '0.5rem',     // 8px
  2.5: '0.625rem', // 10px
  3: '0.75rem',    // 12px
  3.5: '0.875rem', // 14px
  4: '1rem',       // 16px
  5: '1.25rem',    // 20px
  6: '1.5rem',     // 24px
  7: '1.75rem',    // 28px
  8: '2rem',       // 32px
  9: '2.25rem',    // 36px
  10: '2.5rem',    // 40px
  11: '2.75rem',   // 44px
  12: '3rem',      // 48px
  14: '3.5rem',    // 56px
  16: '4rem',      // 64px
  20: '5rem',      // 80px
  24: '6rem',      // 96px
  28: '7rem',      // 112px
  32: '8rem',      // 128px
  36: '9rem',      // 144px
  40: '10rem',     // 160px
  44: '11rem',     // 176px
  48: '12rem',     // 192px
  52: '13rem',     // 208px
  56: '14rem',     // 224px
  60: '15rem',     // 240px
  64: '16rem',     // 256px
  72: '18rem',     // 288px
  80: '20rem',     // 320px
  96: '24rem',     // 384px

  // Semantic spacing aliases
  none: '0',
  xs: '0.25rem',      // 4px
  sm: '0.5rem',       // 8px
  md: '1rem',         // 16px
  lg: '1.5rem',       // 24px
  xl: '2rem',         // 32px
  '2xl': '3rem',      // 48px
  '3xl': '4rem',      // 64px
  '4xl': '6rem',      // 96px

  // Component-specific
  buttonGap: '0.5rem',        // 8px
  buttonPaddingX: '1rem',     // 16px
  buttonPaddingY: '0.5rem',   // 8px
  inputPaddingX: '0.75rem',   // 12px
  inputPaddingY: '0.5rem',    // 8px
  cardPadding: '1.5rem',      // 24px
  cardGap: '1rem',            // 16px
  sectionGap: '2rem',         // 32px
  pagePadding: '1.5rem',      // 24px
  pageGap: '2rem',            // 32px
  sidebarWidth: '14.8125rem', // 237px
  composerWidth: '48.75rem',  // 780px
} as const;

export type SpacingTokens = typeof spacing;
export type SpacingKey = keyof SpacingTokens;