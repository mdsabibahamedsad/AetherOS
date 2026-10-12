/**
 * Design-system Badge — status-aware badge with dot support.
 *
 * The patterns layer needs `success`/`warning`/`status` variants plus `size`
 * and `dot`, which the base ui Badge does not provide. Variant colors are
 * defined here (single place); layout primitives are plain spans.
 */

import * as React from 'react';

import { cn } from '@/lib/utils';

export type DsBadgeVariant =
  | 'default'
  | 'primary'
  | 'secondary'
  | 'success'
  | 'warning'
  | 'destructive'
  | 'outline'
  | 'status';

export interface BadgeProps extends React.ComponentProps<'span'> {
  variant?: DsBadgeVariant;
  size?: 'sm' | 'default' | 'lg';
  dot?: boolean;
}

const VARIANTS: Record<DsBadgeVariant, string> = {
  default: 'bg-primary/10 text-primary',
  primary: 'bg-primary/10 text-primary',
  secondary: 'bg-(--ui-bg-quaternary) text-(--ui-text-primary)',
  success: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  warning: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  destructive: 'bg-destructive/10 text-destructive',
  outline: 'border border-(--ui-stroke-secondary) text-muted-foreground',
  status: 'bg-primary/10 text-primary',
};

const SIZES: Record<NonNullable<BadgeProps['size']>, string> = {
  sm: 'px-1 py-px text-[0.6rem]',
  default: 'px-1.5 py-0.5 text-[0.65rem]',
  lg: 'px-2 py-1 text-xs',
};

const DOT_COLORS: Record<DsBadgeVariant, string> = {
  default: 'bg-primary',
  primary: 'bg-primary',
  secondary: 'bg-(--ui-text-secondary)',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  destructive: 'bg-destructive',
  outline: 'bg-muted-foreground',
  status: 'bg-primary',
};

export function Badge({ variant = 'default', size = 'default', dot = false, className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex w-fit shrink-0 items-center gap-1 rounded-[3px] font-medium leading-none',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      data-slot="ds-badge"
      {...props}
    >
      {dot ? <span aria-hidden="true" className={cn('size-1.5 rounded-full', DOT_COLORS[variant])} /> : null}
      {children}
    </span>
  );
}

export default Badge;
