export type BackgroundTaskStatus = 'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
export type BackgroundTaskType = 'download' | 'indexing' | 'training' | 'searching' | 'mcp' | 'browser' | 'research' | 'automation' | 'code' | 'analysis' | 'processing'

export interface BackgroundTask {
  id: string
  name: string
  type: BackgroundTaskType
  status: BackgroundTaskStatus
  progress: number
  description: string
  result?: unknown
  error?: string
  createdAt: number
  startedAt?: number
  completedAt?: number
  estimatedDuration?: number
  retryCount: number
  maxRetries: number
  logs: string[]
}

const tasks = new Map<string, BackgroundTask>()
let counter = 0
const MAX_CONCURRENT = 5

function nextId(): string {
  return `bg_${++counter}_${Date.now().toString(36)}`
}

function addLog(task: BackgroundTask, message: string): void {
  task.logs.push(`[${new Date().toISOString().slice(11, 19)}] ${message}`)

  if (task.logs.length > 100) {task.logs.shift()}
}

export function createTask(name: string, type: BackgroundTaskType, description: string, opts?: {
  estimatedDuration?: number
  maxRetries?: number
}): BackgroundTask {
  const task: BackgroundTask = {
    id: nextId(),
    name,
    type,
    status: 'queued',
    progress: 0,
    description,
    createdAt: Date.now(),
    retryCount: 0,
    maxRetries: opts?.maxRetries ?? 3,
    logs: [],
    estimatedDuration: opts?.estimatedDuration
  }

  tasks.set(task.id, task)
  addLog(task, 'Task created')
  tryStartNext()

  return task
}

function tryStartNext(): void {
  const running = Array.from(tasks.values()).filter(t => t.status === 'running').length

  if (running >= MAX_CONCURRENT) {return}

  const next = Array.from(tasks.values()).find(t => t.status === 'queued')

  if (!next) {return}

  next.status = 'running'
  next.startedAt = Date.now()
  addLog(next, 'Task started')
}

export function updateProgress(taskId: string, progress: number, log?: string): void {
  const task = tasks.get(taskId)

  if (!task) {return}
  task.progress = Math.min(progress, 100)

  if (log) {addLog(task, log)}
}

export function completeTask(taskId: string, result?: unknown): void {
  const task = tasks.get(taskId)

  if (!task) {return}
  task.status = 'completed'
  task.progress = 100
  task.completedAt = Date.now()
  task.result = result
  addLog(task, 'Task completed')
  tryStartNext()
}

export function failTask(taskId: string, error: string): void {
  const task = tasks.get(taskId)

  if (!task) {return}
  task.status = 'failed'
  task.error = error
  task.completedAt = Date.now()
  addLog(task, `Task failed: ${error}`)
  tryStartNext()
}

export function pauseTask(taskId: string): void {
  const task = tasks.get(taskId)

  if (!task || task.status !== 'running') {return}
  task.status = 'paused'
  addLog(task, 'Task paused')
  tryStartNext()
}

export function resumeTask(taskId: string): void {
  const task = tasks.get(taskId)

  if (!task || task.status !== 'paused') {return}
  task.status = 'running'
  task.startedAt = Date.now()
  addLog(task, 'Task resumed')
}

export function cancelTask(taskId: string): void {
  const task = tasks.get(taskId)

  if (!task) {return}
  task.status = 'cancelled'
  task.completedAt = Date.now()
  addLog(task, 'Task cancelled')
  tryStartNext()
}

export function retryTask(taskId: string): void {
  const task = tasks.get(taskId)

  if (!task || (task.status !== 'failed' && task.status !== 'cancelled')) {return}

  if (task.retryCount >= task.maxRetries) {
    addLog(task, 'Max retries reached')

    return
  }

  task.status = 'queued'
  task.retryCount++
  task.error = undefined
  task.progress = 0
  task.completedAt = undefined
  addLog(task, `Retry #${task.retryCount}`)
  tryStartNext()
}

export function getTask(taskId: string): BackgroundTask | undefined {
  return tasks.get(taskId)
}

export function getAllTasks(): BackgroundTask[] {
  return Array.from(tasks.values())
}

export function getRunningTasks(): BackgroundTask[] {
  return Array.from(tasks.values()).filter(t => t.status === 'running')
}

export function getQueuedTasks(): BackgroundTask[] {
  return Array.from(tasks.values()).filter(t => t.status === 'queued')
}

export function getTaskStats(): { total: number; running: number; queued: number; completed: number; failed: number; paused: number } {
  const all = Array.from(tasks.values())

  return {
    total: all.length,
    running: all.filter(t => t.status === 'running').length,
    queued: all.filter(t => t.status === 'queued').length,
    completed: all.filter(t => t.status === 'completed').length,
    failed: all.filter(t => t.status === 'failed').length,
    paused: all.filter(t => t.status === 'paused').length
  }
}
