import clsx from 'clsx'
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Loader2,
  Download,
  Terminal,
  GitBranch,
  FileJson,
  Cpu,
  Globe,
  type LucideIcon,
} from 'lucide-react'
import type { RuntimeCheck } from '../store'

const RUNTIME_ICONS: Record<string, LucideIcon> = {
  git: GitBranch,
  python: Terminal,
  node: FileJson,
  rust: Cpu,
  vc_redist: Download,
  webview2: Globe,
}

interface RuntimeCardProps {
  runtime: RuntimeCheck
}

const STATUS_STYLES: Record<string, { icon: LucideIcon; className: string }> = {
  compatible: { icon: CheckCircle, className: 'text-green-500' },
  missing: { icon: XCircle, className: 'text-red-500' },
  outdated: { icon: AlertTriangle, className: 'text-amber-500' },
  broken: { icon: XCircle, className: 'text-red-500' },
}

export function RuntimeCard({ runtime }: RuntimeCardProps) {
  const Icon = RUNTIME_ICONS[runtime.kind] ?? Download
  const statusDef = STATUS_STYLES[runtime.status]
  const StatusIcon = statusDef?.icon ?? Loader2

  return (
    <div
      className={clsx(
        'flex items-start gap-4 rounded-lg border p-4 transition-all',
        runtime.status === 'compatible'
          ? 'border-green-500/20 bg-green-500/5'
          : runtime.status === 'missing' || runtime.status === 'broken'
            ? 'border-red-500/20 bg-red-500/5'
            : runtime.status === 'outdated'
              ? 'border-amber-500/20 bg-amber-500/5'
              : 'border-border bg-card'
      )}
    >
      <div
        className={clsx(
          'flex size-10 shrink-0 items-center justify-center rounded-lg',
          runtime.status === 'compatible'
            ? 'bg-green-500/10'
            : runtime.status === 'missing' || runtime.status === 'broken'
              ? 'bg-red-500/10'
              : runtime.status === 'outdated'
                ? 'bg-amber-500/10'
                : 'bg-muted'
        )}
      >
        <Icon
          size={20}
          className={
            runtime.status === 'compatible'
              ? 'text-green-500'
              : runtime.status === 'missing' || runtime.status === 'broken'
                ? 'text-red-500'
                : runtime.status === 'outdated'
                  ? 'text-amber-500'
                  : 'text-muted-foreground'
          }
        />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">
            {runtime.label}
          </span>
          <StatusIcon size={14} className={statusDef?.className ?? 'text-muted-foreground'} />
        </div>

        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
          {runtime.installed_version && (
            <span>
              Installed: <span className="font-medium text-foreground/80">{runtime.installed_version}</span>
            </span>
          )}
          {runtime.required_version && (
            <span>
              Required: <span className="font-medium text-foreground/80">{runtime.required_version}</span>
            </span>
          )}
        </div>

        {runtime.errors.length > 0 && (
          <div className="mt-1.5 space-y-0.5">
            {runtime.errors.map((err, i) => (
              <p key={i} className="text-xs text-red-400">{err}</p>
            ))}
          </div>
        )}
      </div>

      {runtime.install_progress !== undefined && runtime.status !== 'compatible' && (
        <div className="flex shrink-0 items-center gap-2">
          <Loader2 size={14} className="animate-spin text-primary" />
          <span className="text-xs tabular-nums text-muted-foreground">
            {Math.round(runtime.install_progress)}%
          </span>
        </div>
      )}
    </div>
  )
}
