import { atom } from 'nanostores'

export type AgentStatus = 'running' | 'stopped' | 'paused' | 'error' | 'created'
export type AgentTemplate = 'coding' | 'research' | 'writing' | 'automation' | 'data-analyst' | 'devops' | 'browser' | 'file-manager' | 'support' | 'assistant' | 'social-media' | 'email' | 'knowledge' | 'voice' | 'vision' | 'custom'
export type WorkflowType = 'sequential' | 'parallel' | 'coordinator'
export type TriggerType = 'manual' | 'schedule' | 'file-change' | 'webhook' | 'git-commit' | 'email' | 'startup' | 'shutdown'
export type ConditionType = 'if-else' | 'loop' | 'retry' | 'delay' | 'parallel' | 'condition'

export interface AgentConfig {
  id: string
  name: string
  description: string
  template: AgentTemplate
  avatar: string
  systemPrompt: string
  status: AgentStatus
  createdAt: string
  updatedAt: string
  lastRunAt: string | null
  runCount: number

  model: AgentModelConfig
  memory: AgentMemoryConfig
  permissions: AgentPermissions
  tools: AgentToolsConfig
  workspace: AgentWorkspaceConfig
}

export interface AgentModelConfig {
  provider: string
  model: string
  fallbackModel: string | null
  temperature: number
  maxTokens: number
  reasoningLevel: 'off' | 'low' | 'medium' | 'high'
}

export interface AgentMemoryConfig {
  workingMemory: boolean
  longTermMemory: boolean
  knowledgeBase: boolean
  conversationHistory: boolean
  projectMemory: boolean
}

export interface AgentPermissions {
  internetAccess: boolean
  filesystemAccess: boolean
  terminalAccess: boolean
  browserAccess: boolean
  pluginAccess: boolean
  sandbox: boolean
  executionLimit: number
  workspaceScope: string
}

export interface AgentToolsConfig {
  fileSystem: boolean
  browser: boolean
  git: boolean
  shell: boolean
  python: boolean
  search: boolean
  codeEditing: boolean
  mcpTools: boolean
  plugins: boolean
  customTools: string[]
}

export interface AgentWorkspaceConfig {
  path: string
  isolated: boolean
  maxStorageMb: number
}

export interface WorkflowAgent {
  agentId: string
  role: 'coordinator' | 'planner' | 'executor' | 'reviewer' | 'critic' | 'researcher' | 'coder' | 'manager'
  order: number
}

export interface WorkflowStep {
  id: string
  type: 'agent-task' | 'condition' | 'delay' | 'retry' | 'parallel' | 'notification'
  label: string
  config: Record<string, unknown>
}

export interface Workflow {
  id: string
  name: string
  description: string
  type: WorkflowType
  agents: WorkflowAgent[]
  steps: WorkflowStep[]
  enabled: boolean
  createdAt: string
  updatedAt: string
}

export interface AutomationRule {
  id: string
  name: string
  description: string
  trigger: TriggerType
  triggerConfig: Record<string, unknown>
  workflowId: string | null
  enabled: boolean
  createdAt: string
  lastTriggeredAt: string | null
}

export interface TaskRun {
  id: string
  agentId: string
  agentName: string
  status: 'running' | 'queued' | 'completed' | 'failed' | 'cancelled'
  startedAt: string
  completedAt: string | null
  duration: number | null
  inputTokens: number
  outputTokens: number
  costUsd: number
  error: string | null
  logs: TaskLogEntry[]
}

export interface TaskLogEntry {
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
}

export interface AgentHubState {
  agents: AgentConfig[]
  workflows: Workflow[]
  automations: AutomationRule[]
  tasks: TaskRun[]
  selectedAgentId: string | null
  selectedWorkflowId: string | null
  editingAgent: AgentConfig | null
  searchQuery: string
  filterStatus: AgentStatus | 'all'
  filterTemplate: AgentTemplate | 'all'
}

const TEMPLATE_DEFAULTS: Record<AgentTemplate, { description: string; systemPrompt: string; tools: Partial<AgentToolsConfig>; permissions: Partial<AgentPermissions> }> = {
  coding: {
    description: 'Write, review, and debug code across any language',
    systemPrompt: 'You are a coding agent. Write clean, efficient, well-tested code. Review for bugs and security issues. Debug systematically.',
    tools: { fileSystem: true, git: true, shell: true, codeEditing: true, search: true },
    permissions: { internetAccess: true, filesystemAccess: true, terminalAccess: true }
  },
  research: {
    description: 'Deep research across web sources with citation tracking',
    systemPrompt: 'You are a research agent. Gather information from multiple sources, verify facts, and provide cited summaries.',
    tools: { browser: true, search: true, fileSystem: true },
    permissions: { internetAccess: true }
  },
  writing: {
    description: 'Create and edit content with style and clarity',
    systemPrompt: 'You are a writing agent. Help users create, edit, and refine written content with attention to tone, clarity, and structure.',
    tools: { fileSystem: true, search: true },
    permissions: { internetAccess: true }
  },
  automation: {
    description: 'Automate repetitive tasks and workflows',
    systemPrompt: 'You are an automation agent. Design and execute automated workflows, monitor their health, and handle failures gracefully.',
    tools: { shell: true, fileSystem: true, python: true, plugins: true },
    permissions: { internetAccess: true, filesystemAccess: true, terminalAccess: true }
  },
  'data-analyst': {
    description: 'Analyze data, build charts, and derive insights',
    systemPrompt: 'You are a data analyst. Analyze datasets, create visualizations, and provide data-driven insights.',
    tools: { python: true, fileSystem: true, search: true },
    permissions: { internetAccess: true, filesystemAccess: true }
  },
  devops: {
    description: 'Manage infrastructure, deployments, and monitoring',
    systemPrompt: 'You are a DevOps agent. Manage infrastructure, orchestrate deployments, monitor systems, and respond to incidents.',
    tools: { shell: true, git: true, fileSystem: true, plugins: true },
    permissions: { internetAccess: true, filesystemAccess: true, terminalAccess: true }
  },
  browser: {
    description: 'Automate web browsing and data extraction',
    systemPrompt: 'You are a browser agent. Navigate websites, extract data, fill forms, and automate web tasks.',
    tools: { browser: true, fileSystem: true },
    permissions: { internetAccess: true }
  },
  'file-manager': {
    description: 'Organize, search, and manage files and directories',
    systemPrompt: 'You are a file management agent. Organize files, search directories, manage storage, and maintain file systems.',
    tools: { fileSystem: true, search: true },
    permissions: { filesystemAccess: true }
  },
  support: {
    description: 'Handle customer inquiries and support tickets',
    systemPrompt: 'You are a customer support agent. Handle inquiries professionally, escalate when needed, and maintain conversation history.',
    tools: { search: true, fileSystem: true },
    permissions: { internetAccess: true }
  },
  assistant: {
    description: 'General-purpose personal assistant for daily tasks',
    systemPrompt: 'You are a personal assistant. Help with scheduling, information lookup, task management, and general questions.',
    tools: { search: true, browser: true, fileSystem: true },
    permissions: { internetAccess: true }
  },
  'social-media': {
    description: 'Manage social media content and engagement',
    systemPrompt: 'You are a social media agent. Create content, schedule posts, monitor engagement, and manage multiple platforms.',
    tools: { browser: true, search: true, plugins: true },
    permissions: { internetAccess: true }
  },
  email: {
    description: 'Draft, organize, and manage email communications',
    systemPrompt: 'You are an email assistant. Draft responses, organize inbox, manage filters, and handle email workflows.',
    tools: { search: true, fileSystem: true },
    permissions: { internetAccess: true }
  },
  knowledge: {
    description: 'Build and maintain a searchable knowledge base',
    systemPrompt: 'You are a knowledge agent. Collect, organize, and surface information from your knowledge base and external sources.',
    tools: { search: true, fileSystem: true, browser: true },
    permissions: { internetAccess: true, filesystemAccess: true }
  },
  voice: {
    description: 'Process voice commands and audio input',
    systemPrompt: 'You are a voice agent. Process spoken commands, transcribe audio, and respond with natural speech.',
    tools: { search: true, fileSystem: true, plugins: true },
    permissions: { internetAccess: true }
  },
  vision: {
    description: 'Analyze images, screenshots, and visual data',
    systemPrompt: 'You are a vision agent. Analyze images, extract text from screenshots, describe visual content, and process visual data.',
    tools: { fileSystem: true, search: true, python: true },
    permissions: { internetAccess: true, filesystemAccess: true }
  },
  custom: {
    description: 'Fully customizable agent with your own configuration',
    systemPrompt: 'You are a custom agent configured for specific tasks. Follow the instructions provided in your configuration.',
    tools: { fileSystem: true, search: true, shell: true },
    permissions: { internetAccess: true, filesystemAccess: true }
  }
}

const TEMPLATE_LABELS: Record<AgentTemplate, string> = {
  coding: 'Coding Agent',
  research: 'Research Agent',
  writing: 'Writing Agent',
  automation: 'Automation Agent',
  'data-analyst': 'Data Analyst',
  devops: 'DevOps Agent',
  browser: 'Browser Agent',
  'file-manager': 'File Manager',
  support: 'Customer Support',
  assistant: 'Personal Assistant',
  'social-media': 'Social Media Manager',
  email: 'Email Assistant',
  knowledge: 'Knowledge Assistant',
  voice: 'Voice Assistant',
  vision: 'Vision Agent',
  custom: 'Custom Agent'
}

function createDefaultAgent(template: AgentTemplate): AgentConfig {
  const t = TEMPLATE_DEFAULTS[template]
  const now = new Date().toISOString()
  const id = `agent-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

  return {
    id,
    name: TEMPLATE_LABELS[template],
    description: t.description,
    template,
    avatar: template.charAt(0).toUpperCase(),
    systemPrompt: t.systemPrompt,
    status: 'created',
    createdAt: now,
    updatedAt: now,
    lastRunAt: null,
    runCount: 0,
    model: {
      provider: '',
      model: '',
      fallbackModel: null,
      temperature: 0.7,
      maxTokens: 4096,
      reasoningLevel: 'off'
    },
    memory: {
      workingMemory: true,
      longTermMemory: true,
      knowledgeBase: false,
      conversationHistory: true,
      projectMemory: false
    },
    permissions: {
      internetAccess: t.permissions.internetAccess ?? false,
      filesystemAccess: t.permissions.filesystemAccess ?? false,
      terminalAccess: t.permissions.terminalAccess ?? false,
      browserAccess: t.permissions.browserAccess ?? false,
      pluginAccess: false,
      sandbox: true,
      executionLimit: 100,
      workspaceScope: 'agent'
    },
    tools: {
      fileSystem: t.tools.fileSystem ?? false,
      browser: t.tools.browser ?? false,
      git: t.tools.git ?? false,
      shell: t.tools.shell ?? false,
      python: t.tools.python ?? false,
      search: t.tools.search ?? false,
      codeEditing: t.tools.codeEditing ?? false,
      mcpTools: false,
      plugins: t.tools.plugins ?? false,
      customTools: []
    },
    workspace: {
      path: '',
      isolated: true,
      maxStorageMb: 500
    }
  }
}

const INITIAL_AGENTS = [
  createDefaultAgent('coding'),
  createDefaultAgent('research'),
  createDefaultAgent('assistant')
].map((a, i) => ({ ...a, name: `${a.name} ${i + 1}`, status: 'stopped' as AgentStatus }))

export const $agentHub = atom<AgentHubState>({
  agents: INITIAL_AGENTS,
  workflows: [],
  automations: [],
  tasks: [],
  selectedAgentId: null,
  selectedWorkflowId: null,
  editingAgent: null,
  searchQuery: '',
  filterStatus: 'all',
  filterTemplate: 'all'
})

const patch = (update: Partial<AgentHubState>) =>
  $agentHub.set({ ...$agentHub.get(), ...update })

export function setSearchQuery(query: string) { patch({ searchQuery: query }) }

export function setFilterStatus(status: AgentStatus | 'all') { patch({ filterStatus: status }) }

export function setFilterTemplate(tpl: AgentTemplate | 'all') { patch({ filterTemplate: tpl }) }

export function selectAgent(id: string | null) { patch({ selectedAgentId: id }) }

export function selectWorkflow(id: string | null) { patch({ selectedWorkflowId: id }) }

export function createAgent(template: AgentTemplate) {
  const agent = createDefaultAgent(template)
  patch({ agents: [...$agentHub.get().agents, agent], selectedAgentId: agent.id })

  return agent
}

export function duplicateAgent(id: string) {
  const original = $agentHub.get().agents.find(a => a.id === id)

  if (!original) {return null}
  const now = new Date().toISOString()

  const copy: AgentConfig = {
    ...original,
    id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: `${original.name} (copy)`,
    status: 'created',
    createdAt: now,
    updatedAt: now,
    lastRunAt: null,
    runCount: 0
  }

  patch({ agents: [...$agentHub.get().agents, copy] })

  return copy
}

export function deleteAgent(id: string) {
  const state = $agentHub.get()
  patch({
    agents: state.agents.filter(a => a.id !== id),
    selectedAgentId: state.selectedAgentId === id ? null : state.selectedAgentId
  })
}

export function updateAgent(id: string, update: Partial<AgentConfig>) {
  const agents = $agentHub.get().agents.map(a =>
    a.id === id ? { ...a, ...update, updatedAt: new Date().toISOString() } : a
  )

  patch({ agents })
}

export function setAgentStatus(id: string, status: AgentStatus) {
  updateAgent(id, { status })
}

export function setEditingAgent(agent: AgentConfig | null) {
  patch({ editingAgent: agent })
}

export function saveAgentConfig(config: AgentConfig) {
  const agents = $agentHub.get().agents.map(a =>
    a.id === config.id ? { ...config, updatedAt: new Date().toISOString() } : a
  )

  patch({ agents, editingAgent: null })
}

const WORKFLOW_AGENTS: Array<{ role: WorkflowAgent['role']; label: string; description: string }> = [
  { role: 'coordinator', label: 'Coordinator', description: 'Orchestrates the overall workflow' },
  { role: 'planner', label: 'Planner', description: 'Creates execution plans' },
  { role: 'executor', label: 'Executor', description: 'Carries out tasks' },
  { role: 'reviewer', label: 'Reviewer', description: 'Reviews outputs for quality' },
  { role: 'critic', label: 'Critic', description: 'Provides critical feedback' },
  { role: 'researcher', label: 'Researcher', description: 'Gathers information' },
  { role: 'coder', label: 'Coder', description: 'Writes and edits code' },
  { role: 'manager', label: 'Manager', description: 'Manages sub-agent delegation' }
]

export function getWorkflowAgentRoles() { return WORKFLOW_AGENTS }

export function createWorkflow(name: string, type: WorkflowType) {
  const now = new Date().toISOString()

  const workflow: Workflow = {
    id: `workflow-${Date.now()}`,
    name,
    description: '',
    type,
    agents: [],
    steps: [],
    enabled: false,
    createdAt: now,
    updatedAt: now
  }

  patch({ workflows: [...$agentHub.get().workflows, workflow] })

  return workflow
}

export function updateWorkflow(id: string, update: Partial<Workflow>) {
  const workflows = $agentHub.get().workflows.map(w =>
    w.id === id ? { ...w, ...update, updatedAt: new Date().toISOString() } : w
  )

  patch({ workflows })
}

export function deleteWorkflow(id: string) {
  patch({ workflows: $agentHub.get().workflows.filter(w => w.id !== id) })
}

export function addWorkflowAgent(workflowId: string, role: WorkflowAgent['role'], agentId: string) {
  const workflow = $agentHub.get().workflows.find(w => w.id === workflowId)

  if (!workflow) {return}
  const entry: WorkflowAgent = { agentId, role, order: workflow.agents.length }
  updateWorkflow(workflowId, { agents: [...workflow.agents, entry] })
}

export function removeWorkflowAgent(workflowId: string, agentId: string) {
  const workflow = $agentHub.get().workflows.find(w => w.id === workflowId)

  if (!workflow) {return}
  updateWorkflow(workflowId, { agents: workflow.agents.filter(a => a.agentId !== agentId) })
}

export function createAutomation(name: string, trigger: TriggerType) {
  const now = new Date().toISOString()

  const rule: AutomationRule = {
    id: `auto-${Date.now()}`,
    name,
    description: '',
    trigger,
    triggerConfig: {},
    workflowId: null,
    enabled: false,
    createdAt: now,
    lastTriggeredAt: null
  }

  patch({ automations: [...$agentHub.get().automations, rule] })

  return rule
}

export function updateAutomation(id: string, update: Partial<AutomationRule>) {
  const automations = $agentHub.get().automations.map(a =>
    a.id === id ? { ...a, ...update } : a
  )

  patch({ automations })
}

export function deleteAutomation(id: string) {
  patch({ automations: $agentHub.get().automations.filter(a => a.id !== id) })
}

export function addTask(task: TaskRun) {
  patch({ tasks: [$agentHub.get().tasks, task].flat().slice(-100) })
}

export function updateTask(id: string, update: Partial<TaskRun>) {
  const tasks = $agentHub.get().tasks.map(t =>
    t.id === id ? { ...t, ...update } : t
  )

  patch({ tasks })
}

export function removeTask(id: string) {
  patch({ tasks: $agentHub.get().tasks.filter(t => t.id !== id) })
}

export { TEMPLATE_DEFAULTS, TEMPLATE_LABELS }
