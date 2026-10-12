import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  swarmApprove,
  swarmEvents,
  type SwarmRunEvent,
  type SwarmRunView,
  swarmStart,
  swarmStatus,
  swarmStop,
  swarmTrace,
} from '@/lib/swarm-client'
import { $gateway } from '@/store/gateway'

type Tab = 'run' | 'tasks' | 'agents' | 'events' | 'trace'

function useGateway(): ((method: string, params?: Record<string, unknown>) => Promise<never>) | null {
  const client = useStore($gateway) as unknown as {
    request?: (method: string, params?: Record<string, unknown>) => Promise<never>
  } | null

  return client?.request?.bind(client) ?? null
}

export function SwarmCenter() {
  const requestGateway = useGateway()
  const [tab, setTab] = useState<Tab>('run')
  const [goal, setGoal] = useState('')
  const [forceSingle, setForceSingle] = useState(false)
  const [run, setRun] = useState<SwarmRunView | null>(null)
  const [events, setEvents] = useState<SwarmRunEvent[]>([])
  const [trace, setTrace] = useState<Record<string, unknown> | null>(null)
  const [selectedTask, setSelectedTask] = useState<string>('')
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [approvalId, setApprovalId] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [error, setError] = useState('')

  if (requestGateway === null) {
    return (
      <ScrollArea className="h-full">
        <div className="mx-auto max-w-4xl p-6">
          <EmptyState description="Connect the gateway to plan and inspect live swarm runs." icon="hub" title="Swarm backend unavailable" />
        </div>
      </ScrollArea>
    )
  }

  async function start() {
    if (!requestGateway || !goal.trim()) {return}
    setStatus('loading')

    try {
      const r = await swarmStart(requestGateway, goal.trim(), { force_single: forceSingle })
      setRun(r)
      setStatus('idle')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  async function refresh() {
    if (!requestGateway || !run) {return}

    try {
      setRun(await swarmStatus(requestGateway, run.run_id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  async function loadEvents() {
    if (!requestGateway || !run) {return}

    try {
      setEvents(await swarmEvents(requestGateway, run.run_id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  async function loadTrace() {
    if (!requestGateway || !run) {return}

    try {
      setTrace(await swarmTrace(requestGateway, run.run_id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <Card className="p-6">
          <h2 className="text-2xl font-semibold tracking-tight">Swarm Center</h2>
          <p className="text-(--ui-text-tertiary) mb-4">Live multi-agent runs. Every value comes from the backend.</p>
          <div className="mb-3 flex gap-2">
            <input className="flex-1 border px-2 py-1 text-xs" onChange={e => setGoal(e.target.value)}
              placeholder="Goal, e.g. Research three static-site generators then compare them"
              value={goal} />
            <label className="flex items-center gap-1 text-xs">
              <input checked={forceSingle} onChange={e => setForceSingle(e.target.checked)} type="checkbox" />
              single-agent
            </label>
            <button className="text-xs underline" onClick={() => void start()}>
              {status === 'loading' ? 'Planning…' : 'Plan run'}
            </button>
            {run && <button className="text-xs underline" onClick={() => void refresh()}>Refresh</button>}
            {run && <button className="text-xs text-red-400 underline" onClick={() => requestGateway && void swarmStop(requestGateway, run.run_id).then(() => void refresh())}>Stop</button>}
          </div>
          <div className="flex gap-2 text-xs">
            {(['run', 'tasks', 'agents', 'events', 'trace'] as Tab[]).map(t => (
              <button className={tab === t ? 'font-semibold underline' : 'text-(--ui-text-tertiary)'} key={t}
                onClick={() => { setTab(t);

 if (t === 'events') {void loadEvents();}

 if (t === 'trace') {void loadTrace()} }}>
                {t}
              </button>
            ))}
          </div>
        </Card>

        {status === 'error' && <Card className="p-4 text-xs text-red-400">Swarm request failed: {error}</Card>}

        {!run ? (
          <EmptyState description="Enter a goal above to get a live orchestration plan." icon="hub" title="No run planned" />
        ) : (
          <>
            {tab === 'run' && (
              <Card className="p-4 text-xs">
                <div className="mb-2 flex items-center gap-2">
                  <Badge className="text-[8px]" variant="outline">{run.mode}</Badge>
                  <Badge className="text-[8px]" variant="outline">{run.topology}</Badge>
                  <Badge className="text-[8px]" variant="outline">{run.status}</Badge>
                  <span className="text-(--ui-text-tertiary)">roles: {run.roles.join(', ')}</span>
                </div>
                {run.final ? (
                  <pre className="whitespace-pre-wrap text-[11px]">{JSON.stringify(run.final, null, 2)}</pre>
                ) : (
                  <p className="text-(--ui-text-tertiary)">Planned with {run.tasks.length} tasks and {run.agents.length} agents. Execution state refreshes via Refresh.</p>
                )}
                <div className="mt-3 flex gap-2">
                  <input className="border px-2 py-1 text-xs" onChange={e => setApprovalId(e.target.value)}
                    placeholder="Approval request id" value={approvalId} />
                  <button className="text-xs underline" onClick={() => requestGateway && approvalId && void swarmApprove(requestGateway, approvalId, true)}>Approve</button>
                  <button className="text-xs text-red-400 underline" onClick={() => requestGateway && approvalId && void swarmApprove(requestGateway, approvalId, false)}>Reject</button>
                </div>
              </Card>
            )}
            {tab === 'tasks' && (
              <Card className="p-4">
                {run.tasks.map(t => (
                  <div className="border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0" key={t.id}>
                    <button className="flex w-full items-center gap-2 text-left" onClick={() => setSelectedTask(selectedTask === t.id ? '' : t.id)}>
                      <span className="flex-1 truncate font-medium">{t.goal}</span>
                      <Badge className="text-[8px]" variant="outline">{t.role}</Badge>
                      <Badge className="text-[8px]" variant="outline">{t.state}</Badge>
                    </button>
                    {selectedTask === t.id && (
                      <pre className="mt-1 whitespace-pre-wrap text-[11px] text-(--ui-text-tertiary)">{JSON.stringify(t, null, 2)}</pre>
                    )}
                  </div>
                ))}
              </Card>
            )}
            {tab === 'agents' && (
              <Card className="p-4">
                {run.agents.map(a => (
                  <div className="border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0" key={a.id}>
                    <button className="flex w-full items-center gap-2 text-left" onClick={() => setSelectedAgent(selectedAgent === a.id ? '' : a.id)}>
                      <span className="flex-1 truncate font-medium">{a.role}</span>
                      <Badge className="text-[8px]" variant="outline">{a.status}</Badge>
                      <span className="text-[10px] text-(--ui-text-tertiary)">{a.tokens} tok / ${a.cost.toFixed(4)}</span>
                    </button>
                    {selectedAgent === a.id && (
                      <pre className="mt-1 whitespace-pre-wrap text-[11px] text-(--ui-text-tertiary)">{JSON.stringify(a, null, 2)}</pre>
                    )}
                  </div>
                ))}
              </Card>
            )}
            {tab === 'events' && (
              <Card className="p-4">
                {events.length === 0 ? (
                  <EmptyState description="Events stream here with sequence numbers." icon="activity" title="No events yet" />
                ) : (
                  <div className="space-y-1 text-xs">
                    {events.map(e => (
                      <div className="border-b border-(--ui-border) py-1 last:border-0" key={e.seq}>
                        <span className="text-(--ui-text-tertiary)">#{e.seq}</span> {e.kind}
                        <span className="ml-2 text-[10px] text-(--ui-text-tertiary)">{new Date(e.at * 1000).toLocaleTimeString()}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            )}
            {tab === 'trace' && (
              <Card className="p-4">
                {!trace ? (
                  <EmptyState description="Open this tab to load the live trace tree." icon="info" title="No trace loaded" />
                ) : (
                  <pre className="whitespace-pre-wrap text-[11px]">{JSON.stringify(trace, null, 2)}</pre>
                )}
              </Card>
            )}
          </>
        )}
      </div>
    </ScrollArea>
  )
}
