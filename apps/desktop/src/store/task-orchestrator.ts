import { atom, computed } from 'nanostores'

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused' | 'blocked'
export type AgentRole = 'planner' | 'developer' | 'browser' | 'research' | 'writer' | 'qa' | 'deployment' | 'security' | 'memory' | 'coordinator' | 'creative' | 'data' | 'communication' | 'review' | 'coding' | 'file'
export type ExecutionMode = 'sequential' | 'parallel' | 'conditional' | 'dependent' | 'retry' | 'fallback' | 'human_approval'
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'
export type AgentActivityStatus = 'idle' | 'running' | 'thinking' | 'tool_called' | 'waiting' | 'completed' | 'failed' | 'retrying'

export interface OrchestrationTask {
  id: string
  name: string
  description: string
  agentRole: AgentRole
  model: string
  provider: string
  tools: string[]
  dependencies: string[]
  executionMode: ExecutionMode
  status: TaskStatus
  progress: number
  result: unknown
  error: string
  retryCount: number
  maxRetries: number
  requiresApproval: boolean
  estimatedDuration: number
  actualDuration: number
  cost: number
  createdAt: number
  startedAt: number
  completedAt: number
}

export interface OrchestrationPlan {
  id: string
  goal: string
  description: string
  subtasks: OrchestrationTask[]
  dependencies: Record<string, string[]>
  requiredTools: string[]
  requiredAgents: AgentRole[]
  requiredPermissions: string[]
  estimatedCost: number
  estimatedTime: number
  riskLevel: RiskLevel
  createdAt: number
  executionGraph: ExecutionGraph
}

export interface ExecutionGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
  levels: string[][]
}

export interface GraphNode {
  id: string
  name: string
  status: string
  role: string
  mode?: string
}

export interface GraphEdge {
  from: string
  to: string
}

export interface AgentAssignment {
  agentId: string
  role: AgentRole
  name: string
  model: string
  provider: string
  tools: string[]
  permissions: string[]
  parentId: string
  isSubAgent: boolean
}

export interface AgentActivity {
  agentId: string
  name: string
  role: string
  taskId: string
  status: AgentActivityStatus
  model: string
  provider: string
  tool: string
  message: string
  startedAt: number
  updatedAt: number
}

export interface Checkpoint {
  id: string
  planId: string
  taskId: string
  timestamp: number
  state: Record<string, unknown>
}

export interface ApprovalRequest {
  id: string
  taskId: string
  taskName: string
  agentName: string
  agentRole: string
  actions: string[]
  description: string
  details: Record<string, unknown>
  status: 'pending' | 'approved' | 'denied'
  createdAt: number
}

export interface ExecutionState {
  planId: string
  currentTaskId: string
  completedTasks: string[]
  pendingTasks: string[]
  failedTasks: string[]
  runningTasks: string[]
  paused: boolean
  cancelled: boolean
  startedAt: number
  updatedAt: number
}

interface OrchestratorState {
  plans: OrchestrationPlan[]
  currentPlanId: string | null
  executionStates: Record<string, ExecutionState>
  agentActivities: AgentActivity[]
  checkpoints: Checkpoint[]
  approvalRequests: ApprovalRequest[]
  activeAgents: number
  offlineMode: boolean
  limits: {
    maxSteps: number
    maxTime: number
    maxCost: number
    maxTokens: number
    maxSubAgents: number
    maxParallelTasks: number
    maxToolCalls: number
  }
}

export const $orchestrator = atom<OrchestratorState>({
  plans: [],
  currentPlanId: null,
  executionStates: {},
  agentActivities: [],
  checkpoints: [],
  approvalRequests: [],
  activeAgents: 0,
  offlineMode: false,
  limits: {
    maxSteps: 100,
    maxTime: 3600,
    maxCost: 10,
    maxTokens: 1000000,
    maxSubAgents: 10,
    maxParallelTasks: 5,
    maxToolCalls: 500
  }
})

export const $currentPlan = computed($orchestrator, state => {
  if (!state.currentPlanId) {return null}

  return state.plans.find(p => p.id === state.currentPlanId) ?? null
})

export const $currentExecutionState = computed($orchestrator, state => {
  if (!state.currentPlanId) {return null}

  return state.executionStates[state.currentPlanId] ?? null
})

export const $runningAgentActivities = computed($orchestrator, state =>
  state.agentActivities.filter(a => a.status === 'running' || a.status === 'thinking')
)

export const $pendingApprovals = computed($orchestrator, state =>
  state.approvalRequests.filter(a => a.status === 'pending')
)

export function createPlan(goal: string): OrchestrationPlan {
  const planId = generateId()
  const segments = goal.split(/[.?!\n]/).map(s => s.trim()).filter(s => s.length > 0).slice(0, 10)

  const plan: OrchestrationPlan = {
    id: planId,
    goal,
    description: goal,
    subtasks: segments.map((seg, i) => ({
      id: generateId(),
      name: seg.slice(0, 80),
      description: seg,
      agentRole: inferRole(seg),
      model: '',
      provider: '',
      tools: inferTools(seg),
      dependencies: i > 0 ? [planId + '-task-' + (i - 1)] : [],
      executionMode: 'sequential',
      status: 'pending',
      progress: 0,
      result: null,
      error: '',
      retryCount: 0,
      maxRetries: 3,
      requiresApproval: checkApproval(seg),
      estimatedDuration: estimateDuration(seg),
      actualDuration: 0,
      cost: 0,
      createdAt: Date.now(),
      startedAt: 0,
      completedAt: 0
    })),
    dependencies: {},
    requiredTools: [],
    requiredAgents: [],
    requiredPermissions: [],
    estimatedCost: segments.length * 0.01,
    estimatedTime: segments.reduce((sum, seg) => sum + estimateDuration(seg), 0),
    riskLevel: assessRisk(goal),
    createdAt: Date.now(),
    executionGraph: { nodes: [], edges: [], levels: [] }
  }

  plan.subtasks.forEach((t, i) => {
    plan.executionGraph.nodes.push({ id: t.id, name: t.name, status: t.status, role: t.agentRole })

    if (i > 0) {
      plan.executionGraph.edges.push({ from: plan.subtasks[i - 1].id, to: t.id })
    }
  })

  plan.executionGraph.levels = buildLevels(plan.subtasks)

  const state = $orchestrator.get()
  $orchestrator.set({ ...state, plans: [...state.plans, plan], currentPlanId: planId })

  return plan
}

export function setCurrentPlan(planId: string | null) {
  const state = $orchestrator.get()
  $orchestrator.set({ ...state, currentPlanId: planId })
}

export function updateTask(planId: string, taskId: string, updates: Partial<OrchestrationTask>) {
  const state = $orchestrator.get()

  const plans = state.plans.map(p => {
    if (p.id !== planId) {return p}

    return {
      ...p,
      subtasks: p.subtasks.map(t => t.id === taskId ? { ...t, ...updates } : t)
    }
  })

  $orchestrator.set({ ...state, plans })
}

export function updateExecutionState(planId: string, updates: Partial<ExecutionState>) {
  const state = $orchestrator.get()
  $orchestrator.set({
    ...state,
    executionStates: {
      ...state.executionStates,
      [planId]: { ...state.executionStates[planId] ?? createExecutionState(planId), ...updates }
    }
  })
}

export function addAgentActivity(activity: AgentActivity) {
  const state = $orchestrator.get()
  $orchestrator.set({
    ...state,
    agentActivities: [...state.agentActivities.slice(-200), activity],
    activeAgents: state.agentActivities.filter(a => a.status === 'running' || a.status === 'thinking').length + 1
  })
}

export function updateAgentActivity(agentId: string, updates: Partial<AgentActivity>) {
  const state = $orchestrator.get()
  $orchestrator.set({
    ...state,
    agentActivities: state.agentActivities.map(a =>
      a.agentId === agentId ? { ...a, ...updates, updatedAt: Date.now() } : a
    )
  })
}

export function addCheckpoint(checkpoint: Checkpoint) {
  const state = $orchestrator.get()
  $orchestrator.set({ ...state, checkpoints: [...state.checkpoints, checkpoint] })
}

export function addApprovalRequest(request: ApprovalRequest) {
  const state = $orchestrator.get()
  $orchestrator.set({ ...state, approvalRequests: [...state.approvalRequests, request] })
}

export function respondApproval(requestId: string, response: 'approved' | 'denied') {
  const state = $orchestrator.get()
  $orchestrator.set({
    ...state,
    approvalRequests: state.approvalRequests.map(r =>
      r.id === requestId ? { ...r, status: response } : r
    )
  })
}

export function setOfflineMode(offline: boolean) {
  const state = $orchestrator.get()
  $orchestrator.set({ ...state, offlineMode: offline })
}

export function setLimits(limits: Partial<OrchestratorState['limits']>) {
  const state = $orchestrator.get()
  $orchestrator.set({ ...state, limits: { ...state.limits, ...limits } })
}

export function removePlan(planId: string) {
  const state = $orchestrator.get()
  $orchestrator.set({
    ...state,
    plans: state.plans.filter(p => p.id !== planId),
    currentPlanId: state.currentPlanId === planId ? null : state.currentPlanId,
    executionStates: Object.fromEntries(
      Object.entries(state.executionStates).filter(([k]) => k !== planId)
    )
  })
}

function createExecutionState(planId: string): ExecutionState {
  return {
    planId,
    currentTaskId: '',
    completedTasks: [],
    pendingTasks: [],
    failedTasks: [],
    runningTasks: [],
    paused: false,
    cancelled: false,
    startedAt: Date.now(),
    updatedAt: Date.now()
  }
}

function inferRole(text: string): AgentRole {
  const lower = text.toLowerCase()

  if (/research|search|investigate|find|gather/i.test(lower)) {return 'research'}

  if (/code|develop|program|implement|build/i.test(lower)) {return 'developer'}

  if (/write|draft|compose|author|document/i.test(lower)) {return 'writer'}

  if (/browse|navigate|scrape|web/i.test(lower)) {return 'browser'}

  if (/test|verify|validate|qa/i.test(lower)) {return 'qa'}

  if (/deploy|release|publish/i.test(lower)) {return 'deployment'}

  if (/security|audit|threat/i.test(lower)) {return 'security'}

  if (/creative|design|art|generate|imagine/i.test(lower)) {return 'creative'}

  if (/data|analyze|statistic|dashboard|report/i.test(lower)) {return 'data'}

  if (/email|message|communicate|notify|send/i.test(lower)) {return 'communication'}

  if (/review|check|proofread|examine|inspect/i.test(lower)) {return 'review'}

  if (/file|save|open|read/i.test(lower)) {return 'file'}

  if (/plan|organize|coordinate/i.test(lower)) {return 'planner'}

  return 'coordinator'
}

function inferTools(text: string): string[] {
  const tools: string[] = []
  const lower = text.toLowerCase()

  if (/search|research|web|find/i.test(lower)) {tools.push('web_search')}

  if (/browse|navigate|web page/i.test(lower)) {tools.push('browser_navigate')}

  if (/file|save|read|write/i.test(lower)) {tools.push('file_operations')}

  if (/terminal|command|run|shell/i.test(lower)) {tools.push('terminal')}

  if (/code|develop|program/i.test(lower)) {tools.push('code_execution')}

  if (/email|send/i.test(lower)) {tools.push('send_message')}

  if (/image|picture|vision/i.test(lower)) {tools.push('vision')}

  if (/data|analyze|chart/i.test(lower)) {tools.push('data_analysis')}

  return tools
}

function checkApproval(text: string): boolean {
  const lower = text.toLowerCase()

  return /delete|remove|destroy|payment|spend|buy|install|modify system|access sensitive/i.test(lower)
}

function estimateDuration(text: string): number {
  const lower = text.toLowerCase()

  if (/research|investigate/i.test(lower)) {return 120}

  if (/code|develop|implement|build/i.test(lower)) {return 300}

  if (/browse|scrape/i.test(lower)) {return 60}

  if (/analyze|data|report/i.test(lower)) {return 180}

  if (/write|draft|compose/i.test(lower)) {return 120}

  return 60
}

function assessRisk(text: string): RiskLevel {
  const lower = text.toLowerCase()
  const count = [/delete/, /destroy/, /payment/, /install/, /permission/].filter(r => r.test(lower)).length

  if (count >= 2) {return 'high'}

  if (count >= 1) {return 'medium'}

  return 'low'
}

function buildLevels(tasks: OrchestrationTask[]): string[][] {
  const levels: string[][] = []
  const remaining = new Set(tasks.map(t => t.id))
  const completed = new Set<string>()

  while (remaining.size > 0) {
    const level: string[] = []

    for (const tid of remaining) {
      const task = tasks.find(t => t.id === tid)

      if (task && task.dependencies.every(d => completed.has(d))) {
        level.push(tid)
      }
    }

    if (level.length === 0) {
      level.push(...remaining)
    }

    levels.push(level)

    for (const tid of level) {
      remaining.delete(tid)
      completed.add(tid)
    }
  }

  return levels
}

function generateId(): string {
  return 'task_' + Math.random().toString(36).slice(2, 10)
}
