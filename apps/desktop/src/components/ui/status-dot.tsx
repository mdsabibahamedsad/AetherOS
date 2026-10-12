import type { ComponentProps } from 'react'

import { type StatusTone, StatusDot as ToneDot } from '@/components/status-dot'
import { cn } from '@/lib/utils'

// Canonical status dot behind the `ui/` import path. Reuses the single tone
// system in `@/components/status-dot` (good/bad/warn/muted) — no parallel
// color language. `status` accepts human runtime states and maps them onto
// tones; unknown states fall back to muted rather than inventing colors.
export type UiStatusDotStatus =
  | 'success'
  | 'running'
  | 'idle'
  | 'pending'
  | 'warning'
  | 'error'
  | 'failed'
  | 'blocked'
  | 'offline'
  | (string & {})

const STATUS_TONE: Record<string, StatusTone> = {
  success: 'good',
  running: 'warn',
  idle: 'muted',
  pending: 'warn',
  warning: 'warn',
  error: 'bad',
  failed: 'bad',
  blocked: 'bad',
  offline: 'muted',
}

const SIZE_CLASS: Record<string, string> = {
  xs: 'size-1.5',
  sm: 'size-2',
  md: 'size-2.5',
}

interface UiStatusDotProps extends Omit<ComponentProps<'span'>, 'children'> {
  size?: keyof typeof SIZE_CLASS
  status?: UiStatusDotStatus
}

export function StatusDot({ className, size = 'sm', status = 'idle', ...props }: UiStatusDotProps) {
  return (
    <ToneDot
      aria-label={`status: ${status}`}
      className={cn(SIZE_CLASS[size], status === 'running' && 'animate-pulse', className)}
      role="img"
      tone={STATUS_TONE[status] ?? 'muted'}
      {...props}
    />
  )
}
