/**
 * AetherOS Design System — Typography Tokens
 * Systematic type scale with line heights and font weights.
 */

export const fontFamily = {
  sans: '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
  mono: '"JetBrains Mono", "SF Mono", "Cascadia Code", ui-monospace, Menlo, Consolas, monospace',
  display: '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, system-ui, sans-serif',
} as const;

export const fontSize = {
  // Display / Hero
  display: ['2.5rem', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '600' }],      // 40px
  displaySm: ['2rem', { lineHeight: '1.15', letterSpacing: '-0.01em', fontWeight: '600' }],     // 32px

  // Headings
  h1: ['1.875rem', { lineHeight: '1.2', letterSpacing: '-0.01em', fontWeight: '600' }],         // 30px
  h2: ['1.5rem', { lineHeight: '1.3', letterSpacing: '-0.01em', fontWeight: '600' }],           // 24px
  h3: ['1.25rem', { lineHeight: '1.35', letterSpacing: '-0.005em', fontWeight: '600' }],        // 20px
  h4: ['1.125rem', { lineHeight: '1.4', fontWeight: '600' }],                                    // 18px
  h5: ['1rem', { lineHeight: '1.45', fontWeight: '600' }],                                       // 16px
  h6: ['0.875rem', { lineHeight: '1.5', fontWeight: '600' }],                                    // 14px

  // Body
  bodyLg: ['1.125rem', { lineHeight: '1.6', fontWeight: '400' }],                                // 18px
  body: ['1rem', { lineHeight: '1.6', fontWeight: '400' }],                                      // 16px
  bodySm: ['0.875rem', { lineHeight: '1.6', fontWeight: '400' }],                                // 14px
  bodyXs: ['0.8125rem', { lineHeight: '1.55', fontWeight: '400' }],                              // 13px

  // UI Elements
  label: ['0.875rem', { lineHeight: '1.5', fontWeight: '500' }],                                 // 14px
  labelSm: ['0.8125rem', { lineHeight: '1.5', fontWeight: '500' }],                              // 13px
  button: ['0.875rem', { lineHeight: '1.25', fontWeight: '600' }],                               // 14px
  buttonSm: ['0.8125rem', { lineHeight: '1.25', fontWeight: '600' }],                            // 13px

  // Metadata / Caption
  caption: ['0.75rem', { lineHeight: '1.5', fontWeight: '400' }],                                // 12px
  captionSm: ['0.6875rem', { lineHeight: '1.4', fontWeight: '400' }],                            // 11px
  metadata: ['0.6875rem', { lineHeight: '1.4', fontWeight: '400' }],                             // 11px

  // Code
  code: ['0.8125rem', { lineHeight: '1.55', fontWeight: '450' }],                                // 13px
  codeSm: ['0.75rem', { lineHeight: '1.5', fontWeight: '450' }],                                 // 12px
  codeLg: ['0.875rem', { lineHeight: '1.6', fontWeight: '450' }],                                // 14px
} as const;

export const fontWeight = {
  normal: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
} as const;

export const lineHeight = {
  none: '1',
  tight: '1.1',
  snug: '1.25',
  normal: '1.5',
  relaxed: '1.625',
  loose: '2',
} as const;

export const letterSpacing = {
  tighter: '-0.02em',
  tight: '-0.01em',
  normal: '0',
  wide: '0.01em',
  wider: '0.02em',
  widest: '0.04em',
} as const;

// Semantic text styles for consistent usage
export const textStyle = {
  // Page structure
  pageTitle: { fontSize: 'display', fontWeight: '600', lineHeight: '1.1' },
  sectionTitle: { fontSize: 'h3', fontWeight: '600', lineHeight: '1.35' },
  subsectionTitle: { fontSize: 'h4', fontWeight: '600', lineHeight: '1.4' },

  // Content
  body: { fontSize: 'body', fontWeight: '400', lineHeight: '1.6' },
  bodyStrong: { fontSize: 'body', fontWeight: '500', lineHeight: '1.6' },
  bodySm: { fontSize: 'bodySm', fontWeight: '400', lineHeight: '1.6' },

  // UI
  label: { fontSize: 'label', fontWeight: '500', lineHeight: '1.5' },
  labelSm: { fontSize: 'labelSm', fontWeight: '500', lineHeight: '1.5' },
  button: { fontSize: 'button', fontWeight: '600', lineHeight: '1.25' },
  buttonSm: { fontSize: 'buttonSm', fontWeight: '600', lineHeight: '1.25' },

  // Metadata
  caption: { fontSize: 'caption', fontWeight: '400', lineHeight: '1.5' },
  metadata: { fontSize: 'metadata', fontWeight: '400', lineHeight: '1.4' },

  // Code
  code: { fontSize: 'code', fontWeight: '450', lineHeight: '1.55', fontFamily: 'mono' },
  codeSm: { fontSize: 'codeSm', fontWeight: '450', lineHeight: '1.5', fontFamily: 'mono' },
  codeLg: { fontSize: 'codeLg', fontWeight: '450', lineHeight: '1.6', fontFamily: 'mono' },

  // Special
  link: { fontSize: 'bodySm', fontWeight: '500', lineHeight: '1.5', textDecoration: 'underline' },
  badge: { fontSize: 'captionSm', fontWeight: '600', lineHeight: '1', textTransform: 'uppercase', letterSpacing: '0.02em' },
} as const;

export type FontFamilyTokens = typeof fontFamily;
export type FontSizeTokens = typeof fontSize;
export type FontWeightTokens = typeof fontWeight;
export type TextStyleTokens = typeof textStyle;