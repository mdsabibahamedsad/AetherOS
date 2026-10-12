import type { TaskNode, TaskStatus } from './planner'

export type ExecutorCapability =
  | 'mcp'
  | 'agent'
  | 'skill'
  | 'python'
  | 'browser'
  | 'gateway'
  | 'desktop'
  | 'terminal'
  | 'filesystem'
  | 'search'
  | 'memory'
  | 'code'
  | 'research'

export interface ExecutorTask {
  id: string
  capability: ExecutorCapability
  action: string
  params: Record<string, unknown>
  status: TaskStatus
  progress: number
  result?: unknown
  error?: string
  startedAt?: number
}

const activeTasks = new Map<string, ExecutorTask>()

const CAPABILITY_AVAILABILITY: Record<ExecutorCapability, boolean> = {
  mcp: false, agent: true, skill: true, python: false,
  browser: false, gateway: false, desktop: false, terminal: false,
  filesystem: true, search: true, memory: true, code: true, research: true
}

let taskCounter = 0

function nextId(): string {
  return `exec_${++taskCounter}_${Date.now().toString(36)}`
}

export async function executeTask(capability: ExecutorCapability, action: string, params: Record<string, unknown> = {}): Promise<ExecutorTask> {
  const task: ExecutorTask = {
    id: nextId(),
    capability,
    action,
    params,
    status: 'running',
    progress: 0,
    startedAt: Date.now()
  }

  activeTasks.set(task.id, task)

  return task
}

export function updateTask(id: string, update: Partial<ExecutorTask>): void {
  const task = activeTasks.get(id)

  if (!task) {return}
  Object.assign(task, update)
  task.startedAt = task.startedAt ?? Date.now()
}

export function completeTask(id: string, result?: unknown): void {
  const task = activeTasks.get(id)

  if (!task) {return}
  task.status = 'completed'
  task.progress = 100
  task.result = result
}

export function failTask(id: string, error: string): void {
  const task = activeTasks.get(id)

  if (!task) {return}
  task.status = 'failed'
  task.error = error
}

export function getTask(id: string): ExecutorTask | undefined {
  return activeTasks.get(id)
}

export function getActiveTasks(): ExecutorTask[] {
  return Array.from(activeTasks.values()).filter(t => t.status === 'running')
}

export function getAllTasks(): ExecutorTask[] {
  return Array.from(activeTasks.values())
}

export function cancelTask(id: string): void {
  const task = activeTasks.get(id)

  if (!task) {return}
  task.status = 'cancelled'
}

export function isCapabilityAvailable(cap: ExecutorCapability): boolean {
  return CAPABILITY_AVAILABILITY[cap] ?? false
}

export function setCapabilityAvailable(cap: ExecutorCapability, available: boolean): void {
  CAPABILITY_AVAILABILITY[cap] = available
}

export function getCapabilityAvailability(): Record<ExecutorCapability, boolean> {
  return { ...CAPABILITY_AVAILABILITY }
}

export async function resolveNodeToTasks(node: TaskNode): Promise<ExecutorTask[]> {
  const tasks: ExecutorTask[] = []

  if (node.agentType) {
    const t = await executeTask('agent', `Spawn ${node.agentType} agent`, { agentType: node.agentType, label: node.label, description: node.description })
    tasks.push(t)
  }

  if (node.label.toLowerCase().includes('search') || node.label.toLowerCase().includes('research')) {
    const t = await executeTask('research', node.label, { query: node.description })
    tasks.push(t)
  }

  if (node.label.toLowerCase().includes('code') || node.label.toLowerCase().includes('implement') || node.label.toLowerCase().includes('test')) {
    const t = await executeTask('code', node.label, { description: node.description })
    tasks.push(t)
  }

  if (node.label.toLowerCase().includes('deploy') || node.label.toLowerCase().includes('build')) {
    const t = await executeTask('skill', node.label, { description: node.description })
    tasks.push(t)
  }

  if (tasks.length === 0) {
    const t = await executeTask('search', node.label, { description: node.description })
    tasks.push(t)
  }

  return tasks
}
