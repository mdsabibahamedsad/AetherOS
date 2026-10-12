import {
  addJarvisAgent,
  type JarvisAgent,
  removeJarvisAgent,
  updateJarvisAgent
} from '@/store/jarvis-mode'

import type { AgentTask, AgentType, ExecutionPlanStep } from '../types'

// ─── Agent Registry ───────────────────────────────────────────────────────────

export interface AgentDefinition {
  type: AgentType
  label: string
  description: string
  icon: string
  capabilities: string[]
  preferredModels: string[]
  maxConcurrent: number
}

export const AGENT_DEFINITIONS: Record<AgentType, AgentDefinition> = {
  coding: {
    type: 'coding',
    label: 'Coding Agent',
    description: 'Writes, reviews, and debugs code',
    icon: 'code',
    capabilities: ['code-generation', 'code-review', 'debugging', 'refactoring'],
    preferredModels: ['claude-sonnet-4-20250514', 'gpt-4o', 'deepseek-coder'],
    maxConcurrent: 3
  },
  research: {
    type: 'research',
    label: 'Research Agent',
    description: 'Searches web, reads sources, synthesizes findings',
    icon: 'search',
    capabilities: ['web-search', 'source-reading', 'summarization', 'analysis'],
    preferredModels: ['gpt-4o', 'claude-sonnet-4-20250514', 'gemini-2.5-pro'],
    maxConcurrent: 2
  },
  browser: {
    type: 'browser',
    label: 'Browser Agent',
    description: 'Navigates websites, extracts content, interacts with pages',
    icon: 'globe',
    capabilities: ['navigation', 'extraction', 'interaction', 'screenshots'],
    preferredModels: ['gpt-4o', 'gemini-2.5-pro'],
    maxConcurrent: 1
  },
  file: {
    type: 'file',
    label: 'File Agent',
    description: 'Manages files and directories',
    icon: 'file-directory',
    capabilities: ['read', 'write', 'copy', 'move', 'delete', 'search'],
    preferredModels: ['claude-sonnet-4-20250514', 'gpt-4o-mini'],
    maxConcurrent: 5
  },
  memory: {
    type: 'memory',
    label: 'Memory Agent',
    description: 'Manages knowledge graph and semantic memory',
    icon: 'database',
    capabilities: ['memory-store', 'memory-retrieve', 'knowledge-graph', 'embedding'],
    preferredModels: ['text-embedding-3-small'],
    maxConcurrent: 2
  },
  automation: {
    type: 'automation',
    label: 'Automation Agent',
    description: 'Creates and manages scheduled tasks and workflows',
    icon: 'run-all',
    capabilities: ['cron', 'triggers', 'workflows', 'monitoring'],
    preferredModels: ['gpt-4o-mini', 'claude-sonnet-4-20250514'],
    maxConcurrent: 2
  },
  planning: {
    type: 'planning',
    label: 'Planning Agent',
    description: 'Decomposes complex tasks into actionable steps',
    icon: 'list-flat',
    capabilities: ['task-decomposition', 'scheduling', 'dependency-resolution'],
    preferredModels: ['o3', 'claude-sonnet-4-20250514', 'gpt-4o'],
    maxConcurrent: 1
  },
  communication: {
    type: 'communication',
    label: 'Communication Agent',
    description: 'Manages messaging platforms and notifications',
    icon: 'comment-discussion',
    capabilities: ['telegram', 'discord', 'slack', 'email', 'notifications'],
    preferredModels: ['gpt-4o-mini'],
    maxConcurrent: 3
  },
  data: {
    type: 'data',
    label: 'Data Agent',
    description: 'Processes, transforms, and analyzes data',
    icon: 'graph',
    capabilities: ['data-processing', 'analysis', 'visualization', 'etl'],
    preferredModels: ['gpt-4o', 'claude-sonnet-4-20250514'],
    maxConcurrent: 2
  },
  terminal: {
    type: 'terminal',
    label: 'Terminal Agent',
    description: 'Executes shell commands and manages processes',
    icon: 'terminal',
    capabilities: ['shell-exec', 'process-management', 'system-admin'],
    preferredModels: ['gpt-4o-mini', 'claude-sonnet-4-20250514'],
    maxConcurrent: 3
  },
  database: {
    type: 'database',
    label: 'Database Agent',
    description: 'Manages database operations and queries',
    icon: 'database',
    capabilities: ['sql', 'schema-management', 'migration', 'backup'],
    preferredModels: ['gpt-4o', 'claude-sonnet-4-20250514'],
    maxConcurrent: 2
  },
  vision: {
    type: 'vision',
    label: 'Vision Agent',
    description: 'Analyzes images, screenshots, and visual content',
    icon: 'eye',
    capabilities: ['image-analysis', 'ocr', 'screenshot-understanding'],
    preferredModels: ['gemini-2.5-pro', 'gpt-4o', 'claude-sonnet-4-20250514'],
    maxConcurrent: 2
  },
  voice: {
    type: 'voice',
    label: 'Voice Agent',
    description: 'Handles speech recognition and synthesis',
    icon: 'mic',
    capabilities: ['stt', 'tts', 'voice-cloning', 'noise-suppression'],
    preferredModels: ['whisper-large-v3', 'elevenlabs'],
    maxConcurrent: 1
  }
}

// ─── Agent Orchestrator ───────────────────────────────────────────────────────

const activeAgents = new Map<string, AgentTask>()
let agentCounter = 0

export function getAgentDefinition(type: AgentType): AgentDefinition {
  return AGENT_DEFINITIONS[type]
}

export function getActiveAgentCount(type: AgentType): number {
  let count = 0

  for (const task of activeAgents.values()) {
    if (task.agentType === type && task.status === 'running') {count++}
  }

  return count
}

export function canSpawnAgent(type: AgentType): boolean {
  const def = AGENT_DEFINITIONS[type]

  return getActiveAgentCount(type) < def.maxConcurrent
}

export function selectAgentForStep(step: ExecutionPlanStep): AgentType {
  if (step.agentType) {return step.agentType}

  const tools = step.tools

  if (tools.some(t => ['terminal', 'shell.exec'].includes(t))) {return 'terminal'}

  if (tools.some(t => ['browser_navigate', 'browser_click', 'browser_extract'].includes(t))) {return 'browser'}

  if (tools.some(t => ['read_file', 'write_file', 'search_files', 'patch'].includes(t))) {return 'file'}

  if (tools.some(t => ['web_search', 'web_extract'].includes(t))) {return 'research'}

  if (tools.some(t => ['memory_search', 'memory_store'].includes(t))) {return 'memory'}

  if (tools.some(t => ['cronjob'].includes(t))) {return 'automation'}

  return 'coding'
}

export function createAgentTask(
  planId: string,
  step: ExecutionPlanStep,
  prompt: string,
  model?: string
): AgentTask {
  const agentType = selectAgentForStep(step)
  const def = AGENT_DEFINITIONS[agentType]

  const task: AgentTask = {
    id: `agent-${++agentCounter}`,
    agentType,
    planId,
    stepId: step.id,
    prompt,
    model: model ?? def.preferredModels[0],
    status: 'running',
    progress: 0,
    startTime: Date.now(),
    logs: []
  }

  activeAgents.set(task.id, task)

  const jarvisAgent: JarvisAgent = {
    id: task.id,
    name: def.label,
    type: agentType,
    status: 'running',
    progress: 0,
    currentTask: step.label,
    startedAt: task.startTime
  }

  addJarvisAgent(jarvisAgent)

  return task
}

export function updateAgentProgress(taskId: string, progress: number, log?: string) {
  const task = activeAgents.get(taskId)

  if (!task) {return}

  task.progress = progress

  if (log) {task.logs.push(`[${new Date().toISOString()}] ${log}`)}

  updateJarvisAgent(taskId, {
    progress,
    currentTask: log ?? undefined
  })
}

export function completeAgentTask(taskId: string, result: string) {
  const task = activeAgents.get(taskId)

  if (!task) {return}

  task.status = 'completed'
  task.result = result
  task.endTime = Date.now()
  task.progress = 100

  updateJarvisAgent(taskId, {
    status: 'completed',
    progress: 100,
    currentTask: 'Completed'
  })

  setTimeout(() => removeJarvisAgent(taskId), 5000)
  activeAgents.delete(taskId)
}

export function failAgentTask(taskId: string, error: string) {
  const task = activeAgents.get(taskId)

  if (!task) {return}

  task.status = 'failed'
  task.error = error
  task.endTime = Date.now()

  updateJarvisAgent(taskId, {
    status: 'error',
    currentTask: error
  })

  setTimeout(() => removeJarvisAgent(taskId), 8000)
  activeAgents.delete(taskId)
}

export function cancelAgentTask(taskId: string) {
  const task = activeAgents.get(taskId)

  if (!task) {return}

  task.cancelToken?.abort()
  task.status = 'cancelled'
  task.endTime = Date.now()

  updateJarvisAgent(taskId, { status: 'idle' })
  setTimeout(() => removeJarvisAgent(taskId), 2000)
  activeAgents.delete(taskId)
}

export function getActiveAgents(): AgentTask[] {
  return Array.from(activeAgents.values())
}

export function getAgentTask(taskId: string): AgentTask | undefined {
  return activeAgents.get(taskId)
}
