import { useStore } from '@nanostores/react'

import { $buildStatus, $buildSystem, $buildTasks, clearBuildHistory, selectBuildTask } from '../../store/build-system'

export function BuildPanel() {
  const build = useStore($buildSystem)
  const tasks = useStore($buildTasks)
  const status = useStore($buildStatus)

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="flex items-center justify-between px-2 py-1 border-b border-border bg-surface-secondary">
        <span className="font-medium">Build</span>
        <div className="flex items-center gap-2">
          <span className={`px-1.5 py-0.5 rounded text-2xs ${
            status === 'running' ? 'bg-blue-500/20 text-blue-500' :
            status === 'completed' ? 'bg-green-500/20 text-green-500' :
            status === 'failed' ? 'bg-red-500/20 text-red-500' :
            'bg-surface-muted text-foreground-secondary'
          }`}>
            {status}
          </span>
          <button className="text-2xs text-foreground-secondary hover:text-foreground" onClick={() => clearBuildHistory()}>Clear</button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {tasks.map(t => (
          <div
            className={`px-2 py-1 rounded cursor-pointer hover:bg-surface-hover ${build.selectedTaskId === t.id ? 'bg-surface-hover' : ''}`}
            key={t.id}
            onClick={() => selectBuildTask(t.id)}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-xs">{t.name}</span>
              <span className="text-2xs text-foreground-secondary">{t.manager}</span>
            </div>
            <div className="text-2xs text-foreground-secondary font-mono truncate">{t.command}</div>
          </div>
        ))}
        {tasks.length === 0 && (
          <div className="text-center text-foreground-secondary py-4">No build tasks detected</div>
        )}
      </div>
      {build.currentBuild && (
        <div className="border-t border-border p-2 max-h-32 overflow-auto">
          <div className="text-2xs text-foreground-secondary mb-1">Last build: {build.currentBuild.taskName}</div>
          <pre className="text-2xs text-foreground font-mono whitespace-pre-wrap">{build.currentBuild.output.slice(0, 500)}</pre>
        </div>
      )}
    </div>
  )
}
