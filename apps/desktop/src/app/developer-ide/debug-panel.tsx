import { useStore } from '@nanostores/react'

import { $breakpoints, $debugger, $debugStatus, endDebugSession } from '../../store/debugger'

export function DebugPanel() {
  const dbg = useStore($debugger)
  const bps = useStore($breakpoints)
  const status = useStore($debugStatus)

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="px-2 py-1.5 border-b border-border bg-surface-secondary">
        <div className="flex items-center justify-between">
          <span className="font-medium">Debug</span>
          <span className={`px-1.5 py-0.5 rounded text-2xs ${
            status === 'running' ? 'bg-blue-500/20 text-blue-500' :
            status === 'paused' ? 'bg-yellow-500/20 text-yellow-500' :
            'bg-surface-muted text-foreground-secondary'
          }`}>{status}</span>
        </div>
        {dbg.isRunning && (
          <div className="flex gap-1 mt-1">
            <button className="px-1.5 py-0.5 text-2xs bg-surface-hover rounded hover:bg-surface-muted">
              <span className="codicon codicon-debug-continue" />
            </button>
            <button className="px-1.5 py-0.5 text-2xs bg-surface-hover rounded hover:bg-surface-muted">
              <span className="codicon codicon-debug-step-over" />
            </button>
            <button className="px-1.5 py-0.5 text-2xs bg-surface-hover rounded hover:bg-surface-muted">
              <span className="codicon codicon-debug-step-into" />
            </button>
            <button className="px-1.5 py-0.5 text-2xs bg-surface-hover rounded hover:bg-surface-muted">
              <span className="codicon codicon-debug-step-out" />
            </button>
            <button className="ml-auto px-1.5 py-0.5 text-2xs bg-red-500/20 text-red-500 rounded hover:bg-red-500/30" onClick={() => endDebugSession()}>
              Stop
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto">
        <div className="px-2 py-1 text-2xs text-foreground-secondary border-b border-border font-medium">
          Breakpoints ({bps.length})
        </div>
        {bps.map(bp => (
          <div className="flex items-center gap-2 px-3 py-0.5 text-2xs" key={bp.id}>
            <span className={`codicon codicon-${bp.enabled ? 'circle-filled' : 'circle-outline'} ${bp.enabled ? 'text-red-500' : 'text-foreground-secondary'}`} />
            <span className="truncate">{bp.file}:{bp.line}</span>
          </div>
        ))}
        {bps.length === 0 && <div className="px-3 py-1 text-2xs text-foreground-secondary">No breakpoints</div>}

        <div className="px-2 py-1 text-2xs text-foreground-secondary border-b border-border font-medium mt-2">
          Call Stack
        </div>
        {dbg.stackFrames.map((f, i) => (
          <div className={`px-3 py-0.5 text-2xs ${i === 0 ? 'bg-yellow-500/10 text-yellow-500' : ''}`} key={f.id}>
            {f.name} — {f.file}:{f.line}
          </div>
        ))}
        {dbg.stackFrames.length === 0 && <div className="px-3 py-1 text-2xs text-foreground-secondary">Not available</div>}

        <div className="px-2 py-1 text-2xs text-foreground-secondary border-b border-border font-medium mt-2">
          Variables
        </div>
        {dbg.variables.map(v => (
          <div className="px-3 py-0.5 text-2xs flex gap-2" key={v.name}>
            <span className="text-blue-500">{v.name}</span>
            <span className="text-foreground-secondary">=</span>
            <span className="text-green-500">{v.value}</span>
          </div>
        ))}
        {dbg.variables.length === 0 && <div className="px-3 py-1 text-2xs text-foreground-secondary">Not available</div>}
      </div>
    </div>
  )
}
