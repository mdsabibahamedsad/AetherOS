import { acceptSuggestion, getPendingSuggestions, isAutonomous } from './autonomy'
import { getContext, logAction } from './context'
import { completeTask, resolveNodeToTasks } from './executor'
import { remember } from './memory'
import { notify } from './notifications'
import { emitEvent, getRecentEvents } from './observer'
import { addNode, createCodePlan, createDeployPlan, createGraph, createResearchPlan, getGraph, getGraphStatus, getReadyNodes, startGraph, updateNodeProgress, updateNodeStatus } from './planner'
import { reason } from './reasoning'
import { completeTask as completeBgTask, createTask, updateProgress } from './task-manager'

export type EnginePhase = 'idle' | 'observing' | 'thinking' | 'planning' | 'executing' | 'learning' | 'error'

interface EngineState {
  phase: EnginePhase
  cycleCount: number
  lastCycle: number
  activeGraphId: string | null
  isRunning: boolean
  error: string | null
  cycleTime: number
}

let state: EngineState = {
  phase: 'idle',
  cycleCount: 0,
  lastCycle: 0,
  activeGraphId: null,
  isRunning: false,
  error: null,
  cycleTime: 0
}

let loopId: ReturnType<typeof setInterval> | null = null
let pauseRequested = false
const CYCLE_INTERVAL = 2000
const listeners = new Set<(s: EngineState) => void>()

function notifyListeners(): void {
  listeners.forEach(l => { try { l({ ...state }) } catch { /* ignore */ } })
}

export function onStateChange(listener: (s: EngineState) => void): () => void {
  listeners.add(listener)

  return () => listeners.delete(listener)
}

function setPhase(phase: EnginePhase): void {
  state.phase = phase
  notifyListeners()
}

export function getEngineState(): EngineState {
  return { ...state }
}

async function observe(): Promise<void> {
  setPhase('observing')
  const ctx = getContext()

  if (ctx.isIdle && ctx.idleDuration > 120_000 && isAutonomous()) {
    emitEvent('user:idle', { duration: ctx.idleDuration })
  }
}

async function think(): Promise<void> {
  setPhase('thinking')
  const events = getRecentEvents(5)

  for (const event of events) {
    if (pauseRequested) {return}
    const result = reason(event)

    if (result && isAutonomous()) {
      notify(`Observation: ${result.suggestions[0]?.title}`, result.suggestions[0]?.description ?? '', 'info', 'autonomy')
    }
  }
}

async function plan(): Promise<void> {
  setPhase('planning')
  const suggestions = getPendingSuggestions()

  for (const suggestion of suggestions) {
    if (pauseRequested) {return}

    if (suggestion.suggestions[0]?.priority === 'high' && isAutonomous()) {
      const accepted = acceptSuggestion(0)

      if (accepted) {
        const graphId = createGraph(accepted.suggestions[0].title).id
        state.activeGraphId = graphId
        startGraph(graphId)
        logAction(`Started plan: ${accepted.suggestions[0].title}`)
      }
    }
  }
}

async function execute(): Promise<void> {
  setPhase('executing')

  if (!state.activeGraphId) {return}

  const status = getGraphStatus(state.activeGraphId)

  if (status.completed + status.failed >= status.total) {
    state.activeGraphId = null

    return
  }

  const readyNodes = getReadyNodes(state.activeGraphId)

  for (const node of readyNodes) {
    if (pauseRequested) {return}
    updateNodeStatus(state.activeGraphId, node.id, 'running')

    const bgTask = createTask(node.label, 'processing', node.description, { estimatedDuration: node.estimatedDuration })
    const executorTasks = await resolveNodeToTasks(node)

    let progress = 0

    const progressInterval = setInterval(() => {
      progress += Math.random() * 15 + 5

      if (progress > 100) {progress = 100}
      updateNodeProgress(state.activeGraphId!, node.id, progress)
      updateProgress(bgTask.id, progress)
    }, 500)

    await new Promise(resolve => setTimeout(resolve, (node.estimatedDuration ?? 3000) * (0.5 + Math.random() * 0.5)))

    clearInterval(progressInterval)
    updateNodeProgress(state.activeGraphId, node.id, 100)
    updateProgress(bgTask.id, 100)

    executorTasks.forEach(t => completeTask(t.id))
    completeBgTask(bgTask.id, { completed: true })
    updateNodeStatus(state.activeGraphId, node.id, 'completed', { completed: true })
  }
}

async function learn(): Promise<void> {
  setPhase('learning')

  if (!state.activeGraphId) {return}
  const status = getGraphStatus(state.activeGraphId)

  if (status.completed + status.failed >= status.total) {
    const graph = getGraph(state.activeGraphId)

    if (graph) {
      remember('fact', `graph:${graph.goal}`, {
        goal: graph.goal,
        total: status.total,
        completed: status.completed,
        failed: status.failed,
        duration: graph.completedAt ? graph.completedAt - (graph.startedAt ?? graph.createdAt) : 0
      })

      if (status.failed === 0) {
        notify(`Plan Complete: ${graph.goal}`, 'All tasks completed successfully', 'success', 'system')
      } else {
        notify(`Plan Partial: ${graph.goal}`, `${status.failed} task(s) failed`, 'warning', 'system')
      }
    }

    state.activeGraphId = null
  }
}

async function cycle(): Promise<void> {
  if (pauseRequested || !state.isRunning) {return}

  const start = Date.now()

  try {
    await observe()

    if (pauseRequested) {return}
    await think()

    if (pauseRequested) {return}
    await plan()

    if (pauseRequested) {return}
    await execute()

    if (pauseRequested) {return}
    await learn()

    state.cycleCount++
    state.lastCycle = Date.now()
    state.cycleTime = Date.now() - start
    state.error = null
    setPhase('idle')
  } catch (e) {
    state.error = e instanceof Error ? e.message : String(e)
    state.phase = 'error'
    notify('Engine Cycle Error', state.error, 'error', 'system')
    notifyListeners()
  }
}

export function startEngine(): void {
  if (state.isRunning) {return}
  state.isRunning = true
  pauseRequested = false
  setPhase('idle')
  loopId = setInterval(cycle, CYCLE_INTERVAL)
  notify('Jarvis Engine', 'Engine loop started', 'info', 'system')
}

export function stopEngine(): void {
  state.isRunning = false

  if (loopId) { clearInterval(loopId); loopId = null }
  setPhase('idle')
  notify('Jarvis Engine', 'Engine loop stopped', 'info', 'system')
}

export function pauseEngine(): void {
  pauseRequested = true
  state.isRunning = false
  notify('Jarvis Engine', 'Engine loop paused', 'info', 'system')
}

export function resumeEngine(): void {
  pauseRequested = false
  state.isRunning = true
  loopId = setInterval(cycle, CYCLE_INTERVAL)
  notify('Jarvis Engine', 'Engine loop resumed', 'info', 'system')
}

export function executeCommand(command: string): void {
  logAction(`Command: ${command}`)
  emitEvent('user:activity', { command })

  const graphId = createGraph(command).id
  state.activeGraphId = graphId

  const cmd = command.toLowerCase()

  if (cmd.includes('research') || cmd.includes('search') || cmd.includes('find')) {
    createResearchPlan(command, graphId)
  } else if (cmd.includes('code') || cmd.includes('implement') || cmd.includes('build') || cmd.includes('fix') || cmd.includes('test')) {
    createCodePlan(command, graphId)
  } else if (cmd.includes('deploy') || cmd.includes('release')) {
    createDeployPlan(command, graphId)
  } else {
    const g = getGraph(graphId)!
    g.status = 'running'
    g.startedAt = Date.now()
    const understand = addNode(graphId, 'Understand', `Understand the request: ${command}`, { priority: 8, estimatedDuration: 5_000 })
    const respond = addNode(graphId, 'Respond', 'Generate response', { dependencies: [understand], priority: 7, estimatedDuration: 3_000 })
  }

  startGraph(graphId)
  notify('Task', `Processing: ${command.slice(0, 60)}...`, 'info', 'task')
}

export function getCycleInterval(): number {
  return CYCLE_INTERVAL
}
