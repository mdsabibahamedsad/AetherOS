import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { CREDENTIAL_CONTROL_CLASS } from '@/app/settings/credential-key-ui'
import { ListRow } from '@/app/settings/primitives'
import { StatusDot, type StatusTone } from '@/components/status-dot'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Activity, Archive, BarChart3, Brain, FileText, FolderOpen, Globe, Hash, Layers3, Link, Lock, MessageCircle, NotebookTabs, Package, RefreshCw, Search, Send, Sparkles, Trash2, Users, Zap } from '@/lib/icons'
import { cn } from '@/lib/utils'
import {
  $knowledge,
  addBase,
  addCollection,
  addDocument,
  addGraphNode,
  addMemory,
  addSearchResult,
  addTag,
  type AnalyticsStats,
  archiveDocument,
  type FileType,
  getArchivedDocuments,
  getFavoriteDocuments,
  getFilteredBases,
  getFilteredDocuments,
  getFilteredMemory,
  getRecentDocuments,
  type KnowledgeBase,
  type KnowledgeDocument,
  type KnowledgeSection,
  type KnowledgeSource,
  type MemoryEntry,
  type MemoryType,
  pinMemory,
  type ProcessingConfig,
  type ProcessingStatus,
  type RAGConfig,
  removeBase,
  removeCollection,
  removeDocument,
  removeMemory,
  removeTag,
  restoreDocument,
  type SearchResult,
  type SecurityConfig,
  selectMemoryType,
  setKnowledgeSearch,
  setKnowledgeSection,
  setSearchType,
  toggleDocumentFavorite,
  triggerSync,
  unpinMemory,
  updateProcessing,
  updateRAG,
  updateSecurity
} from '@/store/knowledge'

type TabDef = { id: KnowledgeSection; label: string; icon: typeof NotebookTabs }

const SECTIONS: TabDef[] = [
  { id: 'bases', label: 'Bases', icon: Package },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'search', label: 'Search', icon: Search },
  { id: 'memory', label: 'Memory', icon: Brain },
  { id: 'collections', label: 'Collections', icon: FolderOpen },
  { id: 'tags', label: 'Tags', icon: Hash },
  { id: 'favorites', label: 'Favorites', icon: Sparkles },
  { id: 'recent', label: 'Recent', icon: Activity },
  { id: 'shared', label: 'Shared', icon: Send },
  { id: 'archived', label: 'Archived', icon: Archive },
  { id: 'graph', label: 'Graph', icon: Layers3 },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'sync', label: 'Sync', icon: RefreshCw },
  { id: 'settings', label: 'Settings', icon: Lock }
]

function formatBytes(bytes: number): string {
  if (bytes < 1024) {return `${bytes} B`}

  if (bytes < 1048576) {return `${(bytes / 1024).toFixed(1)} KB`}

  if (bytes < 1073741824) {return `${(bytes / 1048576).toFixed(1)} MB`}

  return `${(bytes / 1073741824).toFixed(2)} GB`
}

function formatTime(t: string): string {
  const d = new Date(t); const n = new Date()

  if (d.toDateString() === n.toDateString()) {return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}

  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

const FILE_TYPE_COLORS: Partial<Record<FileType, string>> = {
  pdf: '#EF4444', docx: '#3B82F6', txt: '#6B7280', md: '#10B981',
  csv: '#F59E0B', excel: '#22C55E', ppt: '#F97316',
  json: '#8B5CF6', yaml: '#06B6D4', xml: '#6366F1', html: '#EC4899',
  epub: '#A855F7', code: '#84CC16', zip: '#71717A',
  image: '#14B8A6', audio: '#F43F5E', video: '#8B5CF6'
}

const PROC_STATUS_TONES: Record<ProcessingStatus, StatusTone> = {
  pending: 'warn', processing: 'warn', completed: 'good', failed: 'bad', skipped: 'muted'
}

const SOURCE_ICONS: Partial<Record<KnowledgeSource, typeof NotebookTabs>> = {
  'local-folder': FolderOpen, 'git-repo': Activity, 'github': Activity,
  'website': Globe, 'rss': Hash, 'notion': NotebookTabs,
  'google-drive': Activity, 'dropbox': Activity, 'onedrive': Activity,
  'sharepoint': Activity, 's3': Package, 'webdav': Link, 'custom-api': Zap
}

const MEMORY_ICONS: Record<MemoryType, typeof NotebookTabs> = {
  working: Zap, conversation: MessageCircle, project: FolderOpen,
  'long-term': Package, agent: Brain, shared: Users, pinned: Sparkles, temporary: Activity
}

const MEMORY_COLORS: Record<MemoryType, string> = {
  working: '#F59E0B', conversation: '#3B82F6', project: '#10B981',
  'long-term': '#8B5CF6', agent: '#EC4899', shared: '#06B6D4', pinned: '#EF4444', temporary: '#6B7280'
}

export function KnowledgeView() {
  const state = useStore($knowledge)

  return (
    <div className="flex h-full min-w-0 flex-col overflow-hidden bg-(--ui-chat-surface-background)">
      <div className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Knowledge Hub</h1>
          <p className="mt-0.5 text-xs text-(--ui-text-tertiary)">
            {state.bases.length} bases · {state.documents.length} documents · {(state.analytics.totalStorage / 1048576).toFixed(1)} MB
          </p>
        </div>
        <div className="flex items-center gap-2">
          {state.activeSection === 'search' && (
            <div className="flex items-center gap-1">
              {(['semantic', 'hybrid', 'keyword', 'vector'] as const).map(t => (
                <button className={cn('rounded px-1.5 py-0.5 text-[0.6rem] font-medium transition-colors',
                    state.searchType === t ? 'bg-primary/10 text-primary' : 'text-(--ui-text-tertiary) hover:text-foreground'
                  )} key={t} onClick={() => setSearchType(t)}
                  type="button"
                >{t}</button>
              ))}
            </div>
          )}
          {state.activeSection !== 'search' && (
            <Input
              className={cn('h-7 w-48 text-xs', CREDENTIAL_CONTROL_CLASS)}
              onChange={e => setKnowledgeSearch(e.target.value)}
              placeholder={`Search ${state.activeSection}...`}
              value={state.searchQuery}
            />
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-0.5 overflow-x-auto border-b border-(--ui-stroke-tertiary) px-3">
        {SECTIONS.map(s => {
          const Icon = s.icon

          return (
            <button className={cn('flex shrink-0 items-center gap-1.5 border-b-2 px-2.5 py-2 text-sm font-medium transition-colors',
                state.activeSection === s.id
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-(--ui-text-secondary) hover:text-foreground'
              )} key={s.id} onClick={() => setKnowledgeSection(s.id)}
              type="button"
            >
              <Icon className="size-3.5" />
              <span className="hidden sm:inline">{s.label}</span>
            </button>
          )
        })}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {state.activeSection === 'bases' && <BasesPanel />}
        {state.activeSection === 'documents' && <DocumentsPanel />}
        {state.activeSection === 'search' && <SearchPanel />}
        {state.activeSection === 'memory' && <MemoryPanel />}
        {state.activeSection === 'collections' && <CollectionsPanel />}
        {state.activeSection === 'tags' && <TagsPanel />}
        {state.activeSection === 'favorites' && <FavoritesPanel />}
        {state.activeSection === 'recent' && <RecentPanel />}
        {state.activeSection === 'shared' && <SharedPanel />}
        {state.activeSection === 'archived' && <ArchivedPanel />}
        {state.activeSection === 'graph' && <GraphPanel />}
        {state.activeSection === 'analytics' && <AnalyticsPanel />}
        {state.activeSection === 'sync' && <SyncPanel />}
        {state.activeSection === 'settings' && <SettingsPanel />}
      </div>
    </div>
  )
}

function BasesPanel() {
  const state = useStore($knowledge)
  const filtered = getFilteredBases()
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [source, setSource] = useState<KnowledgeSource>('local-folder')
  const [url, setUrl] = useState('')

  const handleAdd = () => {
    if (!name.trim()) {return}
    addBase({ name: name.trim(), description: desc.trim(), source, sourceUrl: url, fileTypes: ['pdf', 'txt', 'md', 'docx'], processingStatus: 'pending', embeddingModel: 'text-embedding-3-small', lastSync: null, syncInterval: 0, autoSync: false, archived: false, tags: [], workspaceId: 'default', size: 0, error: null })
    setName(''); setDesc(''); setUrl(''); setShowForm(false)
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-(--ui-text-tertiary)">{state.bases.length} knowledge bases</p>
        <Button onClick={() => setShowForm(!showForm)} size="sm" variant="textStrong">+ New Base</Button>
      </div>

      {showForm && (
        <div className="space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4">
          <Input className="h-7 text-xs" onChange={e => setName(e.target.value)} placeholder="Base name..." value={name} />
          <Input className="h-7 text-xs" onChange={e => setDesc(e.target.value)} placeholder="Description..." value={desc} />
          <div className="flex flex-wrap gap-2">
            <select className={CREDENTIAL_CONTROL_CLASS} onChange={e => setSource(e.target.value as any)} value={source}>
              <option value="local-folder">Local Folder</option>
              <option value="git-repo">Git Repository</option>
              <option value="github">GitHub</option>
              <option value="website">Website</option>
              <option value="rss">RSS</option>
              <option value="notion">Notion</option>
              <option value="google-drive">Google Drive</option>
              <option value="dropbox">Dropbox</option>
              <option value="onedrive">OneDrive</option>
              <option value="sharepoint">SharePoint</option>
              <option value="s3">S3</option>
              <option value="webdav">WebDAV</option>
              <option value="custom-api">Custom API</option>
            </select>
          </div>
          <Input className="h-7 text-xs" onChange={e => setUrl(e.target.value)} placeholder="Source URL..." value={url} />
          <div className="flex justify-end gap-2">
            <Button onClick={() => setShowForm(false)} size="xs" variant="ghost">Cancel</Button>
            <Button onClick={handleAdd} size="xs" variant="textStrong">Create</Button>
          </div>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Package className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No knowledge bases</p>
          <p className="mt-1 text-xs text-(--ui-text-tertiary)">Create a knowledge base to start indexing documents</p>
        </div>
      )}

      <div className="space-y-2">
        {filtered.map(base => (
          <BaseCard base={base} key={base.id} />
        ))}
      </div>
    </div>
  )
}

function BaseCard({ base }: { base: KnowledgeBase }) {
  const [expanded, setExpanded] = useState(false)
  const docs = useStore($knowledge).documents.filter(d => d.baseId === base.id)
  const SourceIcon = SOURCE_ICONS[base.source] || FolderOpen

  return (
    <div className="rounded-lg border border-(--ui-stroke-tertiary) transition-colors hover:bg-(--chrome-action-hover)">
      <button className="flex w-full items-center gap-3 px-4 py-3 text-left" onClick={() => setExpanded(!expanded)} type="button">
        <span className="inline-flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary">
          <SourceIcon className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{base.name}</span>
            <Badge className="px-1 py-0 text-[0.55rem]" variant="muted">{base.source.replace(/-/g, ' ')}</Badge>
            <StatusDot tone={PROC_STATUS_TONES[base.processingStatus]} />
          </div>
          {base.description && <p className="mt-0.5 text-xs text-(--ui-text-tertiary)">{base.description}</p>}
          <div className="mt-1 flex items-center gap-3 text-[0.6rem] text-(--ui-text-tertiary)">
            <span>{base.documentCount} docs</span>
            <span>{base.chunkCount} chunks</span>
            <span>{formatBytes(base.size)}</span>
            {base.lastSync && <span>Synced {formatTime(base.lastSync)}</span>}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {base.autoSync && <Badge className="px-1 py-0 text-[0.5rem]" variant="default">Auto</Badge>}
        </div>
      </button>
      {expanded && (
        <div className="border-t border-(--ui-stroke-tertiary) px-4 py-3">
          <div className="mb-3 flex items-center gap-2">
            <Button onClick={() => triggerSync(base.id)} size="xs" variant="outline"><RefreshCw className="size-3" /> Sync</Button>
            <Button onClick={() => { removeBase(base.id) }} size="xs" variant="ghost"><Trash2 className="size-3" /></Button>
          </div>
          {docs.length > 0 && (
            <div className="space-y-1">
              <p className="text-[0.65rem] font-medium text-(--ui-text-tertiary)">Documents ({docs.length})</p>
              {docs.slice(0, 5).map(doc => (
                <div className="flex items-center gap-2 rounded px-2 py-1 text-xs hover:bg-(--chrome-action-hover)" key={doc.id}>
                  <StatusDot tone={PROC_STATUS_TONES[doc.status]} />
                  <span className="min-w-0 flex-1 truncate">{doc.name}</span>
                  <span className="text-(--ui-text-tertiary)">{doc.chunkCount} chunks</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DocumentsPanel() {
  const state = useStore($knowledge)
  const filtered = getFilteredDocuments()
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [fileType, setFileType] = useState<FileType>('pdf')
  const [baseId, setBaseId] = useState('')

  const handleAdd = () => {
    if (!name.trim()) {return}
    addDocument({
      baseId: baseId || 'default', name: name.trim(), fileType,
      size: 0, pageCount: 0, status: 'pending',
      error: null, author: null, language: null,
      sourceUrl: '', checksum: '',
      metadata: {}, tags: [], collections: [],
      favorite: false, archived: false, vectorized: false, indexed: false
    })
    setName(''); setShowForm(false)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-(--ui-text-tertiary)">{state.documents.length} documents</p>
        <Button onClick={() => setShowForm(!showForm)} size="sm" variant="textStrong">+ Add Document</Button>
      </div>

      {showForm && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
          <Input className="h-7 w-60 text-xs" onChange={e => setName(e.target.value)} placeholder="File name..." value={name} />
          <select className={CREDENTIAL_CONTROL_CLASS} onChange={e => setFileType(e.target.value as any)} value={fileType}>
            {(['pdf', 'docx', 'txt', 'md', 'csv', 'excel', 'ppt', 'json', 'yaml', 'xml', 'html', 'epub', 'code', 'zip', 'image', 'audio', 'video'] as FileType[]).map(ft => (
              <option key={ft} value={ft}>{ft.toUpperCase()}</option>
            ))}
          </select>
          <select className={CREDENTIAL_CONTROL_CLASS} onChange={e => setBaseId(e.target.value)} value={baseId}>
            <option value="">Select base...</option>
            {state.bases.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          <Button onClick={handleAdd} size="xs" variant="textStrong">Add</Button>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <FileText className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No documents</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map(doc => (
          <DocumentCard doc={doc} key={doc.id} />
        ))}
      </div>
    </div>
  )
}

function DocumentCard({ doc }: { doc: KnowledgeDocument }) {
  const knowledge = useStore($knowledge)

  return (
    <div className={cn('rounded-lg border border-(--ui-stroke-tertiary) p-3 transition-colors hover:bg-(--chrome-action-hover)', doc.archived && 'opacity-60')}>
      <div className="flex items-start gap-3">
        <span className="inline-grid size-8 shrink-0 place-items-center rounded-md text-xs font-bold"
          style={{ backgroundColor: `color-mix(in srgb, ${FILE_TYPE_COLORS[doc.fileType] ?? '#6B7280'} 16%, transparent)`, color: FILE_TYPE_COLORS[doc.fileType] ?? '#6B7280' }}>
          {doc.fileType.toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium">{doc.name}</span>
            <StatusDot tone={PROC_STATUS_TONES[doc.status]} />
          </div>
          <div className="mt-0.5 flex flex-wrap gap-1">
            {doc.tags.map(tagId => {
              const tag = knowledge.tags.find(t => t.id === tagId)

              return tag ? <span className="rounded bg-(--ui-row-active-background) px-1 py-0 text-[0.5rem] text-(--ui-text-tertiary)" key={tagId}>{tag.name}</span> : null
            })}
          </div>
          <div className="mt-1 flex items-center gap-2 text-[0.55rem] text-(--ui-text-tertiary)">
            <span>{formatBytes(doc.size)}</span>
            {doc.pageCount > 0 && <span>{doc.pageCount} pages</span>}
            <span>{doc.chunkCount} chunks</span>
            {doc.author && <span>{doc.author}</span>}
          </div>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-1">
        <Button onClick={() => toggleDocumentFavorite(doc.id)} size="xs" variant="ghost">
          <Sparkles className={cn('size-3', doc.favorite && 'fill-amber-500 text-amber-500')} />
        </Button>
        <Button onClick={() => archiveDocument(doc.id)} size="xs" variant="ghost"><Archive className="size-3" /></Button>
        <Button onClick={() => { removeDocument(doc.id) }} size="xs" variant="ghost"><Trash2 className="size-3" /></Button>
        {doc.status === 'pending' && (
          <span className="ml-auto text-[0.55rem] text-(--ui-text-tertiary)">{doc.progress}%</span>
        )}
      </div>
      {doc.error && <p className="mt-1 text-[0.6rem] text-destructive">{doc.error}</p>}
    </div>
  )
}

function SearchPanel() {
  const state = useStore($knowledge)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])

  const handleSearch = () => {
    if (!query.trim()) {return}
    const q = query.toLowerCase().trim()

    const docs = state.documents.filter(d =>
      d.name.toLowerCase().includes(q) || d.tags.some(t => t.toLowerCase().includes(q))
    )

    const mockResults: SearchResult[] = docs.slice(0, 10).map((d, i) => ({
      id: `sr-${i}`, documentId: d.id, baseId: d.baseId,
      chunkIndex: 0, content: d.name,
      score: 1 - (i * 0.1), source: d.sourceUrl || d.name,
      documentName: d.name, fileType: d.fileType,
      highlights: [], metadata: d.metadata
    }))

    setResults(mockResults)
    addSearchResult(query.trim(), mockResults)
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex gap-2">
        <Input className="h-8 flex-1 text-xs" onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="Search across all knowledge bases..." value={query} />
        <Button onClick={handleSearch} size="sm" variant="textStrong"><Search className="size-3.5" /> Search</Button>
      </div>

      {results.length > 0 && (
        <>
          <p className="text-xs text-(--ui-text-tertiary)">{results.length} results</p>
          <div className="space-y-2">
            {results.map(r => (
              <div className="rounded-lg border border-(--ui-stroke-tertiary) p-3 transition-colors hover:bg-(--chrome-action-hover)" key={r.id}>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[0.55rem] font-medium text-primary">
                    {r.fileType.toUpperCase()}
                  </span>
                  <span className="text-sm font-medium">{r.documentName}</span>
                  <span className="ml-auto text-[0.55rem] text-(--ui-text-tertiary)">
                    Score: {(r.score * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="mt-1 text-xs text-(--ui-text-tertiary)">{r.content}</p>
                <p className="mt-0.5 text-[0.55rem] text-(--ui-text-tertiary)">{r.source}</p>
              </div>
            ))}
          </div>
        </>
      )}

      {results.length === 0 && query && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Search className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No results</p>
        </div>
      )}
    </div>
  )
}

function MemoryPanel() {
  const state = useStore($knowledge)
  const filtered = getFilteredMemory()
  const [showForm, setShowForm] = useState(false)
  const [content, setContent] = useState('')
  const [memType, setMemType] = useState<MemoryType>('working')

  const MEMORY_TYPES: { id: MemoryType; label: string }[] = [
    { id: 'working', label: 'Working' }, { id: 'conversation', label: 'Conversation' },
    { id: 'project', label: 'Project' }, { id: 'long-term', label: 'Long-Term' },
    { id: 'agent', label: 'Agent' }, { id: 'shared', label: 'Shared' },
    { id: 'pinned', label: 'Pinned' }, { id: 'temporary', label: 'Temporary' }
  ]

  const handleAdd = () => {
    if (!content.trim()) {return}
    addMemory({ type: memType, content: content.trim(), summary: null, source: 'manual', agentId: null, sessionId: null, projectId: null, tags: [], pinned: false, lastAccessed: null, relevanceScore: 0.5, ttl: memType === 'temporary' ? 3600000 : null })
    setContent(''); setShowForm(false)
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-1">
          <button className={cn('rounded px-1.5 py-0.5 text-[0.6rem] font-medium transition-colors', state.selectedMemoryType === 'all' ? 'bg-primary/10 text-primary' : 'text-(--ui-text-tertiary) hover:text-foreground')} key="all" onClick={() => selectMemoryType('all')}
            type="button">
            All ({state.memory.length})
          </button>
          {MEMORY_TYPES.map(mt => {
            const count = state.memory.filter(m => m.type === mt.id).length

            return (
              <button className={cn('rounded px-1.5 py-0.5 text-[0.6rem] font-medium transition-colors', state.selectedMemoryType === mt.id ? 'bg-primary/10 text-primary' : 'text-(--ui-text-tertiary) hover:text-foreground')} key={mt.id} onClick={() => selectMemoryType(mt.id)}
                type="button">
                {mt.label} ({count})
              </button>
            )
          })}
        </div>
        <Button onClick={() => setShowForm(!showForm)} size="sm" variant="textStrong">+ Add</Button>
      </div>

      {showForm && (
        <div className="space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
          <textarea className={cn('min-h-[60px] w-full resize-none rounded-md border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1.5 text-xs', CREDENTIAL_CONTROL_CLASS)}
            onChange={e => setContent(e.target.value)} placeholder="Memory content..." value={content} />
          <div className="flex items-center justify-between">
            <select className={CREDENTIAL_CONTROL_CLASS} onChange={e => setMemType(e.target.value as any)} value={memType}>
              {MEMORY_TYPES.map(mt => <option key={mt.id} value={mt.id}>{mt.label}</option>)}
            </select>
            <div className="flex gap-2">
              <Button onClick={() => setShowForm(false)} size="xs" variant="ghost">Cancel</Button>
              <Button onClick={handleAdd} size="xs" variant="textStrong">Save</Button>
            </div>
          </div>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Brain className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No memory entries</p>
        </div>
      )}

      <div className="space-y-2">
        {filtered.map(entry => (
          <MemoryCard entry={entry} key={entry.id} />
        ))}
      </div>
    </div>
  )
}

function MemoryCard({ entry }: { entry: MemoryEntry }) {
  const Icon = MEMORY_ICONS[entry.type]
  const color = MEMORY_COLORS[entry.type]

  return (
    <div className="rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5 transition-colors hover:bg-(--chrome-action-hover)">
      <div className="flex items-start gap-3">
        <span className="inline-flex size-7 items-center justify-center rounded-md" style={{ backgroundColor: `color-mix(in srgb, ${color} 16%, transparent)` }}>
          <Icon className="size-3.5" style={{ color }} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium capitalize">{entry.type} Memory</span>
            {entry.pinned && <Badge className="px-1 py-0 text-[0.5rem]" variant="default">Pinned</Badge>}
          </div>
          <p className="mt-0.5 text-xs text-(--ui-text-secondary)">{entry.content}</p>
          {entry.summary && <p className="mt-0.5 text-[0.6rem] italic text-(--ui-text-tertiary)">{entry.summary}</p>}
          <div className="mt-1 flex items-center gap-2 text-[0.55rem] text-(--ui-text-tertiary)">
            <span>Score: {(entry.relevanceScore * 100).toFixed(0)}%</span>
            <span>Access: {entry.accessCount}</span>
            {entry.source && <span>Source: {entry.source}</span>}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {entry.pinned
            ? <Button onClick={() => unpinMemory(entry.id)} size="xs" variant="ghost"><Sparkles className="size-3 fill-amber-500 text-amber-500" /></Button>
            : <Button onClick={() => pinMemory(entry.id)} size="xs" variant="ghost"><Sparkles className="size-3" /></Button>
          }
          <Button onClick={() => { removeMemory(entry.id) }} size="xs" variant="ghost"><Trash2 className="size-3" /></Button>
        </div>
      </div>
    </div>
  )
}

function CollectionsPanel() {
  const state = useStore($knowledge)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [color, setColor] = useState('#3B82F6')

  const handleAdd = () => {
    if (!name.trim()) {return}
    addCollection({ name: name.trim(), description: desc.trim(), color, icon: 'folder' })
    setName(''); setDesc(''); setShowForm(false)
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-(--ui-text-tertiary)">{state.collections.length} collections</p>
        <Button onClick={() => setShowForm(!showForm)} size="sm" variant="textStrong">+ New Collection</Button>
      </div>
      {showForm && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
          <Input className="h-7 w-48 text-xs" onChange={e => setName(e.target.value)} placeholder="Name..." value={name} />
          <Input className="h-7 flex-1 text-xs" onChange={e => setDesc(e.target.value)} placeholder="Description..." value={desc} />
          <input className="h-7 w-8 cursor-pointer rounded border border-(--ui-stroke-tertiary)" onChange={e => setColor(e.target.value)} type="color" value={color} />
          <Button onClick={handleAdd} size="xs" variant="textStrong">Create</Button>
        </div>
      )}
      {state.collections.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <FolderOpen className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No collections</p>
        </div>
      )}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {state.collections.map(coll => (
          <div className="rounded-lg border border-(--ui-stroke-tertiary) p-3 transition-colors hover:bg-(--chrome-action-hover)" key={coll.id}>
            <div className="flex items-center gap-3">
              <span className="inline-grid size-8 place-items-center rounded-md text-sm" style={{ backgroundColor: `color-mix(in srgb, ${coll.color} 16%, transparent)` }}>
                <FolderOpen className="size-4" style={{ color: coll.color }} />
              </span>
              <div className="min-w-0 flex-1">
                <span className="text-sm font-medium">{coll.name}</span>
                <p className="text-xs text-(--ui-text-tertiary)">{coll.description}</p>
                <p className="text-[0.55rem] text-(--ui-text-tertiary)">{coll.documentCount} documents</p>
              </div>
              <Button onClick={() => { removeCollection(coll.id) }} size="xs" variant="ghost"><Trash2 className="size-3" /></Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function TagsPanel() {
  const state = useStore($knowledge)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [color, setColor] = useState('#3B82F6')

  const handleAdd = () => {
    if (!name.trim()) {return}
    addTag({ name: name.trim(), color })
    setName(''); setShowForm(false)
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-(--ui-text-tertiary)">{state.tags.length} tags</p>
        <Button onClick={() => setShowForm(!showForm)} size="sm" variant="textStrong">+ New Tag</Button>
      </div>
      {showForm && (
        <div className="flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
          <Input className="h-7 w-40 text-xs" onChange={e => setName(e.target.value)} placeholder="Tag name..." value={name} />
          <input className="h-7 w-8 cursor-pointer rounded border border-(--ui-stroke-tertiary)" onChange={e => setColor(e.target.value)} type="color" value={color} />
          <Button onClick={handleAdd} size="xs" variant="textStrong">Add</Button>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {state.tags.map(tag => (
          <div className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs transition-colors hover:opacity-80" key={tag.id}
            style={{ backgroundColor: `color-mix(in srgb, ${tag.color} 16%, transparent)`, color: tag.color }}>
            <Hash className="size-3" />
            <span>{tag.name}</span>
            <span className="opacity-60">({tag.documentCount})</span>
            <button className="ml-0.5 opacity-50 hover:opacity-100" onClick={() => { removeTag(tag.id) }} type="button">×</button>
          </div>
        ))}
      </div>
    </div>
  )
}

function FavoritesPanel() {
  const favs = getFavoriteDocuments()

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <p className="text-sm text-(--ui-text-tertiary)">{favs.length} favorites</p>
      {favs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Sparkles className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No favorites yet</p>
          <p className="mt-1 text-xs text-(--ui-text-tertiary)">Star documents to add them to favorites</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {favs.map(doc => <DocumentCard doc={doc} key={doc.id} />)}
        </div>
      )}
    </div>
  )
}

function RecentPanel() {
  const recent = getRecentDocuments()

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <p className="text-sm text-(--ui-text-tertiary)">{recent.length} recently viewed</p>
      {recent.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Activity className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No recent documents</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {recent.map(doc => <DocumentCard doc={doc} key={doc.id} />)}
        </div>
      )}
    </div>
  )
}

function SharedPanel() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <Send className="mb-3 size-8 text-(--ui-text-tertiary)" />
      <p className="text-sm font-medium">No shared documents</p>
      <p className="mt-1 text-xs text-(--ui-text-tertiary)">Share documents with other agents and workspaces</p>
    </div>
  )
}

function ArchivedPanel() {
  const archived = getArchivedDocuments()

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <p className="text-sm text-(--ui-text-tertiary)">{archived.length} archived</p>
      {archived.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Archive className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No archived documents</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {archived.map(doc => (
            <div className="rounded-lg border border-(--ui-stroke-tertiary) p-3 opacity-60 transition-colors hover:bg-(--chrome-action-hover)" key={doc.id}>
              <div className="flex items-center gap-3">
                <span className="inline-grid size-8 place-items-center rounded-md text-xs font-bold text-(--ui-text-tertiary) bg-(--ui-row-active-background)">{doc.fileType.toUpperCase()}</span>
                <div className="min-w-0 flex-1">
                  <span className="text-sm font-medium">{doc.name}</span>
                  <div className="flex gap-2 text-[0.55rem] text-(--ui-text-tertiary)">
                    <span>{formatBytes(doc.size)}</span>
                    <span>{doc.chunkCount} chunks</span>
                  </div>
                </div>
                <Button onClick={() => restoreDocument(doc.id)} size="xs" variant="ghost">Restore</Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function GraphPanel() {
  const state = useStore($knowledge)
  const hasData = state.graphNodes.length > 0 || state.documents.length > 0

  const handleGenerate = () => {
    for (const doc of state.documents.slice(0, 10)) {
      addGraphNode({ type: 'document', label: doc.name, color: FILE_TYPE_COLORS[doc.fileType] ?? '#6B7280', connections: [] })
    }

    for (const agent of ['Research Agent', 'Knowledge Agent', 'Code Agent']) {
      addGraphNode({ type: 'agent', label: agent, color: '#8B5CF6', connections: [] })
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-(--ui-text-tertiary)">{state.graphNodes.length} nodes</p>
        <Button onClick={handleGenerate} size="sm" variant="textStrong"><Layers3 className="size-3.5" /> Generate Graph</Button>
      </div>
      {!hasData ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Layers3 className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No knowledge graph</p>
          <p className="mt-1 text-xs text-(--ui-text-tertiary)">Generate a graph to visualize relationships between documents, agents, and projects</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {state.graphNodes.map(node => (
            <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 transition-colors hover:bg-(--chrome-action-hover)" key={node.id}>
              <span className="inline-grid size-7 shrink-0 place-items-center rounded text-[0.55rem] font-bold"
                style={{ backgroundColor: `color-mix(in srgb, ${node.color} 16%, transparent)`, color: node.color }}>
                {node.type[0].toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <span className="text-sm font-medium capitalize">{node.label}</span>
                <p className="text-[0.55rem] text-(--ui-text-tertiary)">{node.type}</p>
              </div>
              <span className="shrink-0 text-[0.55rem] text-(--ui-text-tertiary)">{node.connections.length} edges</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AnalyticsPanel() {
  const analytics = useStore($knowledge).analytics
  const [showSearches, setShowSearches] = useState(false)

  const cards: { key: keyof AnalyticsStats; label: string; icon: typeof NotebookTabs; format?: (v: any) => string }[] = [
    { key: 'totalDocuments', label: 'Documents', icon: FileText },
    { key: 'totalChunks', label: 'Chunks', icon: Layers3 },
    { key: 'totalBases', label: 'Bases', icon: Package },
    { key: 'totalStorage', label: 'Storage', icon: Archive, format: v => formatBytes(v) },
    { key: 'totalEmbeddings', label: 'Embeddings', icon: Zap },
    { key: 'searchCount', label: 'Searches', icon: Search },
    { key: 'memoryUsage', label: 'Memory', icon: Brain },
    { key: 'activeAgents', label: 'Agents', icon: Users }
  ]

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {cards.map(c => {
          const val = analytics[c.key]

          return (
          <div className="rounded-lg border border-(--ui-stroke-tertiary) px-3 py-3" key={c.key}>
            <div className="flex items-center justify-between">
              <c.icon className="size-4 text-(--ui-text-tertiary)" />
            </div>
            <p className="mt-1 text-xl font-semibold tracking-tight">
              {c.format ? c.format(val) : typeof val === 'number' ? val : 0}
            </p>
            <p className="text-xs text-(--ui-text-tertiary)">{c.label}</p>
          </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-(--ui-stroke-tertiary) p-3">
          <p className="mb-2 text-xs font-semibold">Documents by Type</p>
          {analytics.documentsByType.map(d => (
            <div className="flex items-center gap-2 py-1" key={d.type}>
              <span className="w-12 text-[0.6rem] text-(--ui-text-tertiary)">{d.type.toUpperCase()}</span>
              <div className="h-1.5 flex-1 rounded-full bg-(--ui-row-active-background)">
                <div className="h-1.5 rounded-full bg-primary" style={{ width: `${(d.count / Math.max(...analytics.documentsByType.map(x => x.count), 1)) * 100}%` }} />
              </div>
              <span className="w-6 text-right text-[0.55rem] text-(--ui-text-tertiary)">{d.count}</span>
            </div>
          ))}
          {analytics.documentsByType.length === 0 && <p className="py-2 text-center text-xs text-(--ui-text-tertiary)">No data</p>}
        </div>

        <div className="rounded-lg border border-(--ui-stroke-tertiary) p-3">
          <p className="mb-2 flex items-center justify-between text-xs font-semibold">
            <span>Recent Searches</span>
            <button className="text-(--ui-text-tertiary)" onClick={() => setShowSearches(!showSearches)} type="button">{showSearches ? 'Hide' : `Show (${analytics.recentSearches.length})`}</button>
          </p>
          {showSearches && analytics.recentSearches.map((s, i) => (
            <div className="flex items-center justify-between py-0.5 text-[0.6rem]" key={i}>
              <span className="truncate text-(--ui-text-secondary)">{s.query}</span>
              <span className="text-(--ui-text-tertiary)">{s.results} results</span>
            </div>
          ))}
          {analytics.recentSearches.length === 0 && <p className="py-2 text-center text-xs text-(--ui-text-tertiary)">No searches yet</p>}
        </div>
      </div>
    </div>
  )
}

function SyncPanel() {
  const state = useStore($knowledge)
  const jobs = state.syncJobs

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <p className="text-sm text-(--ui-text-tertiary)">{jobs.length} sync jobs</p>
      {jobs.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <RefreshCw className="mb-3 size-8 text-(--ui-text-tertiary)" />
          <p className="text-sm font-medium">No sync jobs</p>
          <p className="mt-1 text-xs text-(--ui-text-tertiary)">Sync jobs appear when you trigger a knowledge base sync</p>
        </div>
      )}
      <div className="space-y-1">
        {jobs.map(job => {
          const base = state.bases.find(b => b.id === job.baseId)

          return (
            <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5" key={job.id}>
              <StatusDot tone={job.status === 'success' ? 'good' : job.status === 'error' ? 'bad' : job.status === 'syncing' ? 'warn' : 'muted'} />
              <div className="min-w-0 flex-1">
                <span className="text-sm font-medium">{base?.name ?? 'Unknown Base'}</span>
                <p className="text-xs capitalize text-(--ui-text-tertiary)">{job.status}{job.progress > 0 && ` (${job.progress}%)`}</p>
                {job.error && <p className="text-xs text-destructive">{job.error}</p>}
              </div>
              <span className="text-xs text-(--ui-text-tertiary)">{job.lastRun ? formatTime(job.lastRun) : 'Never'}</span>
              {job.status === 'idle' && <Button onClick={() => triggerSync(job.baseId)} size="xs" variant="outline"><RefreshCw className="size-3" /></Button>}
            </div>
          )
        })}
      </div>

      <p className="pt-4 text-xs font-semibold text-(--ui-text-tertiary)">Available for sync:</p>
      <div className="space-y-1">
        {state.bases.filter(b => !jobs.some(j => j.baseId === b.id)).map(base => (
          <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5" key={base.id}>
            <StatusDot tone="muted" />
            <div className="min-w-0 flex-1">
              <span className="text-sm font-medium">{base.name}</span>
            </div>
            <Button onClick={() => triggerSync(base.id)} size="xs" variant="textStrong">Sync Now</Button>
          </div>
        ))}
      </div>
    </div>
  )
}

function SettingsPanel() {
  const state = useStore($knowledge)

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <section>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Lock className="size-4" /> Security</h3>
        <div className="space-y-1">
          {(['workspaceIsolation', 'encryption', 'permissionManagement', 'auditLogs'] as (keyof SecurityConfig)[]).map(key => (
            <ListRow action={<Switch checked={state.security[key]} onCheckedChange={c => updateSecurity({ [key]: c })} size="xs" />} description={securityDesc(key)}
              key={key} title={securityLabel(key)} />
          ))}
        </div>
      </section>

      <section>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Zap className="size-4" /> Processing</h3>
        <div className="space-y-1">
          {(['ocr', 'vision', 'speechToText', 'metadataExtraction', 'languageDetection', 'deduplication', 'chunking', 'embedding', 'indexing'] as (keyof ProcessingConfig)[]).map(key => (
            <ListRow action={<Switch checked={state.processing[key]} onCheckedChange={c => updateProcessing({ [key]: c })} size="xs" />} description={processingDesc(key)}
              key={key} title={processingLabel(key)} />
          ))}
        </div>
      </section>

      <section>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><NotebookTabs className="size-4" /> RAG Configuration</h3>
        <div className="space-y-1">
          {(['contextInjection', 'citation', 'sourceTracking', 'confidenceScore', 'multiDocumentRetrieval'] as (keyof RAGConfig)[]).map(key => (
            <ListRow action={<Switch checked={state.rag[key] as boolean} onCheckedChange={c => updateRAG({ [key]: c })} size="xs" />} description={ragDesc(key)}
              key={key} title={ragLabel(key)} />
          ))}
        </div>
        <div className="mt-3 grid grid-cols-2 gap-4 px-4">
          <div>
            <p className="text-xs text-(--ui-text-secondary)">Max Context Chunks</p>
            <select className={cn('mt-1 w-full', CREDENTIAL_CONTROL_CLASS)} onChange={e => updateRAG({ maxContextChunks: Number(e.target.value) })}
              value={state.rag.maxContextChunks}>
              {[5, 10, 15, 20, 30, 50].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div>
            <p className="text-xs text-(--ui-text-secondary)">Similarity Threshold</p>
            <select className={cn('mt-1 w-full', CREDENTIAL_CONTROL_CLASS)} onChange={e => updateRAG({ similarityThreshold: Number(e.target.value) })}
              value={state.rag.similarityThreshold}>
              {[0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>
      </section>
    </div>
  )
}

function securityLabel(key: keyof SecurityConfig): string {
  const labels: Record<keyof SecurityConfig, string> = { workspaceIsolation: 'Workspace Isolation', encryption: 'Encryption', permissionManagement: 'Permission Management', auditLogs: 'Audit Logs' }

  return labels[key]
}

function securityDesc(key: keyof SecurityConfig): string {
  const descs: Record<keyof SecurityConfig, string> = { workspaceIsolation: 'Isolate knowledge between workspaces', encryption: 'Encrypt all knowledge at rest', permissionManagement: 'Granular access control per document', auditLogs: 'Log all access and modifications' }

  return descs[key]
}

function processingLabel(key: keyof ProcessingConfig): string {
  const labels: Record<keyof ProcessingConfig, string> = { ocr: 'OCR', vision: 'Vision', speechToText: 'Speech to Text', metadataExtraction: 'Metadata Extraction', languageDetection: 'Language Detection', deduplication: 'Deduplication', chunking: 'Chunking', embedding: 'Embedding', indexing: 'Indexing' }

  return labels[key]
}

function processingDesc(key: keyof ProcessingConfig): string {
  const descs: Record<keyof ProcessingConfig, string> = { ocr: 'Extract text from images and scanned PDFs', vision: 'Analyze images with computer vision', speechToText: 'Transcribe audio content', metadataExtraction: 'Extract metadata from documents', languageDetection: 'Auto-detect document language', deduplication: 'Remove duplicate content', chunking: 'Split documents into processable chunks', embedding: 'Generate vector embeddings', indexing: 'Build search indexes' }

  return descs[key]
}

function ragLabel(key: keyof RAGConfig): string {
  const labels: Record<string, string> = { contextInjection: 'Context Injection', citation: 'Citation', sourceTracking: 'Source Tracking', confidenceScore: 'Confidence Score', multiDocumentRetrieval: 'Multi-Document Retrieval', maxContextChunks: 'Max Context Chunks', similarityThreshold: 'Similarity Threshold' }

  return labels[key] ?? key
}

function ragDesc(key: keyof RAGConfig): string {
  const descs: Record<string, string> = { contextInjection: 'Inject relevant context into prompts', citation: 'Include source citations in responses', sourceTracking: 'Track document sources for responses', confidenceScore: 'Show confidence scores with results', multiDocumentRetrieval: 'Retrieve from multiple documents simultaneously', maxContextChunks: '', similarityThreshold: '' }

  return descs[key] ?? ''
}
