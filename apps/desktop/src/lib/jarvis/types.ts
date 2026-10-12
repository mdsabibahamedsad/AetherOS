// ─── Core Types ───────────────────────────────────────────────────────────────

export type IntentType =
  | 'chat'
  | 'code'
  | 'research'
  | 'deploy'
  | 'automate'
  | 'search'
  | 'file-operation'
  | 'terminal'
  | 'browser'
  | 'database'
  | 'memory-query'
  | 'system'
  | 'unknown'

export type TaskStatus = 'pending' | 'planning' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'queued'
export type AgentType = 'coding' | 'research' | 'browser' | 'file' | 'memory' | 'automation' | 'planning' | 'communication' | 'data' | 'terminal' | 'database' | 'vision' | 'voice'
export type ModelCapability = 'coding' | 'reasoning' | 'vision' | 'fast' | 'search' | 'long-context' | 'offline'
export type PermissionScope = 'filesystem' | 'browser' | 'camera' | 'microphone' | 'terminal' | 'database' | 'network'

export interface Intent {
  type: IntentType
  confidence: number
  entities: Record<string, string>
  context: string[]
  requiresTools: string[]
}

export interface ExecutionPlanStep {
  id: string
  label: string
  agentType?: AgentType
  tools: string[]
  status: TaskStatus
  progress: number
  result?: string
  error?: string
  startTime?: number
  endTime?: number
  dependencies: string[]
}

export interface ExecutionPlan {
  id: string
  intent: Intent
  steps: ExecutionPlanStep[]
  status: TaskStatus
  startTime: number
  endTime?: number
  result?: string
}

export interface AgentTask {
  id: string
  agentType: AgentType
  planId: string
  stepId: string
  prompt: string
  model?: string
  provider?: string
  status: TaskStatus
  progress: number
  result?: string
  error?: string
  startTime: number
  endTime?: number
  sessionId?: string
  logs: string[]
  cancelToken?: AbortController
}

export interface BackgroundJob {
  id: string
  name: string
  type: 'ai-task' | 'automation' | 'monitoring' | 'scheduled'
  status: TaskStatus
  progress: number
  eta?: number
  result?: string
  error?: string
  startTime: number
  endTime?: number
  logs: JobLog[]
  cancelToken?: AbortController
  retryCount: number
  maxRetries: number
}

export interface JobLog {
  timestamp: number
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
}

export interface ModelRoute {
  capability: ModelCapability
  provider: string
  model: string
  priority: number
  available: boolean
}

export interface MemoryNode {
  id: string
  type: 'project' | 'preference' | 'codebase' | 'file' | 'person' | 'company' | 'task' | 'conversation' | 'knowledge'
  label: string
  content: string
  embedding?: number[]
  metadata: Record<string, unknown>
  relations: MemoryRelation[]
  createdAt: number
  updatedAt: number
}

export interface MemoryRelation {
  targetId: string
  type: 'related' | 'contains' | 'depends-on' | 'authored-by' | 'belongs-to'
  weight: number
}

export interface WorkspaceContext {
  cwd: string
  gitRoot?: string
  branch?: string
  openFiles: string[]
  projectType?: string
  framework?: string
  language?: string
  recentCommands: string[]
}

export interface SecurityPolicy {
  requireApproval: PermissionScope[]
  autoApprove: PermissionScope[]
  deniedActions: string[]
}

export interface JarvisConfig {
  jarvisMode: boolean
  animations: boolean
  voiceEnabled: boolean
  wakeWord: string
  transparency: number
  performanceMode: boolean
  gpuEffects: boolean
  developerMode: boolean
  autoModelSelection: boolean
  maxConcurrentAgents: number
  backgroundJobLimit: number
}
