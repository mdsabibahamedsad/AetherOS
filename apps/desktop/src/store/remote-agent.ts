import { atom } from 'nanostores'

export type RemoteInstanceStatus = 'online' | 'offline' | 'connecting' | 'error'
export type AgentStatus = 'running' | 'stopped' | 'paused' | 'starting' | 'stopping' | 'error'

export interface RemoteInstance {
  id: string
  name: string
  host: string
  port: number
  status: RemoteInstanceStatus
  version: string
  lastConnected: string | null
  latency: number | null
  healthCheck: HealthCheckResult | null
  errorMessage: string | null
}

export interface HealthCheckResult {
  passed: boolean
  timestamp: string
  responseTime: number
  details: string | null
}

export interface RemoteAgentStatus {
  status: AgentStatus
  cpu: number
  memory: number
  uptime: number
  startedAt: string | null
  errorMessage: string | null
}

export interface RemoteLogEntry {
  id: string
  timestamp: string
  level: 'debug' | 'info' | 'warn' | 'error'
  source: string
  message: string
}

export interface RemoteTask {
  id: string
  name: string
  status: 'running' | 'completed' | 'failed' | 'queued'
  progress: number
  startedAt: string | null
  completedAt: string | null
  errorMessage: string | null
}

export interface RemoteAgentState {
  instances: RemoteInstance[]
  activeInstanceId: string | null
  agentStatus: RemoteAgentStatus
  logs: RemoteLogEntry[]
  tasks: RemoteTask[]
  connected: boolean
  loading: boolean
  logLevelFilter: string
}

const INITIAL_AGENT_STATUS: RemoteAgentStatus = {
  status: 'stopped',
  cpu: 0,
  memory: 0,
  uptime: 0,
  startedAt: null,
  errorMessage: null,
}

export const $remoteInstances = atom<RemoteInstance[]>([])
export const $activeInstanceId = atom<string | null>(null)
export const $remoteAgentStatus = atom<RemoteAgentStatus>(INITIAL_AGENT_STATUS)
export const $remoteLogs = atom<RemoteLogEntry[]>([])
export const $remoteTasks = atom<RemoteTask[]>([])
export const $remoteConnected = atom<boolean>(false)
export const $remoteLoading = atom<boolean>(false)
export const $remoteLogLevelFilter = atom<string>('all')

export function getActiveInstance(): RemoteInstance | null {
  const id = $activeInstanceId.get()

  if (!id) {return null}

  return $remoteInstances.get().find(i => i.id === id) ?? null
}

export function addRemoteInstance(instance: RemoteInstance) {
  const instances = $remoteInstances.get()

  if (instances.some(i => i.id === instance.id)) {return}
  $remoteInstances.set([...instances, instance])
}

export function removeRemoteInstance(id: string) {
  const current = $activeInstanceId.get()

  if (current === id) {
    $activeInstanceId.set(null)
    $remoteConnected.set(false)
  }

  $remoteInstances.set($remoteInstances.get().filter(i => i.id !== id))
}

export function updateInstanceStatus(id: string, status: RemoteInstanceStatus, errorMessage?: string) {
  $remoteInstances.set($remoteInstances.get().map(i =>
    i.id === id ? { ...i, status, errorMessage: errorMessage ?? null } : i
  ))
}

export function updateInstanceLatency(id: string, latency: number) {
  $remoteInstances.set($remoteInstances.get().map(i =>
    i.id === id ? { ...i, latency } : i
  ))
}

export function updateInstanceHealth(id: string, health: HealthCheckResult) {
  $remoteInstances.set($remoteInstances.get().map(i =>
    i.id === id ? { ...i, healthCheck: health } : i
  ))
}

export function setActiveInstance(id: string | null) {
  $activeInstanceId.set(id)
}

export async function connect(id: string) {
  setActiveInstance(id)
  updateInstanceStatus(id, 'connecting')
  $remoteConnected.set(true)
  updateInstanceStatus(id, 'online')
}

export async function disconnect() {
  const id = $activeInstanceId.get()

  if (id) {
    updateInstanceStatus(id, 'offline')
  }

  $remoteConnected.set(false)
  $activeInstanceId.set(null)
  $remoteAgentStatus.set(INITIAL_AGENT_STATUS)
  $remoteLogs.set([])
  $remoteTasks.set([])
}

export async function reconnect(id: string) {
  await disconnect()
  await connect(id)
}

export function startAgent() {
  const current = $remoteAgentStatus.get()
  $remoteAgentStatus.set({ ...current, status: 'starting' })
  $remoteAgentStatus.set({ ...current, status: 'running', startedAt: new Date().toISOString(), errorMessage: null })
}

export function stopAgent() {
  const current = $remoteAgentStatus.get()
  $remoteAgentStatus.set({ ...current, status: 'stopping' })
  $remoteAgentStatus.set({ ...current, status: 'stopped', startedAt: null, uptime: 0 })
}

export function pauseAgent() {
  const current = $remoteAgentStatus.get()

  if (current.status === 'running') {
    $remoteAgentStatus.set({ ...current, status: 'paused' })
  }
}

export function resumeAgent() {
  const current = $remoteAgentStatus.get()

  if (current.status === 'paused') {
    $remoteAgentStatus.set({ ...current, status: 'running' })
  }
}

export function restartAgent() {
  stopAgent()
  setTimeout(() => startAgent(), 500)
}

export function updateAgentMetrics(cpu: number, memory: number, uptime: number) {
  const current = $remoteAgentStatus.get()
  $remoteAgentStatus.set({ ...current, cpu, memory, uptime })
}

export function setAgentError(message: string) {
  const current = $remoteAgentStatus.get()
  $remoteAgentStatus.set({ ...current, status: 'error', errorMessage: message })
}

export function refreshLogs() {
  $remoteLoading.set(true)
  $remoteLoading.set(false)
}

export function addLogEntry(entry: RemoteLogEntry) {
  const logs = $remoteLogs.get()
  $remoteLogs.set([entry, ...logs].slice(0, 1000))
}

export function clearLogs() {
  $remoteLogs.set([])
}

export function setLogLevelFilter(level: string) {
  $remoteLogLevelFilter.set(level)
}

export function getFilteredLogs(): RemoteLogEntry[] {
  const level = $remoteLogLevelFilter.get()

  if (level === 'all') {return $remoteLogs.get()}

  return $remoteLogs.get().filter(l => l.level === level)
}

export function refreshTasks() {
  $remoteLoading.set(true)
  $remoteLoading.set(false)
}

export function addTask(task: RemoteTask) {
  const tasks = $remoteTasks.get()
  $remoteTasks.set([...tasks, task])
}

export function updateTaskStatus(id: string, status: RemoteTask['status'], errorMessage?: string) {
  $remoteTasks.set($remoteTasks.get().map(t =>
    t.id === id ? { ...t, status, errorMessage: errorMessage ?? null, completedAt: status === 'completed' || status === 'failed' ? new Date().toISOString() : t.completedAt } : t
  ))
}

export function updateTaskProgress(id: string, progress: number) {
  $remoteTasks.set($remoteTasks.get().map(t =>
    t.id === id ? { ...t, progress } : t
  ))
}

export function removeTask(id: string) {
  $remoteTasks.set($remoteTasks.get().filter(t => t.id !== id))
}
