import { useStore } from '@nanostores/react'

import { $filteredProblems, $problemsPanel, $problemSummary, selectProblem, toggleProblemType } from '../../store/problems-panel'

export function ProblemsPanel() {
  const panel = useStore($problemsPanel)
  const filtered = useStore($filteredProblems)
  const summary = useStore($problemSummary)

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="flex items-center gap-2 px-2 py-1 border-b border-border bg-surface-secondary text-2xs">
        <button className={`flex items-center gap-1 ${panel.showErrors ? 'text-red-500' : 'text-foreground-secondary'}`} onClick={() => toggleProblemType('error')}>
          <span className="codicon codicon-error" />{summary.errors}
        </button>
        <button className={`flex items-center gap-1 ${panel.showWarnings ? 'text-yellow-500' : 'text-foreground-secondary'}`} onClick={() => toggleProblemType('warning')}>
          <span className="codicon codicon-warning" />{summary.warnings}
        </button>
        <button className={`flex items-center gap-1 ${panel.showInfo ? 'text-blue-500' : 'text-foreground-secondary'}`} onClick={() => toggleProblemType('info')}>
          <span className="codicon codicon-info" />{summary.info}
        </button>
      </div>
      <div className="flex-1 overflow-auto">
        {filtered.length === 0 ? (
          <div className="p-4 text-center text-foreground-secondary">No problems detected</div>
        ) : (
          filtered.map(p => (
            <div
              className={`px-3 py-1 cursor-pointer hover:bg-surface-hover flex items-start gap-2 ${
                panel.selectedProblemId === p.id ? 'bg-surface-hover' : ''
              }`}
              key={p.id}
              onClick={() => selectProblem(p.id)}
            >
              <span className={`codicon codicon-${p.type === 'error' ? 'error' : p.type === 'warning' ? 'warning' : 'info'} mt-0.5 ${
                p.type === 'error' ? 'text-red-500' : p.type === 'warning' ? 'text-yellow-500' : 'text-blue-500'
              }`} />
              <div className="min-w-0">
                <div className="truncate">{p.message}</div>
                <div className="text-2xs text-foreground-secondary">
                  {p.file}:{p.line}:{p.column} ({p.source})
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
