import { atom } from 'nanostores'

export type SyncStatus = 'idle' | 'syncing' | 'paused' | 'error'

export interface SyncScope {
  id: string
  name: string
  description: string
  enabled: boolean
}

export interface SyncEvent {
  id: string
  scope: string
  type: 'push' | 'pull' | 'conflict' | 'error'
  status: 'success' | 'failed' | 'pending'
  timestamp: string
  itemsCount: number
  errorMessage?: string
  deviceId?: string
}

export interface SyncConflict {
  id: string
  scope: string
  filePath: string
  localVersion: string
  remoteVersion: string
  localModifiedAt: string
  remoteModifiedAt: string
  status: 'unresolved' | 'resolved' | 'merged'
  resolution?: 'keep-local' | 'keep-remote' | 'merged'
  resolvedAt?: string
}

export interface SyncState {
  status: SyncStatus
  enabled: boolean
  scopes: SyncScope[]
  history: SyncEvent[]
  conflicts: SyncConflict[]
  lastSync: string | null
  progress: number
  online: boolean
  queueSize: number
  deviceCount: number
  errorMessage: string | null
}

const DEFAULT_SCOPES: SyncScope[] = [
  { id: 'messages', name: 'Messages', description: 'Synchronize conversation messages across devices', enabled: true },
  { id: 'sessions', name: 'Sessions', description: 'Sync active sessions and their state', enabled: true },
  { id: 'memory', name: 'Memory', description: 'Distribute agent memory across instances', enabled: true },
  { id: 'knowledge', name: 'Knowledge', description: 'Sync knowledge base entries and embeddings', enabled: true },
  { id: 'files', name: 'Files', description: 'Synchronize workspace files and attachments', enabled: true },
  { id: 'config', name: 'Configuration', description: 'Sync settings and preferences', enabled: true },
  { id: 'plugins', name: 'Plugins', description: 'Distribute plugin installations and state', enabled: true },
  { id: 'skills', name: 'Skills', description: 'Sync skill definitions and usage data', enabled: true },
  { id: 'cron', name: 'Scheduled Jobs', description: 'Distribute cron job definitions', enabled: false },
  { id: 'contacts', name: 'Contacts', description: 'Sync contact and address book', enabled: true },
  { id: 'bookmarks', name: 'Bookmarks', description: 'Sync bookmarks and saved items', enabled: true },
  { id: 'templates', name: 'Templates', description: 'Sync message and response templates', enabled: false },
  { id: 'agent-state', name: 'Agent State', description: 'Sync agent behavior and persona settings', enabled: true },
  { id: 'toolsets', name: 'Toolsets', description: 'Sync enabled toolsets configuration', enabled: true },
  { id: 'gateway', name: 'Gateway', description: 'Sync gateway platform configurations', enabled: false },
  { id: 'ui-state', name: 'UI State', description: 'Sync desktop layout and UI preferences', enabled: false },
]

const INITIAL_STATE: SyncState = {
  status: 'idle',
  enabled: true,
  scopes: DEFAULT_SCOPES,
  history: [],
  conflicts: [],
  lastSync: null,
  progress: 0,
  online: true,
  queueSize: 0,
  deviceCount: 1,
  errorMessage: null,
}

export const $syncStatus = atom<SyncStatus>('idle')
export const $syncEnabled = atom<boolean>(true)
export const $syncScopes = atom<SyncScope[]>(DEFAULT_SCOPES)
export const $syncHistory = atom<SyncEvent[]>([])
export const $syncConflicts = atom<SyncConflict[]>([])
export const $syncLastSync = atom<string | null>(null)
export const $syncProgress = atom<number>(0)
export const $syncOnline = atom<boolean>(true)
export const $syncQueueSize = atom<number>(0)
export const $deviceCount = atom<number>(1)
export const $syncError = atom<string | null>(null)

export function enableSync() {
  $syncEnabled.set(true)
}

export function disableSync() {
  $syncEnabled.set(false)

  if ($syncStatus.get() === 'syncing') {
    $syncStatus.set('idle')
  }
}

export function setSyncScope(scopeId: string, enabled: boolean) {
  const scopes = $syncScopes.get()
  $syncScopes.set(scopes.map(s => s.id === scopeId ? { ...s, enabled } : s))
}

export function startSync() {
  if (!$syncEnabled.get()) {return}
  $syncStatus.set('syncing')
}

export function pauseSync() {
  if ($syncStatus.get() === 'syncing') {
    $syncStatus.set('paused')
  }
}

export function resumeSync() {
  if ($syncStatus.get() === 'paused') {
    $syncStatus.set('syncing')
  }
}

export function completeSync(errorMessage?: string) {
  $syncStatus.set(errorMessage ? 'error' : 'idle')
  $syncLastSync.set(new Date().toISOString())
  $syncProgress.set(100)

  if (errorMessage) {
    $syncError.set(errorMessage)
  }
}

export function setSyncProgress(progress: number) {
  $syncProgress.set(Math.min(100, Math.max(0, progress)))
}

export function setSyncOnline(online: boolean) {
  $syncOnline.set(online)
}

export function setDeviceCount(count: number) {
  $deviceCount.set(count)
}

export function addSyncEvent(event: SyncEvent) {
  const history = $syncHistory.get()
  $syncHistory.set([event, ...history].slice(0, 500))
}

export function addSyncConflict(conflict: SyncConflict) {
  const conflicts = $syncConflicts.get()
  $syncConflicts.set([conflict, ...conflicts])
}

export function resolveConflict(conflictId: string, resolution: SyncConflict['resolution']) {
  const conflicts = $syncConflicts.get()
  $syncConflicts.set(conflicts.map(c =>
    c.id === conflictId
      ? { ...c, status: 'resolved' as const, resolution, resolvedAt: new Date().toISOString() }
      : c
  ))
}

export function clearSyncHistory() {
  $syncHistory.set([])
}

export function clearSyncError() {
  $syncError.set(null)
}

export function addToQueue(count: number) {
  $syncQueueSize.set($syncQueueSize.get() + count)
}

export function drainQueue(count: number) {
  const current = $syncQueueSize.get()
  $syncQueueSize.set(Math.max(0, current - count))
}

export function getEnabledScopes(): SyncScope[] {
  return $syncScopes.get().filter(s => s.enabled)
}

export function getScope(id: string): SyncScope | undefined {
  return $syncScopes.get().find(s => s.id === id)
}
