/**
 * AetherOS Design System — StatusIndicator Pattern
 * Consistent status display for agents, tasks, systems, etc.
 */

import { cn } from '@/lib/utils';

import { Badge } from '../components/Badge';

export type StatusType =
  | 'running'
  | 'pending'
  | 'success'
  | 'error'
  | 'warning'
  | 'idle'
  | 'paused'
  | 'blocked'
  | 'offline'
  | 'unknown';

export interface StatusConfig {
  type: StatusType;
  label?: string;
  showDot?: boolean;
  showLabel?: boolean;
  size?: 'sm' | 'default' | 'lg';
  variant?: 'default' | 'badge' | 'dot-only';
  className?: string;
}

const statusLabels: Record<StatusType, string> = {
  running: 'Running',
  pending: 'Pending',
  success: 'Success',
  error: 'Error',
  warning: 'Warning',
  idle: 'Idle',
  paused: 'Paused',
  blocked: 'Blocked',
  offline: 'Offline',
  unknown: 'Unknown',
};

const statusVariants: Record<StatusType, 'success' | 'warning' | 'destructive' | 'default' | 'status'> = {
  running: 'status',
  pending: 'warning',
  success: 'success',
  error: 'destructive',
  warning: 'warning',
  idle: 'default',
  paused: 'warning',
  blocked: 'destructive',
  offline: 'default',
  unknown: 'default',
};

export function StatusIndicator({
  type,
  label,
  showDot = true,
  showLabel = true,
  size = 'default',
  variant = 'default',
  className,
}: StatusConfig) {
  const displayLabel = label || statusLabels[type];
  const badgeVariant = statusVariants[type];

  if (variant === 'dot-only') {
    return (
      <span
        aria-label={displayLabel}
        className={cn(
          'inline-flex items-center gap-1.5',
          className
        )}
      >
        {showDot && <span aria-hidden="true" className={cn('flex-shrink-0 w-2 h-2 rounded-full', `bg-status-${type}`)} />}
        {showLabel && <span className="text-body-sm font-medium">{displayLabel}</span>}
      </span>
    );
  }

  if (variant === 'badge') {
    return (
      <Badge className={className} dot={showDot} size={size} variant={badgeVariant}>
        {displayLabel}
      </Badge>
    );
  }

  return (
    <span aria-label={displayLabel} className={cn('inline-flex items-center gap-1.5', className)}>
      {showDot && <span aria-hidden="true" className={cn('flex-shrink-0 w-2 h-2 rounded-full', `bg-status-${type}`)} />}
      {showLabel && <span className="text-body-sm font-medium">{displayLabel}</span>}
    </span>
  );
}

export function StatusBadge({ type, label, size = 'default', className }: { type: StatusType; label?: string; size?: 'sm' | 'default' | 'lg'; className?: string }) {
  return (
    <Badge className={className} dot size={size} variant={statusVariants[type]}>
      {label || statusLabels[type]}
    </Badge>
  );
}

export function StatusDot({ type, size = 'default', className }: { type: StatusType; size?: 'sm' | 'default' | 'lg'; className?: string }) {
  const sizeClasses = {
    sm: 'w-1.5 h-1.5',
    default: 'w-2 h-2',
    lg: 'w-3 h-3',
  };

  return (
    <span
      aria-label={statusLabels[type]}
      className={cn('inline-flex flex-shrink-0 rounded-full', sizeClasses[size], `bg-status-${type}`, className)}
    />
  );
}

export function StatusPill({ type, label, className }: { type: StatusType; label: string; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-caption-sm font-medium',
        `bg-status-${type}/10 text-status-${type} border border-status-${type}/20`,
        className
      )}
    >
      <span aria-hidden="true" className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: `var(--color-status-${type})` }} />
      {label}
    </span>
  );
}

export default StatusIndicator;