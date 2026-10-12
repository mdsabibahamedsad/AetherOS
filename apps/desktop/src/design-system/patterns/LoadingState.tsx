/**
 * AetherOS Design System — LoadingState Pattern
 * Consistent loading states across the application.
 */

import { cn } from '@/lib/utils';

import { Card, CardContent } from '../components/Card';

export interface LoadingStateProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg' | 'full';
  showSpinner?: boolean;
  className?: string;
}

export function LoadingState({
  message = 'Loading...',
  size = 'md',
  showSpinner = true,
  className,
}: LoadingStateProps) {
  const sizeClasses = {
    sm: 'py-4 px-4',
    md: 'py-8 px-6',
    lg: 'py-12 px-8',
    full: 'flex-1',
  };

  return (
    <Card className={cn('flex flex-col items-center justify-center text-center', sizeClasses[size], className)}>
      <CardContent className="flex flex-col items-center gap-3 w-full">
        {showSpinner && (
          <div aria-hidden="true" className="relative">
            <svg className="animate-spin h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
              />
              <path
                className="opacity-75"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                fill="currentColor"
              />
            </svg>
          </div>
        )}
        <p className="text-body-sm text-muted-foreground">{message}</p>
      </CardContent>
    </Card>
  );
}

export function InlineLoading({ message = 'Loading...', size = 'md' }: { message?: string; size?: 'sm' | 'md' }) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
  };

  return (
    <div aria-live="polite" className="flex items-center gap-2 text-muted-foreground" role="status">
      <svg aria-hidden="true" className={`animate-spin ${sizeClasses[size]}`} fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
        <path className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor" />
      </svg>
      <span className="text-body-sm">{message}</span>
    </div>
  );
}

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'animate-shimmer rounded-md bg-muted',
        'bg-[linear-gradient(90deg,var(--color-muted)_25%,color-mix(in_srgb,var(--color-muted)_50%,transparent)_50%,var(--color-muted)_75%)]',
        'bg-[length:200%_100%]',
        className
      )}
      {...props}
    />
  );
}

export function SkeletonText({ lines = 3, className, ...props }: { lines?: number; className?: string } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('space-y-2', className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton className="h-4 w-full" key={i} style={{ width: i === lines - 1 ? '60%' : '100%' }} />
      ))}
    </div>
  );
}

export function SkeletonCard({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('space-y-4 p-6', className)} {...props}>
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <SkeletonText lines={2} />
    </div>
  );
}

export default LoadingState;