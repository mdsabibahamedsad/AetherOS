import type { AgentType, ExecutionPlan, ExecutionPlanStep, Intent, IntentType } from '../types'

interface PlanningStrategy {
  steps: PlanningStepDef[]
}

interface PlanningStepDef {
  label: string
  agentType?: AgentType
  tools: string[]
  deps: number[] 
  parallelGroup?: string
}

const STRATEGIES: Record<IntentType, PlanningStrategy> = {
  code: {
    steps: [
      { label: 'Understanding code request', agentType: 'planning', tools: [], deps: [] },
      { label: 'Analyzing existing codebase', agentType: 'coding', tools: ['search_files', 'read_file'], deps: [0] },
      { label: 'Designing solution architecture', agentType: 'planning', tools: [], deps: [1] },
      { label: 'Writing implementation', agentType: 'coding', tools: ['write_file', 'patch'], deps: [2] },
      { label: 'Running tests', agentType: 'terminal', tools: ['terminal'], deps: [3] },
      { label: 'Validating output', agentType: 'coding', tools: ['read_file'], deps: [4] },
    ]
  },
  research: {
    steps: [
      { label: 'Understanding research goal', agentType: 'planning', tools: [], deps: [] },
      { label: 'Searching web sources', agentType: 'research', tools: ['web_search'], deps: [0] },
      { label: 'Reading source content', agentType: 'research', tools: ['web_extract'], deps: [1] },
      { label: 'Cross-referencing findings', agentType: 'research', tools: [], deps: [2] },
      { label: 'Synthesizing report', agentType: 'research', tools: [], deps: [3] },
    ]
  },
  deploy: {
    steps: [
      { label: 'Understanding deployment target', agentType: 'planning', tools: [], deps: [] },
      { label: 'Checking prerequisites', agentType: 'terminal', tools: ['terminal', 'read_file'], deps: [0] },
      { label: 'Running build process', agentType: 'terminal', tools: ['terminal'], deps: [1] },
      { label: 'Deploying to target', agentType: 'terminal', tools: ['terminal'], deps: [2] },
      { label: 'Verifying deployment', agentType: 'browser', tools: ['browser_navigate'], deps: [3] },
    ]
  },
  automate: {
    steps: [
      { label: 'Understanding automation need', agentType: 'planning', tools: [], deps: [] },
      { label: 'Designing automation rule', agentType: 'automation', tools: [], deps: [0] },
      { label: 'Creating automation', agentType: 'automation', tools: ['cronjob'], deps: [1] },
      { label: 'Testing automation', agentType: 'automation', tools: [], deps: [2] },
    ]
  },
  search: {
    steps: [
      { label: 'Understanding search intent', agentType: 'planning', tools: [], deps: [] },
      { label: 'Searching memory graph', agentType: 'memory', tools: ['memory_search'], deps: [0] },
      { label: 'Searching external sources', agentType: 'research', tools: ['web_search'], deps: [0], parallelGroup: 'search' },
      { label: 'Merging results', agentType: 'research', tools: [], deps: [1, 2] },
    ]
  },
  'file-operation': {
    steps: [
      { label: 'Understanding file operation', agentType: 'planning', tools: [], deps: [] },
      { label: 'Locating target files', agentType: 'file', tools: ['search_files'], deps: [0] },
      { label: 'Executing operation', agentType: 'file', tools: ['read_file', 'write_file', 'patch'], deps: [1] },
      { label: 'Verifying result', agentType: 'file', tools: ['read_file'], deps: [2] },
    ]
  },
  terminal: {
    steps: [
      { label: 'Understanding command intent', agentType: 'planning', tools: [], deps: [] },
      { label: 'Preparing execution context', agentType: 'terminal', tools: [], deps: [0] },
      { label: 'Executing command', agentType: 'terminal', tools: ['terminal'], deps: [1] },
      { label: 'Processing output', agentType: 'terminal', tools: [], deps: [2] },
    ]
  },
  browser: {
    steps: [
      { label: 'Understanding browsing goal', agentType: 'planning', tools: [], deps: [] },
      { label: 'Launching browser', agentType: 'browser', tools: ['browser_navigate'], deps: [0] },
      { label: 'Extracting content', agentType: 'browser', tools: ['browser_extract'], deps: [1] },
      { label: 'Processing results', agentType: 'research', tools: [], deps: [2] },
    ]
  },
  database: {
    steps: [
      { label: 'Understanding database request', agentType: 'planning', tools: [], deps: [] },
      { label: 'Analyzing schema', agentType: 'database', tools: ['terminal'], deps: [0] },
      { label: 'Executing query', agentType: 'database', tools: ['terminal'], deps: [1] },
      { label: 'Validating results', agentType: 'database', tools: [], deps: [2] },
    ]
  },
  'memory-query': {
    steps: [
      { label: 'Understanding memory query', agentType: 'planning', tools: [], deps: [] },
      { label: 'Querying memory graph', agentType: 'memory', tools: ['memory_search'], deps: [0] },
      { label: 'Retrieving related context', agentType: 'memory', tools: [], deps: [1] },
      { label: 'Presenting findings', agentType: 'memory', tools: [], deps: [2] },
    ]
  },
  system: {
    steps: [
      { label: 'Understanding system request', agentType: 'planning', tools: [], deps: [] },
      { label: 'Gathering system state', agentType: 'terminal', tools: ['terminal'], deps: [0] },
      { label: 'Analyzing results', agentType: 'planning', tools: [], deps: [1] },
      { label: 'Presenting report', agentType: 'planning', tools: [], deps: [2] },
    ]
  },
  chat: {
    steps: [
      { label: 'Understanding conversation', agentType: 'planning', tools: [], deps: [] },
      { label: 'Retrieving relevant context', agentType: 'memory', tools: ['memory_search'], deps: [0] },
      { label: 'Formulating response', agentType: 'planning', tools: [], deps: [1] },
    ]
  },
  unknown: {
    steps: [
      { label: 'Analyzing request', agentType: 'planning', tools: [], deps: [] },
      { label: 'Searching memory for context', agentType: 'memory', tools: ['memory_search'], deps: [0] },
      { label: 'Processing request', agentType: 'coding', tools: ['terminal', 'read_file'], deps: [1] },
    ]
  }
}

export function createExecutionPlan(intent: Intent): ExecutionPlan {
  const strategy = STRATEGIES[intent.type] ?? STRATEGIES.unknown
  const steps: ExecutionPlanStep[] = []

  for (let i = 0; i < strategy.steps.length; i++) {
    const def = strategy.steps[i]
    steps.push({
      id: `step-${i + 1}`,
      label: def.label,
      agentType: def.agentType,
      tools: def.tools,
      status: 'pending',
      progress: 0,
      dependencies: def.deps.map(d => steps[d]?.id).filter(Boolean),
      startTime: undefined,
      endTime: undefined,
    })
  }

  return {
    id: `plan-${Date.now()}`,
    intent,
    steps,
    status: 'pending',
    startTime: Date.now(),
  }
}

export function getPlanSummary(plan: ExecutionPlan): string {
  const completed = plan.steps.filter(s => s.status === 'completed').length
  const total = plan.steps.length

  const elapsed = plan.endTime
    ? ((plan.endTime - plan.startTime) / 1000).toFixed(1)
    : ((Date.now() - plan.startTime) / 1000).toFixed(1)

  return `Plan: ${completed}/${total} steps in ${elapsed}s`
}

export function getNextPendingSteps(plan: ExecutionPlan): ExecutionPlanStep[] {
  return plan.steps.filter(s => {
    if (s.status !== 'pending') {return false}

    return s.dependencies.every(depId => {
      const dep = plan.steps.find(s => s.id === depId)

      return dep?.status === 'completed'
    })
  })
}

export function hasParallelSteps(plan: ExecutionPlan): boolean {
  return getNextPendingSteps(plan).length > 1
}

export function estimateCompletion(plan: ExecutionPlan): number {
  const now = Date.now()
  const running = plan.steps.filter(s => s.status === 'running')
  const pending = plan.steps.filter(s => s.status === 'pending')

  if (running.length === 0 && pending.length === 0) {return 0}

  const elapsed = now - plan.startTime
  const completed = plan.steps.filter(s => s.status === 'completed').length
  const total = plan.steps.length

  if (completed === 0) {return 0}
  const rate = elapsed / completed

  return rate * (total - completed)
}
