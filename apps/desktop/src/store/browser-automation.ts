import { atom } from 'nanostores'

export type WorkflowNodeType =
  | 'open_url' | 'search' | 'click' | 'type' | 'select' | 'scroll'
  | 'wait' | 'extract' | 'screenshot' | 'navigate' | 'condition'
  | 'loop' | 'variable' | 'download' | 'upload' | 'webhook'
  | 'send_email' | 'send_notification' | 'save_file' | 'filter'

export interface WorkflowNode {
  id: string
  type: WorkflowNodeType
  label: string
  config: Record<string, unknown>
  position: { x: number; y: number }
  connections: string[]
}

export interface BrowserWorkflow {
  id: string
  name: string
  description: string
  nodes: WorkflowNode[]
  schedule: string
  status: 'draft' | 'active' | 'paused' | 'archived'
  createdAt: string
  updatedAt: string
  tags: string[]
}

export interface WorkflowExecution {
  id: string
  workflowId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  currentNodeId: string
  results: Record<string, unknown>
  errors: string[]
  startedAt: string
  completedAt: string
}

export interface BrowserAutomationState {
  workflows: BrowserWorkflow[]
  activeWorkflowId: string
  executions: WorkflowExecution[]
  builderOpen: boolean
  selectedNodeId: string
  editingNode: boolean
}

export const $browserAutomation = atom<BrowserAutomationState>({
  workflows: [],
  activeWorkflowId: '',
  executions: [],
  builderOpen: false,
  selectedNodeId: '',
  editingNode: false,
})

export function createWorkflow(name: string, description = ''): string {
  const state = $browserAutomation.get()
  const id = `wf_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

  const workflow: BrowserWorkflow = {
    id,
    name,
    description,
    nodes: [],
    schedule: '',
    status: 'draft',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    tags: [],
  }

  $browserAutomation.set({ ...state, workflows: [...state.workflows, workflow], activeWorkflowId: id })

  return id
}

export function updateWorkflow(id: string, updates: Partial<BrowserWorkflow>) {
  const state = $browserAutomation.get()

  const workflows = state.workflows.map(w =>
    w.id === id ? { ...w, ...updates, updatedAt: new Date().toISOString() } : w
  )

  $browserAutomation.set({ ...state, workflows })
}

export function deleteWorkflow(id: string) {
  const state = $browserAutomation.get()
  const workflows = state.workflows.filter(w => w.id !== id)
  const activeWorkflowId = state.activeWorkflowId === id ? (workflows[0]?.id ?? '') : state.activeWorkflowId
  $browserAutomation.set({ ...state, workflows, activeWorkflowId })
}

export function setActiveWorkflow(id: string) {
  const state = $browserAutomation.get()
  $browserAutomation.set({ ...state, activeWorkflowId: id })
}

export function setBuilderOpen(open: boolean) {
  const state = $browserAutomation.get()
  $browserAutomation.set({ ...state, builderOpen: open })
}

export function setSelectedNode(nodeId: string) {
  const state = $browserAutomation.get()
  $browserAutomation.set({ ...state, selectedNodeId: nodeId })
}

export function setEditingNode(editing: boolean) {
  const state = $browserAutomation.get()
  $browserAutomation.set({ ...state, editingNode: editing })
}

export function addNodeToWorkflow(workflowId: string, type: WorkflowNodeType, label = ''): string | null {
  const state = $browserAutomation.get()
  const wf = state.workflows.find(w => w.id === workflowId)

  if (!wf) {return null}
  const id = `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

  const node: WorkflowNode = {
    id,
    type,
    label: label || type.replace(/_/g, ' '),
    config: {},
    position: { x: 100 + wf.nodes.length * 30, y: 100 + wf.nodes.length * 80 },
    connections: [],
  }

  const workflows = state.workflows.map(w =>
    w.id === workflowId ? { ...w, nodes: [...w.nodes, node], updatedAt: new Date().toISOString() } : w
  )

  $browserAutomation.set({ ...state, workflows, selectedNodeId: id })

  return id
}

export function removeNodeFromWorkflow(workflowId: string, nodeId: string) {
  const state = $browserAutomation.get()

  const workflows = state.workflows.map(w => {
    if (w.id !== workflowId) {return w}

    const nodes = w.nodes.filter(n => n.id !== nodeId).map(n => ({
      ...n,
      connections: n.connections.filter(c => c !== nodeId),
    }))

    return { ...w, nodes, updatedAt: new Date().toISOString() }
  })

  const selectedNodeId = state.selectedNodeId === nodeId ? '' : state.selectedNodeId
  $browserAutomation.set({ ...state, workflows, selectedNodeId })
}

export function connectNodes(workflowId: string, fromNodeId: string, toNodeId: string) {
  const state = $browserAutomation.get()

  const workflows = state.workflows.map(w => {
    if (w.id !== workflowId) {return w}

    const nodes = w.nodes.map(n =>
      n.id === fromNodeId && !n.connections.includes(toNodeId)
        ? { ...n, connections: [...n.connections, toNodeId] }
        : n
    )

    return { ...w, nodes, updatedAt: new Date().toISOString() }
  })

  $browserAutomation.set({ ...state, workflows })
}

export function updateNodeConfig(workflowId: string, nodeId: string, config: Record<string, unknown>) {
  const state = $browserAutomation.get()

  const workflows = state.workflows.map(w => {
    if (w.id !== workflowId) {return w}

    const nodes = w.nodes.map(n =>
      n.id === nodeId ? { ...n, config: { ...n.config, ...config } } : n
    )

    return { ...w, nodes, updatedAt: new Date().toISOString() }
  })

  $browserAutomation.set({ ...state, workflows })
}

export function updateNodePosition(workflowId: string, nodeId: string, position: { x: number; y: number }) {
  const state = $browserAutomation.get()

  const workflows = state.workflows.map(w => {
    if (w.id !== workflowId) {return w}
    const nodes = w.nodes.map(n => (n.id === nodeId ? { ...n, position } : n))

    return { ...w, nodes, updatedAt: new Date().toISOString() }
  })

  $browserAutomation.set({ ...state, workflows })
}

export function setWorkflowSchedule(workflowId: string, schedule: string) {
  const state = $browserAutomation.get()

  const workflows = state.workflows.map(w =>
    w.id === workflowId ? { ...w, schedule, updatedAt: new Date().toISOString() } : w
  )

  $browserAutomation.set({ ...state, workflows })
}

export function addExecution(execution: WorkflowExecution) {
  const state = $browserAutomation.get()
  $browserAutomation.set({ ...state, executions: [...state.executions, execution] })
}

export function updateExecution(id: string, updates: Partial<WorkflowExecution>) {
  const state = $browserAutomation.get()
  const executions = state.executions.map(e => (e.id === id ? { ...e, ...updates } : e))
  $browserAutomation.set({ ...state, executions })
}
