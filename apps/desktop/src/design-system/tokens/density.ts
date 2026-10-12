/**
 * AetherOS Design System — Density Tokens
 * Controls visual density/compactness of UI components.
 * Supports: comfortable (default), compact, cozy
 */

export const density = {
  // Density levels
  comfortable: {
    name: 'comfortable',
    label: 'Comfortable',
    multiplier: 1,
    description: 'Spacious, generous padding — default for most users',
    // Spacing adjustments
    spacing: {
      buttonPaddingX: '1rem',     // 16px
      buttonPaddingY: '0.5rem',   // 8px
      inputPaddingX: '0.75rem',   // 12px
      inputPaddingY: '0.5rem',    // 8px
      cardPadding: '1.5rem',      // 24px
      cardGap: '1rem',            // 16px
      listGap: '0.5rem',          // 8px
      sectionGap: '2rem',         // 32px
      pagePadding: '1.5rem',      // 24px
    },
    // Size adjustments
    size: {
      buttonHeight: '2.25rem',    // 36px
      buttonHeightSm: '1.875rem', // 30px
      inputHeight: '2.25rem',     // 36px
      inputHeightSm: '1.875rem',  // 30px
      avatarSize: '2.5rem',       // 40px
      avatarSizeSm: '1.5rem',     // 24px
      iconSize: '1.25rem',        // 20px
      iconSizeSm: '1rem',         // 16px
    },
    // Typography adjustments
    typography: {
      bodyLineHeight: '1.6',
      headingLineHeight: '1.3',
    },
  },

  compact: {
    name: 'compact',
    label: 'Compact',
    multiplier: 0.75,
    description: 'Reduced padding for power users, more content on screen',
    spacing: {
      buttonPaddingX: '0.75rem',  // 12px
      buttonPaddingY: '0.375rem', // 6px
      inputPaddingX: '0.625rem',  // 10px
      inputPaddingY: '0.375rem',  // 6px
      cardPadding: '1rem',        // 16px
      cardGap: '0.75rem',         // 12px
      listGap: '0.375rem',        // 6px
      sectionGap: '1.5rem',       // 24px
      pagePadding: '1rem',        // 16px
    },
    size: {
      buttonHeight: '2rem',       // 32px
      buttonHeightSm: '1.625rem', // 26px
      inputHeight: '2rem',        // 32px
      inputHeightSm: '1.625rem',  // 26px
      avatarSize: '2rem',         // 32px
      avatarSizeSm: '1.25rem',    // 20px
      iconSize: '1rem',           // 16px
      iconSizeSm: '0.875rem',     // 14px
    },
    typography: {
      bodyLineHeight: '1.5',
      headingLineHeight: '1.25',
    },
  },

  cozy: {
    name: 'cozy',
    label: 'Cozy',
    multiplier: 1.25,
    description: 'Extra spacing for accessibility, touch targets, readability',
    spacing: {
      buttonPaddingX: '1.25rem',  // 20px
      buttonPaddingY: '0.625rem', // 10px
      inputPaddingX: '1rem',      // 16px
      inputPaddingY: '0.625rem',  // 10px
      cardPadding: '2rem',        // 32px
      cardGap: '1.25rem',         // 20px
      listGap: '0.75rem',         // 12px
      sectionGap: '2.5rem',       // 40px
      pagePadding: '2rem',        // 32px
    },
    size: {
      buttonHeight: '2.5rem',     // 40px
      buttonHeightSm: '2.125rem', // 34px
      inputHeight: '2.5rem',      // 40px
      inputHeightSm: '2.125rem',  // 34px
      avatarSize: '3rem',         // 48px
      avatarSizeSm: '1.75rem',    // 28px
      iconSize: '1.5rem',         // 24px
      iconSizeSm: '1.25rem',      // 20px
    },
    typography: {
      bodyLineHeight: '1.7',
      headingLineHeight: '1.35',
    },
  },
} as const;

// Default density
export const defaultDensity = 'comfortable' as const;

// Density CSS variable prefix
export const densityCssVars = {
  multiplier: '--density-multiplier',
  buttonPaddingX: '--density-button-padding-x',
  buttonPaddingY: '--density-button-padding-y',
  inputPaddingX: '--density-input-padding-x',
  inputPaddingY: '--density-input-padding-y',
  cardPadding: '--density-card-padding',
  cardGap: '--density-card-gap',
  listGap: '--density-list-gap',
  sectionGap: '--density-section-gap',
  pagePadding: '--density-page-padding',
  buttonHeight: '--density-button-height',
  buttonHeightSm: '--density-button-height-sm',
  inputHeight: '--density-input-height',
  inputHeightSm: '--density-input-height-sm',
  avatarSize: '--density-avatar-size',
  avatarSizeSm: '--density-avatar-size-sm',
  iconSize: '--density-icon-size',
  iconSizeSm: '--density-icon-size-sm',
  bodyLineHeight: '--density-body-line-height',
  headingLineHeight: '--density-heading-line-height',
} as const;

export type DensityTokens = typeof density;
export type DensityLevel = keyof DensityTokens;
export type DensityConfig = DensityTokens[DensityLevel];