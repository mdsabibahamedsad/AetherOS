import { useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { EmptyState } from '@/components/ui/empty-state'
import { ScrollArea } from '@/components/ui/scroll-area'
import { SearchField } from '@/components/ui/search-field'
import { notify } from '@/store/notifications'

// Audit Log renders the REAL backend log stream (Electron `getRecentLogs`)
// with local search. It previously displayed 500 procedurally generated
// entries — removed. Lines are shown verbatim; nothing is synthesized.
export function AuditLogView() {
  const [lines, setLines] = useState<string[]>([])
  const [sourcePath, setSourcePath] = useState('')
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [visibleCount, setVisibleCount] = useState(200)

  async function refresh() {
    setLoading(true)
    setFailed(false)

    try {
      const recent = await window.aetherosDesktop?.getRecentLogs?.()

      if (recent?.lines) {
        setLines(recent.lines)
        setSourcePath(recent.path ?? '')
      } else {
        setFailed(true)
      }
    } catch {
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()

    if (!q) {return lines}

    return lines.filter(l => l.toLowerCase().includes(q))
  }, [lines, searchQuery])

  const visible = filtered.slice(-visibleCount)

  function handleExport() {
    try {
      const blob = new Blob([filtered.join('\n')], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'aetheros-backend.log'
      a.click()
      URL.revokeObjectURL(url)
      notify({ kind: 'success', title: 'Log Exported', message: `${filtered.length} lines exported` })
    } catch {
      notify({ kind: 'error', title: 'Export Failed', message: 'Could not export log lines' })
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <SearchField
          containerClassName="w-64"
          onChange={setSearchQuery}
          placeholder="Filter log lines..."
          value={searchQuery}
        />
        <span className="truncate text-[0.65rem] text-muted-foreground/60" title={sourcePath}>
          {sourcePath || 'backend log stream'}
        </span>
        <div className="ml-auto flex items-center gap-1">
          <Button className="text-xs" onClick={() => window.aetherosDesktop?.revealLogs?.()} size="sm" variant="ghost">
            <Codicon className="mr-1" name="folder-opened" size="0.75rem" /> Reveal
          </Button>
          <Button className="text-xs" onClick={handleExport} size="sm" variant="ghost">
            <Codicon className="mr-1" name="export" size="0.75rem" /> Export
          </Button>
          <Button className="text-xs" onClick={() => void refresh()} size="sm" variant="ghost">
            <Codicon className="mr-1" name="refresh" size="0.75rem" /> Refresh
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 font-mono text-[0.65rem] leading-5">
          {loading ? (
            <p className="py-8 text-center text-muted-foreground">Loading backend logs…</p>
          ) : failed ? (
            <div className="py-8 text-center">
              <EmptyState
                description="The backend log stream could not be read. Check that the backend is running."
                icon="history"
                title="Logs unavailable"
              />
            </div>
          ) : visible.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">
              {lines.length === 0 ? 'No log lines yet' : 'No lines match the filter'}
            </p>
          ) : (
            <>
              {filtered.length > visible.length && (
                <button
                  className="mb-2 text-muted-foreground underline"
                  onClick={() => setVisibleCount(c => c + 500)}
                  type="button"
                >
                  Show more ({filtered.length - visible.length} older lines hidden)
                </button>
              )}
              {visible.map((line, i) => (
                <div className="whitespace-pre-wrap break-words text-(--ui-text-tertiary)" key={`${i}-${line.slice(0, 32)}`}>
                  {line}
                </div>
              ))}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
