import { useStore } from '@nanostores/react'
import { useCallback, useMemo, useState } from 'react'

import { getActionStatus, runBackup, runImport } from '@/aetheros'
import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { pollActionDone } from '@/lib/backup'
import { cn } from '@/lib/utils'
import { notify, notifyError } from '@/store/notifications'
import {
  $syncConflicts,
  $syncEnabled,
  $syncError,
  $syncHistory,
  $syncLastSync,
  $syncOnline,
  $syncScopes,
  $syncStatus,
  addSyncEvent,
  clearSyncError,
  completeSync,
  setSyncScope,
  type SyncEvent,
} from '@/store/sync'

const SCOPE_ICONS: Record<string, string> = {
  messages: 'comment-discussion',
  sessions: 'window',
  memory: 'database',
  knowledge: 'book',
  files: 'file-directory',
  config: 'gear',
  plugins: 'extensions',
  skills: 'hubot',
  cron: 'history',
  contacts: 'organization',
  bookmarks: 'bookmark',
  templates: 'copy',
  'agent-state': 'robot',
  toolsets: 'tools',
  gateway: 'server',
  'ui-state': 'paintcan',
}

// Device sync has no backend in this build: scopes/history/conflicts below
// are LOCAL state. Backups are real — POST /api/ops/backup spawns
// `aetheros backup` and restore runs `aetheros import`, both tracked via
// getActionStatus until the process exits. Nothing here simulates success.
export function SyncDashboardView() {
  const status = useStore($syncStatus)
  const enabled = useStore($syncEnabled)
  const scopes = useStore($syncScopes)
  const history = useStore($syncHistory)
  const conflicts = useStore($syncConflicts)
  const lastSync = useStore($syncLastSync)
  const online = useStore($syncOnline)
  const syncError = useStore($syncError)

  const [busy, setBusy] = useState(false)
  const [archive, setArchive] = useState('')

  const backupEvents = useMemo(() => history.filter(e => e.scope === 'backup'), [history])
  const lastBackup = backupEvents.find(e => e.status === 'success') ?? null
  const failedCount = useMemo(() => history.filter(e => e.status === 'failed').length, [history])

  const statusIcon = useMemo(() => {
    if (!enabled) {return 'circle-slash'}

    if (syncError) {return 'error'}

    if (status === 'syncing') {return 'sync'}

    if (status === 'paused') {return 'pause'}

    return online ? 'check' : 'circle-slash'
  }, [status, enabled, online, syncError])

  const statusColor = useMemo(() => {
    if (!enabled || !online) {return 'text-muted-foreground'}

    if (syncError) {return 'text-destructive'}

    if (status === 'syncing') {return 'text-primary'}

    if (status === 'paused') {return 'text-amber-500'}

    return 'text-emerald-500'
  }, [status, enabled, online, syncError])

  const statusLabel = useMemo(() => {
    if (!enabled) {return 'Disabled'}

    if (syncError) {return 'Error'}

    if (status === 'syncing') {return 'Working'}

    if (status === 'paused') {return 'Paused'}

    return online ? 'Online' : 'Offline'
  }, [status, enabled, online, syncError])

  const handleRunBackup = useCallback(async () => {
    if (busy) {return}
    setBusy(true)
    clearSyncError()
    const id = `backup-${Date.now()}`

    try {
      await runBackup()
      const outcome = await pollActionDone(getActionStatus, 'backup')
      completeSync(outcome.ok ? undefined : 'Backup failed')

      if (!outcome.ok) {
        const tail = outcome.lines.slice(-3).join('\n')
        throw new Error(tail || 'Backup exited non-zero')
      }

      addSyncEvent({
        id,
        scope: 'backup',
        type: 'push',
        status: 'success',
        timestamp: new Date().toISOString(),
        itemsCount: 1,
      })
      notify({ kind: 'success', title: 'Backup complete', message: 'AetherOS backup finished successfully' })
    } catch (error) {
      completeSync(error instanceof Error ? error.message : String(error))
      addSyncEvent({
        id,
        scope: 'backup',
        type: 'error',
        status: 'failed',
        timestamp: new Date().toISOString(),
        itemsCount: 0,
        errorMessage: error instanceof Error ? error.message : String(error),
      })
      notifyError(error, 'Backup failed')
    } finally {
      setBusy(false)
    }
  }, [busy])

  const handleRestore = useCallback(async () => {
    const path = archive.trim()

    if (!path || busy) {return}

    // Destructive: overwrites local config/state. Backend aborts without
    // force; the UI confirms explicitly before sending force=true.
    if (!window.confirm(`Restore from this archive?\n\n${path}\n\nThis overwrites local configuration and state.`)) {
      return
    }

    setBusy(true)
    const id = `restore-${Date.now()}`

    try {
      await runImport(path, true)
      const outcome = await pollActionDone(getActionStatus, 'import')

      if (!outcome.ok) {
        const tail = outcome.lines.slice(-3).join('\n')
        throw new Error(tail || 'Restore exited non-zero')
      }

      addSyncEvent({
        id,
        scope: 'backup',
        type: 'pull',
        status: 'success',
        timestamp: new Date().toISOString(),
        itemsCount: 1,
      })
      notify({ kind: 'success', title: 'Restore complete', message: 'Archive restored — restart AetherOS to apply' })
    } catch (error) {
      addSyncEvent({
        id,
        scope: 'backup',
        type: 'error',
        status: 'failed',
        timestamp: new Date().toISOString(),
        itemsCount: 0,
        errorMessage: error instanceof Error ? error.message : String(error),
      })
      notifyError(error, 'Restore failed')
    } finally {
      setBusy(false)
    }
  }, [archive, busy])

  const handleToggleScope = useCallback((scopeId: string, value: boolean) => {
    setSyncScope(scopeId, value)
    const scope = $syncScopes.get().find(s => s.id === scopeId)
    notify({ kind: 'info', title: `${scope?.name ?? scopeId}`, message: value ? 'Sync enabled' : 'Sync disabled' })
  }, [])

  const enabledCount = useMemo(() => scopes.filter(s => s.enabled).length, [scopes])

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div className="flex items-center justify-between">
            <div>
              <PageTitle>Sync & Backup</PageTitle>
              <PageDescription>Local sync preferences and real backend backups</PageDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className={cn('flex items-center gap-1.5', statusColor)}>
                  <Codicon name={statusIcon} size="0.75rem" />
                  {statusLabel}
                </span>
              </div>
              <Button disabled={busy || !enabled} onClick={() => void handleRunBackup()} size="sm">
                <Codicon className={cn(busy && 'animate-spin')} name={busy ? 'sync' : 'database'} size="0.85rem" />
                {busy ? 'Working…' : 'Run backup'}
              </Button>
            </div>
          </div>
        </PageHeader>
      }
    >
      <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/5 p-3 text-xs text-muted-foreground" role="note">
        Device sync has no connected backend in this build — scopes and history below are local state.
        Backups and restores run against the real backend (`aetheros backup` / `aetheros import`).
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Codicon name="checklist" size="0.85rem" />
            <span>Scopes</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{enabledCount}/{scopes.length}</p>
        </div>
        <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Codicon name="warning" size="0.85rem" />
            <span>Conflicts</span>
          </div>
          <p className={cn('mt-1 text-lg font-semibold', conflicts.length > 0 && 'text-amber-500')}>{conflicts.length}</p>
        </div>
        <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Codicon name="database" size="0.85rem" />
            <span>Backups</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{backupEvents.filter(e => e.status === 'success').length}</p>
        </div>
        <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Codicon name="error" size="0.85rem" />
            <span>Failed</span>
          </div>
          <p className={cn('mt-1 text-lg font-semibold', failedCount > 0 && 'text-destructive')}>{failedCount}</p>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-(--ui-stroke-tertiary) p-4">
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Backup & Restore</h3>
        <p className="text-xs text-muted-foreground" role="status">
          {lastBackup
            ? `Last backup: ${new Date(lastBackup.timestamp).toLocaleString()}`
            : lastSync
              ? `Last activity: ${new Date(lastSync).toLocaleString()}`
              : 'No backups recorded yet'}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Input
            aria-label="Backup archive path for restore"
            className="h-8 max-w-sm flex-1 text-xs"
            disabled={busy}
            onChange={e => setArchive(e.target.value)}
            placeholder="/path/to/aetheros-backup.tar.gz"
            value={archive}
          />
          <Button disabled={busy || !archive.trim()} onClick={() => void handleRestore()} size="sm" variant="outline">
            Restore from archive
          </Button>
        </div>
        <p className="mt-2 text-[0.65rem] text-muted-foreground">
          Restore overwrites local configuration and state, then asks you to restart. Confirmation is required.
        </p>
      </div>

      <div className="mt-4">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Local Sync Scopes</h3>
        <div className="grid grid-cols-2 gap-2">
          {scopes.map(scope => (
            <div
              className="flex items-center justify-between rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) px-3 py-2"
              key={scope.id}
            >
              <div className="flex items-center gap-2.5">
                <span className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Codicon name={SCOPE_ICONS[scope.id] ?? 'symbol-misc'} size="0.85rem" />
                </span>
                <div>
                  <p className="text-xs font-medium">{scope.name}</p>
                  <p className="text-[0.6rem] text-muted-foreground">{scope.description}</p>
                </div>
              </div>
              <Switch checked={scope.enabled} onCheckedChange={v => handleToggleScope(scope.id, v)} />
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recent Activity</h3>
        <div className="space-y-1">
          {history.length === 0 && (
            <div className="grid min-h-24 place-items-center text-center">
              <div>
                <Codicon className="text-muted-foreground/40" name="history" size="1.5rem" />
                <p className="mt-1 text-xs text-muted-foreground">No sync activity yet</p>
              </div>
            </div>
          )}
          {history.slice(0, 10).map(event => (
            <EventRow event={event} key={event.id} />
          ))}
        </div>
      </div>
    </PageShell>
  )
}

function EventRow({ event }: { event: SyncEvent }) {
  const typeIcon = useMemo(() => {
    switch (event.type) {
      case 'push': return 'arrow-up'

      case 'pull': return 'arrow-down'

      case 'conflict': return 'warning'

      case 'error': return 'error'
    }
  }, [event.type])

  const statusColor = useMemo(() => {
    switch (event.status) {
      case 'success': return 'text-emerald-500'

      case 'failed': return 'text-destructive'

      case 'pending': return 'text-amber-500'
    }
  }, [event.status])

  return (
    <div className="flex items-center justify-between rounded-md px-2.5 py-1.5 text-xs transition-colors hover:bg-accent/30">
      <div className="flex items-center gap-2.5">
        <Codicon className={statusColor} name={typeIcon} size="0.75rem" />
        <span className="capitalize">{event.type} - {event.scope}</span>
        <Badge className="text-[0.55rem]" variant={event.status === 'failed' ? 'destructive' : 'muted'}>{event.status}</Badge>
        <span className="text-muted-foreground">{event.itemsCount} items</span>
      </div>
      <span className="text-muted-foreground">{new Date(event.timestamp).toLocaleTimeString()}</span>
    </div>
  )
}
