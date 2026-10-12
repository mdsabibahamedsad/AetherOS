import { useStore } from '@nanostores/react'

import { $dependencyManager, $selectedManagerData, setSelectedManager } from '../../store/dependency-manager'

export function DependencyManager() {
  const dm = useStore($dependencyManager)
  const selected = useStore($selectedManagerData)

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="px-2 py-1.5 border-b border-border bg-surface-secondary">
        <div className="flex items-center gap-2">
          <span className="font-medium">Dependencies</span>
          {dm.managers.map(m => (
            <button
              className={`px-1.5 py-0.5 text-2xs rounded ${
                dm.selectedManager === m.name ? 'bg-accent text-white' : 'bg-surface-hover text-foreground-secondary'
              }`}
              key={m.name}
              onClick={() => setSelectedManager(m.name)}
            >
              {m.name}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {dm.dependencies.length === 0 ? (
          <div className="text-center text-foreground-secondary py-4">
            <p>No dependencies found</p>
            <p className="text-2xs mt-1">Open a project with package.json or requirements.txt</p>
          </div>
        ) : (
          dm.dependencies.map(dep => (
            <div className="flex items-center justify-between px-2 py-1 hover:bg-surface-hover rounded" key={dep.name}>
              <div className="flex items-center gap-1">
                <span className="codicon codicon-package text-2xs" />
                <span>{dep.name}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-foreground-secondary text-2xs">{dep.version}</span>
                <span className={`text-2xs px-1 rounded ${
                  dep.type === 'production' ? 'bg-blue-500/10 text-blue-500' : 'bg-green-500/10 text-green-500'
                }`}>{dep.type === 'production' ? 'prod' : 'dev'}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
