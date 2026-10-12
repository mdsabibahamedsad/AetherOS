import { useCallback, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'
import {
  $syncConflicts,
  resolveConflict,
  type SyncConflict,
} from '@/store/sync'

const RESOLVED_SAMPLE: SyncConflict[] = [
  {
    id: 'resolved-1',
    scope: 'files',
    filePath: 'notes/project-plan.md',
    localVersion: '## Updated plan\n\n- Task A completed\n- Task B in progress',
    remoteVersion: '## Updated plan\n\n- Task A in progress\n- Task B completed',
    localModifiedAt: '2026-07-20T10:00:00Z',
    remoteModifiedAt: '2026-07-20T10:30:00Z',
    status: 'resolved',
    resolution: 'merged',
    resolvedAt: '2026-07-21T08:00:00Z',
  },
  {
    id: 'resolved-2',
    scope: 'config',
    filePath: 'config/themes.json',
    localVersion: '{"theme": "dark"}',
    remoteVersion: '{"theme": "light"}',
    localModifiedAt: '2026-07-19T14:00:00Z',
    remoteModifiedAt: '2026-07-19T15:00:00Z',
    status: 'resolved',
    resolution: 'keep-local',
    resolvedAt: '2026-07-20T09:00:00Z',
  },
]

export function ConflictResolutionView() {
  const unresolvedConflicts = $syncConflicts.get()
  const [selectedConflict, setSelectedConflict] = useState<SyncConflict | null>(null)
  const [showResolved, setShowResolved] = useState(false)
  const [resolvedHistory] = useState<SyncConflict[]>(RESOLVED_SAMPLE)

  const handleResolve = useCallback((conflict: SyncConflict, resolution: SyncConflict['resolution']) => {
    resolveConflict(conflict.id, resolution)

    if (selectedConflict?.id === conflict.id) {
      setSelectedConflict(null)
    }

    notify({ kind: 'success', title: 'Conflict Resolved', message: `Resolution: ${resolution}` })
  }, [selectedConflict])

  const handleResolveAllLocal = useCallback(() => {
    for (const c of unresolvedConflicts) {
      resolveConflict(c.id, 'keep-local')
    }

    setSelectedConflict(null)
    notify({ kind: 'success', title: 'All Resolved', message: `Resolved ${unresolvedConflicts.length} conflicts — kept local versions` })
  }, [unresolvedConflicts])

  const handleResolveAllRemote = useCallback(() => {
    for (const c of unresolvedConflicts) {
      resolveConflict(c.id, 'keep-remote')
    }

    setSelectedConflict(null)
    notify({ kind: 'success', title: 'All Resolved', message: `Resolved ${unresolvedConflicts.length} conflicts — kept remote versions` })
  }, [unresolvedConflicts])

  const resolutionColor = (r?: SyncConflict['resolution']) => {
    switch (r) {
      case 'keep-local': return 'text-blue-500'

      case 'keep-remote': return 'text-purple-500'

      case 'merged': return 'text-emerald-500'

      default: return 'text-muted-foreground'
    }
  }

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div className="flex items-center justify-between">
            <div>
              <PageTitle>Conflict Resolution</PageTitle>
              <PageDescription>Review and resolve synchronization conflicts</PageDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                className="text-xs"
                disabled={unresolvedConflicts.length === 0}
                onClick={handleResolveAllLocal}
                size="sm"
                variant="outline"
              >
                Keep All Local
              </Button>
              <Button
                className="text-xs"
                disabled={unresolvedConflicts.length === 0}
                onClick={handleResolveAllRemote}
                size="sm"
                variant="outline"
              >
                Keep All Remote
              </Button>
            </div>
          </div>
        </PageHeader>
      }
    >
      <div className="flex gap-4">
        <div className="w-80 shrink-0 space-y-1">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Unresolved ({unresolvedConflicts.length})
            </h3>
            <button
              className="text-[0.6rem] text-primary hover:underline"
              onClick={() => setShowResolved(!showResolved)}
              type="button"
            >
              {showResolved ? 'Hide Resolved' : `Show Resolved (${resolvedHistory.length})`}
            </button>
          </div>

          {unresolvedConflicts.length === 0 && !showResolved && (
            <div className="grid min-h-32 place-items-center text-center">
              <div>
                <Codicon className="text-muted-foreground/40" name="check" size="1.5rem" />
                <p className="mt-1 text-xs text-muted-foreground">No conflicts</p>
              </div>
            </div>
          )}

          {unresolvedConflicts.map(conflict => (
            <button
              className={cn(
                'w-full rounded-md border px-2.5 py-2 text-left text-xs transition-colors',
                selectedConflict?.id === conflict.id
                  ? 'border-primary/40 bg-primary/5'
                  : 'border-(--ui-stroke-tertiary) hover:bg-accent/30'
              )}
              key={conflict.id}
              onClick={() => setSelectedConflict(conflict)}
              type="button"
            >
              <div className="flex items-center gap-1.5">
                <Codicon className="text-amber-500" name="warning" size="0.7rem" />
                <span className="truncate font-medium">{conflict.filePath}</span>
              </div>
              <p className="mt-0.5 text-[0.6rem] text-muted-foreground">{conflict.scope}</p>
              <div className="mt-1 flex gap-2 text-[0.55rem] text-muted-foreground">
                <span>Local: {new Date(conflict.localModifiedAt).toLocaleDateString()}</span>
                <span>Remote: {new Date(conflict.remoteModifiedAt).toLocaleDateString()}</span>
              </div>
            </button>
          ))}

          {showResolved && resolvedHistory.map(conflict => (
            <div
              className="rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-2.5 py-2 text-xs"
              key={conflict.id}
            >
              <div className="flex items-center gap-1.5">
                <Codicon className="text-emerald-500" name="check" size="0.7rem" />
                <span className="truncate font-medium">{conflict.filePath}</span>
              </div>
              <div className="mt-1 flex items-center gap-2 text-[0.6rem]">
                <span className={cn('font-medium capitalize', resolutionColor(conflict.resolution))}>
                  {conflict.resolution?.replace('-', ' ')}
                </span>
                <span className="text-muted-foreground">
                  {conflict.resolvedAt ? new Date(conflict.resolvedAt).toLocaleString() : ''}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="min-w-0 flex-1">
          {selectedConflict ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium">{selectedConflict.filePath}</h3>
                  <p className="text-xs text-muted-foreground">Scope: {selectedConflict.scope}</p>
                </div>
                <Badge variant="destructive">Unresolved</Badge>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-(--ui-stroke-tertiary)">
                  <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-3 py-1.5">
                    <span className="flex items-center gap-1.5 text-xs font-medium">
                      <Codicon name="device-desktop" size="0.75rem" />
                      Local Version
                    </span>
                    <span className="text-[0.6rem] text-muted-foreground">
                      {new Date(selectedConflict.localModifiedAt).toLocaleString()}
                    </span>
                  </div>
                  <pre className="max-h-60 overflow-auto p-3 text-xs leading-relaxed">{selectedConflict.localVersion}</pre>
                </div>

                <div className="rounded-lg border border-(--ui-stroke-tertiary)">
                  <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-3 py-1.5">
                    <span className="flex items-center gap-1.5 text-xs font-medium">
                      <Codicon name="cloud" size="0.75rem" />
                      Remote Version
                    </span>
                    <span className="text-[0.6rem] text-muted-foreground">
                      {new Date(selectedConflict.remoteModifiedAt).toLocaleString()}
                    </span>
                  </div>
                  <pre className="max-h-60 overflow-auto p-3 text-xs leading-relaxed">{selectedConflict.remoteVersion}</pre>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button className="text-xs" onClick={() => handleResolve(selectedConflict, 'keep-local')} size="sm" variant="default">
                  <Codicon name="check" size="0.75rem" />
                  Keep Local
                </Button>
                <Button className="text-xs" onClick={() => handleResolve(selectedConflict, 'keep-remote')} size="sm" variant="outline">
                  <Codicon name="check" size="0.75rem" />
                  Keep Remote
                </Button>
                <Button className="text-xs" onClick={() => handleResolve(selectedConflict, 'merged')} size="sm" variant="outline">
                  <Codicon name="git-merge" size="0.75rem" />
                  Merge
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid min-h-64 place-items-center text-center">
              <div>
                <Codicon className="text-muted-foreground/40" name="warning" size="2rem" />
                <p className="mt-2 text-sm text-muted-foreground">Select a conflict to review</p>
                <p className="text-xs text-muted-foreground/60">Choose from the list on the left</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageShell>
  )
}
