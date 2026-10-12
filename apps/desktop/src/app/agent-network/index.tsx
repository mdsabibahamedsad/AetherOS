import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  $emergencyStopped,
  $networkAgents,
  $networkError,
  $networkLoading,
  $networkSection,
  $networkTasks,
  type NetworkSection,
  setEmergencyStopped,
  setNetworkSection,
} from '@/store/agent-network'
import { notify, notifyError } from '@/store/notifications'

const SECTIONS: { id: NetworkSection; label: string }[] = [
  { id: 'network', label: 'Network' },
  { id: 'discover', label: 'Discover' },
  { id: 'trusted', label: 'Trusted' },
  { id: 'remote', label: 'Remote' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'trust', label: 'Trust' },
  { id: 'security', label: 'Security' },
  { id: 'activity', label: 'Activity' },
]

function TrustBadge({ trust }: { trust: string }) {
  const tone =
    trust === 'blocked' || trust === 'revoked'
      ? 'destructive'
      : trust === 'fully_trusted' || trust === 'user_trusted' || trust === 'organization_trusted'
        ? 'default'
        : trust === 'verified'
          ? 'secondary'
          : 'outline'

  return <Badge variant={tone as 'default' | 'secondary' | 'destructive' | 'outline'}>{trust.toUpperCase()}</Badge>
}

export function AgentNetworkView({ requestGateway }: {
  requestGateway: <T>(method: string, params?: Record<string, unknown>) => Promise<T>
}) {
  const agents = useStore($networkAgents)
  const tasks = useStore($networkTasks)
  const loading = useStore($networkLoading)
  const error = useStore($networkError)
  const section = useStore($networkSection)
  const stopped = useStore($emergencyStopped)
  const [url, setUrl] = useState('')

  const refresh = async () => {
    const { networkList, networkTasks } = await import('@/lib/agent-network-client')

    const { setNetworkAgents, setNetworkTasks, setNetworkError, setNetworkLoading } =
      await import('@/store/agent-network')

    setNetworkLoading(true)

    try {
      setNetworkAgents(await networkList(requestGateway))
      const t = await networkTasks(requestGateway)
      setNetworkTasks(t.tasks)
      setNetworkError(null)
    } catch (e) {
      setNetworkError(e instanceof Error ? e.message : String(e))
    } finally {
      setNetworkLoading(false)
    }
  }

  const discover = async () => {
    if (!url.trim()) {return}

    try {
      const { networkDiscover } = await import('@/lib/agent-network-client')
      const res = await networkDiscover(requestGateway, url.trim())

      if (!res.ok) {
        notifyError(res.errors?.join('; ') ?? 'Discovery failed', 'Agent Network')

        return
      }

      notify({ title: 'Agent Network', message: `Discovered (UNTRUSTED): ${res.agent_id}` })
      setUrl('')
      await refresh()
    } catch (e) {
      notifyError(e instanceof Error ? e.message : String(e), 'Agent Network')
    }
  }

  const act = async (id: string, op: 'verify' | 'trust' | 'block' | 'revoke' | 'connect') => {
    try {
      const c = await import('@/lib/agent-network-client')

      if (op === 'verify') {
        const res = await c.networkVerify(requestGateway, id)
        notify({ title: 'Agent Network', message: `Verification: ${res.label}` })
      } else if (op === 'trust') {
        await c.networkTrust(requestGateway, id, 'user_trusted')
        notify({ title: 'Agent Network', message: `Trusted: ${id}` })
      } else if (op === 'block') {
        await c.networkBlock(requestGateway, id)
      } else if (op === 'revoke') {
        await c.networkRevoke(requestGateway, id)
      } else {
        await c.networkConnect(requestGateway, id)
      }

      await refresh()
    } catch (e) {
      notifyError(e instanceof Error ? e.message : String(e), 'Agent Network')
    }
  }

  const visible =
    section === 'trusted'
      ? agents.filter(a => ['user_trusted', 'organization_trusted', 'fully_trusted'].includes(a.trust))
      : section === 'remote'
        ? agents.filter(a => !a.removed)
        : agents

  return (
    <PageShell>
      <PageHeader>
        <PageTitle>Agent Network</PageTitle>
        <PageDescription>
          Trusted A2A agent federation. Discovered agents are UNTRUSTED until verified and
          explicitly approved. No agent is shown as connected unless a live probe succeeded.
        </PageDescription>
      </PageHeader>

      <div className="flex flex-wrap gap-2">
        {SECTIONS.map(s => (
          <Button
            key={s.id}
            onClick={() => void setNetworkSection(s.id)}
            size="sm"
            variant={section === s.id ? 'default' : 'outline'}
          >
            {s.label}
          </Button>
        ))}
        <Button disabled={loading} onClick={() => void refresh()} size="sm" variant="outline">
          {loading ? 'Refreshing…' : 'Refresh'}
        </Button>
        <Button
          onClick={() => void setEmergencyStopped(!stopped)}
          size="sm"
          variant={stopped ? 'default' : 'destructive'}
        >
          {stopped ? 'Resume remote agents' : 'Stop all remote agents'}
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {(section === 'network' || section === 'discover') && (
        <div className="flex gap-2">
          <Input
            onChange={e => setUrl(e.target.value)}
            placeholder="https://agent.example/ — discover Agent Card (untrusted)"
            value={url}
          />
          <Button onClick={() => void discover()}>Discover</Button>
        </div>
      )}

      {(section === 'network' || section === 'trusted' || section === 'remote') && (
        <div className="grid gap-2">
          {visible.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No agents known. Discover one by URL — it will appear here as UNTRUSTED.
            </p>
          )}
          {visible.map(a => (
            <div className="rounded border p-3" key={a.agent_id}>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm">{a.agent_id}</span>
                <TrustBadge trust={a.trust} />
                <Badge variant="outline">{a.health.toUpperCase()}</Badge>
                {a.latency_ms != null && (
                  <span className="text-xs text-muted-foreground">{a.latency_ms.toFixed(0)} ms</span>
                )}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button onClick={() => void act(a.agent_id, 'connect')} size="sm" variant="outline">Connect</Button>
                <Button onClick={() => void act(a.agent_id, 'verify')} size="sm" variant="outline">Verify</Button>
                <Button onClick={() => void act(a.agent_id, 'trust')} size="sm" variant="outline">Trust</Button>
                <Button onClick={() => void act(a.agent_id, 'block')} size="sm" variant="outline">Block</Button>
                <Button onClick={() => void act(a.agent_id, 'revoke')} size="sm" variant="outline">Revoke</Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {section === 'tasks' && (
        <div className="grid gap-2">
          {tasks.length === 0 && (
            <p className="text-sm text-muted-foreground">No remote tasks. Delegate from CLI or an approved flow.</p>
          )}
          {tasks.map(t => (
            <div className="rounded border p-3" key={t.task_id}>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm">{t.task_id}</span>
                <Badge variant="outline">{t.status.toUpperCase()}</Badge>
                <span className="text-xs text-muted-foreground">→ {t.target_agent}</span>
              </div>
              <p className="mt-1 text-sm">{t.purpose}</p>
            </div>
          ))}
        </div>
      )}
    </PageShell>
  )
}
