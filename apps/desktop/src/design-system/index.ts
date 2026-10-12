/**
 * AetherOS Design System — Main Export
 * Single entry point for the entire design system.
 *
 * NOTE: the canonical component library lives in `components/ui/`.
 * The legacy `design-system/components/` duplicate was removed (it was
 * unimported and had type drift); do not reintroduce a second system.
 */

export * from './accessibility';
export * from './patterns';
export type { ActionBarProps, ActionItem } from './patterns/ActionBar';

export type { DataListItem, DataListProps } from './patterns/DataList';
export type { EmptyStateProps } from './patterns/EmptyState';
export type { ErrorStateProps } from './patterns/ErrorState';
export type { LoadingStateProps } from './patterns/LoadingState';
export type { PageHeaderProps } from './patterns/PageHeader';
export type { SectionProps } from './patterns/Section';
export type { StatusConfig, StatusType } from './patterns/StatusIndicator';
export * from './tokens';
export type { BreakpointKey, BreakpointTokens, ContainerTokens } from './tokens/breakpoints';
// Re-export commonly used types
export type { ColorMode, ColorTokens, SemanticColor } from './tokens/color';

export type { DensityConfig, DensityLevel, DensityTokens } from './tokens/density';
export type { ElevationLevel, ElevationTokens, SemanticElevation } from './tokens/elevation';
export type { AnimationTokens, DurationKey, DurationTokens, EasingKey, EasingTokens, KeyframesTokens } from './tokens/motion';
export type { OpacityKey, OpacityTokens } from './tokens/opacity';
export type { RadiusKey, RadiusTokens } from './tokens/radius';
export type { SpacingKey, SpacingTokens } from './tokens/spacing';
export type { FontFamilyTokens, FontSizeTokens, FontWeightTokens, TextStyleTokens } from './tokens/typography';
export type { LayerGroup, ZIndexKey, ZIndexTokens } from './tokens/zIndex';