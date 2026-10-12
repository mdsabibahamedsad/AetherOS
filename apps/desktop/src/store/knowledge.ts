import { atom } from 'nanostores'

export type KnowledgeSource =
  | 'local-folder' | 'git-repo' | 'github' | 'website' | 'rss'
  | 'notion' | 'google-drive' | 'dropbox' | 'onedrive' | 'sharepoint'
  | 's3' | 'webdav' | 'custom-api'

export type FileType =
  | 'pdf' | 'docx' | 'txt' | 'md' | 'csv' | 'excel' | 'ppt'
  | 'json' | 'yaml' | 'xml' | 'html' | 'epub' | 'code' | 'zip'
  | 'image' | 'audio' | 'video'

export type MemoryType =
  | 'working' | 'conversation' | 'project' | 'long-term'
  | 'agent' | 'shared' | 'pinned' | 'temporary'

export type SearchType = 'semantic' | 'hybrid' | 'keyword' | 'vector'

export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'skipped'

export type KnowledgeSection =
  | 'bases' | 'documents' | 'search' | 'memory'
  | 'collections' | 'tags' | 'favorites' | 'recent'
  | 'shared' | 'archived' | 'graph' | 'analytics'
  | 'sync' | 'settings'

export interface KnowledgeBase {
  id: string
  name: string
  description: string
  source: KnowledgeSource
  sourceUrl: string
  fileTypes: FileType[]
  documentCount: number
  chunkCount: number
  embeddingModel: string
  processingStatus: ProcessingStatus
  lastSync: string | null
  syncInterval: number
  autoSync: boolean
  createdAt: string
  updatedAt: string
  archived: boolean
  tags: string[]
  workspaceId: string
  size: number
  error: string | null
}

export interface KnowledgeDocument {
  id: string
  baseId: string
  name: string
  fileType: FileType
  size: number
  pageCount: number
  chunkCount: number
  status: ProcessingStatus
  progress: number
  error: string | null
  author: string | null
  language: string | null
  createdAt: string
  updatedAt: string
  sourceUrl: string
  checksum: string
  metadata: Record<string, string>
  tags: string[]
  collections: string[]
  favorite: boolean
  archived: boolean
  vectorized: boolean
  indexed: boolean
}

export interface DocumentChunk {
  id: string
  documentId: string
  baseId: string
  content: string
  index: number
  chunkSize: number
  tokens: number
  embedding: number[] | null
  metadata: Record<string, string>
  score: number | null
}

export interface MemoryEntry {
  id: string
  type: MemoryType
  content: string
  summary: string | null
  source: string
  agentId: string | null
  sessionId: string | null
  projectId: string | null
  tags: string[]
  pinned: boolean
  createdAt: string
  updatedAt: string
  accessCount: number
  lastAccessed: string | null
  relevanceScore: number
  ttl: number | null
}

export interface KnowledgeCollection {
  id: string
  name: string
  description: string
  documentCount: number
  color: string
  icon: string
  createdAt: string
  updatedAt: string
}

export interface KnowledgeTag {
  id: string
  name: string
  color: string
  documentCount: number
}

export interface SearchResult {
  id: string
  documentId: string
  baseId: string
  chunkIndex: number
  content: string
  score: number
  source: string
  documentName: string
  fileType: FileType
  highlights: { start: number; end: number }[]
  metadata: Record<string, string>
}

export interface KnowledgeGraphNode {
  id: string
  type: 'document' | 'agent' | 'project' | 'person' | 'task' | 'file'
  label: string
  color: string
  connections: string[]
}

export interface KnowledgeGraphEdge {
  source: string
  target: string
  relationship: string
  weight: number
}

export interface AnalyticsStats {
  totalDocuments: number
  totalChunks: number
  totalBases: number
  totalStorage: number
  totalEmbeddings: number
  searchCount: number
  memoryUsage: number
  knowledgeUsage: number
  activeAgents: number
  documentsByType: { type: FileType; count: number }[]
  documentsByStatus: { status: ProcessingStatus; count: number }[]
  recentSearches: { query: string; timestamp: string; results: number }[]
}

export interface SyncJob {
  id: string
  baseId: string
  status: 'idle' | 'syncing' | 'success' | 'error'
  progress: number
  lastRun: string | null
  error: string | null
}

export interface SecurityConfig {
  workspaceIsolation: boolean
  encryption: boolean
  permissionManagement: boolean
  auditLogs: boolean
}

export interface ProcessingConfig {
  ocr: boolean
  vision: boolean
  speechToText: boolean
  metadataExtraction: boolean
  languageDetection: boolean
  deduplication: boolean
  chunking: boolean
  embedding: boolean
  indexing: boolean
}

export interface RAGConfig {
  contextInjection: boolean
  citation: boolean
  sourceTracking: boolean
  confidenceScore: boolean
  multiDocumentRetrieval: boolean
  maxContextChunks: number
  similarityThreshold: number
}

export interface KnowledgeState {
  activeSection: KnowledgeSection
  searchQuery: string
  searchType: SearchType
  selectedBase: string | null
  selectedDocument: string | null
  selectedCollection: string | null
  selectedMemoryType: MemoryType | 'all'
  loading: boolean
  bases: KnowledgeBase[]
  documents: KnowledgeDocument[]
  chunks: DocumentChunk[]
  memory: MemoryEntry[]
  collections: KnowledgeCollection[]
  tags: KnowledgeTag[]
  searchResults: SearchResult[]
  graphNodes: KnowledgeGraphNode[]
  graphEdges: KnowledgeGraphEdge[]
  analytics: AnalyticsStats
  syncJobs: SyncJob[]
  security: SecurityConfig
  processing: ProcessingConfig
  rag: RAGConfig
  recentDocuments: string[]
  favoriteIds: string[]
  sharedIds: string[]
}

const DEFAULT_SECURITY: SecurityConfig = {
  workspaceIsolation: true,
  encryption: true,
  permissionManagement: false,
  auditLogs: false
}

const DEFAULT_PROCESSING: ProcessingConfig = {
  ocr: true,
  vision: false,
  speechToText: false,
  metadataExtraction: true,
  languageDetection: true,
  deduplication: true,
  chunking: true,
  embedding: true,
  indexing: true
}

const DEFAULT_RAG: RAGConfig = {
  contextInjection: true,
  citation: true,
  sourceTracking: true,
  confidenceScore: false,
  multiDocumentRetrieval: true,
  maxContextChunks: 10,
  similarityThreshold: 0.7
}

const DEFAULT_COLLECTIONS: KnowledgeCollection[] = [
  { id: 'col-general', name: 'General Knowledge', description: 'General purpose knowledge collection', documentCount: 0, color: '#3B82F6', icon: 'book', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'col-technical', name: 'Technical Docs', description: 'Technical documentation and references', documentCount: 0, color: '#10B981', icon: 'code', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'col-research', name: 'Research', description: 'Research papers and findings', documentCount: 0, color: '#8B5CF6', icon: 'search', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'col-projects', name: 'Projects', description: 'Project-related documents', documentCount: 0, color: '#F59E0B', icon: 'folder', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
]

const DEFAULT_TAGS: KnowledgeTag[] = [
  { id: 'tag-important', name: 'important', color: '#EF4444', documentCount: 0 },
  { id: 'tag-reference', name: 'reference', color: '#3B82F6', documentCount: 0 },
  { id: 'tag-archived', name: 'archived', color: '#6B7280', documentCount: 0 },
  { id: 'tag-draft', name: 'draft', color: '#F59E0B', documentCount: 0 },
  { id: 'tag-final', name: 'final', color: '#10B981', documentCount: 0 }
]

const DEFAULT_STATS: AnalyticsStats = {
  totalDocuments: 0,
  totalChunks: 0,
  totalBases: 0,
  totalStorage: 0,
  totalEmbeddings: 0,
  searchCount: 0,
  memoryUsage: 0,
  knowledgeUsage: 0,
  activeAgents: 0,
  documentsByType: [],
  documentsByStatus: [],
  recentSearches: []
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
const now = () => new Date().toISOString()

const initialState: KnowledgeState = {
  activeSection: 'bases',
  searchQuery: '',
  searchType: 'semantic',
  selectedBase: null,
  selectedDocument: null,
  selectedCollection: null,
  selectedMemoryType: 'all',
  loading: false,
  bases: [],
  documents: [],
  chunks: [],
  memory: [
    { id: 'mem-working', type: 'working', content: '', summary: 'Current session context', source: 'system', agentId: null, sessionId: null, projectId: null, tags: [], pinned: false, createdAt: now(), updatedAt: now(), accessCount: 0, lastAccessed: null, relevanceScore: 1, ttl: 3600000 },
    { id: 'mem-longterm-1', type: 'long-term', content: 'AetherOS is a personal AI agent platform', summary: 'System overview', source: 'system', agentId: null, sessionId: null, projectId: null, tags: ['reference'], pinned: true, createdAt: now(), updatedAt: now(), accessCount: 5, lastAccessed: now(), relevanceScore: 0.9, ttl: null }
  ],
  collections: DEFAULT_COLLECTIONS,
  tags: DEFAULT_TAGS,
  searchResults: [],
  graphNodes: [],
  graphEdges: [],
  analytics: DEFAULT_STATS,
  syncJobs: [],
  security: DEFAULT_SECURITY,
  processing: DEFAULT_PROCESSING,
  rag: DEFAULT_RAG,
  recentDocuments: [],
  favoriteIds: [],
  sharedIds: []
}

export const $knowledge = atom<KnowledgeState>(initialState)

const patch = (update: Partial<KnowledgeState>) => $knowledge.set({ ...$knowledge.get(), ...update })

export function setKnowledgeSection(section: KnowledgeSection) { patch({ activeSection: section }) }

export function setKnowledgeSearch(query: string) { patch({ searchQuery: query }) }

export function setSearchType(type: SearchType) { patch({ searchType: type }) }

export function setKnowledgeLoading(loading: boolean) { patch({ loading }) }

export function selectBase(id: string | null) { patch({ selectedBase: id }) }

export function selectDocument(id: string | null) { patch({ selectedDocument: id }) }

export function selectCollection(id: string | null) { patch({ selectedCollection: id }) }

export function selectMemoryType(type: MemoryType | 'all') { patch({ selectedMemoryType: type }) }

export function updateSecurity(update: Partial<SecurityConfig>) {
  patch({ security: { ...$knowledge.get().security, ...update } })
}

export function updateProcessing(update: Partial<ProcessingConfig>) {
  patch({ processing: { ...$knowledge.get().processing, ...update } })
}

export function updateRAG(update: Partial<RAGConfig>) {
  patch({ rag: { ...$knowledge.get().rag, ...update } })
}

export function addBase(base: Omit<KnowledgeBase, 'id' | 'createdAt' | 'updatedAt' | 'documentCount' | 'chunkCount'>) {
  const newBase: KnowledgeBase = {
    ...base, id: generateId(), createdAt: now(), updatedAt: now(),
    documentCount: 0, chunkCount: 0
  }

  patch({ bases: [...$knowledge.get().bases, newBase] })
  updateAnalytics({ totalBases: $knowledge.get().bases.length + 1 })
}

export function updateBase(id: string, update: Partial<KnowledgeBase>) {
  const bases = $knowledge.get().bases.map(b => b.id === id ? { ...b, ...update, updatedAt: now() } : b)
  patch({ bases })
}

export function removeBase(id: string) {
  const state = $knowledge.get()
  const docsToRemove = state.documents.filter(d => d.baseId === id)
  patch({
    bases: state.bases.filter(b => b.id !== id),
    documents: state.documents.filter(d => d.baseId !== id),
    chunks: state.chunks.filter(c => c.baseId !== id),
    recentDocuments: state.recentDocuments.filter(rid => !docsToRemove.some(d => d.id === rid)),
    favoriteIds: state.favoriteIds.filter(fid => !docsToRemove.some(d => d.id === fid))
  })
}

export function addDocument(doc: Omit<KnowledgeDocument, 'id' | 'createdAt' | 'updatedAt' | 'chunkCount' | 'progress'>) {
  const newDoc: KnowledgeDocument = {
    ...doc, id: generateId(), createdAt: now(), updatedAt: now(),
    chunkCount: 0, progress: 0
  }

  const docs = [...$knowledge.get().documents, newDoc]
  patch({
    documents: docs,
    recentDocuments: [newDoc.id, ...$knowledge.get().recentDocuments].slice(0, 50)
  })
  updateAnalytics({ totalDocuments: docs.length })
}

export function updateDocument(id: string, update: Partial<KnowledgeDocument>) {
  const documents = $knowledge.get().documents.map(d =>
    d.id === id ? { ...d, ...update, updatedAt: now() } : d
  )

  patch({ documents })
}

export function removeDocument(id: string) {
  const state = $knowledge.get()
  const removed = state.documents.find(d => d.id === id)

  if (!removed) {return}
  const baseId = removed.baseId
  patch({
    documents: state.documents.filter(d => d.id !== id),
    chunks: state.chunks.filter(c => c.documentId !== id),
    recentDocuments: state.recentDocuments.filter(rid => rid !== id),
    favoriteIds: state.favoriteIds.filter(fid => fid !== id)
  })
  updateBase(baseId, { documentCount: Math.max(0, (state.bases.find(b => b.id === baseId)?.documentCount ?? 1) - 1) })
  updateAnalytics({ totalDocuments: state.documents.length - 1 })
}

export function addChunk(chunk: Omit<DocumentChunk, 'id' | 'embedding'>) {
  const newChunk: DocumentChunk = { ...chunk, id: generateId(), embedding: null }
  const chunks = [...$knowledge.get().chunks, newChunk]
  patch({ chunks })
  const doc = $knowledge.get().documents.find(d => d.id === chunk.documentId)

  if (doc) {
    updateDocument(chunk.documentId, { chunkCount: doc.chunkCount + 1 })
  }
}

export function toggleFavorite(id: string) {
  const favs = $knowledge.get().favoriteIds
  const updated = favs.includes(id) ? favs.filter(f => f !== id) : [...favs, id]
  patch({ favoriteIds: updated })
}

export function toggleDocumentFavorite(id: string) {
  toggleFavorite(id)
  updateDocument(id, { favorite: !$knowledge.get().documents.find(d => d.id === id)?.favorite })
}

export function archiveDocument(id: string) {
  updateDocument(id, { archived: true })
}

export function restoreDocument(id: string) {
  updateDocument(id, { archived: false })
}

export function addMemory(entry: Omit<MemoryEntry, 'id' | 'createdAt' | 'updatedAt' | 'accessCount'>) {
  const newEntry: MemoryEntry = {
    ...entry, id: generateId(), createdAt: now(), updatedAt: now(), accessCount: 0
  }

  patch({ memory: [...$knowledge.get().memory, newEntry] })
  updateAnalytics({ memoryUsage: $knowledge.get().memory.length + 1 })
}

export function updateMemory(id: string, update: Partial<MemoryEntry>) {
  const memory = $knowledge.get().memory.map(m =>
    m.id === id ? { ...m, ...update, updatedAt: now(), accessCount: m.accessCount + 1, lastAccessed: now() } : m
  )

  patch({ memory })
}

export function removeMemory(id: string) {
  patch({ memory: $knowledge.get().memory.filter(m => m.id !== id) })
  updateAnalytics({ memoryUsage: $knowledge.get().memory.length - 1 })
}

export function pinMemory(id: string) {
  updateMemory(id, { pinned: true })
}

export function unpinMemory(id: string) {
  updateMemory(id, { pinned: false })
}

export function addCollection(coll: Omit<KnowledgeCollection, 'id' | 'createdAt' | 'updatedAt' | 'documentCount'>) {
  const newColl: KnowledgeCollection = {
    ...coll, id: generateId(), createdAt: now(), updatedAt: now(), documentCount: 0
  }

  patch({ collections: [...$knowledge.get().collections, newColl] })
}

export function updateCollection(id: string, update: Partial<KnowledgeCollection>) {
  const collections = $knowledge.get().collections.map(c =>
    c.id === id ? { ...c, ...update, updatedAt: now() } : c
  )

  patch({ collections })
}

export function removeCollection(id: string) {
  const docs = $knowledge.get().documents.map(d => ({
    ...d,
    collections: d.collections.filter(c => c !== id)
  }))

  patch({
    collections: $knowledge.get().collections.filter(c => c.id !== id),
    documents: docs
  })
}

export function addTag(tag: Omit<KnowledgeTag, 'id' | 'documentCount'>) {
  const newTag: KnowledgeTag = { ...tag, id: generateId(), documentCount: 0 }
  patch({ tags: [...$knowledge.get().tags, newTag] })
}

export function updateTag(id: string, update: Partial<KnowledgeTag>) {
  const tags = $knowledge.get().tags.map(t => t.id === id ? { ...t, ...update } : t)
  patch({ tags })
}

export function removeTag(id: string) {
  patch({ tags: $knowledge.get().tags.filter(t => t.id !== id) })
}

export function addDocumentsToCollection(documentIds: string[], collectionId: string) {
  const documents = $knowledge.get().documents.map(d =>
    documentIds.includes(d.id)
      ? { ...d, collections: [...new Set([...d.collections, collectionId])] }
      : d
  )

  const coll = $knowledge.get().collections.find(c => c.id === collectionId)

  if (coll) {
    const collections = $knowledge.get().collections.map(c =>
      c.id === collectionId ? { ...c, documentCount: c.documentCount + documentIds.length } : c
    )

    patch({ documents, collections })
  }
}

export function tagDocument(documentId: string, tagId: string) {
  const doc = $knowledge.get().documents.find(d => d.id === documentId)

  if (!doc || doc.tags.includes(tagId)) {return}
  updateDocument(documentId, { tags: [...doc.tags, tagId] })
  const tag = $knowledge.get().tags.find(t => t.id === tagId)

  if (tag) {updateTag(tagId, { documentCount: tag.documentCount + 1 })}
}

export function untagDocument(documentId: string, tagId: string) {
  const doc = $knowledge.get().documents.find(d => d.id === documentId)

  if (!doc) {return}
  updateDocument(documentId, { tags: doc.tags.filter(t => t !== tagId) })
  const tag = $knowledge.get().tags.find(t => t.id === tagId)

  if (tag) {updateTag(tagId, { documentCount: Math.max(0, tag.documentCount - 1) })}
}

export function addSyncJob(job: Omit<SyncJob, 'id'>) {
  const newJob: SyncJob = { ...job, id: generateId() }
  patch({ syncJobs: [...$knowledge.get().syncJobs, newJob] })
}

export function updateSyncJob(id: string, update: Partial<SyncJob>) {
  const syncJobs = $knowledge.get().syncJobs.map(j => j.id === id ? { ...j, ...update } : j)
  patch({ syncJobs })
}

export function triggerSync(baseId: string) {
  const existing = $knowledge.get().syncJobs.find(j => j.baseId === baseId)

  if (existing) {
    updateSyncJob(existing.id, { status: 'syncing', progress: 0, error: null })
  } else {
    addSyncJob({ baseId, status: 'syncing', progress: 0, lastRun: null, error: null })
  }
}

export function completeSync(baseId: string, success: boolean, error?: string) {
  const job = $knowledge.get().syncJobs.find(j => j.baseId === baseId)

  if (job) {
    updateSyncJob(job.id, {
      status: success ? 'success' : 'error',
      progress: success ? 100 : job.progress,
      lastRun: now(),
      error: error ?? null
    })
    updateBase(baseId, { lastSync: now(), processingStatus: success ? 'completed' : 'failed' })
  }
}

export function addSearchResult(query: string, results: SearchResult[]) {
  patch({ searchResults: results })
  const state = $knowledge.get()

  const recentSearches = [
    { query, timestamp: now(), results: results.length },
    ...state.analytics.recentSearches
  ].slice(0, 20)

  updateAnalytics({ searchCount: state.analytics.searchCount + 1, recentSearches })
}

export function addGraphNode(node: Omit<KnowledgeGraphNode, 'id'>) {
  const newNode: KnowledgeGraphNode = { ...node, id: generateId() }
  patch({ graphNodes: [...$knowledge.get().graphNodes, newNode] })
}

export function addGraphEdge(edge: KnowledgeGraphEdge) {
  patch({ graphEdges: [...$knowledge.get().graphEdges, edge] })
}

export function updateAnalytics(update: Partial<AnalyticsStats>) {
  const current = $knowledge.get().analytics
  patch({ analytics: { ...current, ...update } })
}

export function recalcAnalytics() {
  const state = $knowledge.get()
  const docs = state.documents
  const chunks = state.chunks
  const byType: { type: FileType; count: number }[] = []
  const typeMap = new Map<FileType, number>()

  for (const d of docs) { typeMap.set(d.fileType, (typeMap.get(d.fileType) ?? 0) + 1) }

  for (const [type, count] of typeMap) { byType.push({ type, count }) }
  const byStatus: { status: ProcessingStatus; count: number }[] = []
  const statusMap = new Map<ProcessingStatus, number>()

  for (const d of docs) { statusMap.set(d.status, (statusMap.get(d.status) ?? 0) + 1) }

  for (const [status, count] of statusMap) { byStatus.push({ status, count }) }

  patch({
    analytics: {
      ...state.analytics,
      totalDocuments: docs.length,
      totalChunks: chunks.length,
      totalBases: state.bases.length,
      totalStorage: docs.reduce((s, d) => s + d.size, 0),
      totalEmbeddings: chunks.filter(c => c.embedding).length,
      memoryUsage: state.memory.length,
      documentsByType: byType,
      documentsByStatus: byStatus
    }
  })
}

export function getFilteredMemory(): MemoryEntry[] {
  const state = $knowledge.get()
  let entries = state.memory

  if (state.selectedMemoryType !== 'all') {
    entries = entries.filter(e => e.type === state.selectedMemoryType)
  }

  const q = state.searchQuery.toLowerCase().trim()

  if (q) {
    entries = entries.filter(e =>
      e.content.toLowerCase().includes(q) ||
      (e.summary?.toLowerCase().includes(q)) ||
      e.tags.some(t => t.toLowerCase().includes(q))
    )
  }

  return entries.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
}

export function getFilteredBases(): KnowledgeBase[] {
  const state = $knowledge.get()
  let bases = state.bases
  const q = state.searchQuery.toLowerCase().trim()

  if (q) {
    bases = bases.filter(b =>
      b.name.toLowerCase().includes(q) ||
      b.description.toLowerCase().includes(q) ||
      b.tags.some(t => t.toLowerCase().includes(q))
    )
  }

  return bases
}

export function getFilteredDocuments(): KnowledgeDocument[] {
  const state = $knowledge.get()
  let docs = state.documents
  const q = state.searchQuery.toLowerCase().trim()

  if (q) {
    docs = docs.filter(d =>
      d.name.toLowerCase().includes(q) ||
      d.author?.toLowerCase().includes(q) ||
      d.tags.some(t => t.toLowerCase().includes(q))
    )
  }

  return docs
}

export function getFavoriteDocuments(): KnowledgeDocument[] {
  return $knowledge.get().documents.filter(d => d.favorite || $knowledge.get().favoriteIds.includes(d.id))
}

export function getRecentDocuments(): KnowledgeDocument[] {
  const state = $knowledge.get()

  return state.recentDocuments
    .map(id => state.documents.find(d => d.id === id))
    .filter((d): d is KnowledgeDocument => d !== undefined)
    .slice(0, 20)
}

export function getArchivedDocuments(): KnowledgeDocument[] {
  return $knowledge.get().documents.filter(d => d.archived)
}

export function getDocumentsByCollection(collectionId: string): KnowledgeDocument[] {
  return $knowledge.get().documents.filter(d => d.collections.includes(collectionId))
}

export function getBaseDocuments(baseId: string): KnowledgeDocument[] {
  return $knowledge.get().documents.filter(d => d.baseId === baseId)
}
