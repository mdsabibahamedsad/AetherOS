import { useStore } from '@nanostores/react'

import { $communications, clearActivity } from '@/store/communications'

export function ActivityLog() {
  const comms = useStore($communications)
  const activities = comms.activityFeed

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <h2 className="text-sm font-semibold">Activity Log</h2>
        <button className="flex items-center gap-1 rounded-md px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)" onClick={clearActivity}>
          <span className="codicon codicon-clear-all" />
          Clear
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {activities.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <span className="codicon codicon-history text-3xl text-(--ui-text-tertiary)" />
              <p className="mt-2 text-sm text-(--ui-text-tertiary)">No activity yet</p>
            </div>
          </div>
        ) : (
          <div className="relative ml-6 border-l border-(--ui-stroke-tertiary)">
            {activities.map((a, i) => (
              <div className="relative ml-4 pb-4 pl-4" key={a.id}>
                <div className={`absolute -left-6 mt-1.5 size-3 rounded-full border-2 border-(--ui-stroke-tertiary) ${
                  a.type === 'message' ? 'bg-blue-500' :
                  a.type === 'connection' ? 'bg-green-500' :
                  a.type === 'ai_reply' ? 'bg-purple-500' :
                  a.type === 'error' ? 'bg-red-500' :
                  'bg-(--ui-text-tertiary)'
                }`} />
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs">{a.description}</p>
                    <p className="text-[10px] text-(--ui-text-tertiary)">
                      {a.platformName}
                      <span className="ml-2">{new Date(a.timestamp).toLocaleString()}</span>
                    </p>
                  </div>
                  <span className={`rounded-md px-1.5 py-0.5 text-[10px] ${
                    a.type === 'message' ? 'bg-blue-500/10 text-blue-500' :
                    a.type === 'connection' ? 'bg-green-500/10 text-green-500' :
                    a.type === 'error' ? 'bg-red-500/10 text-red-500' :
                    'bg-purple-500/10 text-purple-500'
                  }`}>
                    {a.type}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
