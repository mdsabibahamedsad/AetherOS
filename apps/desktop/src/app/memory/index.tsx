import { useStore } from '@nanostores/react'
import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  memoryExplain,
  memoryForget,
  memoryHealth,
  type MemoryHealth,
  memoryProject,
  memorySearch,
  type MemorySearchHit,
  memoryTimeline,
} from '@/lib/memory2-client'
import { $gateway } from '@/store/gateway'

type Tab = 'search' | 'timeline' | 'project' | 'inspector' | 'health'

function useGateway(): ((method: string, params?: Record<string, unknown>) => Promise<never>) | null {
  const client = useStore($gateway) as unknown as {
    request?: (method: string, params?: Record<string, unknown>) => Promise<never>
  } | null

  return client?.request?.bind(client) ?? null
}

export function MemoryView() {
  const requestGateway = useGateway()
  const [tab, setTab] = useState<Tab>('search')
  const [query, setQuery] = useState('')
  const [projectId, setProjectId] = useState('')
  const [hits, setHits] = useState<MemorySearchHit[]>([])
  const [timeline, setTimeline] = useState<unknown[]>([])
  const [project, setProject] = useState<Record<string, unknown> | null>(null)
  const [health, setHealth] = useState<MemoryHealth | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [explanation, setExplanation] = useState<Record<string, unknown> | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'error' | 'unavailable'>('idle')
  const [error, setError] = useState('')

  const unavailable = requestGateway === null

  async function runSearch() {
    if (!requestGateway || !query.trim()) {return}
    setStatus('loading')

    try {
      const res = await memorySearch(requestGateway, query, { project_id: projectId || undefined })
      setHits(res)
      setStatus('idle')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  async function loadTimeline() {
    if (!requestGateway) {return}
    setStatus('loading')

    try {
      setTimeline(await memoryTimeline(requestGateway, { project_id: projectId || undefined }))
      setStatus('idle')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  async function loadProject() {
    if (!requestGateway || !projectId.trim()) {return}
    setStatus('loading')

    try {
      setProject(await memoryProject(requestGateway, projectId.trim()))
      setStatus('idle')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  async function loadHealth() {
    if (!requestGateway) {return}
    setStatus('loading')

    try {
      setHealth(await memoryHealth(requestGateway))
      setStatus('idle')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  async function inspect(id: string) {
    if (!requestGateway) {return}
    setSelectedId(id)

    try {
      setExplanation(await memoryExplain(requestGateway, id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  async function forget(id: string) {
    if (!requestGateway) {return}

    try {
      await memoryForget(requestGateway, { id })
      setHits(h => h.filter(x => x.id !== id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  useEffect(() => {
    if (tab === 'timeline' && requestGateway) {void loadTimeline()}

    if (tab === 'health' && requestGateway) {void loadHealth()}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab])

  if (unavailable) {
    return (
      <ScrollArea className="h-full">
        <div className="mx-auto max-w-4xl p-6">
          <EmptyState description="Connect the gateway to browse Memory 2.0." icon="database" title="Memory backend unavailable" />
        </div>
      </ScrollArea>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <Card className="p-6">
          <h2 className="text-2xl font-semibold tracking-tight">Memory Center</h2>
          <p className="text-(--ui-text-tertiary) mb-4">Live Memory 2.0 state. Every value below comes from the backend.</p>
          <div className="flex gap-2 text-xs">
            {(['search', 'timeline', 'project', 'inspector', 'health'] as Tab[]).map(t => (
              <button className={tab === t ? 'font-semibold underline' : 'text-(--ui-text-tertiary)'} key={t}
                onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
          </div>
        </Card>

        {status === 'error' && (
          <Card className="p-4 text-xs text-red-400">Memory request failed: {error}</Card>
        )}

        {tab === 'search' && (
          <Card className="p-4">
            <div className="flex gap-2 mb-3">
              <input className="flex-1 border px-2 py-1 text-xs" onChange={e => setQuery(e.target.value)}
                placeholder='Search memories, e.g. "Why did we choose Electron?"'
                value={query} />
              <input className="border px-2 py-1 text-xs" onChange={e => setProjectId(e.target.value)}
                placeholder="Project filter (optional)" value={projectId} />
              <button className="text-xs underline" onClick={() => void runSearch()}>
                {status === 'loading' ? 'Searching…' : 'Search'}
              </button>
            </div>
            {hits.length === 0 ? (
              <EmptyState description="Run a search to see live memory hits with scores." icon="search" title="No results" />
            ) : (
              <div className="space-y-2">
                {hits.map(h => (
                  <div className="border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0" key={h.id}>
                    <div className="flex items-center gap-2">
                      <span className="flex-1 truncate font-medium">{h.summary || h.content}</span>
                      <Badge className="text-[8px]" variant="outline">{h.type}</Badge>
                      <Badge className="text-[8px]" variant="outline">score {h.score.toFixed(2)}</Badge>
                      <Badge className="text-[8px]" variant="outline">{h.confidence_band}</Badge>
                      {h.conflicted && <Badge className="text-[8px]" variant="outline">conflicted</Badge>}
                    </div>
                    <div className="text-[10px] text-(--ui-text-tertiary)">{h.explanation}</div>
                    <div className="flex gap-2 text-[10px]">
                      <button className="underline" onClick={() => { setTab('inspector'); void inspect(h.id) }}>Inspect</button>
                      <button className="underline text-red-400" onClick={() => void forget(h.id)}>Forget</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {tab === 'timeline' && (
          <Card className="p-4">
            <h3 className="mb-3 text-sm font-medium">Timeline (live)</h3>
            {timeline.length === 0 ? (
              <EmptyState description="Memories will appear here as they are created." icon="clock" title="No timeline entries" />
            ) : (
              <div className="space-y-1 text-xs">
                {(timeline as Record<string, unknown>[]).map((t, i) => (
                  <div className="border-b border-(--ui-border) py-1 last:border-0" key={String(t.id ?? i)}>
                    <span className="text-(--ui-text-tertiary)">{new Date((t.created_at as number) * 1000).toLocaleString()}</span>
                    {' — '}{String(t.summary ?? '')}
                    <Badge className="ml-2 text-[8px]" variant="outline">{String(t.type ?? '')}</Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {tab === 'project' && (
          <Card className="p-4">
            <div className="mb-3 flex gap-2">
              <input className="flex-1 border px-2 py-1 text-xs" onChange={e => setProjectId(e.target.value)}
                placeholder="Project id" value={projectId} />
              <button className="text-xs underline" onClick={() => void loadProject()}>Load</button>
            </div>
            {!project ? (
              <EmptyState description="Enter a project id to see its live memory panel." icon="folder" title="No project loaded" />
            ) : (
              <pre className="whitespace-pre-wrap text-[11px]">{JSON.stringify(project, null, 2)}</pre>
            )}
          </Card>
        )}

        {tab === 'inspector' && (
          <Card className="p-4">
            <h3 className="mb-3 text-sm font-medium">Memory Inspector</h3>
            {!explanation ? (
              <EmptyState description={selectedId ? `Loading ${selectedId}…` : 'Select Inspect on a search hit.'} icon="info" title="Nothing selected" />
            ) : (
              <pre className="whitespace-pre-wrap text-[11px]">{JSON.stringify(explanation, null, 2)}</pre>
            )}
          </Card>
        )}

        {tab === 'health' && (
          <Card className="p-4">
            <h3 className="mb-3 text-sm font-medium">Memory Health (measured)</h3>
            {!health ? (
              <EmptyState description={status === 'loading' ? 'Loading…' : 'Open this tab to query live health.'} icon="activity" title="Not loaded" />
            ) : (
              <pre className="whitespace-pre-wrap text-[11px]">{JSON.stringify(health, null, 2)}</pre>
            )}
          </Card>
        )}
      </div>
    </ScrollArea>
  )
}
