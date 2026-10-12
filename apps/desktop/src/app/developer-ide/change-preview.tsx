import { useStore } from '@nanostores/react'

import { $aiCoding, $pendingChanges, $totalChanges, applyChanges, approveChange, rejectAllChanges, rejectChange } from '../../store/ai-coding-assistant'

export function ChangePreview() {
  const ai = useStore($aiCoding)
  const pending = useStore($pendingChanges)
  const totals = useStore($totalChanges)

  if (pending.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-surface text-foreground-secondary">
        <div className="text-center">
          <span className="codicon codicon-diff text-3xl block mb-2" />
          <p className="text-sm">No pending changes</p>
          <p className="text-xs mt-1">Ask the AI to make changes to see a preview here</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-surface overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-surface-secondary">
        <div className="flex items-center gap-2 text-xs">
          <span className="font-medium">Change Preview</span>
          <span className="text-foreground-secondary">{totals.total} files</span>
          <span className="text-green-500">+{totals.added}</span>
          <span className="text-red-500">-{totals.removed}</span>
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700" onClick={() => applyChanges(pending)}>
            Apply All
          </button>
          <button className="px-3 py-1 text-xs bg-surface-hover text-foreground rounded hover:bg-surface-muted" onClick={() => rejectAllChanges()}>
            Reject All
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-4">
        {pending.map(change => (
          <div className="border border-border rounded" key={change.id}>
            <div className="flex items-center justify-between px-3 py-1.5 bg-surface-secondary border-b border-border">
              <div className="flex items-center gap-2 text-xs">
                <span className="codicon codicon-file" />
                <span className="font-mono">{change.filePath}</span>
                <span className={`px-1.5 py-0.5 rounded text-2xs ${
                  change.riskLevel === 'high' ? 'bg-red-500/20 text-red-500' :
                  change.riskLevel === 'medium' ? 'bg-yellow-500/20 text-yellow-500' :
                  'bg-green-500/20 text-green-500'
                }`}>
                  {change.riskLevel} risk
                </span>
              </div>
              <div className="flex gap-2">
                <button className="px-2 py-0.5 text-2xs bg-green-600 text-white rounded" onClick={() => approveChange(change.id)}>Accept</button>
                <button className="px-2 py-0.5 text-2xs bg-red-600 text-white rounded" onClick={() => rejectChange(change.id)}>Reject</button>
              </div>
            </div>
            <div className="p-2 font-mono text-xs overflow-x-auto">
              <div className="text-foreground-secondary pb-1">+{change.linesAdded} / -{change.linesRemoved} lines</div>
              <pre className="text-foreground-secondary italic">Diff preview for {change.filePath}</pre>
              <div className="mt-1 text-2xs text-foreground-secondary">{change.reason}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
