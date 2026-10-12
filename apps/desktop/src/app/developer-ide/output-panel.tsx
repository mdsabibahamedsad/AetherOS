import { useState } from 'react'

export function OutputPanel() {
  const [lines] = useState([
    '[12:00:01] AetherOS IDE initialized',
    '[12:00:02] Project loaded: my-project',
    '[12:00:05] Code index updated (42 files)',
    '[12:00:10] Git status refreshed',
    '[12:00:15] Ready',
  ])

  return (
    <div className="flex flex-col h-full text-xs font-mono bg-surface">
      <div className="flex items-center px-2 py-1 border-b border-border bg-surface-secondary text-2xs text-foreground-secondary">
        <span className="codicon codicon-terminal mr-1" />
        Output
      </div>
      <div className="flex-1 overflow-auto p-2 text-foreground space-y-0.5">
        {lines.map((line, i) => (
          <div className="text-xs text-foreground-secondary" key={i}>{line}</div>
        ))}
      </div>
    </div>
  )
}
