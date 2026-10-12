/**
 * AetherOS Design System — ErrorState Pattern
 * Consistent error states with recovery actions.
 */

import { type ReactNode } from 'react';

import { AlertCircle, Home, RefreshCw } from '@/lib/icons';
import { cn } from '@/lib/utils';

import { Button, type ButtonProps } from '../components/Button';
import { Card, CardContent } from '../components/Card';

export interface ErrorStateProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  primaryAction?: ButtonProps & { label: string };
  secondaryAction?: ButtonProps & { label: string };
  className?: string;
  showHomeLink?: boolean;
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'An unexpected error occurred. Please try again.',
  icon,
  primaryAction,
  secondaryAction,
  className,
  showHomeLink = false,
}: ErrorStateProps) {
  return (
    <Card className={cn('flex flex-col items-center justify-center text-center py-12 px-6 border-destructive/20 bg-destructive/5', className)}>
      <CardContent className="flex flex-col items-center gap-4 w-full max-w-md">
        <div aria-hidden="true" className="flex-shrink-0 text-destructive">
          {icon || <AlertCircle className="h-12 w-12" />}
        </div>
        <div className="space-y-2">
          <h3 className="text-h5 font-semibold text-foreground">{title}</h3>
          <p className="text-body-sm text-muted-foreground">{description}</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 w-full mt-2">
          {primaryAction && (
            <Button
              className="flex-1"
              disabled={primaryAction.disabled}
              leftIcon={<RefreshCw className="h-4 w-4" />}
              onClick={primaryAction.onClick}
              size={primaryAction.size || 'default'}
              variant={primaryAction.variant || 'primary'}
            >
              {primaryAction.label}
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
          {showHomeLink && (
            <Button
              className="flex-1"
              leftIcon={<Home className="h-4 w-4" />}
              onClick={() => (window.location.href = '/home')}
              size="default"
              variant="ghost"
            >
              Go Home
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default ErrorState;