/**
 * Design-system Button — adapter over the shared ui Button.
 *
 * The patterns layer references `design-system/components/Button`, which did
 * not exist (typecheck failure). This module provides the exact API the
 * patterns use: `primary` variant, icon slots, full-width opt-in. Visual
 * behavior is inherited from `components/ui/button` — no forked styles.
 */

import * as React from 'react';

import { cn } from '@/lib/utils';

import { Button as UiButton } from '../../components/ui/button';

export type DsButtonVariant = 'primary' | 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
export type DsButtonSize = 'default' | 'xs' | 'sm' | 'lg' | 'icon' | 'inline';

export interface ButtonProps extends Omit<React.ComponentProps<'button'>, 'size'> {
  variant?: DsButtonVariant;
  size?: DsButtonSize | string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

const VARIANT_MAP: Record<DsButtonVariant, 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'> = {
  primary: 'default',
  default: 'default',
  destructive: 'destructive',
  outline: 'outline',
  secondary: 'secondary',
  ghost: 'ghost',
  link: 'link',
};

const KNOWN_SIZES = new Set(['default', 'xs', 'sm', 'lg', 'icon', 'inline']);

export function Button({
  variant = 'primary',
  size = 'default',
  leftIcon,
  rightIcon,
  fullWidth = false,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <UiButton
      className={cn(fullWidth && 'w-full', className)}
      size={(KNOWN_SIZES.has(size) ? size : 'default') as DsButtonSize}
      variant={VARIANT_MAP[variant]}
      {...props}
    >
      {leftIcon ? <span aria-hidden="true">{leftIcon}</span> : null}
      {children}
      {rightIcon ? <span aria-hidden="true">{rightIcon}</span> : null}
    </UiButton>
  );
}

export default Button;
