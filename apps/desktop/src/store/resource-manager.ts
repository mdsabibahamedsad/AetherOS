import { atom } from 'nanostores'

export interface ResourceMetric {
  id: string
  label: string
  value: number
  unit: string
  max: number
  history: number[]
  thresholds: { warning: number; critical: number }
}

export interface ProcessInfo {
  id: string
  name: string
  pid: number
  cpu: number
  memory: number
  status: 'running' | 'sleeping' | 'stopped'
}

export interface DiskUsage {
  mount: string
  total: number
  used: number
  percent: number
}

export interface NetworkTraffic {
  rx: number
  tx: number
  connections: number
}

export interface ResourceManagerState {
  metrics: ResourceMetric[]
  processes: ProcessInfo[]
  disks: DiskUsage[]
  network: NetworkTraffic | null
  alertHistory: Array<{ id: string; metric: string; message: string; timestamp: number; severity: 'info' | 'warning' | 'critical' }>
  monitoringActive: boolean
  selectedTab: 'overview' | 'processes' | 'disks' | 'network'
}

export const $resourceManager = atom<ResourceManagerState>({
  metrics: [
    { id: 'cpu', label: 'CPU', value: 0, unit: '%', max: 100, history: [], thresholds: { warning: 70, critical: 90 } },
    { id: 'memory', label: 'Memory', value: 0, unit: '%', max: 100, history: [], thresholds: { warning: 75, critical: 90 } },
    { id: 'gpu', label: 'GPU', value: 0, unit: '%', max: 100, history: [], thresholds: { warning: 80, critical: 95 } },
    { id: 'disk', label: 'Disk', value: 0, unit: '%', max: 100, history: [], thresholds: { warning: 80, critical: 95 } }
  ],
  processes: [],
  disks: [],
  network: null,
  alertHistory: [],
  monitoringActive: false,
  selectedTab: 'overview'
})

const patch = (update: Partial<ResourceManagerState>) =>
  $resourceManager.set({ ...$resourceManager.get(), ...update })

export function updateMetric(id: string, value: number) {
  const metrics = $resourceManager.get().metrics.map(m => {
    if (m.id !== id) {return m}
    const history = [...m.history.slice(-59), value]

    return { ...m, value, history }
  })

  patch({ metrics })
}

export function setProcesses(processes: ProcessInfo[]) { patch({ processes }) }

export function setDisks(disks: DiskUsage[]) { patch({ disks }) }

export function setNetwork(network: NetworkTraffic) { patch({ network }) }

export function setMonitoringActive(active: boolean) { patch({ monitoringActive: active }) }

export function setResourceTab(tab: ResourceManagerState['selectedTab']) { patch({ selectedTab: tab }) }

export function addAlert(alert: ResourceManagerState['alertHistory'][number]) {
  patch({ alertHistory: [...$resourceManager.get().alertHistory.slice(-49), alert] })
}

export function clearAlerts() {
  patch({ alertHistory: [] })
}
