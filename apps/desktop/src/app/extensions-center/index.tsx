import { useStore } from '@nanostores/react'
import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  extensionDisable,
  extensionEnable,
  extensionEvents,
  extensionInfo,
  extensionInstall,
  extensionList,
  extensionPermissions,
  extensionQuarantine,
  extensionRevoke,
  extensionUninstall,
  extensionVerify,
  type ExtRecord,
} from '@/lib/extension-client'
import { $gateway } from '@/store/gateway'

type Tab = 'installed' | 'detail' | 'security' | 'events'

function useGateway(): ((method: string, params?: Record<string, unknown>) => Promise<never>) | null {
  const client = useStore($gateway) as unknown as {
    request?: (method: string, params?: Record<string, unknown>) => Promise<never>
  } | null

  return client?.request?.bind(client) ?? null
}

export function ExtensionsCenter() {
  const requestGateway = useGateway()
  const [tab, setTab] = useState<Tab>('installed')
  const [query, setQuery] = useState('')
  const [exts, setExts] = useState<ExtRecord[]>([])
  const [selected, setSelected] = useState('')
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  const [perms, setPerms] = useState<Record<string, unknown> | null>(null)
  const [verify, setVerify] = useState<Record<string, unknown> | null>(null)
  const [events, setEvents] = useState<Record<string, unknown>[]>([])
  const [installSrc, setInstallSrc] = useState('')
  const [installResult, setInstallResult] = useState<Record<string, unknown> | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [error, setError] = useState('')

  async function refresh() {
    if (!requestGateway) {return}
    setStatus('loading')

    try {
      setExts(await extensionList(requestGateway, { query: query || undefined }))
      setEvents(await extensionEvents(requestGateway))
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
          <EmptyState description="Connect the gateway to manage real extensions." icon="package" title="Extension backend unavailable" />
        </div>
      </ScrollArea>
    )
  }

  async function inspect(id: string) {
    if (!requestGateway) {return}
    setSelected(id)
    setTab('detail')

    try {
      setDetail(await extensionInfo(requestGateway, id))
      setPerms(await extensionPermissions(requestGateway, id))
      setVerify(await extensionVerify(requestGateway, id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
    }
  }

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <Card className="p-6">
          <h2 className="text-2xl font-semibold tracking-tight">Extensions Center</h2>
          <p className="text-(--ui-text-tertiary) mb-4">Live extension platform state. Only metadata that exists is shown.</p>
          <div className="mb-3 flex gap-2">
            <input className="flex-1 border px-2 py-1 text-xs" onChange={e => setQuery(e.target.value)}
              placeholder="Search extensions…" value={query} />
            <button className="text-xs underline" onClick={() => void refresh()}>
              {status === 'loading' ? 'Loading…' : 'Search'}
            </button>
          </div>
          <div className="mb-3 flex gap-2">
            <input className="flex-1 border px-2 py-1 text-xs" onChange={e => setInstallSrc(e.target.value)}
              placeholder="Install from .aetherext path or directory…" value={installSrc} />
            <button className="text-xs underline" onClick={() => requestGateway && installSrc.trim() && extensionInstall(requestGateway, installSrc.trim()).then(r => { setInstallResult(r); void refresh() }).catch(e => { setError(String(e)); setStatus('error') })}>Install</button>
          </div>
          {installResult && <pre className="mb-3 whitespace-pre-wrap text-[11px]">{JSON.stringify(installResult, null, 2)}</pre>}
          <div className="flex gap-2 text-xs">
            {(['installed', 'detail', 'security', 'events'] as Tab[]).map(t => (
              <button className={tab === t ? 'font-semibold underline' : 'text-(--ui-text-tertiary)'} key={t}
                onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
          </div>
        </Card>

        {status === 'error' && <Card className="p-4 text-xs text-red-400">Extension request failed: {error}</Card>}

        {tab === 'installed' && (
          <Card className="p-4">
            {exts.length === 0 ? (
              <EmptyState description="Install one from a package path above." icon="package" title="No extensions" />
            ) : exts.map(e => (
              <div className="border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0" key={e.id}>
                <div className="flex items-center gap-2">
                  <button className="flex-1 truncate text-left font-medium underline" onClick={() => void inspect(e.id)}>{e.id}</button>
                  <Badge className="text-[8px]" variant="outline">{String((e.manifest as Record<string, unknown>)?.extension_type ?? '')}</Badge>
                  <Badge className="text-[8px]" variant="outline">{e.installed_version || '—'}</Badge>
                  <Badge className="text-[8px]" variant="outline">{e.state}</Badge>
                  <Badge className="text-[8px]" variant="outline">{e.trust_level}</Badge>
                  <button className="underline" onClick={() => requestGateway && void extensionEnable(requestGateway, e.id).then(() => void refresh())}>Enable</button>
                  <button className="underline" onClick={() => requestGateway && void extensionDisable(requestGateway, e.id).then(() => void refresh())}>Disable</button>
                  <button className="text-red-400 underline" onClick={() => requestGateway && void extensionUninstall(requestGateway, e.id).then(() => void refresh())}>Uninstall</button>
                </div>
              </div>
            ))}
          </Card>
        )}

        {tab === 'detail' && (
          <Card className="p-4">
            {!detail ? (
              <EmptyState description="Select an extension to inspect manifest, trust, health." icon="info" title="Nothing selected" />
            ) : (
              <pre className="whitespace-pre-wrap text-[11px]">{JSON.stringify(detail, null, 2)}</pre>
            )}
          </Card>
        )}

        {tab === 'security' && (
          <Card className="p-4">
            {!selected ? (
              <EmptyState description="Select one to review permissions and integrity." icon="shield" title="No extension selected" />
            ) : (
              <div className="space-y-3">
                <div className="flex gap-2 text-xs">
                  <button className="underline" onClick={() => requestGateway && void extensionRevoke(requestGateway, selected).then(() => void inspect(selected))}>Revoke all grants</button>
                  <button className="text-red-400 underline" onClick={() => requestGateway && void extensionQuarantine(requestGateway, selected, 'manual quarantine').then(() => void refresh())}>Quarantine</button>
                </div>
                <pre className="whitespace-pre-wrap text-[11px]">{JSON.stringify({ permissions: perms, verify }, null, 2)}</pre>
              </div>
            )}
          </Card>
        )}

        {tab === 'events' && (
          <Card className="p-4">
            {events.length === 0 ? (
              <EmptyState description="Install/enable/disable actions appear here." icon="activity" title="No extension events" />
            ) : (
              <div className="space-y-1 text-xs">
                {events.map((e, i) => (
                  <div className="border-b border-(--ui-border) py-1 last:border-0" key={i}>
                    {String(e.kind ?? '')} — {String(e.extension ?? '')}
                    <span className="ml-2 text-[10px] text-(--ui-text-tertiary)">{new Date(Number(e.at ?? 0) * 1000).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}
      </div>
    </ScrollArea>
  )
}
