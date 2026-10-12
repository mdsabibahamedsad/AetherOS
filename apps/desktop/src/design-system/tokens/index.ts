/**
 * AetherOS Design System — Token Index
 * Single entry point for all design tokens.
 */

export * from './breakpoints';
export type { BreakpointKey, BreakpointTokens, ContainerTokens } from './breakpoints';
export * from './color';
// Re-export types (only what each module actually declares)
export type { ColorMode, ColorTokens, SemanticColor } from './color';
export * from './density';
export type { DensityConfig, DensityLevel, DensityTokens } from './density';
export * from './elevation';
export type { ElevationLevel, ElevationTokens, SemanticElevation } from './elevation';
export * from './motion';
export type { AnimationTokens, DurationKey, DurationTokens, EasingKey, EasingTokens, KeyframesTokens } from './motion';

export * from './opacity';
export type { OpacityKey, OpacityTokens } from './opacity';
export * from './radius';
export type { RadiusKey, RadiusTokens } from './radius';
export * from './spacing';
export type { SpacingKey, SpacingTokens } from './spacing';
export * from './typography';
export type { FontFamilyTokens, FontSizeTokens, FontWeightTokens, TextStyleTokens } from './typography';
export * from './zIndex';
export type { LayerGroup, ZIndexKey, ZIndexTokens } from './zIndex';

import { breakpoints, container } from './breakpoints';
// Aggregated token object for easy consumption
import { color } from './color';
import { defaultDensity, density, densityCssVars } from './density';
import { elevation } from './elevation';
import { animation, duration, easing, keyframes, reducedMotion } from './motion';
import { opacity } from './opacity';
import { radius } from './radius';
import { spacing } from './spacing';
import { fontFamily, fontSize, fontWeight, letterSpacing, lineHeight, textStyle } from './typography';
import { zIndex } from './zIndex';

export const tokens = {
  color,
  spacing,
  fontFamily,
  fontSize,
  fontWeight,
  lineHeight,
  letterSpacing,
  textStyle,
  radius,
  elevation,
  duration,
  easing,
  keyframes,
  animation,
  reducedMotion,
  breakpoints,
  container,
  zIndex,
  opacity,
  density,
  defaultDensity,
  densityCssVars,
} as const;

export type Tokens = typeof tokens;

export default tokens;