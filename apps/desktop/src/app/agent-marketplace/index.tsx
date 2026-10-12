import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  $marketBudget,
  $marketDelegations,
  $marketError,
  $marketHits,
  $marketLedger,
  $marketLoading,
  $marketPolicy,
  $marketQuery,
  $marketSection,
  $marketStopped,
  addMarketDelegation,
  type MarketSection,
  setMarketBudget,
  setMarketError,
  setMarketHits,
  setMarketLedger,
  setMarketLoading,
  setMarketPolicy,
  setMarketQuery,
  setMarketSection,
  setMarketStopped,
} from '@/store/agent-marketplace'
import { notify, notifyError } from '@/store/notifications'

const SECTIONS: { id: MarketSection; label: string }[] = [
  { id: 'discover', label: 'Discover' },
  { id: 'recommended', label: 'Recommended' },
  { id: 'agents', label: 'Agents' },
  { id: 'services', label: 'Services' },
  { id: 'reputation', label: 'Reputation' },
  { id: 'contracts', label: 'Contracts' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'budgets', label: 'Budgets' },
  { id: 'disputes', label: 'Disputes' },
  { id: 'security', label: 'Security' },
  { id: 'trust', label: 'Trust' },
]

function fmtMoney(minor: number | undefined, currency = 'USD'): string {
  if (minor == null) {return 'quote required'}

  return `${(minor / 100).toFixed(2)} ${currency}`
}

export function AgentMarketplaceView({ requestGateway }: {
  requestGateway: <T>(method: string, params?: Record<string, unknown>) => Promise<T>
}) {
  const hits = useStore($marketHits)
  const query = useStore($marketQuery)
  const delegations = useStore($marketDelegations)
  const ledger = useStore($marketLedger)
  const budget = useStore($marketBudget)
  const policy = useStore($marketPolicy)
  const loading = useStore($marketLoading)
  const error = useStore($marketError)
  const section = useStore($marketSection)
  const stopped = useStore($marketStopped)
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  const [detailKind, setDetailKind] = useState<'agent' | 'service' | null>(null)

  const runSearch = async () => {
    if (!query.trim()) {return}
    const c = await import('@/lib/agent-marketplace-client')
    setMarketLoading(true)

    try {
      const res = await c.marketSearch(requestGateway, query.trim())
      setMarketHits(res.hits)
      setMarketError(null)

      if (res.hits.length === 0) {
        notify({ title: 'Marketplace', message: 'No matching services — constraints eliminated all candidates' })
      }
    } catch (e) {
      setMarketError(e instanceof Error ? e.message : String(e))
    } finally {
      setMarketLoading(false)
    }
  }

  const openDetail = async (kind: 'agent' | 'service', id: string) => {
    try {
      const c = await import('@/lib/agent-marketplace-client')

      const res = kind === 'agent'
        ? await c.marketAgent(requestGateway, id)
        : await c.marketService(requestGateway, id)

      setDetail(res)
      setDetailKind(kind)
    } catch (e) {
      notifyError(e instanceof Error ? e.message : String(e), 'Marketplace')
    }
  }

  const refreshOps = async () => {
    try {
      const c = await import('@/lib/agent-marketplace-client')
      setMarketLedger(await c.marketTransactions(requestGateway))
      setMarketBudget(await c.marketBudget(requestGateway))
      setMarketPolicy(await c.marketPolicy(requestGateway))
      setMarketError(null)
    } catch (e) {
      setMarketError(e instanceof Error ? e.message : String(e))
    }
  }

  const delegateTo = async (hit: { service_id: string; agent_id: string }) => {
    try {
      const c = await import('@/lib/agent-marketplace-client')

      const res = await c.marketDelegate(
        requestGateway,
        {
          summary: query || `Marketplace task via ${hit.service_id}`,
          data_class: 'INTERNAL',
          verification_requirements: ['schema'],
          payment_provider: 'none',
        },
        { service_id: hit.service_id, agent_id: hit.agent_id },
      )

      addMarketDelegation(res)

      if (res.status === 'awaiting_approval') {
        notify({ title: 'Marketplace', message: `Approval required (${res.tier}, ${fmtMoney(res.amount_minor, res.currency)})` })
      } else {
        notify({ title: 'Marketplace', message: `Delegated: ${res.delegation_id}` })
      }
    } catch (e) {
      notifyError(e instanceof Error ? e.message : String(e), 'Marketplace')
    }
  }

  return (
    <PageShell>
      <PageHeader>
        <PageTitle>Agent Marketplace</PageTitle>
        <PageDescription>
          Discover, evaluate, delegate to, verify, and settle with external agents.
          Listings are UNVERIFIED until reconciled. Money never moves without policy,
          budget, and explicit authorization. Empty states are real — never simulated.
        </PageDescription>
      </PageHeader>

      <div className="flex flex-wrap gap-2">
        {SECTIONS.map(s => (
          <Button
            key={s.id}
            onClick={() => void setMarketSection(s.id)}
            size="sm"
            variant={section === s.id ? 'default' : 'outline'}
          >
            {s.label}
          </Button>
        ))}
        <Button onClick={() => void refreshOps()} size="sm" variant="outline">
          Operations
        </Button>
        <Button
          onClick={() => void setMarketStopped(!stopped)}
          size="sm"
          variant={stopped ? 'default' : 'destructive'}
        >
          {stopped ? 'Resume marketplace' : 'Stop all marketplace activity'}
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {(section === 'discover' || section === 'recommended') && (
        <>
          <div className="flex gap-2">
            <Input
              onChange={e => setMarketQuery(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') {void runSearch()} }}
              placeholder="What do I need? e.g. analyze financial spreadsheets"
              value={query}
            />
            <Button disabled={loading} onClick={() => void runSearch()}>
              {loading ? 'Searching…' : 'Search'}
            </Button>
          </div>
          <div className="grid gap-2">
            {hits.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No results yet. Search states what you need; only real registry services match.
              </p>
            )}
            {hits.map(h => (
              <div className="rounded border p-3" key={`${h.source}:${h.service_id}`}>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm">{h.service_id}</span>
                  <Badge variant={h.exact ? 'default' : 'secondary'}>
                    {h.exact ? 'EXACT' : `KW ${h.keyword_score.toFixed(2)}`}
                  </Badge>
                  <Badge variant="outline">{h.source.toUpperCase()}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">agent: {h.agent_id}</p>
                <ul className="mt-1 list-disc pl-5 text-xs text-muted-foreground">
                  {h.reasons.slice(0, 4).map((r, i) => <li key={i}>{r}</li>)}
                </ul>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button onClick={() => void openDetail('service', h.service_id)} size="sm" variant="outline">
                    Inspect
                  </Button>
                  <Button onClick={() => void openDetail('agent', h.agent_id)} size="sm" variant="outline">
                    Agent
                  </Button>
                  <Button disabled={stopped} onClick={() => void delegateTo(h)} size="sm">
                    Delegate
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {detail && (
        <div className="rounded border p-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">
              {detailKind === 'agent' ? 'Agent detail' : 'Service detail'}
            </span>
            <Button onClick={() => setDetail(null)} size="sm" variant="outline">Close</Button>
          </div>
          <pre className="mt-2 max-h-96 overflow-auto text-xs">
            {JSON.stringify(detail, null, 2)}
          </pre>
        </div>
      )}

      {(section === 'transactions' || section === 'budgets' || section === 'contracts') && (
        <div className="grid gap-2">
          <div className="rounded border p-3">
            <p className="text-sm font-semibold">Ledger + accounting (append-only, hash-chained)</p>
            <pre className="mt-1 max-h-64 overflow-auto text-xs">
              {ledger ? JSON.stringify(ledger, null, 2) : 'Press Operations to load real ledger state.'}
            </pre>
          </div>
          <div className="rounded border p-3">
            <p className="text-sm font-semibold">Budget usage</p>
            <pre className="mt-1 max-h-64 overflow-auto text-xs">
              {budget ? JSON.stringify(budget, null, 2) : 'Press Operations to load real budget state.'}
            </pre>
          </div>
          <div className="rounded border p-3">
            <p className="text-sm font-semibold">Policy + flags</p>
            <pre className="mt-1 max-h-64 overflow-auto text-xs">
              {policy ? JSON.stringify(policy, null, 2) : 'Press Operations to load effective policy.'}
            </pre>
          </div>
        </div>
      )}

      {section === 'disputes' && (
        <p className="text-sm text-muted-foreground">
          Open disputes from the CLI (`aetheros agent-marketplace disputes --open-file …`) or the
          dispute IPC channel. Evidence is immutable and referenced by id.
        </p>
      )}

      {(section === 'security' || section === 'trust' || section === 'reputation') && (
        <p className="text-sm text-muted-foreground">
          Select Inspect on a service or Agent on a hit to see listing verification, scan level
          (scanned / partially scanned / not scanned), trust dimensions with provenance, and
          reputation metrics with sample counts. Metrics without samples read
          “insufficient evidence” — never a percentage.
        </p>
      )}

      {delegations.length > 0 && (
        <div className="grid gap-2">
          <p className="text-sm font-semibold">This session&apos;s delegations</p>
          {delegations.map(d => (
            <div className="rounded border p-3" key={d.delegation_id ?? d.contract_id}>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm">{d.delegation_id ?? d.contract_id}</span>
                <Badge variant="outline">{(d.status ?? 'unknown').toUpperCase()}</Badge>
                {d.amount_minor != null && d.amount_minor > 0 && (
                  <span className="text-xs">{fmtMoney(d.amount_minor, d.currency)}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </PageShell>
  )
}
