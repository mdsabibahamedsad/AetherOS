import { useCallback, useMemo, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Switch } from '@/components/ui/switch'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'

interface UpdateItem {
  id: string
  name: string
  type: 'core' | 'plugin' | 'mcp' | 'extension'
  currentVersion: string
  latestVersion: string
  changelog: string
  publishedAt: string
  size?: string
  severity?: 'critical' | 'important' | 'optional'
  installed: boolean
  autoUpdate: boolean
}

interface UpdatedItem {
  id: string
  name: string
  type: 'core' | 'plugin' | 'mcp' | 'extension'
  version: string
  updatedAt: string
}

const AVAILABLE_UPDATES: UpdateItem[] = [
  {
    id: 'aetheros-core',
    name: 'AetherOS Core',
    type: 'core',
    currentVersion: '0.16.0',
    latestVersion: '0.16.2',
    changelog: '## 0.16.2\n- Fixed memory leak in session manager\n- Improved prompt caching performance\n- Updated model provider SDK\n\n## 0.16.1\n- Hotfix for gateway reconnection\n- Fixed cron job scheduling edge case',
    publishedAt: '2026-07-20T10:00:00Z',
    size: '12.4 MB',
    severity: 'critical',
    installed: false,
    autoUpdate: true
  },
  {
    id: 'code-analyzer',
    name: 'Code Analyzer',
    type: 'plugin',
    currentVersion: '2.1.0',
    latestVersion: '2.2.0',
    changelog: '## 2.2.0\n- Added Rust language support\n- Improved type inference\n- 20% faster analysis for large files\n- Fixed false positives in null checks',
    publishedAt: '2026-07-19T14:30:00Z',
    size: '3.2 MB',
    severity: 'important',
    installed: true,
    autoUpdate: true
  },
  {
    id: 'search-assistant',
    name: 'Search Assistant',
    type: 'plugin',
    currentVersion: '1.3.2',
    latestVersion: '1.4.0',
    changelog: '## 1.4.0\n- Added DuckDuckGo support\n- Improved result relevance ranking\n- Custom search engine configuration\n- Fixed rate limit handling',
    publishedAt: '2026-07-18T09:00:00Z',
    size: '1.8 MB',
    severity: 'optional',
    installed: true,
    autoUpdate: true
  },
  {
    id: 'filesystem-mcp',
    name: 'Filesystem MCP',
    type: 'mcp',
    currentVersion: '1.0.0',
    latestVersion: '1.1.0',
    changelog: '## 1.1.0\n- Added glob pattern support\n- Improved large directory listing performance\n- New file search tool',
    publishedAt: '2026-07-17T16:45:00Z',
    size: '0.5 MB',
    severity: 'important',
    installed: true,
    autoUpdate: false
  },
  {
    id: 'github-mcp',
    name: 'GitHub MCP',
    type: 'mcp',
    currentVersion: '2.0.0',
    latestVersion: '2.1.0',
    changelog: '## 2.1.0\n- GitHub Actions integration\n- Pull request review tool\n- Repository statistics endpoint',
    publishedAt: '2026-07-16T11:20:00Z',
    size: '0.8 MB',
    severity: 'optional',
    installed: true,
    autoUpdate: true
  },
  {
    id: 'vision-analyzer',
    name: 'Vision Analyzer',
    type: 'extension',
    currentVersion: '1.0.0',
    latestVersion: '1.1.0',
    changelog: '## 1.1.0\n- Added support for WebP format\n- Improved OCR accuracy\n- Batch processing mode\n- Lower memory usage',
    publishedAt: '2026-07-15T08:00:00Z',
    size: '4.1 MB',
    severity: 'important',
    installed: true,
    autoUpdate: true
  }
]

const RECENTLY_UPDATED: UpdatedItem[] = [
  { id: 'task-automation', name: 'Task Automation', type: 'plugin', version: '3.0.1', updatedAt: '2026-07-14T10:00:00Z' },
  { id: 'database-gateway', name: 'Database Gateway', type: 'plugin', version: '2.2.1', updatedAt: '2026-07-13T15:30:00Z' },
  { id: 'voice-control', name: 'Voice Control', type: 'plugin', version: '1.2.1', updatedAt: '2026-07-12T09:45:00Z' },
  { id: 'translate-plus', name: 'Translate Plus', type: 'extension', version: '2.0.0', updatedAt: '2026-07-11T14:20:00Z' },
  { id: 'email-hub', name: 'Email Hub', type: 'plugin', version: '1.0.3', updatedAt: '2026-07-10T11:00:00Z' }
]

const TYPE_ICONS: Record<string, string> = {
  core: 'aetheros',
  plugin: 'extensions',
  mcp: 'server',
  extension: 'package'
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-600 dark:text-red-400',
  important: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  optional: 'bg-sky-500/10 text-sky-600 dark:text-sky-400'
}

export function UpdatesManagerView() {
  const { t } = useI18n()
  const [updates, setUpdates] = useState<UpdateItem[]>(AVAILABLE_UPDATES)
  const [filter, setFilter] = useState<'all' | 'core' | 'plugin' | 'mcp' | 'extension'>('all')
  const [selectedUpdateId, setSelectedUpdateId] = useState<string | null>(null)
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set())
  const [updatingAll, setUpdatingAll] = useState(false)
  const [autoUpdateGlobal, setAutoUpdateGlobal] = useState(true)

  const filteredUpdates = useMemo(() => {
    return filter === 'all' ? updates : updates.filter(u => u.type === filter)
  }, [updates, filter])

  const selectedUpdate = useMemo(
    () => updates.find(u => u.id === selectedUpdateId) ?? filteredUpdates[0] ?? null,
    [updates, selectedUpdateId, filteredUpdates]
  )

  const pendingCount = updates.filter(u => !u.installed).length
  const criticalCount = updates.filter(u => !u.installed && u.severity === 'critical').length

  const handleUpdate = useCallback(async (item: UpdateItem) => {
    setUpdatingIds(prev => new Set(prev).add(item.id))
    await new Promise(r => setTimeout(r, 2000))
    setUpdates(current => current.map(u => u.id === item.id ? { ...u, installed: true, currentVersion: u.latestVersion } : u))
    setUpdatingIds(prev => { const next = new Set(prev); next.delete(item.id);

 return next })
    notify({ kind: 'success', title: 'Update Installed', message: `${item.name} updated to v${item.latestVersion}` })
  }, [])

  const handleUpdateAll = useCallback(async () => {
    setUpdatingAll(true)
    const pending = updates.filter(u => !u.installed)

    for (const item of pending) {
      await new Promise(r => setTimeout(r, 800))
      setUpdates(current => current.map(u => u.id === item.id ? { ...u, installed: true, currentVersion: u.latestVersion } : u))
    }

    setUpdatingAll(false)
    notify({ kind: 'success', title: 'All Updates Installed', message: `${pending.length} update(s) applied` })
  }, [updates])

  const handleToggleAutoUpdate = useCallback((itemId: string) => {
    setUpdates(current => current.map(u => u.id === itemId ? { ...u, autoUpdate: !u.autoUpdate } : u))
  }, [])

  const formatDate = (iso: string) => {
    const d = new Date(iso)

    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const formatRelativeDate = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime()
    const days = Math.floor(diff / 86400000)

    if (days === 0) {return 'Today'}

    if (days === 1) {return 'Yesterday'}

    if (days < 7) {return `${days} days ago`}

    return formatDate(iso)
  }

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Updates & Upgrades</PageTitle>
            <PageDescription>
              {pendingCount > 0
                ? `${pendingCount} update${pendingCount > 1 ? 's' : ''} available${criticalCount > 0 ? ` (${criticalCount} critical)` : ''}`
                : 'All components are up to date'}
            </PageDescription>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Switch checked={autoUpdateGlobal} onCheckedChange={setAutoUpdateGlobal} />
              Auto-Update
            </label>
            {pendingCount > 0 && (
              <Button
                className="text-xs"
                disabled={updatingAll}
                onClick={() => void handleUpdateAll()}
                size="sm"
              >
                <Codicon className={cn('mr-1', updatingAll && 'animate-spin')} name={updatingAll ? 'loading' : 'cloud-download'} size="0.75rem" />
                {updatingAll ? 'Updating...' : `Update All (${pendingCount})`}
              </Button>
            )}
          </div>
        </PageHeader>
      }
    >
      <div className="flex h-full gap-4">
        <div className="w-64 shrink-0 space-y-3">
          <div className="flex gap-1">
            {(['all', 'core', 'plugin', 'mcp', 'extension'] as const).map(type => (
              <button
                className={cn(
                  'rounded-md px-2 py-1 text-[0.6rem] font-medium transition-colors',
                  filter === type ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
                )}
                key={type}
                onClick={() => setFilter(type)}
                type="button"
              >
                {type === 'all' ? 'All' : type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
          <div className="space-y-0.5">
            {filteredUpdates.length === 0 ? (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">No updates available</div>
            ) : (
              filteredUpdates.map(item => (
                <button
                  className={cn(
                    'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors',
                    selectedUpdate?.id === item.id ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
                  )}
                  key={item.id}
                  onClick={() => setSelectedUpdateId(item.id)}
                  type="button"
                >
                  <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <Codicon name={TYPE_ICONS[item.type] as 'cloud' | 'extensions' | 'server' | 'package'} size="0.75rem" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-sm font-medium">{item.name}</span>
                      {item.installed && <Codicon className="shrink-0 text-emerald-500" name="check" size="0.65rem" />}
                    </div>
                    <div className="text-[0.6rem] text-muted-foreground">
                      {item.installed
                        ? `v${item.currentVersion}`
                        : `v${item.currentVersion} → v${item.latestVersion}`
                      }
                    </div>
                  </div>
                  {!item.installed && item.severity && (
                    <Badge className={cn('shrink-0 text-[0.55rem]', SEVERITY_STYLES[item.severity])}>
                      {item.severity}
                    </Badge>
                  )}
                </button>
              ))
            )}
          </div>

          <div className="border-t border-(--ui-stroke-tertiary) pt-3">
            <h4 className="mb-2 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground">Recently Updated</h4>
            <div className="space-y-0.5">
              {RECENTLY_UPDATED.map(item => (
                <div className="flex items-center gap-2.5 px-2.5 py-1.5" key={item.id}>
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-(--ui-bg-quinary) text-muted-foreground">
                    <Codicon name={TYPE_ICONS[item.type] as 'cloud' | 'extensions' | 'server' | 'package'} size="0.65rem" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-medium">{item.name}</div>
                    <div className="text-[0.55rem] text-muted-foreground">v{item.version}</div>
                  </div>
                  <span className="shrink-0 text-[0.55rem] text-muted-foreground">{formatRelativeDate(item.updatedAt)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="min-w-0 flex-1 overflow-y-auto">
          {selectedUpdate ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Codicon name={TYPE_ICONS[selectedUpdate.type] as 'cloud' | 'extensions' | 'server' | 'package'} size="1.25rem" />
                    </span>
                    <div>
                      <h3 className="text-lg font-semibold">{selectedUpdate.name}</h3>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="outline">{selectedUpdate.type}</Badge>
                        {selectedUpdate.severity && (
                          <Badge className={SEVERITY_STYLES[selectedUpdate.severity]}>
                            {selectedUpdate.severity}
                          </Badge>
                        )}
                        {selectedUpdate.size && <span>{selectedUpdate.size}</span>}
                        <span>Published {formatDate(selectedUpdate.publishedAt)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {!selectedUpdate.installed ? (
                      <Button
                        className="text-xs"
                        disabled={updatingIds.has(selectedUpdate.id)}
                        onClick={() => void handleUpdate(selectedUpdate)}
                        size="sm"
                      >
                        <Codicon className={cn('mr-1', updatingIds.has(selectedUpdate.id) && 'animate-spin')} name={updatingIds.has(selectedUpdate.id) ? 'loading' : 'cloud-download'} size="0.75rem" />
                        {updatingIds.has(selectedUpdate.id) ? 'Installing...' : `Update to v${selectedUpdate.latestVersion}`}
                      </Button>
                    ) : (
                      <Badge className="text-xs" variant="default">Up to date</Badge>
                    )}
                    <label className="flex items-center gap-1 text-[0.6rem] text-muted-foreground">
                      <Switch
                        checked={selectedUpdate.autoUpdate}
                        onCheckedChange={() => handleToggleAutoUpdate(selectedUpdate.id)}
                      />
                      Auto
                    </label>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-4">
                  {[
                    { label: 'Current Version', value: `v${selectedUpdate.currentVersion}` },
                    { label: 'Latest Version', value: `v${selectedUpdate.latestVersion}` },
                    { label: 'Release Date', value: formatDate(selectedUpdate.publishedAt) }
                  ].map(stat => (
                    <div className="rounded-md bg-(--ui-bg-quinary) px-3 py-2" key={stat.label}>
                      <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">{stat.label}</div>
                      <div className="mt-0.5 text-sm font-medium tabular-nums">{stat.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {!selectedUpdate.installed && (
                <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
                  <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Version Comparison</h4>
                  <div className="flex items-center gap-4">
                    <div className="flex-1 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2">
                      <div className="text-[0.6rem] font-medium text-muted-foreground">Current</div>
                      <div className="mt-0.5 text-lg font-semibold">v{selectedUpdate.currentVersion}</div>
                    </div>
                    <Codicon className="text-muted-foreground/40" name="arrow-right" size="1.25rem" />
                    <div className="flex-1 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2">
                      <div className="text-[0.6rem] font-medium text-primary">Latest</div>
                      <div className="mt-0.5 text-lg font-semibold text-primary">v{selectedUpdate.latestVersion}</div>
                    </div>
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-(--ui-stroke-tertiary) overflow-hidden">
                <div className="border-b border-(--ui-stroke-tertiary) px-4 py-2.5">
                  <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    <Codicon name="note" size="0.75rem" />
                    Changelog
                  </h4>
                </div>
                <div className="px-4 py-3">
                  <pre className="font-mono text-xs leading-relaxed text-foreground/80 whitespace-pre-wrap">
                    {selectedUpdate.changelog}
                  </pre>
                </div>
              </div>
            </div>
          ) : (
            <div className="grid min-h-52 place-items-center text-center">
              <div>
                <Codicon className="text-muted-foreground/40" name="check" size="2rem" />
                <div className="mt-2 text-sm font-medium text-muted-foreground">All up to date</div>
                <div className="mt-1 text-xs text-muted-foreground/60">
                  {updates.length} {updates.length === 1 ? 'component is' : 'components are'} at the latest version
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageShell>
  )
}
