/**
 * AetherOS Design System — EmptyState Pattern
 * Consistent empty states across the application.
 */

import { type ReactNode } from 'react';

import { cn } from '@/lib/utils';

import { Button, type ButtonProps } from '../components/Button';
import { Card, CardContent } from '../components/Card';

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ButtonProps & { label: string };
  secondaryAction?: ButtonProps & { label: string };
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  className,
}: EmptyStateProps) {
  return (
    <Card className={cn('flex flex-col items-center justify-center text-center py-12 px-6', className)}>
      <CardContent className="flex flex-col items-center gap-4 w-full">
        {icon && (
          <div aria-hidden="true" className="flex-shrink-0 text-muted-foreground/50">
            {icon}
          </div>
        )}
        <div className="space-y-2">
          <h3 className="text-h5 font-semibold text-foreground">{title}</h3>
          {description && <p className="text-body-sm text-muted-foreground max-w-md">{description}</p>}
        </div>
        {(action || secondaryAction) && (
          <div className="flex flex-col sm:flex-row gap-3 w-full max-w-md mt-2">
            {action && (
              <Button
                className="flex-1"
                disabled={action.disabled}
                onClick={action.onClick}
                size={action.size || 'default'}
                variant={action.variant || 'primary'}
              >
                {action.label}
              </Button>
            )}
            {secondaryAction && (
              <Button
                className="flex-1"
                disabled={secondaryAction.disabled}
                onClick={secondaryAction.onClick}
                size={secondaryAction.size || 'default'}
                variant={secondaryAction.variant || 'outline'}
              >
                {secondaryAction.label}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default EmptyState;