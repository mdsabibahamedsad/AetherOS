/**
 * Design-system Divider — thin wrapper over the shared ui Separator.
 */

import * as React from 'react';

import { cn } from '@/lib/utils';

import { Separator } from '../../components/ui/separator';

export interface DividerProps extends React.ComponentProps<typeof Separator> {
  spacing?: 'none' | 'sm' | 'md' | 'lg';
}

const SPACING: Record<NonNullable<DividerProps['spacing']>, string> = {
  none: '',
  sm: 'my-2',
  md: 'my-4',
  lg: 'my-6',
};

export function Divider({ spacing = 'md', className, ...props }: DividerProps) {
  return <Separator className={cn(SPACING[spacing], className)} {...props} />;
}

export default Divider;
