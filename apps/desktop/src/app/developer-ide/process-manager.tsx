import { useStore } from '@nanostores/react'

import { $processManager, $runningProcesses, removeProcess, selectProcess } from '../../store/process-manager'

export function ProcessManager() {
  const pm = useStore($processManager)
  const running = useStore($runningProcesses)

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="px-2 py-1.5 border-b border-border bg-surface-secondary">
        <div className="flex items-center justify-between">
          <span className="font-medium">Processes</span>
          <span className="text-2xs text-foreground-secondary">{running.length} running</span>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        {pm.processes.map(p => (
          <div
            className={`px-3 py-1.5 cursor-pointer hover:bg-surface-hover ${
              pm.selectedProcessId === p.id ? 'bg-surface-hover' : ''
            }`}
            key={p.id}
            onClick={() => selectProcess(p.id)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                <span className={`codicon codicon-${p.status === 'running' ? 'debug-start' : 'circle-slash'} ${
                  p.status === 'running' ? 'text-green-500' : 'text-foreground-secondary'
                }`} />
                <span className="font-medium">{p.name}</span>
              </div>
              <div className="flex items-center gap-1">
                {p.pid && <span className="text-2xs text-foreground-secondary">PID {p.pid}</span>}
                {p.status === 'running' && (
                  <button className="text-2xs text-red-500 hover:underline" onClick={e => { e.stopPropagation(); removeProcess(p.id) }}>
                    Stop
                  </button>
                )}
              </div>
            </div>
            <div className="text-2xs text-foreground-secondary font-mono truncate mt-0.5">{p.command}</div>
          </div>
        ))}
        {pm.processes.length === 0 && (
          <div className="p-4 text-center text-foreground-secondary">No running processes</div>
        )}
      </div>
    </div>
  )
}
