import { getWorkspaceContext } from '../workspace/workspace-awareness'

export interface JarvisContext {
  currentProject: string | null
  currentFiles: string[]
  currentBranch: string | null
  currentProvider: string
  currentModel: string
  openChats: number
  recentActions: string[]
  runningTasks: string[]
  activeAgentCount: number
  mcpServerCount: number
  systemCpu: number
  systemMemory: number
  uptime: number
  lastActivity: number
  isIdle: boolean
  idleDuration: number
}

let context: JarvisContext = {
  currentProject: null,
  currentFiles: [],
  currentBranch: null,
  currentProvider: '',
  currentModel: '',
  openChats: 0,
  recentActions: [],
  runningTasks: [],
  activeAgentCount: 0,
  mcpServerCount: 0,
  systemCpu: 0,
  systemMemory: 0,
  uptime: 0,
  lastActivity: Date.now(),
  isIdle: false,
  idleDuration: 0
}

const actionLog: string[] = []
const MAX_ACTIONS = 50

export function getContext(): JarvisContext {
  const ws = getWorkspaceContext()

  return {
    ...context,
    currentBranch: ws.branch ?? null,
    currentFiles: ws.openFiles,
    currentProject: ws.gitRoot ? ws.gitRoot.split(/[/\\]/).pop() ?? null : null,
    idleDuration: context.isIdle ? Date.now() - context.lastActivity : 0
  }
}

export function updateContext(partial: Partial<JarvisContext>): void {
  context = { ...context, ...partial, lastActivity: Date.now(), isIdle: false }
}

export function logAction(action: string): void {
  actionLog.unshift(`${Date.now()}: ${action}`)

  if (actionLog.length > MAX_ACTIONS) {actionLog.pop()}
  context.recentActions = actionLog.slice(0, 10)
  context.lastActivity = Date.now()
  context.isIdle = false
}

export function markIdle(): void {
  context.isIdle = true
  context.lastActivity = Date.now()
}

export function resetContext(): void {
  context = { ...context, currentFiles: [], recentActions: [], runningTasks: [], idleDuration: 0, isIdle: false }
}
