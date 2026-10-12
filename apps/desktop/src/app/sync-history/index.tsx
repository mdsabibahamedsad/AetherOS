import { useCallback, useMemo, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { SearchField } from '@/components/ui/search-field'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'
import { $syncHistory, clearSyncHistory, type SyncEvent } from '@/store/sync'

const SAMPLE_EVENTS: SyncEvent[] = Array.from({ length: 45 }, (_, i) => ({
  id: `sample-${i}`,
  scope: ['messages', 'sessions', 'memory', 'files', 'config', 'knowledge', 'plugins', 'skills'][Math.floor(Math.random() * 8)],
  type: (['push', 'pull', 'conflict', 'error'] as const)[Math.floor(Math.random() * 4)],
  status: (['success', 'failed', 'pending'] as const)[Math.floor(Math.random() * 3)] as SyncEvent['status'],
  timestamp: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
  itemsCount: Math.floor(Math.random() * 50) + 1,
  errorMessage: undefined,
  deviceId: `device-${Math.floor(Math.random() * 3) + 1}`,
})).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

const SCOPES = ['all', 'messages', 'sessions', 'memory', 'files', 'config', 'knowledge', 'plugins', 'skills']
const STATUSES = ['all', 'success', 'failed', 'pending']
const PAGE_SIZE = 10

export function SyncHistoryView() {
  const storeHistory = $syncHistory.get()
  const events = storeHistory.length > 0 ? storeHistory : SAMPLE_EVENTS

  const [search, setSearch] = useState('')
  const [scopeFilter, setScopeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)

  const filteredEvents = useMemo(() => {
    const q = search.trim().toLowerCase()

    return events.filter(e => {
      if (scopeFilter !== 'all' && e.scope !== scopeFilter) {return false}

      if (statusFilter !== 'all' && e.status !== statusFilter) {return false}

      if (q && !e.scope.toLowerCase().includes(q) && !e.type.toLowerCase().includes(q) && !e.id.toLowerCase().includes(q)) {return false}

      return true
    })
  }, [events, search, scopeFilter, statusFilter])

  const totalPages = Math.max(1, Math.ceil(filteredEvents.length / PAGE_SIZE))
  const paginatedEvents = filteredEvents.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const handleExport = useCallback(() => {
    const data = JSON.stringify(filteredEvents, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `sync-history-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    notify({ kind: 'success', title: 'Exported', message: `Exported ${filteredEvents.length} events` })
  }, [filteredEvents])

  const handleClear = useCallback(() => {
    clearSyncHistory()
    notify({ kind: 'info', title: 'History Cleared', message: 'Sync history has been cleared' })
  }, [])

  const handlePageChange = useCallback((newPage: number) => {
    setPage(Math.max(1, Math.min(newPage, totalPages)))
  }, [totalPages])

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div className="flex items-center justify-between">
            <div>
              <PageTitle>Sync History</PageTitle>
              <PageDescription>Review past synchronization activity</PageDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button className="text-xs" onClick={handleExport} size="sm" variant="outline">
                <Codicon name="download" size="0.75rem" />
                Export
              </Button>
              <Button className="text-xs" disabled={events.length === 0} onClick={handleClear} size="sm" variant="ghost">
                <Codicon name="trash" size="0.75rem" />
                Clear
              </Button>
            </div>
          </div>
        </PageHeader>
      }
    >
      <div className="flex items-center gap-3">
        <SearchField
          containerClassName="flex-1 max-w-xs"
          onChange={v => { setSearch(v); setPage(1) }}
          placeholder="Search history..."
          value={search}
        />
        <Select onValueChange={v => { setScopeFilter(v); setPage(1) }} value={scopeFilter}>
          <SelectTrigger className="h-8 w-32 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SCOPES.map(s => (
              <SelectItem key={s} value={s}>
                <span className="capitalize">{s}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select onValueChange={v => { setStatusFilter(v); setPage(1) }} value={statusFilter}>
          <SelectTrigger className="h-8 w-28 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUSES.map(s => (
              <SelectItem key={s} value={s}>
                <span className="capitalize">{s === 'failed' ? 'Failed' : s === 'pending' ? 'Pending' : s === 'all' ? 'All Status' : 'Success'}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="mt-4 space-y-1">
        {paginatedEvents.length === 0 && (
          <div className="grid min-h-40 place-items-center text-center">
            <div>
              <Codicon className="text-muted-foreground/40" name="history" size="2rem" />
              <p className="mt-2 text-sm text-muted-foreground">No sync events found</p>
              <p className="text-xs text-muted-foreground/60">Try adjusting filters</p>
            </div>
          </div>
        )}

        {paginatedEvents.map((event, i) => {
          const date = new Date(event.timestamp)
          const showDateHeader = i === 0 || new Date(paginatedEvents[i - 1]?.timestamp ?? 0).toDateString() !== date.toDateString()

          return (
            <div key={event.id}>
              {showDateHeader && (
                <p className="sticky top-0 z-10 bg-(--ui-app-background) py-1 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground">
                  {date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                </p>
              )}
              <div className="flex items-center justify-between rounded-md px-2.5 py-1.5 text-xs transition-colors hover:bg-accent/30">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className={cn(
                    'flex size-6 shrink-0 items-center justify-center rounded',
                    event.status === 'success' ? 'bg-emerald-500/10 text-emerald-500' :
                    event.status === 'failed' ? 'bg-destructive/10 text-destructive' :
                    'bg-muted text-muted-foreground'
                  )}>
                    <Codicon
                      name={event.type === 'push' ? 'arrow-up' : event.type === 'pull' ? 'arrow-down' : event.type === 'conflict' ? 'warning' : 'error'}
                      size="0.65rem"
                    />
                  </span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate font-medium capitalize">{event.scope}</span>
                      <Badge className="shrink-0 text-[0.5rem]" variant={event.status === 'failed' ? 'destructive' : event.status === 'pending' ? 'muted' : 'outline'}>
                        {event.status}
                      </Badge>
                    </div>
                    <p className="text-[0.6rem] text-muted-foreground">
                      <span className="capitalize">{event.type}</span>
                      {event.deviceId && <span> · {event.deviceId}</span>}
                      <span> · {event.itemsCount} items</span>
                    </p>
                  </div>
                </div>
                <span className="shrink-0 text-[0.6rem] text-muted-foreground">
                  {date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-[0.6rem] text-muted-foreground">
            Page {page} of {totalPages} ({filteredEvents.length} events)
          </span>
          <div className="flex items-center gap-1">
            <Button
              disabled={page <= 1}
              onClick={() => handlePageChange(page - 1)}
              size="sm"
              variant="ghost"
            >
              <Codicon name="chevron-left" size="0.75rem" />
            </Button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const start = Math.max(1, Math.min(page - 2, totalPages - 4))
              const pageNum = start + i

              if (pageNum > totalPages) {return null}

              return (
                <Button
                  className={cn('min-w-7 px-1 text-xs', pageNum === page && 'bg-primary/10 text-primary')}
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  size="sm"
                  variant="ghost"
                >
                  {pageNum}
                </Button>
              )
            })}
            <Button
              disabled={page >= totalPages}
              onClick={() => handlePageChange(page + 1)}
              size="sm"
              variant="ghost"
            >
              <Codicon name="chevron-right" size="0.75rem" />
            </Button>
          </div>
        </div>
      )}
    </PageShell>
  )
}
