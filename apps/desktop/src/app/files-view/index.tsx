import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableSkeletonRows } from '@/components/ui/table'
import type { AetherosReadDirEntry } from '@/global'
import { readDesktopDir } from '@/lib/desktop-fs'

// Files browses the REAL project filesystem through the Electron bridge
// (`readDir`, path-validated in main). Entries expose only what the bridge
// returns (name/path/isDirectory) — sizes and dates are not shown because
// the bridge does not provide them. Previously this view rendered
// hardcoded sample files — removed.
function parentOf(path: string): string | null {
  const trimmed = path.replace(/[/\\]+$/, '')
  const idx = Math.max(trimmed.lastIndexOf('/'), trimmed.lastIndexOf('\\'))

  if (idx <= 0) {return null}

  return trimmed.slice(0, idx)
}

export function FilesView() {
  const [cwd, setCwd] = useState<string | null>(null)
  const [entries, setEntries] = useState<AetherosReadDirEntry[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [refreshTick, setRefreshTick] = useState(0)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error' | 'unavailable'>('loading')
  const [error, setError] = useState('')

  function refresh() {
    setRefreshTick(t => t + 1)
  }

  useEffect(() => {
    let live = true

    ;(async () => {
      try {
        const settings = await window.aetherosDesktop?.settings?.getDefaultProjectDir?.()

        if (!live) {return}
        const root = settings?.resolvedCwd || settings?.dir

        if (!root) {
          setStatus('unavailable')

          return
        }

        setCwd(root)
      } catch {
        if (live) {setStatus('unavailable')}
      }
    })()

    return () => {
      live = false
    }
  }, [])

  useEffect(() => {
    if (!cwd) {return}
    let live = true
    setStatus('loading')

    ;(async () => {
      try {
        const result = await readDesktopDir(cwd)

        if (!live) {return}

        if (result.error) {
          setError(result.error)
          setStatus('error')

          return
        }

        setEntries(result.entries)
        setStatus('ready')
      } catch (e) {
        if (!live) {return}
        setError(e instanceof Error ? e.message : String(e))
        setStatus('error')
      }
    })()

    return () => {
      live = false
    }
  }, [cwd, refreshTick])

  const q = searchQuery.trim().toLowerCase()
  const visible = entries.filter(e => !q || e.name.toLowerCase().includes(q))
  const parent = cwd ? parentOf(cwd) : null

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <Card className="p-6">
          <h2 className="text-2xl font-semibold tracking-tight">Files</h2>
          <p className="mb-6 text-sm text-(--ui-text-tertiary)">Browse the project filesystem</p>

          <div className="mb-4 flex flex-col gap-3 sm:flex-row">
            <Input
              className="flex-1 sm:w-64"
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Filter by name..."
              value={searchQuery}
            />
            <div className="flex items-center gap-2">
              <Button
                disabled={!parent || status === 'loading'}
                onClick={() => parent && setCwd(parent)}
                size="sm"
                variant="secondary"
              >
                Up
              </Button>
              <Button disabled={status === 'loading'} onClick={refresh} size="sm" variant="outline">
                Refresh
              </Button>
            </div>
          </div>

          <p className="mb-3 truncate font-mono text-xs text-(--ui-text-tertiary)" title={cwd ?? ''}>
            {cwd ?? 'No directory selected'}
          </p>

          {status === 'loading' ? (
            <Table loading>
              <TableHead>
                <TableRow>
                  <TableHeader>Name</TableHeader>
                  <TableHeader>Type</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableSkeletonRows columns={2} rows={8} />
              </TableBody>
            </Table>
          ) : status === 'unavailable' ? (
            <EmptyState
              description="The desktop bridge is not connected, so no directory can be listed."
              icon="file-directory"
              title="Filesystem bridge unavailable"
            />
          ) : status === 'error' ? (
            <ErrorState description={error || 'The directory could not be read.'} title="Could not list directory">
              <Button onClick={refresh} size="sm" variant="outline">
                Retry
              </Button>
            </ErrorState>
          ) : visible.length === 0 ? (
            <EmptyState
              description={entries.length === 0 ? 'This directory contains no entries.' : 'No entry names match the filter.'}
              icon="file-directory"
              title={entries.length === 0 ? 'Empty directory' : 'No matches'}
            />
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeader>Name</TableHeader>
                  <TableHeader>Type</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {visible.map(entry => (
                  <TableRow key={entry.path}>
                    <TableCell>
                      {entry.isDirectory ? (
                        <button className="truncate text-left font-medium underline" onClick={() => setCwd(entry.path)} type="button">
                          <span className="codicon codicon-folder mr-2" />
                          {entry.name}
                        </button>
                      ) : (
                        <span className="truncate">
                          <span className="codicon codicon-file mr-2" />
                          {entry.name}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-(--ui-text-tertiary)">
                      {entry.isDirectory ? 'Folder' : 'File'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      </div>
    </ScrollArea>
  )
}
