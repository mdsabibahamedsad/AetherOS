import { useCallback, useMemo, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { SearchField } from '@/components/ui/search-field'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'

const CATEGORIES = [
  'AI', 'Coding', 'Productivity', 'Automation', 'Research',
  'DevTools', 'Security', 'Vision', 'Speech', 'Translation',
  'Database', 'Cloud', 'Email', 'Communication', 'Filesystem', 'Utilities'
] as const

const SORT_OPTIONS = ['popularity', 'downloads', 'latest', 'verified'] as const

interface PluginAuthor {
  name: string
  avatar?: string
  url?: string
}

interface PluginVersion {
  version: string
  changelog?: string
  date: string
  requires?: string[]
}

interface PluginDependency {
  name: string
  version: string
  optional?: boolean
}

interface PluginPermission {
  name: string
  description: string
  required: boolean
}

interface PluginReview {
  id: string
  author: string
  rating: number
  comment: string
  date: string
}

interface PluginInfo {
  id: string
  name: string
  description: string
  longDescription?: string
  icon: string
  author: PluginAuthor
  version: string
  latestVersion?: string
  license: string
  homepage?: string
  repository?: string
  category: string
  rating: number
  downloads: number
  verified: boolean
  featured: boolean
  trending: boolean
  installed: boolean
  enabled: boolean
  installProgress?: number
  versions: PluginVersion[]
  dependencies: PluginDependency[]
  permissions: PluginPermission[]
  reviews: PluginReview[]
  screenshots: string[]
  readme?: string
  tags: string[]
}

const SAMPLE_PLUGINS: PluginInfo[] = [
  {
    id: 'aether-code-analyzer',
    name: 'Code Analyzer',
    description: 'Static analysis and linting for 40+ languages with real-time feedback',
    icon: 'code',
    author: { name: 'AetherOS Labs', url: 'https://aetheros.dev' },
    version: '2.1.0',
    license: 'MIT',
    homepage: 'https://github.com/aetheros/code-analyzer',
    category: 'Coding',
    rating: 4.8,
    downloads: 15234,
    verified: true,
    featured: true,
    trending: true,
    installed: true,
    enabled: true,
    versions: [
      { version: '2.1.0', changelog: 'Added Rust support, improved performance', date: '2026-06-15', requires: ['core>=0.16'] },
      { version: '2.0.0', changelog: 'Major refactor, new API', date: '2026-05-01', requires: ['core>=0.15'] }
    ],
    dependencies: [
      { name: 'core', version: '>=0.16', optional: false },
      { name: 'language-server-protocol', version: '>=1.0', optional: true }
    ],
    permissions: [
      { name: 'file:read', description: 'Read source files for analysis', required: true },
      { name: 'file:write', description: 'Write lint fixes', required: false }
    ],
    reviews: [
      { id: 'r1', author: 'dev42', rating: 5, comment: 'Essential tool for any developer', date: '2026-06-20' }
    ],
    screenshots: [],
    tags: ['linting', 'static-analysis', 'developer-tools']
  },
  {
    id: 'aether-search-assistant',
    name: 'Search Assistant',
    description: 'Intelligent web search with result summarization and source tracking',
    icon: 'globe',
    author: { name: 'AetherOS Labs' },
    version: '1.3.2',
    license: 'MIT',
    category: 'AI',
    rating: 4.6,
    downloads: 28901,
    verified: true,
    featured: true,
    trending: false,
    installed: false,
    enabled: false,
    versions: [
      { version: '1.3.2', changelog: 'Fixed rate limiting issues', date: '2026-06-10', requires: ['core>=0.15'] }
    ],
    dependencies: [{ name: 'core', version: '>=0.15', optional: false }],
    permissions: [
      { name: 'network:http', description: 'Make web search requests', required: true }
    ],
    reviews: [],
    screenshots: [],
    tags: ['search', 'web', 'ai']
  },
  {
    id: 'aether-task-automation',
    name: 'Task Automation',
    description: 'Visual workflow builder with 200+ integrations and triggers',
    icon: 'zap',
    author: { name: 'AetherOS Labs' },
    version: '3.0.1',
    license: 'Apache-2.0',
    category: 'Automation',
    rating: 4.7,
    downloads: 42100,
    verified: true,
    featured: false,
    trending: true,
    installed: false,
    enabled: false,
    versions: [
      { version: '3.0.1', changelog: 'New triggers: file change, webhook', date: '2026-06-01', requires: ['core>=0.16'] }
    ],
    dependencies: [
      { name: 'core', version: '>=0.16', optional: false },
      { name: 'aether-scheduler', version: '>=1.0', optional: true }
    ],
    permissions: [
      { name: 'file:*', description: 'Read and write files for workflow actions', required: true },
      { name: 'network:http', description: 'Make HTTP requests to integrations', required: true }
    ],
    reviews: [],
    screenshots: [],
    tags: ['automation', 'workflow', 'integrations']
  },
  {
    id: 'aether-vision-analyzer',
    name: 'Vision Analyzer',
    description: 'Image recognition, OCR, and object detection using local models',
    icon: 'photo',
    author: { name: 'AetherOS Labs' },
    version: '1.0.0',
    license: 'MIT',
    category: 'Vision',
    rating: 4.3,
    downloads: 8900,
    verified: true,
    featured: false,
    trending: false,
    installed: false,
    enabled: false,
    versions: [
      { version: '1.0.0', changelog: 'Initial release', date: '2026-05-20', requires: ['core>=0.15'] }
    ],
    dependencies: [{ name: 'core', version: '>=0.15', optional: false }],
    permissions: [
      { name: 'file:read', description: 'Read image files', required: true },
      { name: 'hardware:gpu', description: 'Access GPU for model inference', required: false }
    ],
    reviews: [],
    screenshots: [],
    tags: ['vision', 'ocr', 'image']
  },
  {
    id: 'aether-database-gateway',
    name: 'Database Gateway',
    description: 'Connect to PostgreSQL, MySQL, SQLite, and MongoDB with query builder',
    icon: 'database',
    author: { name: 'AetherOS Labs' },
    version: '2.2.1',
    license: 'MIT',
    category: 'Database',
    rating: 4.5,
    downloads: 12400,
    verified: true,
    featured: false,
    trending: false,
    installed: false,
    enabled: false,
    versions: [
      { version: '2.2.1', changelog: 'Added MongoDB support', date: '2026-06-18', requires: ['core>=0.16'] }
    ],
    dependencies: [{ name: 'core', version: '>=0.16', optional: false }],
    permissions: [
      { name: 'network:tcp', description: 'Connect to database servers', required: true },
      { name: 'file:read', description: 'Read SQLite databases', required: true }
    ],
    reviews: [],
    screenshots: [],
    tags: ['database', 'sql', 'nosql']
  },
  {
    id: 'aether-cloud-deploy',
    name: 'Cloud Deploy',
    description: 'One-click deployment to AWS, GCP, Azure, and DigitalOcean',
    icon: 'cloud',
    author: { name: 'AetherOS Labs' },
    version: '1.1.0',
    license: 'MIT',
    category: 'Cloud',
    rating: 4.2,
    downloads: 6700,
    verified: false,
    featured: false,
    trending: false,
    installed: false,
    enabled: false,
    versions: [
      { version: '1.1.0', changelog: 'Added Azure support', date: '2026-06-05', requires: ['core>=0.15'] }
    ],
    dependencies: [
      { name: 'core', version: '>=0.15', optional: false },
      { name: 'aether-terminal', version: '>=1.0', optional: true }
    ],
    permissions: [
      { name: 'network:http', description: 'Communicate with cloud provider APIs', required: true },
      { name: 'secret:env', description: 'Access cloud provider credentials', required: true }
    ],
    reviews: [],
    screenshots: [],
    tags: ['cloud', 'deployment', 'devops']
  },
  {
    id: 'aether-translate',
    name: 'Translate Plus',
    description: 'Real-time translation across 120+ languages with dialect detection',
    icon: 'language',
    author: { name: 'AetherOS Labs' },
    version: '2.0.0',
    license: 'MIT',
    category: 'Translation',
    rating: 4.4,
    downloads: 32100,
    verified: true,
    featured: false,
    trending: true,
    installed: false,
    enabled: false,
    versions: [
      { version: '2.0.0', changelog: 'Added offline translation mode', date: '2026-06-12', requires: ['core>=0.16'] }
    ],
    dependencies: [{ name: 'core', version: '>=0.16', optional: false }],
    permissions: [
      { name: 'network:http', description: 'Fetch translation models', required: true },
      { name: 'file:read', description: 'Read offline model files', required: false }
    ],
    reviews: [],
    screenshots: [],
    tags: ['translation', 'language', 'i18n']
  },
  {
    id: 'aether-security-scan',
    name: 'Security Scanner',
    description: 'Vulnerability scanning, dependency auditing, and secret detection',
    icon: 'shield',
    author: { name: 'AetherOS Labs' },
    version: '1.5.0',
    license: 'MIT',
    category: 'Security',
    rating: 4.9,
    downloads: 19800,
    verified: true,
    featured: true,
    trending: true,
    installed: false,
    enabled: false,
    versions: [
      { version: '1.5.0', changelog: 'Added real-time monitoring', date: '2026-06-20', requires: ['core>=0.16'] }
    ],
    dependencies: [{ name: 'core', version: '>=0.16', optional: false }],
    permissions: [
      { name: 'file:read', description: 'Scan files for vulnerabilities', required: true },
      { name: 'network:http', description: 'Check vulnerability databases', required: true }
    ],
    reviews: [],
    screenshots: [],
    tags: ['security', 'audit', 'vulnerability']
  },
  {
    id: 'aether-voice-control',
    name: 'Voice Control',
    description: 'Hands-free operation with wake word, commands, and dictation',
    icon: 'mic',
    author: { name: 'AetherOS Labs' },
    version: '1.2.1',
    license: 'MIT',
    category: 'Speech',
    rating: 4.1,
    downloads: 15400,
    verified: false,
    featured: false,
    trending: false,
    installed: false,
    enabled: false,
    versions: [
      { version: '1.2.1', changelog: 'Improved wake word detection', date: '2026-06-08', requires: ['core>=0.15'] }
    ],
    dependencies: [{ name: 'core', version: '>=0.15', optional: false }],
    permissions: [
      { name: 'hardware:audio', description: 'Access microphone for voice input', required: true }
    ],
    reviews: [],
    screenshots: [],
    tags: ['voice', 'speech', 'dictation']
  },
  {
    id: 'aether-email-hub',
    name: 'Email Hub',
    description: 'Unified inbox for Gmail, Outlook, and IMAP with AI-powered replies',
    icon: 'mail',
    author: { name: 'AetherOS Labs' },
    version: '1.0.3',
    license: 'MIT',
    category: 'Email',
    rating: 4.0,
    downloads: 9100,
    verified: false,
    featured: false,
    trending: false,
    installed: false,
    enabled: false,
    versions: [
      { version: '1.0.3', changelog: 'Bug fixes', date: '2026-06-14', requires: ['core>=0.15'] }
    ],
    dependencies: [{ name: 'core', version: '>=0.15', optional: false }],
    permissions: [
      { name: 'network:http', description: 'Connect to email servers', required: true },
      { name: 'secret:oauth', description: 'Store OAuth tokens for email providers', required: true }
    ],
    reviews: [],
    screenshots: [],
    tags: ['email', 'communication', 'inbox']
  },
  {
    id: 'aether-file-manager',
    name: 'File Manager Pro',
    description: 'Advanced file operations, sync, compression, and preview for any format',
    icon: 'folder',
    author: { name: 'AetherOS Labs' },
    version: '3.2.0',
    license: 'MIT',
    category: 'Filesystem',
    rating: 4.6,
    downloads: 45200,
    verified: true,
    featured: false,
    trending: false,
    installed: false,
    enabled: false,
    versions: [
      { version: '3.2.0', changelog: 'Added cloud sync support', date: '2026-06-22', requires: ['core>=0.16'] }
    ],
    dependencies: [{ name: 'core', version: '>=0.16', optional: false }],
    permissions: [
      { name: 'file:*', description: 'Full filesystem access', required: true },
      { name: 'network:http', description: 'Sync with cloud storage', required: false }
    ],
    reviews: [],
    screenshots: [],
    tags: ['files', 'sync', 'compression']
  },
  {
    id: 'aether-productivity-suite',
    name: 'Productivity Suite',
    description: 'Todo lists, notes, calendar, and project tracking in one place',
    icon: 'checklist',
    author: { name: 'AetherOS Labs' },
    version: '2.3.0',
    license: 'MIT',
    category: 'Productivity',
    rating: 4.5,
    downloads: 56000,
    verified: true,
    featured: true,
    trending: false,
    installed: false,
    enabled: false,
    versions: [
      { version: '2.3.0', changelog: 'Calendar integration', date: '2026-06-19', requires: ['core>=0.16'] }
    ],
    dependencies: [{ name: 'core', version: '>=0.16', optional: false }],
    permissions: [
      { name: 'file:read', description: 'Read notes and todo files', required: true },
      { name: 'file:write', description: 'Write notes and todo files', required: true }
    ],
    reviews: [],
    screenshots: [],
    tags: ['productivity', 'todo', 'notes']
  }
]

interface MarketplaceViewProps {
  onPluginSelect?: (plugin: PluginInfo) => void
  onBack?: () => void
}

export function MarketplaceView({ onPluginSelect, onBack }: MarketplaceViewProps) {
  const { t } = useI18n()
  const [query, setQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<string>('popularity')
  const [plugins, setPlugins] = useState<PluginInfo[]>(SAMPLE_PLUGINS)
  const [selectedPlugin, setSelectedPlugin] = useState<PluginInfo | null>(null)
  const [installingId, setInstallingId] = useState<string | null>(null)
  const [showFeatured, setShowFeatured] = useState(true)

  const filteredPlugins = useMemo(() => {
    const q = query.trim().toLowerCase()

    return plugins
      .filter(p => {
        if (activeCategory && p.category !== activeCategory) {return false}

        if (!q) {return true}

        return (
          p.name.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.author.name.toLowerCase().includes(q) ||
          p.tags.some(tag => tag.includes(q))
        )
      })
      .sort((a, b) => {
        switch (sortBy) {
          case 'downloads': return b.downloads - a.downloads

          case 'latest': return new Date(b.versions[0]?.date || 0).getTime() - new Date(a.versions[0]?.date || 0).getTime()

          case 'verified': return (b.verified ? 1 : 0) - (a.verified ? 1 : 0)

          default: return b.rating - a.rating || b.downloads - a.downloads
        }
      })
  }, [plugins, query, activeCategory, sortBy])

  const featuredPlugins = useMemo(() => plugins.filter(p => p.featured), [plugins])
  const trendingPlugins = useMemo(() => plugins.filter(p => p.trending), [plugins])

  const categoryCounts = useMemo(() => {
    const counts = new Map<string, number>()

    for (const p of plugins) {
      counts.set(p.category, (counts.get(p.category) || 0) + 1)
    }

    return counts
  }, [plugins])

  const handleInstall = useCallback(async (plugin: PluginInfo) => {
    setInstallingId(plugin.id)
    setPlugins(current => current.map(p => p.id === plugin.id ? { ...p, installProgress: 0 } : p))

    for (let i = 0; i <= 100; i += 20) {
      await new Promise(r => setTimeout(r, 200))
      setPlugins(current => current.map(p => p.id === plugin.id ? { ...p, installProgress: i } : p))
    }

    await new Promise(r => setTimeout(r, 500))
    setPlugins(current => current.map(p => p.id === plugin.id ? { ...p, installed: true, enabled: true, installProgress: undefined } : p))
    setInstallingId(null)
    notify({ kind: 'success', title: 'Plugin Installed', message: `${plugin.name} v${plugin.version} installed successfully` })
  }, [])

  const handleUninstall = useCallback(async (plugin: PluginInfo) => {
    setPlugins(current => current.map(p => p.id === plugin.id ? { ...p, installed: false, enabled: false } : p))
    notify({ kind: 'success', title: 'Plugin Removed', message: `${plugin.name} has been removed` })
  }, [])

  const handleToggleEnable = useCallback((plugin: PluginInfo) => {
    setPlugins(current => current.map(p => p.id === plugin.id ? { ...p, enabled: !p.enabled } : p))
  }, [])

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Plugin Marketplace</PageTitle>
            <PageDescription>Discover and install plugins to extend AetherOS</PageDescription>
          </div>
        </PageHeader>
      }
    >
      <div className="flex h-full gap-4">
        <aside className="w-48 shrink-0 space-y-1">
          <div className="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">Categories</div>
          <button
            className={cn(
              'flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-xs transition-colors',
              activeCategory === null ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'
            )}
            onClick={() => setActiveCategory(null)}
            type="button"
          >
            <span>All Plugins</span>
            <span className="text-[0.6rem] text-muted-foreground">{plugins.length}</span>
          </button>
          {CATEGORIES.map(category => (
            <button
              className={cn(
                'flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-xs transition-colors',
                activeCategory === category ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'
              )}
              key={category}
              onClick={() => setActiveCategory(activeCategory === category ? null : category)}
              type="button"
            >
              <span>{category}</span>
              <span className="text-[0.6rem] text-muted-foreground">{categoryCounts.get(category) || 0}</span>
            </button>
          ))}
        </aside>

        <div className="min-w-0 flex-1 space-y-4 overflow-y-auto">
          <div className="flex items-center gap-3">
            <SearchField
              containerClassName="flex-1 max-w-md"
              onChange={setQuery}
              placeholder="Search plugins..."
              value={query}
            />
            <Select onValueChange={setSortBy} value={sortBy}>
              <SelectTrigger className="h-8 w-36 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt}>
                    {opt.charAt(0).toUpperCase() + opt.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {showFeatured && !query && !activeCategory && (
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Featured</h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {featuredPlugins.slice(0, 3).map(plugin => (
                  <FeaturedPluginCard
                    installing={installingId === plugin.id}
                    key={plugin.id}
                    onInstall={() => void handleInstall(plugin)}
                    onSelect={() => setSelectedPlugin(plugin)}
                    plugin={plugin}
                  />
                ))}
              </div>
              {trendingPlugins.length > 0 && (
                <>
                  <h3 className="pt-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Trending</h3>
                  <div className="flex gap-3 overflow-x-auto pb-2">
                    {trendingPlugins.slice(0, 6).map(plugin => (
                      <TrendingPluginCard
                        key={plugin.id}
                        onSelect={() => setSelectedPlugin(plugin)}
                        plugin={plugin}
                      />
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          <div className="space-y-1">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {activeCategory || 'All Plugins'}
              <span className="ml-1 text-muted-foreground/60">({filteredPlugins.length})</span>
            </h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filteredPlugins.map(plugin => (
                <PluginCard
                  installing={installingId === plugin.id}
                  key={plugin.id}
                  onInstall={() => void handleInstall(plugin)}
                  onSelect={() => setSelectedPlugin(plugin)}
                  onToggleEnable={() => handleToggleEnable(plugin)}
                  onUninstall={() => void handleUninstall(plugin)}
                  plugin={plugin}
                />
              ))}
            </div>
            {filteredPlugins.length === 0 && (
              <div className="grid min-h-52 place-items-center text-center">
                <div>
                  <Codicon className="text-muted-foreground/40" name="search" size="2rem" />
                  <div className="mt-2 text-sm font-medium text-muted-foreground">No plugins found</div>
                  <div className="mt-1 text-xs text-muted-foreground/60">Try adjusting your search or filters</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <PluginDetailDialog
        installing={installingId === selectedPlugin?.id}
        onClose={() => setSelectedPlugin(null)}
        onInstall={() => selectedPlugin && void handleInstall(selectedPlugin)}
        onToggleEnable={() => selectedPlugin && handleToggleEnable(selectedPlugin)}
        onUninstall={() => {
          if (selectedPlugin) { void handleUninstall(selectedPlugin); setSelectedPlugin(null) }
        }}
        open={selectedPlugin !== null}
        plugin={selectedPlugin}
      />
    </PageShell>
  )
}

function FeaturedPluginCard({
  installing,
  onInstall,
  onSelect,
  plugin
}: {
  installing: boolean
  onInstall: () => void
  onSelect: () => void
  plugin: PluginInfo
}) {
  return (
    <button
      className="group relative flex flex-col overflow-hidden rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) text-left transition-all hover:border-(--ui-stroke-secondary) hover:shadow-sm"
      onClick={onSelect}
      type="button"
    >
      <div className="bg-gradient-to-br from-primary/5 to-primary/10 p-4">
        <PluginIcon category={plugin.category} />
      </div>
      <div className="flex flex-1 flex-col gap-1.5 p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium">{plugin.name}</span>
          {plugin.verified && <Codicon className="shrink-0 text-primary" name="verified" size="0.75rem" />}
        </div>
        <p className="line-clamp-2 text-xs text-muted-foreground">{plugin.description}</p>
        <div className="mt-auto flex items-center justify-between pt-2">
          <div className="flex items-center gap-1 text-[0.65rem] text-muted-foreground">
            <Codicon name="star" size="0.65rem" />
            {plugin.rating}
            <span className="ml-1">·</span>
            <Codicon name="download" size="0.65rem" />
            {(plugin.downloads / 1000).toFixed(1)}k
          </div>
          {plugin.installed ? (
            <Badge className="text-[0.6rem]" variant="muted">Installed</Badge>
          ) : (
            <Badge className="text-[0.6rem]" variant="default">
              {installing ? `Installing ${plugin.installProgress}%` : 'Install'}
            </Badge>
          )}
        </div>
      </div>
    </button>
  )
}

function TrendingPluginCard({
  onSelect,
  plugin
}: {
  onSelect: () => void
  plugin: PluginInfo
}) {
  return (
    <button
      className="flex shrink-0 items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-left text-xs transition-colors hover:bg-accent/60"
      onClick={onSelect}
      type="button"
    >
      <PluginIcon category={plugin.category} />
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-sm font-medium">{plugin.name}</span>
        </div>
        <span className="text-muted-foreground">by {plugin.author.name}</span>
      </div>
      <Badge className="shrink-0 text-[0.55rem]" variant="default">Trending</Badge>
    </button>
  )
}

function PluginCard({
  installing,
  onInstall,
  onSelect,
  onToggleEnable,
  onUninstall,
  plugin
}: {
  installing: boolean
  onInstall: () => void
  onSelect: () => void
  onToggleEnable: () => void
  onUninstall: () => void
  plugin: PluginInfo
}) {
  return (
    <div
      className="group relative flex flex-col rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) transition-all hover:border-(--ui-stroke-secondary) hover:shadow-sm"
    >
      <button className="flex flex-col p-3 text-left" onClick={onSelect} type="button">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <PluginIcon category={plugin.category} />
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="truncate text-sm font-medium">{plugin.name}</span>
                {plugin.verified && <Codicon className="shrink-0 text-primary" name="verified" size="0.65rem" />}
              </div>
              <span className="text-[0.6rem] text-muted-foreground">v{plugin.version}</span>
            </div>
          </div>
        </div>
        <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{plugin.description}</p>
        <div className="mt-2 flex items-center gap-2 text-[0.6rem] text-muted-foreground">
          <span>{plugin.author.name}</span>
          <span>·</span>
          <Codicon name="star" size="0.6rem" />
          {plugin.rating}
          <span>·</span>
          <Codicon name="download" size="0.6rem" />
          {(plugin.downloads / 1000).toFixed(1)}k
        </div>
      </button>
      <div className="flex items-center gap-1 border-t border-(--ui-stroke-tertiary) px-3 py-2">
        {plugin.installed ? (
          <>
            <Button className="flex-1 text-xs" onClick={onToggleEnable} size="sm" variant={plugin.enabled ? 'default' : 'outline'}>
              {plugin.enabled ? 'Enabled' : 'Disabled'}
            </Button>
            <Button className="flex-1 text-xs text-muted-foreground hover:text-destructive" onClick={onUninstall} size="sm" variant="ghost">
              Remove
            </Button>
          </>
        ) : (
          <Button className="flex-1 text-xs" disabled={installing} onClick={onInstall} size="sm">
            {installing ? `Installing ${plugin.installProgress}%` : 'Install'}
          </Button>
        )}
      </div>
    </div>
  )
}

function PluginDetailDialog({
  installing,
  onClose,
  onInstall,
  onToggleEnable,
  onUninstall,
  open,
  plugin
}: {
  installing: boolean
  onClose: () => void
  onInstall: () => void
  onToggleEnable: () => void
  onUninstall: () => void
  open: boolean
  plugin: PluginInfo | null
}) {
  if (!plugin) {return null}

  return (
    <Dialog onOpenChange={v => !v && onClose()} open={open}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <PluginIcon category={plugin.category} />
            <div>
              <DialogTitle>{plugin.name}</DialogTitle>
              <DialogDescription>
                {plugin.description}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="max-h-[60vh] space-y-5 overflow-y-auto px-1">
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            <span><span className="font-medium text-foreground">Version:</span> {plugin.version}</span>
            <span><span className="font-medium text-foreground">Author:</span> {plugin.author.name}</span>
            <span><span className="font-medium text-foreground">License:</span> {plugin.license}</span>
            {plugin.homepage && (
              <a className="flex items-center gap-1 text-primary hover:underline" href={plugin.homepage} rel="noreferrer" target="_blank">
                Homepage <Codicon name="link-external" size="0.65rem" />
              </a>
            )}
            <span><span className="font-medium text-foreground">Rating:</span> {plugin.rating} / 5</span>
            <span><span className="font-medium text-foreground">Downloads:</span> {plugin.downloads.toLocaleString()}</span>
          </div>

          <div>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Description</h4>
            <p className="text-xs leading-relaxed text-foreground/80">{plugin.longDescription || plugin.description}</p>
          </div>

          <div>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tags</h4>
            <div className="flex flex-wrap gap-1.5">
              {plugin.tags.map(tag => (
                <Badge key={tag} variant="outline">{tag}</Badge>
              ))}
            </div>
          </div>

          <div>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Permissions</h4>
            <div className="space-y-1">
              {plugin.permissions.map(perm => (
                <div className="flex items-start gap-2 rounded-md bg-(--ui-bg-quinary) px-2.5 py-1.5" key={perm.name}>
                  <Codicon className="mt-0.5 shrink-0 text-muted-foreground" name={perm.required ? 'lock' : 'unlock'} size="0.75rem" />
                  <div>
                    <span className="text-xs font-medium">{perm.name}</span>
                    <p className="text-[0.65rem] text-muted-foreground">{perm.description}</p>
                  </div>
                  {perm.required ? (
                    <Badge className="ml-auto shrink-0 text-[0.55rem]" variant="default">Required</Badge>
                  ) : (
                    <Badge className="ml-auto shrink-0 text-[0.55rem]" variant="outline">Optional</Badge>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Dependencies</h4>
            <div className="space-y-1">
              {plugin.dependencies.map(dep => (
                <div className="flex items-center gap-2 text-xs" key={dep.name}>
                  <Codicon name="package" size="0.75rem" />
                  <span className="font-medium">{dep.name}</span>
                  <span className="text-muted-foreground">({dep.version})</span>
                  {dep.optional && <Badge className="text-[0.55rem]" variant="outline">Optional</Badge>}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Version History</h4>
            <div className="space-y-1.5">
              {plugin.versions.map(v => (
                <div className="rounded-md border border-(--ui-stroke-tertiary) px-2.5 py-1.5" key={v.version}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium">v{v.version}</span>
                    <span className="text-[0.6rem] text-muted-foreground">{v.date}</span>
                  </div>
                  {v.changelog && <p className="mt-0.5 text-[0.65rem] text-muted-foreground">{v.changelog}</p>}
                </div>
              ))}
            </div>
          </div>

          {plugin.reviews.length > 0 && (
            <div>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Reviews</h4>
              <div className="space-y-1.5">
                {plugin.reviews.map(review => (
                  <div className="rounded-md bg-(--ui-bg-quinary) px-2.5 py-1.5" key={review.id}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium">{review.author}</span>
                      <span className="flex items-center gap-1 text-[0.6rem] text-amber-500">
                        <Codicon name="star" size="0.6rem" />{review.rating}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[0.65rem] text-muted-foreground">{review.comment}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          {plugin.installed ? (
            <>
              <Button onClick={onToggleEnable} size="sm" variant={plugin.enabled ? 'outline' : 'default'}>
                {plugin.enabled ? 'Disable' : 'Enable'}
              </Button>
              <Button onClick={onUninstall} size="sm" variant="destructive">Remove</Button>
            </>
          ) : (
            <Button disabled={installing} onClick={onInstall} size="sm">
              {installing ? `Installing ${plugin.installProgress}%` : `Install v${plugin.version}`}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function PluginIcon({ category, className }: { category: string; className?: string }) {
  const iconMap: Record<string, string> = {
    'AI': 'brain',
    'Coding': 'code',
    'Productivity': 'checklist',
    'Automation': 'zap',
    'Research': 'book',
    'DevTools': 'tools',
    'Security': 'shield',
    'Vision': 'eye',
    'Speech': 'mic',
    'Translation': 'globe',
    'Database': 'database',
    'Cloud': 'cloud',
    'Email': 'mail',
    'Communication': 'comment',
    'Filesystem': 'folder',
    'Utilities': 'wrench'
  }

  return (
    <span className={cn('flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary', className)}>
      <Codicon name={iconMap[category] || 'package'} size="1rem" />
    </span>
  )
}
