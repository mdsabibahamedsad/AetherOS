import { useStore } from '@nanostores/react'
import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  automationBuild,
  type AutomationDef,
  automationDelete,
  automationDisable,
  automationEnable,
  automationHealth,
  automationPreview,
  automationRun,
  automationRuns,
  automationSearch,
  automationStopAll,
} from '@/lib/automation-client'
import { $gateway } from '@/store/gateway'

type Tab = 'overview' | 'automations' | 'runs' | 'builder'

function useGateway(): ((method: string, params?: Record<string, unknown>) => Promise<never>) | null {
  const client = useStore($gateway) as unknown as {
    request?: (method: string, params?: Record<string, unknown>) => Promise<never>
  } | null

  return client?.request?.bind(client) ?? null
}

export function AutomationCenter() {
  const requestGateway = useGateway()
  const [tab, setTab] = useState<Tab>('overview')
  const [autos, setAutos] = useState<AutomationDef[]>([])
  const [runs, setRuns] = useState<Record<string, unknown>[]>([])
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  const [selected, setSelected] = useState<string>('')
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)
  const [nlText, setNlText] = useState('')
  const [built, setBuilt] = useState<Record<string, unknown> | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [error, setError] = useState('')

  async function refresh() {
    if (!requestGateway) {return}
    setStatus('loading')

    try {
      setAutos(await automationSearch(requestGateway))
      setRuns(await automationRuns(requestGateway))
      setHealth(await automationHealth(requestGateway))
      setStatus('idle')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  useEffect(() => {
    if (requestGateway) {void refresh()}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestGateway !== null])

  if (requestGateway === null) {
    return (
      <ScrollArea className="h-full">
        <div className="mx-auto max-w-4xl p-6">
          <EmptyState description="Connect the gateway to manage live automations." icon="zap" title="Automation backend unavailable" />
        </div>
      </ScrollArea>
    )
  }

  async function inspect(id: string) {
    if (!requestGateway) {return}
    setSelected(id)

    try {
      setPreview(await automationPreview(requestGateway, id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <Card className="p-6">
          <h2 className="text-2xl font-semibold tracking-tight">Automation Center</h2>
          <p className="text-(--ui-text-tertiary) mb-4">Live autonomous operations. Every value comes from the backend.</p>
          <div className="flex gap-2 text-xs">
            {(['overview', 'automations', 'runs', 'builder'] as Tab[]).map(t => (
              <button className={tab === t ? 'font-semibold underline' : 'text-(--ui-text-tertiary)'} key={t}
                onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
            <span className="flex-1" />
            <button className="underline" onClick={() => void refresh()}>Refresh</button>
            <button className="text-red-400 underline" onClick={() => requestGateway && void automationStopAll(requestGateway).then(() => void refresh())}>Stop all</button>
          </div>
        </Card>

        {status === 'error' && <Card className="p-4 text-xs text-red-400">Automation request failed: {error}</Card>}

        {tab === 'overview' && (
          <Card className="p-4">
            {!health ? (
              <EmptyState description={status === 'loading' ? 'Loading…' : 'Press Refresh.'} icon="activity" title="No health data" />
            ) : (
              <pre className="whitespace-pre-wrap text-[11px]">{JSON.stringify(health, null, 2)}</pre>
            )}
          </Card>
        )}

        {tab === 'automations' && (
          <Card className="p-4">
            {autos.length === 0 ? (
              <EmptyState description="Build one in the builder tab." icon="zap" title="No automations" />
            ) : autos.map(a => (
              <div className="border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0" key={a.id}>
                <div className="flex items-center gap-2">
                  <button className="flex-1 truncate text-left font-medium underline" onClick={() => void inspect(a.id)}>{a.name}</button>
                  <Badge className="text-[8px]" variant="outline">{a.auto_type}</Badge>
                  <Badge className="text-[8px]" variant="outline">{a.enabled ? 'active' : 'draft'}</Badge>
                  <button className="underline" onClick={() => requestGateway && void automationEnable(requestGateway, a.id).then(() => void refresh())}>Enable</button>
                  <button className="underline" onClick={() => requestGateway && void automationDisable(requestGateway, a.id).then(() => void refresh())}>Disable</button>
                  <button className="underline" onClick={() => requestGateway && void automationRun(requestGateway, a.id, true).then(r => setPreview({ dry_run: r }))}>Dry-run</button>
                  <button className="underline" onClick={() => requestGateway && void automationRun(requestGateway, a.id).then(() => void refresh())}>Run now</button>
                  <button className="text-red-400 underline" onClick={() => requestGateway && void automationDelete(requestGateway, a.id).then(() => void refresh())}>Delete</button>
                </div>
                {selected === a.id && preview && (
                  <pre className="mt-1 whitespace-pre-wrap text-[11px] text-(--ui-text-tertiary)">{JSON.stringify(preview, null, 2)}</pre>
                )}
              </div>
            ))}
          </Card>
        )}

        {tab === 'runs' && (
          <Card className="p-4">
            {runs.length === 0 ? (
              <EmptyState description="Runs appear here with states, durations and costs." icon="clock" title="No runs yet" />
            ) : runs.map((r, i) => {
              const run = r as Record<string, unknown>

              return (
                <div className="border-b border-(--ui-border) py-1 text-xs last:border-0" key={String(run.run_id ?? i)}>
                  <span className="font-medium">{String(run.run_id ?? '').slice(0, 8)}</span>
                  {' — '}{String(run.state ?? '')}
                  <span className="ml-2 text-(--ui-text-tertiary)">trigger: {String(run.trigger_kind ?? '')} steps: {Array.isArray(run.steps) ? run.steps.length : 0}</span>
                  {run.error ? <span className="ml-2 text-red-400">{String(run.error)}</span> : null}
                </div>
              )
            })}
          </Card>
        )}

        {tab === 'builder' && (
          <Card className="p-4">
            <div className="mb-3 flex gap-2">
              <input className="flex-1 border px-2 py-1 text-xs" onChange={e => setNlText(e.target.value)}
                placeholder='e.g. "Every Friday research AI agent developments and send me a summary"'
                value={nlText} />
              <button className="text-xs underline" onClick={() => requestGateway && nlText.trim() && automationBuild(requestGateway, nlText.trim()).then(setBuilt).catch(e => { setError(String(e)); setStatus('error') })}>Build plan</button>
            </div>
            {!built ? (
              <EmptyState description="A draft plan preview appears here. Nothing activates without approval." icon="plus" title="Describe an automation" />
            ) : (
              <pre className="whitespace-pre-wrap text-[11px]">{JSON.stringify(built, null, 2)}</pre>
            )}
          </Card>
        )}
      </div>
    </ScrollArea>
  )
}
