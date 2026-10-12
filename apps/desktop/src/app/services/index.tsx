import { useStore } from '@nanostores/react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { StatusDot, type StatusTone } from '@/components/status-dot'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  getMessagingPlatforms,
  type MessagingPlatformInfo,
  updateMessagingPlatform
} from '@/hermes'
import type { Globe} from '@/lib/icons';
import { Activity, BarChart3, CheckCircle2, Cpu, ExternalLink, Link, Loader2, MessageCircle, Package, Plus, RefreshCw, Settings, Wrench, Zap } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { notify, notifyError } from '@/store/notifications'
import {
  $serviceHub,
  categorizeConnectors,
  type ConnectedServiceInfo,
  CONNECTOR_CATALOG,
  type ConnectorCatalogEntry,
  connectorFromPlatform,
  type ServiceCategory,
  setConnectedServices,
  setServiceHubCategory,
  setServiceHubSearch,
  setServiceHubTab,
  updateConnectedService
} from '@/store/services'
import { $healthStatus, $syncStatus } from '@/store/system'

import { useRefreshHotkey } from '../hooks/use-refresh-hotkey'
import { CREDENTIAL_CONTROL_CLASS } from '../settings/credential-key-ui'
import { ListRow } from '../settings/primitives'

import { ConnectWizard } from './connect-wizard'
import { ServiceDetailDialog } from './service-detail-dialog'
import { SyncManager } from './sync-manager'

const TAB_ICONS: Record<string, typeof BarChart3> = {
  dashboard: BarChart3,
  connected: MessageCircle,
  marketplace: Package,
  sync: RefreshCw,
  settings: Settings
}

const PILL_TONE: Record<StatusTone, string> = {
  good: 'bg-primary/10 text-primary',
  muted: 'bg-muted text-muted-foreground',
  warn: 'bg-amber-500/10 text-amber-600 dark:text-amber-300',
  bad: 'bg-destructive/10 text-destructive'
}

const CATEGORY_ICONS: Record<ServiceCategory, typeof Globe> = {
  messaging: MessageCircle,
  automation: Zap,
  'developer-tools': Wrench,
  storage: Cpu,
  productivity: Activity,
  'ai-models': BarChart3
}

function stateTone(platform: { enabled: boolean; state?: string | null }): StatusTone {
  if (!platform.enabled) {return 'muted'}

  if (platform.state === 'connected') {return 'good'}

  if (platform.state === 'fatal' || platform.state === 'startup_failed') {return 'bad'}

  return 'warn'
}

function iconForConnector(connector: ConnectorCatalogEntry | ConnectedServiceInfo) {
  switch (connector.icon) {
    case 'send': return <Codicon name="send" size="1rem" />

    case 'message-circle': return <MessageCircle className="size-3.5" />

    case 'message-square-text': return <MessageCircle className="size-3.5" />

    case 'mail': return <Codicon name="mail" size="1rem" />

    case 'home': return <Codicon name="home" size="1rem" />

    case 'link': return <Link className="size-3.5" />

    case 'terminal': return <Codicon name="terminal" size="1rem" />

    case 'layers-3': return <Codicon name="layers" size="1rem" />

    default: return <Codicon name="plug" size="1rem" />
  }
}

export function ServicesView() {
  const hub = useStore($serviceHub)
  const health = useStore($healthStatus)
  const syncStatus = useStore($syncStatus)
  const [platforms, setPlatforms] = useState<MessagingPlatformInfo[] | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [saving, setSaving] = useState<string | null>(null)
  const [detailService, setDetailService] = useState<ConnectedServiceInfo | null>(null)
  const [wizardConnector, setWizardConnector] = useState<ConnectorCatalogEntry | null>(null)

  const refreshPlatforms = useCallback(async (silent = false) => {
    if (!silent) {setRefreshing(true)}

    try {
      const result = await getMessagingPlatforms()
      setPlatforms(result.platforms)

      const connected: ConnectedServiceInfo[] = result.platforms.map(p => ({
        id: p.id,
        name: p.name,
        description: p.description,
        category: connectorFromPlatform(p)?.category ?? 'messaging',
        icon: connectorFromPlatform(p)?.icon ?? 'plug',
        color: connectorFromPlatform(p)?.color ?? '#71717A',
        enabled: p.enabled,
        configured: p.configured,
        connected: p.state === 'connected',
        state: p.state ?? null,
        error: p.error_message,
        lastSync: p.updated_at
      }))

      setConnectedServices(connected)
    } catch (err) {
      if (!silent) {notifyError(err, 'Failed to load services')}
    } finally {
      if (!silent) {setRefreshing(false)}
    }
  }, [])

  useRefreshHotkey(() => void refreshPlatforms())

  useEffect(() => { void refreshPlatforms() }, [refreshPlatforms])

  useEffect(() => {
    let cancelled = false

    function tick() {
      if (cancelled || document.hidden) {return}
      void refreshPlatforms(true)
    }

    const id = window.setInterval(tick, 10000)

    return () => { cancelled = true; window.clearInterval(id) }
  }, [refreshPlatforms])

  async function handleToggle(platformId: string, name: string, enabled: boolean) {
    setSaving(`enabled:${platformId}`)

    try {
      await updateMessagingPlatform(platformId, { enabled })
      updateConnectedService(platformId, {
        enabled,
        connected: enabled ? false : false,
        state: enabled ? 'pending_restart' : 'disabled'
      })
      notify({ kind: 'success', title: enabled ? `${name} enabled` : `${name} disabled`, message: 'Restart gateway to apply' })
    } catch (err) {
      notifyError(err, `Failed to update ${name}`)
    } finally {
      setSaving(null)
    }
  }

  const connectedCount = hub.connectedServices.filter(s => s.enabled).length
  const runningCount = health?.services.filter(s => s.status === 'running').length ?? 0
  const errorCount = health?.services.filter(s => s.status === 'error').length ?? 0

  const marketplaceItems = useMemo(() => {
    const configured = new Set(hub.connectedServices.map(s => s.id))

    return categorizeConnectors(CONNECTOR_CATALOG, hub.selectedCategory).filter(c => !configured.has(c.id))
  }, [hub.connectedServices, hub.selectedCategory])

  const filteredConnected = useMemo(() => {
    const q = hub.searchQuery.trim().toLowerCase()

    if (!q) {return hub.connectedServices}

    return hub.connectedServices.filter(s =>
      [s.name, s.description, s.id, s.state].filter(Boolean).some(v => String(v).toLowerCase().includes(q))
    )
  }, [hub.connectedServices, hub.searchQuery])

  const filteredMarketplace = useMemo(() => {
    const q = hub.searchQuery.trim().toLowerCase()

    if (!q) {return marketplaceItems}

    return marketplaceItems.filter(c =>
      [c.name, c.description, c.id, c.category].filter(Boolean).some(v => String(v).toLowerCase().includes(q))
    )
  }, [marketplaceItems, hub.searchQuery])

  return (
    <div className="flex h-full min-w-0 flex-col overflow-hidden bg-(--ui-chat-surface-background)">
      <div className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2.5">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Service & Integration Hub</h1>
          <p className="mt-0.5 text-sm text-(--ui-text-tertiary)">
            {connectedCount} connected · {runningCount} running · {hub.connectedServices.length} total
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button disabled={refreshing} onClick={() => void refreshPlatforms()} size="sm" variant="ghost">
            <RefreshCw className={cn('size-3.5', refreshing && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary) px-3">
        {(['dashboard', 'connected', 'marketplace', 'sync', 'settings'] as const).map(tab => {
          const Icon = TAB_ICONS[tab]

          return (
            <button
              className={cn(
                'flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors',
                hub.activeTab === tab
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-(--ui-text-secondary) hover:text-foreground'
              )}
              key={tab}
              onClick={() => setServiceHubTab(tab)}
              type="button"
            >
              <Icon className="size-4" />
              {tab === 'dashboard' && 'Dashboard'}
              {tab === 'connected' && 'Connected'}
              {tab === 'marketplace' && 'Marketplace'}
              {tab === 'sync' && 'Sync Status'}
              {tab === 'settings' && 'Settings'}
            </button>
          )
        })}
      </div>

      {hub.activeTab !== 'dashboard' && hub.activeTab !== 'sync' && hub.activeTab !== 'settings' && (
        <div className="flex shrink-0 items-center gap-3 px-3 pb-2 pt-2">
          {hub.activeTab === 'marketplace' && (
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1">
              {(['all', 'messaging', 'automation', 'developer-tools'] as const).map(cat => (
                <button
                  className={cn(
                    'rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
                    hub.selectedCategory === cat
                      ? 'bg-primary/10 text-primary'
                      : 'text-(--ui-text-tertiary) hover:text-foreground'
                  )}
                  key={cat}
                  onClick={() => setServiceHubCategory(cat === 'all' ? 'all' : cat)}
                  type="button"
                >
                  {cat === 'all' ? 'All' : cat === 'messaging' ? 'Messaging' : cat === 'automation' ? 'Automation' : 'Developer Tools'}
                </button>
              ))}
            </div>
          )}
          {hub.activeTab === 'connected' && <div className="flex-1" />}
          <div className="flex shrink-0 items-center">
            <Input
              className={cn('h-7 w-48 text-xs', CREDENTIAL_CONTROL_CLASS)}
              onChange={e => setServiceHubSearch(e.target.value)}
              placeholder={hub.activeTab === 'marketplace' ? 'Search connectors...' : 'Search services...'}
              value={hub.searchQuery}
            />
          </div>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {hub.activeTab === 'dashboard' && (
          <DashboardTab
            connectedCount={connectedCount}
            errorCount={errorCount}
            health={health}
            platforms={platforms}
            runningCount={runningCount}
            services={hub.connectedServices}
            syncStatus={syncStatus}
          />
        )}
        {hub.activeTab === 'connected' && (
          <ConnectedServicesTab
            onSelect={s => setDetailService(s)}
            onToggle={(id, name, enabled) => void handleToggle(id, name, enabled)}
            saving={saving}
            services={filteredConnected}
          />
        )}
        {hub.activeTab === 'marketplace' && (
          <MarketplaceTab connectors={filteredMarketplace} onSetup={c => setWizardConnector(c)} />
        )}
        {hub.activeTab === 'sync' && (
          <SyncManager
            services={hub.connectedServices}
            syncStatus={syncStatus}
          />
        )}
        {hub.activeTab === 'settings' && (
          <SettingsTab />
        )}
      </div>

      <ServiceDetailDialog
        onOpenChange={open => { if (!open) {setDetailService(null)} }}
        onToggle={(id, name, enabled) => void handleToggle(id, name, enabled)}
        open={detailService !== null}
        saving={saving}
        service={detailService}
      />
      <ConnectWizard
        connector={wizardConnector}
        onOpenChange={open => { if (!open) {setWizardConnector(null)} }}
        open={wizardConnector !== null}
      />
    </div>
  )
}

function DashboardTab({
  connectedCount,
  runningCount,
  errorCount,
  health,
  platforms,
  syncStatus,
  services
}: {
  connectedCount: number
  runningCount: number
  errorCount: number
  health: { overall: string; services: { id: string; name: string; status: string }[] } | null
  platforms: MessagingPlatformInfo[] | null
  syncStatus: string
  services: ConnectedServiceInfo[]
}) {
  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={MessageCircle} label="Connected Services" tone="good" value={connectedCount} />
        <StatCard icon={Cpu} label="Backend Services" subtitle={`${(health?.services.length ?? 0)} total`} tone="good" value={runningCount} />
        <StatCard icon={Activity} label="Sync Status" tone={syncStatus === 'error' ? 'bad' : syncStatus === 'syncing' ? 'warn' : 'good'} value={syncStatus === 'idle' ? 'Idle' : syncStatus === 'syncing' ? 'Syncing' : 'Error'} />
        <StatCard icon={BarChart3} label="Active Integrations" subtitle={`${services.length - services.filter(s => s.enabled).length} disabled`} tone="good" value={services.filter(s => s.enabled).length} />
      </div>

      {errorCount > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <Codicon name="error" size="1rem" />
          <span>{errorCount} backend {errorCount === 1 ? 'service has' : 'services have'} errors. Check the Logs view for details.</span>
        </div>
      )}

      <section>
        <h3 className="mb-3 text-sm font-semibold">Backend Services</h3>
        <div className="space-y-1">
          {health?.services.map(service => (
            <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2" key={service.id}>
              <StatusDot tone={service.status === 'running' ? 'good' : service.status === 'error' ? 'bad' : 'warn'} />
              <span className="min-w-0 flex-1 text-sm font-medium">{service.name}</span>
              <span className={cn(
                'text-xs font-medium',
                service.status === 'running' ? 'text-emerald-500' : service.status === 'error' ? 'text-red-500' : 'text-amber-500'
              )}>
                {service.status}
              </span>
            </div>
          ))}
          {(!health?.services || health.services.length === 0) && (
            <p className="py-4 text-center text-xs text-(--ui-text-tertiary)">No backend services</p>
          )}
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold">Messaging Platforms</h3>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {platforms?.slice(0, 6).map(platform => (
            <PlatformMiniCard key={platform.id} platform={platform} />
          ))}
        </div>
        {platforms && platforms.length > 6 && (
          <p className="mt-2 text-xs text-(--ui-text-tertiary)">+{platforms.length - 6} more platforms</p>
        )}
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold">Sync Overview</h3>
        <div className="flex items-center gap-4 rounded-lg border border-(--ui-stroke-tertiary) px-4 py-3">
          <StatusDot tone={syncStatus === 'error' ? 'bad' : syncStatus === 'syncing' ? 'warn' : 'good'} />
          <div className="min-w-0 flex-1">
            <span className="text-sm font-medium capitalize">Status: {syncStatus}</span>
            <p className="text-xs text-(--ui-text-tertiary)">Data synchronization across connected services</p>
          </div>
          {syncStatus === 'syncing' && <Loader2 className="size-4 animate-spin text-(--ui-text-tertiary)" />}
        </div>
      </section>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, tone, subtitle }: { icon: typeof BarChart3; label: string; value: string | number; tone: StatusTone; subtitle?: string }) {
  return (
    <div className="rounded-lg border border-(--ui-stroke-tertiary) px-4 py-3">
      <div className="flex items-center justify-between">
        <Icon className="size-4 text-(--ui-text-tertiary)" />
        <StatusDot tone={tone} />
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="text-xs text-(--ui-text-tertiary)">{label}</p>
      {subtitle && <p className="mt-0.5 text-[0.65rem] text-(--ui-text-tertiary)">{subtitle}</p>}
    </div>
  )
}

function PlatformMiniCard({ platform }: { platform: MessagingPlatformInfo }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2">
      <StatusDot tone={stateTone(platform)} />
      <span className="min-w-0 flex-1 truncate text-sm font-medium">{platform.name}</span>
      <Badge variant={platform.enabled ? 'default' : 'muted'}>{platform.enabled ? 'Enabled' : 'Off'}</Badge>
    </div>
  )
}

function ConnectedServicesTab({
  saving,
  services,
  onSelect,
  onToggle
}: {
  saving: string | null
  services: ConnectedServiceInfo[]
  onSelect: (service: ConnectedServiceInfo) => void
  onToggle: (id: string, name: string, enabled: boolean) => void
}) {
  if (services.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Codicon className="mb-3 text-(--ui-text-tertiary)" name="dashboard" size="2rem" />
        <h3 className="text-sm font-medium">No connected services</h3>
        <p className="mt-1 text-xs text-(--ui-text-tertiary)">Configure a messaging platform or enable a connector from the Marketplace tab.</p>
      </div>
    )
  }

  const enabledServices = services.filter(s => s.enabled)
  const disabledServices = services.filter(s => !s.enabled)

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <section>
        <h3 className="mb-2 text-sm font-semibold">Enabled ({enabledServices.length})</h3>
        <div className="space-y-1">
          {enabledServices.map(service => (
            <ServiceRow key={service.id} onSelect={onSelect} onToggle={onToggle} saving={saving} service={service} />
          ))}
        </div>
      </section>
      {disabledServices.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold text-(--ui-text-tertiary)">Disabled ({disabledServices.length})</h3>
          <div className="space-y-1">
            {disabledServices.map(service => (
              <ServiceRow key={service.id} onSelect={onSelect} onToggle={onToggle} saving={saving} service={service} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function ServiceRow({
  saving,
  service,
  onSelect,
  onToggle
}: {
  saving: string | null
  service: ConnectedServiceInfo
  onSelect: (service: ConnectedServiceInfo) => void
  onToggle: (id: string, name: string, enabled: boolean) => void
}) {
  const color = service.color

  return (
    <button
      className="flex w-full items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5 text-left transition-colors hover:bg-(--chrome-action-hover)"
      onClick={() => onSelect(service)}
      type="button"
    >
      <span
        className="inline-grid size-7 shrink-0 place-items-center rounded-md text-xs font-medium"
        style={{
          backgroundColor: `color-mix(in srgb, ${color} 16%, transparent)`,
          color
        }}
      >
        {iconForConnector(service)}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{service.name}</span>
          {service.connected && <Badge variant="default">Connected</Badge>}
          {!service.connected && service.enabled && <Badge variant="warn">Pending</Badge>}
          {!service.enabled && <Badge variant="muted">Disabled</Badge>}
        </div>
        <p className="text-xs text-(--ui-text-tertiary)">{service.description}</p>
        {service.error && <p className="mt-0.5 text-xs text-destructive">{service.error}</p>}
      </div>
      <Switch
        aria-label={`${service.enabled ? 'Disable' : 'Enable'} ${service.name}`}
        checked={service.enabled}
        disabled={saving === `enabled:${service.id}`}
        onCheckedChange={checked => onToggle(service.id, service.name, checked)}
        size="xs"
      />
    </button>
  )
}

function MarketplaceTab({ connectors, onSetup }: { connectors: ConnectorCatalogEntry[]; onSetup: (connector: ConnectorCatalogEntry) => void }) {
  const grouped = useMemo(() => {
    const groups: Record<string, ConnectorCatalogEntry[]> = {}

    for (const c of connectors) {
      const key = c.category

      if (!groups[key]) {groups[key] = []}
      groups[key].push(c)
    }

    return groups
  }, [connectors])

  if (connectors.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Package className="mb-3 size-8 text-(--ui-text-tertiary)" />
        <h3 className="text-sm font-medium">All connectors configured</h3>
        <p className="mt-1 text-xs text-(--ui-text-tertiary)">All available platform adapters have been configured.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      {(Object.entries(grouped) as [ServiceCategory, ConnectorCatalogEntry[]][]).map(([category, items]) => {
        const CatIcon = CATEGORY_ICONS[category] || Package
        const categoryLabel = category === 'messaging' ? 'Messaging' : category === 'automation' ? 'Automation' : category === 'developer-tools' ? 'Developer Tools' : category === 'storage' ? 'Storage' : category === 'productivity' ? 'Productivity' : 'AI Models'

        return (
          <section key={category}>
            <div className="mb-3 flex items-center gap-2">
              <CatIcon className="size-4 text-(--ui-text-tertiary)" />
              <h3 className="text-sm font-semibold">{categoryLabel}</h3>
              <span className="text-xs text-(--ui-text-tertiary)">({items.length})</span>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {items.map(connector => (
                <ConnectorCard connector={connector} key={connector.id} onSetup={onSetup} />
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}

function ConnectorCard({ connector, onSetup }: { connector: ConnectorCatalogEntry; onSetup: (connector: ConnectorCatalogEntry) => void }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-(--ui-stroke-tertiary) p-3 transition-colors hover:bg-(--chrome-action-hover)">
      <div className="flex items-start gap-3">
        <span
          className="inline-grid size-8 shrink-0 place-items-center rounded-md text-sm font-medium"
          style={{
            backgroundColor: `color-mix(in srgb, ${connector.color} 16%, transparent)`,
            color: connector.color
          }}
        >
          {iconForConnector(connector)}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{connector.name}</span>
            {connector.popular && <Badge variant="default">Popular</Badge>}
            {connector.beta && <Badge variant="warn">Beta</Badge>}
          </div>
          <p className="mt-0.5 text-xs text-(--ui-text-tertiary)">{connector.description}</p>
        </div>
      </div>
      <p className="text-[0.65rem] leading-relaxed text-(--ui-text-tertiary)">{connector.setupGuide}</p>
      <div className="flex items-center justify-between">
        <span className="text-[0.6rem] uppercase tracking-wider text-(--ui-text-tertiary)">
          {connector.authType === 'token' ? 'Token Auth' : connector.authType === 'oauth' ? 'OAuth' : connector.authType === 'webhook' ? 'Webhook' : 'No Auth'}
        </span>
        <div className="flex items-center gap-1">
          <Button asChild size="xs" variant="ghost">
            <a href={connector.docsUrl} rel="noreferrer" target="_blank">
              <ExternalLink className="size-3" />
              Docs
            </a>
          </Button>
          <Button onClick={() => onSetup(connector)} size="xs" variant="textStrong">
            <Plus className="size-3" />
            Setup
          </Button>
        </div>
      </div>
    </div>
  )
}

function SyncTab({
  syncStatus,
  services,
  syncJobs
}: {
  syncStatus: string
  services: ConnectedServiceInfo[]
  syncJobs: { id: string; name: string; status: string; lastRun: string | null }[]
}) {
  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center gap-4 rounded-lg border border-(--ui-stroke-tertiary) px-4 py-3">
        <StatusDot tone={syncStatus === 'error' ? 'bad' : syncStatus === 'syncing' ? 'warn' : 'good'} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium capitalize">Overall Sync: {syncStatus}</p>
          <p className="text-xs text-(--ui-text-tertiary)">Synchronization state across all connected services</p>
        </div>
        {syncStatus === 'syncing' && <Loader2 className="size-4 animate-spin text-(--ui-text-tertiary)" />}
        {syncStatus === 'error' && (
          <Button size="xs" variant="outline">
            <RefreshCw className="size-3" />
            Retry
          </Button>
        )}
      </div>

      <section>
        <h3 className="mb-2 text-sm font-semibold">Service Sync Status</h3>
        <div className="space-y-1">
          {services.filter(s => s.enabled).map(service => (
            <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2" key={service.id}>
              <StatusDot tone={service.connected ? 'good' : 'warn'} />
              <span className="min-w-0 flex-1 text-sm font-medium">{service.name}</span>
              {service.lastSync && (
                <span className="text-xs text-(--ui-text-tertiary)">Last sync: {new Date(service.lastSync).toLocaleString()}</span>
              )}
              {!service.lastSync && <span className="text-xs text-(--ui-text-tertiary)">Never synced</span>}
              <Badge variant={service.connected ? 'default' : 'muted'}>{service.connected ? 'Synced' : 'Pending'}</Badge>
            </div>
          ))}
          {services.filter(s => s.enabled).length === 0 && (
            <p className="py-4 text-center text-xs text-(--ui-text-tertiary)">No enabled services to sync</p>
          )}
        </div>
      </section>

      {syncJobs.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold">Sync Jobs</h3>
          <div className="space-y-1">
            {syncJobs.map(job => (
              <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2" key={job.id}>
                <StatusDot tone={job.status === 'success' ? 'good' : job.status === 'error' ? 'bad' : job.status === 'syncing' ? 'warn' : 'muted'} />
                <span className="min-w-0 flex-1 text-sm font-medium">{job.name}</span>
                <span className="text-xs capitalize text-(--ui-text-tertiary)">{job.status}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function SettingsTab() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <section>
        <h3 className="mb-2 text-sm font-semibold">Service Hub Preferences</h3>
        <div className="space-y-1">
          <ListRow
            action={<Switch defaultChecked size="xs" />}
            description="Show sync status in the sidebar navigation"
            title="Display sync status in sidebar"
          />
          <ListRow
            action={<Switch defaultChecked size="xs" />}
            description="Automatically check for service updates"
            title="Auto-check service health"
          />
          <ListRow
            action={<Switch defaultChecked size="xs" />}
            description="Show desktop notifications for service errors"
            title="Service error notifications"
          />
        </div>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold">Diagnostics</h3>
        <div className="space-y-1">
          <ListRow
            action={
              <Button size="xs" variant="outline">
                <CheckCircle2 className="size-3" />
                Run Check
              </Button>
            }
            description="Check connectivity and configuration for all services"
            title="Run health check"
          />
          <ListRow
            action={
              <Button size="xs" variant="textStrong">
                View Logs
              </Button>
            }
            description="Service-specific logs and error details"
            title="Service logs"
          />
        </div>
      </section>
    </div>
  )
}
