import { atom } from 'nanostores'

export interface SyncJobConfig {
  id: string
  name: string
  serviceId: string
  description: string
  intervalMs: number
  enabled: boolean
  lastRunAt: string | null
  lastStatus: 'success' | 'error' | 'cancelled' | null
  itemsSynced: number
  errorMessage: string | null
}

export interface SyncJobRun {
  id: string
  jobId: string
  startedAt: string
  completedAt: string | null
  status: 'running' | 'success' | 'error' | 'cancelled'
  itemsProcessed: number
  errorMessage: string | null
}

export interface ServiceSyncState {
  jobs: SyncJobConfig[]
  activeRuns: SyncJobRun[]
  history: SyncJobRun[]
  globalSyncEnabled: boolean
  autoSync: boolean
  syncIntervalMs: number
}

const DEFAULT_SYNC_JOBS: SyncJobConfig[] = [
  {
    id: 'sync-messaging-telegram',
    name: 'Telegram Message Sync',
    serviceId: 'telegram',
    description: 'Synchronize messages and sessions from Telegram',
    intervalMs: 300000,
    enabled: false,
    lastRunAt: null,
    lastStatus: null,
    itemsSynced: 0,
    errorMessage: null
  },
  {
    id: 'sync-messaging-discord',
    name: 'Discord Message Sync',
    serviceId: 'discord',
    description: 'Synchronize messages and sessions from Discord',
    intervalMs: 300000,
    enabled: false,
    lastRunAt: null,
    lastStatus: null,
    itemsSynced: 0,
    errorMessage: null
  },
  {
    id: 'sync-messaging-slack',
    name: 'Slack Message Sync',
    serviceId: 'slack',
    description: 'Synchronize messages from Slack workspace',
    intervalMs: 300000,
    enabled: false,
    lastRunAt: null,
    lastStatus: null,
    itemsSynced: 0,
    errorMessage: null
  },
  {
    id: 'sync-homeassistant',
    name: 'Home Assistant State Sync',
    serviceId: 'homeassistant',
    description: 'Synchronize device states and entities from Home Assistant',
    intervalMs: 60000,
    enabled: false,
    lastRunAt: null,
    lastStatus: null,
    itemsSynced: 0,
    errorMessage: null
  },
  {
    id: 'sync-webhook',
    name: 'Webhook Event Sync',
    serviceId: 'webhook',
    description: 'Process queued webhook events',
    intervalMs: 10000,
    enabled: false,
    lastRunAt: null,
    lastStatus: null,
    itemsSynced: 0,
    errorMessage: null
  }
]

const initialSyncState: ServiceSyncState = {
  jobs: DEFAULT_SYNC_JOBS,
  activeRuns: [],
  history: [],
  globalSyncEnabled: true,
  autoSync: true,
  syncIntervalMs: 300000
}

export const $serviceSync = atom<ServiceSyncState>(initialSyncState)

const patch = (update: Partial<ServiceSyncState>) =>
  $serviceSync.set({ ...$serviceSync.get(), ...update })

export function setGlobalSyncEnabled(enabled: boolean) { patch({ globalSyncEnabled: enabled }) }

export function setAutoSync(auto: boolean) { patch({ autoSync: auto }) }

export function setSyncInterval(ms: number) { patch({ syncIntervalMs: ms }) }

export function updateSyncJob(id: string, update: Partial<SyncJobConfig>) {
  const jobs = $serviceSync.get().jobs.map(j =>
    j.id === id ? { ...j, ...update } : j
  )

  patch({ jobs })
}

export function toggleSyncJob(id: string) {
  const job = $serviceSync.get().jobs.find(j => j.id === id)

  if (job) {updateSyncJob(id, { enabled: !job.enabled })}
}

export function startSyncRun(jobId: string): SyncJobRun {
  const run: SyncJobRun = {
    id: `run-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    jobId,
    startedAt: new Date().toISOString(),
    completedAt: null,
    status: 'running',
    itemsProcessed: 0,
    errorMessage: null
  }

  const state = $serviceSync.get()
  patch({ activeRuns: [...state.activeRuns, run] })
  updateSyncJob(jobId, {
    lastRunAt: run.startedAt,
    lastStatus: 'success',
    errorMessage: null
  })

  return run
}

export function completeSyncRun(runId: string, status: SyncJobRun['status'], itemsProcessed?: number, errorMessage?: string | null) {
  const state = $serviceSync.get()
  const run = state.activeRuns.find(r => r.id === runId)

  if (!run) {return}

  const completed: SyncJobRun = {
    ...run,
    completedAt: new Date().toISOString(),
    status,
    itemsProcessed: itemsProcessed ?? run.itemsProcessed,
    errorMessage: errorMessage ?? null
  }

  patch({
    activeRuns: state.activeRuns.filter(r => r.id !== runId),
    history: [completed, ...state.history].slice(0, 100)
  })
  updateSyncJob(run.jobId, {
    lastStatus: status === 'success' ? 'success' : 'error',
    itemsSynced: (state.jobs.find(j => j.id === run.jobId)?.itemsSynced ?? 0) + (itemsProcessed ?? 0),
    errorMessage: errorMessage ?? null
  })
}

export function triggerSyncNow(jobId: string) {
  const run = startSyncRun(jobId)
  setTimeout(() => {
    completeSyncRun(run.id, 'success', Math.floor(Math.random() * 50) + 1)
  }, 1500 + Math.random() * 2000)

  return run
}

export function getSyncJobsForService(serviceId: string): SyncJobConfig[] {
  return $serviceSync.get().jobs.filter(j => j.serviceId === serviceId)
}

export function getRecentHistory(limit = 20): SyncJobRun[] {
  return $serviceSync.get().history.slice(0, limit)
}
