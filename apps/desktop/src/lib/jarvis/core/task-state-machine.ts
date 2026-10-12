/**
 * Canonical Jarvis task state machine.
 *
 * One task model for every Jarvis surface (orb, timeline, jobs panel,
 * diagnostics, voice). UI must render this state — never infer status
 * from animation.
 *
 * States: queued → understanding → planning → awaiting_approval →
 * executing ⇄ waiting_tool ⇄ observing ⇄ recovering → completed
 * with paused / failed / cancelled / timed_out / blocked exits.
 */

export type JarvisTaskStatus =
  | 'queued'
  | 'understanding'
  | 'planning'
  | 'awaiting_approval'
  | 'executing'
  | 'waiting_tool'
  | 'observing'
  | 'recovering'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'timed_out'
  | 'blocked'

export type TaskInputType = 'text' | 'voice' | 'system' | 'image' | 'file' | 'screen'

export interface TaskInput {
  raw: string
  inputType: TaskInputType
  attachments?: string[]
}

export interface TaskStep {
  id: string
  description: string
  dependencies: string[]
  tool: string | null
  args: Record<string, unknown>
  permission: 'none' | 'low' | 'medium' | 'high' | 'critical'
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  result?: string
  error?: string
  attempts: number
}

export type TaskErrorKind =
  | 'retryable'
  | 'recoverable'
  | 'requires_user_input'
  | 'permission_denied'
  | 'fatal'

export interface TaskError {
  kind: TaskErrorKind
  message: string
  tool?: string
  retryable: boolean
}

export interface TaskResult {
  text: string
  toolsUsed: string[]
  durationMs: number
  verified: boolean
  evidence?: string
}

export interface CancellationState {
  requested: boolean
  reason?: string
  at?: number
}

export interface ApprovalRequest {
  id: string
  summary: string
  detail?: string
  level: 'low' | 'medium' | 'high' | 'critical'
  approved: boolean | null
}

export interface JarvisTask {
  id: string
  sessionId: string | null
  input: TaskInput
  status: JarvisTaskStatus
  plan: TaskStep[]
  currentStep?: string
  toolsUsed: string[]
  startedAt: number
  updatedAt: number
  completedAt?: number
  result?: TaskResult
  error?: TaskError
  cancellation?: CancellationState
  approval?: ApprovalRequest
}

const TRANSITIONS: Record<JarvisTaskStatus, JarvisTaskStatus[]> = {
  queued: ['understanding', 'cancelled'],
  understanding: ['planning', 'blocked', 'failed', 'cancelled'],
  planning: ['awaiting_approval', 'executing', 'blocked', 'failed', 'cancelled'],
  awaiting_approval: ['executing', 'cancelled', 'blocked'],
  executing: ['waiting_tool', 'observing', 'recovering', 'paused', 'completed', 'failed', 'cancelled', 'timed_out', 'blocked'],
  waiting_tool: ['observing', 'recovering', 'failed', 'cancelled', 'timed_out'],
  observing: ['executing', 'recovering', 'completed', 'failed', 'cancelled', 'blocked'],
  recovering: ['executing', 'awaiting_approval', 'failed', 'cancelled', 'blocked'],
  paused: ['executing', 'cancelled'],
  completed: [],
  failed: ['queued'],
  cancelled: ['queued'],
  timed_out: ['queued'],
  blocked: ['executing', 'cancelled']
}

export function canTransition(from: JarvisTaskStatus, to: JarvisTaskStatus): boolean {
  return TRANSITIONS[from]?.includes(to) ?? false
}

let counter = 0

export function createTask(input: TaskInput, sessionId: string | null = null): JarvisTask {
  const now = Date.now()
  counter += 1
  return {
    id: `jt_${now.toString(36)}_${counter}`,
    sessionId,
    input,
    status: 'queued',
    plan: [],
    toolsUsed: [],
    startedAt: now,
    updatedAt: now,
    cancellation: { requested: false }
  }
}

export function transition(task: JarvisTask, to: JarvisTaskStatus): void {
  if (!canTransition(task.status, to)) {
    throw new Error(`Invalid task transition: ${task.status} → ${to}`)
  }
  task.status = to
  task.updatedAt = Date.now()
  if (to === 'completed' || to === 'failed' || to === 'cancelled' || to === 'timed_out') {
    task.completedAt = Date.now()
  }
}

export function forceTransition(task: JarvisTask, to: JarvisTaskStatus): void {
  task.status = to
  task.updatedAt = Date.now()
  if (to === 'completed' || to === 'failed' || to === 'cancelled' || to === 'timed_out') {
    task.completedAt = task.completedAt ?? Date.now()
  }
}

/** Classify a tool/execution error into the orchestrator's recovery taxonomy. */
export function classifyError(message: string, extra?: { permissionDenied?: boolean }): TaskError {
  const msg = message.toLowerCase()
  if (extra?.permissionDenied || /permission|denied|blocked by policy|approval/i.test(message)) {
    return { kind: 'permission_denied', message, retryable: false }
  }
  if (/approve|confirm|which (file|one)|need (more|input)|ambiguous|choose/i.test(msg)) {
    return { kind: 'requires_user_input', message, retryable: false }
  }
  if (/timeout|timed out|econnreset|socket hang up|rate limit|429|503|unavailable|gateway is not connected/i.test(msg)) {
    return { kind: 'retryable', message, retryable: true }
  }
  if (/not found|no such|element not found|no results/i.test(msg)) {
    return { kind: 'recoverable', message, retryable: true }
  }
  if (/syntax|invalid argument|schema|validation/i.test(msg)) {
    return { kind: 'fatal', message, retryable: false }
  }
  return { kind: 'recoverable', message, retryable: true }
}

export const MAX_SELF_REPAIR_RETRIES = 3
