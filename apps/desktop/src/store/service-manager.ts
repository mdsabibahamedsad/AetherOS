import { atom } from 'nanostores'

export interface ManagedService {
  id: string
  name: string
  description: string
  category: 'system' | 'messaging' | 'automation' | 'sync' | 'developer' | 'ai'
  status: 'running' | 'stopped' | 'error' | 'starting' | 'stopping'
  uptime?: number
  memory?: number
  cpu?: number
  autoRestart: boolean
  lastError?: string
  lastRestart?: number
  pid?: number
  version?: string
}

export interface ServiceLog {
  id: string
  serviceId: string
  timestamp: number
  level: 'debug' | 'info' | 'warn' | 'error'
  message: string
}

export interface ServiceManagerState {
  services: ManagedService[]
  logs: ServiceLog[]
  selectedServiceId: string | null
  selectedTab: 'dashboard' | 'services' | 'logs' | 'settings'
  logFilter: 'all' | 'debug' | 'info' | 'warn' | 'error'
  autoRefresh: boolean
}

const DEFAULT_SERVICES: ManagedService[] = [
  { id: 'gateway', name: 'Gateway', description: 'Messaging gateway for multi-platform communication', category: 'messaging', status: 'running', uptime: 86400, memory: 128, cpu: 2, autoRestart: true, version: '2.4.0' },
  { id: 'scheduler', name: 'Scheduler', description: 'Cron job scheduler and timer management', category: 'system', status: 'running', uptime: 86400, memory: 32, cpu: 1, autoRestart: true, version: '1.2.0' },
  { id: 'sync', name: 'Sync Engine', description: 'Cross-device and cloud synchronization', category: 'sync', status: 'running', uptime: 43200, memory: 64, cpu: 1, autoRestart: true, version: '1.1.0' },
  { id: 'automation', name: 'Automation Engine', description: 'Automation workflow execution engine', category: 'automation', status: 'running', uptime: 72000, memory: 96, cpu: 3, autoRestart: true, version: '2.0.0' },
  { id: 'plugin-host', name: 'Plugin Host', description: 'Plugin sandbox and extension runtime', category: 'developer', status: 'running', uptime: 86400, memory: 256, cpu: 5, autoRestart: true, version: '1.3.0' },
  { id: 'memory-db', name: 'Memory Database', description: 'Persistent memory and knowledge graph store', category: 'ai', status: 'running', uptime: 86400, memory: 192, cpu: 2, autoRestart: true, version: '3.1.0' },
  { id: 'curator', name: 'Curator', description: 'Background skill maintenance and archival', category: 'system', status: 'stopped', autoRestart: false, lastError: 'Disabled by config', version: '1.0.0' },
  { id: 'updater', name: 'Auto Updater', description: 'Background update check and installation', category: 'system', status: 'running', uptime: 86400, memory: 16, cpu: 0, autoRestart: true, version: '1.0.0' }
]

export const $serviceManager = atom<ServiceManagerState>({
  services: DEFAULT_SERVICES,
  logs: [],
  selectedServiceId: null,
  selectedTab: 'dashboard',
  logFilter: 'all',
  autoRefresh: true
})

const patch = (u: Partial<ServiceManagerState>) =>
  $serviceManager.set({ ...$serviceManager.get(), ...u })

export function setServiceManagerTab(tab: ServiceManagerState['selectedTab']) { patch({ selectedTab: tab }) }

export function setLogFilter(filter: ServiceManagerState['logFilter']) { patch({ logFilter: filter }) }

export function setAutoRefresh(v: boolean) { patch({ autoRefresh: v }) }

export function selectService(id: string | null) { patch({ selectedServiceId: id }) }

export function updateServiceStatus(id: string, status: ManagedService['status'], extras?: Partial<ManagedService>) {
  const services = $serviceManager.get().services.map(s =>
    s.id === id ? { ...s, ...extras, status } : s
  )

  patch({ services })
}

export function addServiceLog(log: ServiceLog) {
  patch({ logs: [...$serviceManager.get().logs.slice(-199), log] })
}

export function toggleServiceAutoRestart(id: string) {
  const services = $serviceManager.get().services.map(s =>
    s.id === id ? { ...s, autoRestart: !s.autoRestart } : s
  )

  patch({ services })
}
