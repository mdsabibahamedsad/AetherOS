export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused' | 'retrying'
export type TaskMode = 'sequential' | 'parallel' | 'background'

export interface TaskNode {
  id: string
  label: string
  description: string
  status: TaskStatus
  mode: TaskMode
  dependencies: string[]
  priority: number
  retryCount: number
  maxRetries: number
  progress: number
  result?: unknown
  error?: string
  startedAt?: number
  completedAt?: number
  subtasks: TaskNode[]
  agentType?: string
  estimatedDuration?: number
}

export interface TaskGraph {
  id: string
  goal: string
  nodes: Map<string, TaskNode>
  status: 'pending' | 'running' | 'completed' | 'failed'
  createdAt: number
  startedAt?: number
  completedAt?: number
}

const graphs = new Map<string, TaskGraph>()
let nodeCounter = 0

function nextId(prefix = 'task'): string {
  return `${prefix}_${++nodeCounter}_${Date.now().toString(36)}`
}

export function createGraph(goal: string): TaskGraph {
  const graph: TaskGraph = {
    id: nextId('graph'),
    goal,
    nodes: new Map(),
    status: 'pending',
    createdAt: Date.now()
  }

  graphs.set(graph.id, graph)

  return graph
}

export function addNode(graphId: string, label: string, description: string, opts?: {
  mode?: TaskMode
  dependencies?: string[]
  priority?: number
  maxRetries?: number
  agentType?: string
  estimatedDuration?: number
}): string {
  const graph = graphs.get(graphId)

  if (!graph) {throw new Error(`Graph ${graphId} not found`)}

  const node: TaskNode = {
    id: nextId('node'),
    label,
    description,
    status: 'pending',
    mode: opts?.mode ?? 'sequential',
    dependencies: opts?.dependencies ?? [],
    priority: opts?.priority ?? 5,
    retryCount: 0,
    maxRetries: opts?.maxRetries ?? 0,
    progress: 0,
    subtasks: [],
    agentType: opts?.agentType,
    estimatedDuration: opts?.estimatedDuration
  }

  graph.nodes.set(node.id, node)

  return node.id
}

export function getGraph(graphId: string): TaskGraph | undefined {
  return graphs.get(graphId)
}

export function getReadyNodes(graphId: string): TaskNode[] {
  const graph = graphs.get(graphId)

  if (!graph || graph.status !== 'running') {return []}

  return Array.from(graph.nodes.values()).filter(n => {
    if (n.status !== 'pending') {return false}

    return n.dependencies.every(depId => {
      const dep = graph.nodes.get(depId)

      return dep?.status === 'completed'
    })
  }).sort((a, b) => b.priority - a.priority)
}

export function updateNodeStatus(graphId: string, nodeId: string, status: TaskStatus, result?: unknown, error?: string): void {
  const graph = graphs.get(graphId)

  if (!graph) {return}
  const node = graph.nodes.get(nodeId)

  if (!node) {return}

  node.status = status

  if (status === 'running') {node.startedAt = Date.now()}

  if (status === 'completed') { node.completedAt = Date.now(); node.result = result }

  if (status === 'failed') {node.error = error}

  if (status === 'running') {node.progress = 0}

  if (status === 'completed') {node.progress = 100}

  checkGraphCompletion(graph)
}

export function updateNodeProgress(graphId: string, nodeId: string, progress: number): void {
  const graph = graphs.get(graphId)

  if (!graph) {return}
  const node = graph.nodes.get(nodeId)

  if (!node) {return}
  node.progress = Math.min(progress, 100)
}

export function startGraph(graphId: string): void {
  const graph = graphs.get(graphId)

  if (!graph) {return}
  graph.status = 'running'
  graph.startedAt = Date.now()
}

export function pauseNode(graphId: string, nodeId: string): void {
  const graph = graphs.get(graphId)

  if (!graph) {return}
  const node = graph.nodes.get(nodeId)

  if (!node || node.status !== 'running') {return}
  node.status = 'paused'
}

export function resumeNode(graphId: string, nodeId: string): void {
  const graph = graphs.get(graphId)

  if (!graph) {return}
  const node = graph.nodes.get(nodeId)

  if (!node || node.status !== 'paused') {return}
  node.status = 'pending'
}

export function retryNode(graphId: string, nodeId: string): void {
  const graph = graphs.get(graphId)

  if (!graph) {return}
  const node = graph.nodes.get(nodeId)

  if (!node) {return}
  node.status = 'pending'
  node.retryCount++
  node.error = undefined
}

export function cancelNode(graphId: string, nodeId: string): void {
  const graph = graphs.get(graphId)

  if (!graph) {return}
  const node = graph.nodes.get(nodeId)

  if (!node) {return}
  node.status = 'cancelled'
}

export function cancelGraph(graphId: string): void {
  const graph = graphs.get(graphId)

  if (!graph) {return}
  graph.nodes.forEach(n => { if (n.status === 'pending' || n.status === 'running' || n.status === 'paused') {n.status = 'cancelled'} })
  graph.status = 'failed'
}

export function getGraphStatus(graphId: string): { total: number; completed: number; failed: number; running: number; pending: number; progress: number } {
  const graph = graphs.get(graphId)

  if (!graph) {return { total: 0, completed: 0, failed: 0, running: 0, pending: 0, progress: 0 }}

  const nodes = Array.from(graph.nodes.values())
  const total = nodes.length || 1
  const completed = nodes.filter(n => n.status === 'completed').length
  const failed = nodes.filter(n => n.status === 'failed').length
  const running = nodes.filter(n => n.status === 'running').length
  const pending = nodes.filter(n => n.status === 'pending' || n.status === 'paused').length

  return {
    total: nodes.length,
    completed,
    failed,
    running,
    pending,
    progress: Math.round((completed / total) * 100)
  }
}

export function getAllGraphs(): TaskGraph[] {
  return Array.from(graphs.values())
}

function checkGraphCompletion(graph: TaskGraph): void {
  const nodes = Array.from(graph.nodes.values())
  const allDone = nodes.every(n => n.status === 'completed' || n.status === 'failed' || n.status === 'cancelled')

  if (allDone) {
    graph.status = nodes.some(n => n.status === 'failed') ? 'failed' : 'completed'
    graph.completedAt = Date.now()
  }
}

export function createResearchPlan(goal: string, graphId?: string): string {
  const gid = graphId ?? createGraph(goal).id
  const g = graphs.get(gid)!
  g.status = 'running'
  g.startedAt = Date.now()

  const search = addNode(gid, 'Search', `Search for information about: ${goal}`, { mode: 'parallel', priority: 8, estimatedDuration: 10_000 })
  const gather = addNode(gid, 'Gather', 'Collect and organize findings', { dependencies: [search], priority: 7, estimatedDuration: 5_000 })
  const analyze = addNode(gid, 'Analyze', 'Analyze gathered information', { dependencies: [gather], priority: 6, estimatedDuration: 8_000 })
  const summarize = addNode(gid, 'Summarize', 'Create summary report', { dependencies: [analyze], priority: 5, estimatedDuration: 5_000 })
  const save = addNode(gid, 'Save', 'Save report to workspace', { dependencies: [summarize], priority: 4, estimatedDuration: 2_000 })

  return gid
}

export function createCodePlan(goal: string, graphId?: string): string {
  const gid = graphId ?? createGraph(goal).id
  const g = graphs.get(gid)!
  g.status = 'running'
  g.startedAt = Date.now()

  const understand = addNode(gid, 'Understand', 'Read project structure and key files', { priority: 9, estimatedDuration: 8_000 })
  const plan = addNode(gid, 'Plan', 'Design implementation approach', { dependencies: [understand], priority: 8, estimatedDuration: 5_000 })
  const implement = addNode(gid, 'Implement', 'Write code changes', { dependencies: [plan], priority: 7, agentType: 'coding', estimatedDuration: 30_000 })
  const review = addNode(gid, 'Review', 'Review code for issues', { dependencies: [implement], priority: 6, estimatedDuration: 10_000 })
  const test = addNode(gid, 'Test', 'Run tests and verify', { dependencies: [review], priority: 5, estimatedDuration: 15_000 })

  return gid
}

export function createDeployPlan(goal: string, graphId?: string): string {
  const gid = graphId ?? createGraph(goal).id
  const g = graphs.get(gid)!
  g.status = 'running'
  g.startedAt = Date.now()

  const build = addNode(gid, 'Build', 'Build project for production', { priority: 9, estimatedDuration: 20_000 })
  const test = addNode(gid, 'Test', 'Run test suite', { priority: 8, estimatedDuration: 15_000 })
  const security = addNode(gid, 'Security Scan', 'Run security checks', { mode: 'parallel', priority: 7, estimatedDuration: 10_000 })
  const deploy = addNode(gid, 'Deploy', 'Deploy to production server', { dependencies: [build, test, security], priority: 6, estimatedDuration: 25_000 })
  const verify = addNode(gid, 'Verify', 'Verify deployment is healthy', { dependencies: [deploy], priority: 5, estimatedDuration: 10_000 })

  return gid
}
