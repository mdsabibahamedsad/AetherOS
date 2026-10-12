import type { SubagentStatus } from '@/store/subagents'

/**
 * Canonical AGI state vocabulary (UX Phase 7/11/55). One set of labels for
 * tasks, agents, and timeline rows — mapped from the real backend states,
 * never invented. Anything without a backend signal maps to `unknown`,
 * which renders as "Unknown", not as a guess.
 */

export type TaskState =
  | 'draft'
  | 'queued'
  | 'planning'
  | 'waiting_for_approval'
  | 'running'
  | 'paused'
  | 'blocked'
  | 'verifying'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'unknown'

export type AgentLifecycle =
  | 'created'
  | 'initializing'
  | 'ready'
  | 'planning'
  | 'running'
  | 'waiting'
  | 'needs_approval'
  | 'completing'
  | 'completed'
  | 'blocked'
  | 'failed'
  | 'cancelled'
  | 'paused'
  | 'unknown'

export const TASK_STATE_LABEL: Record<TaskState, string> = {
  draft: 'Draft',
  queued: 'Queued',
  planning: 'Planning',
  waiting_for_approval: 'Waiting for approval',
  running: 'Running',
  paused: 'Paused',
  blocked: 'Blocked',
  verifying: 'Verifying',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
  unknown: 'Unknown',
}

export const AGENT_LIFECYCLE_LABEL: Record<AgentLifecycle, string> = {
  created: 'Created',
  initializing: 'Initializing',
  ready: 'Ready',
  planning: 'Planning',
  running: 'Running',
  waiting: 'Waiting',
  needs_approval: 'Needs approval',
  completing: 'Completing',
  completed: 'Completed',
  blocked: 'Blocked',
  failed: 'Failed',
  cancelled: 'Cancelled',
  paused: 'Paused',
  unknown: 'Unknown',
}

/** Subagent runtime states → canonical agent lifecycle (one-to-one). */
export function agentLifecycleFromSubagent(status: SubagentStatus): AgentLifecycle {
  switch (status) {
    case 'running':
      return 'running'

    case 'queued':
      return 'waiting'

    case 'completed':
      return 'completed'

    case 'failed':
      return 'failed'

    case 'interrupted':
      return 'cancelled'
  }
}

/**
 * Cron/action raw states → canonical task state. Cron jobs expose
 * enabled/paused/next-run/error; action tasks expose running/exit_code.
 * PAUSE exists for cron (pauseCronJob) but NOT for sessions — callers must
 * use `session.interrupt` and label it Stop, never Pause.
 */
export function taskStateFromCron(opts: {
  enabled?: boolean
  paused?: boolean
  lastError?: string | null
}): TaskState {
  if (opts.lastError) {
    return 'failed'
  }

  if (opts.paused || opts.enabled === false) {
    return 'paused'
  }

  return 'queued'
}

export function taskStateFromAction(opts: {
  running?: boolean
  exitCode?: number | null
}): TaskState {
  if (opts.running) {
    return 'running'
  }

  if (opts.exitCode === 0) {
    return 'completed'
  }

  if (typeof opts.exitCode === 'number') {
    return 'failed'
  }

  return 'unknown'
}

/**
 * Autonomy levels mapped ONLY to controls the repository implements:
 * per-session YOLO bypass, global YOLO bypass (`approvals.mode`), and the
 * parked clarify/approval gates. There is no guided-plan-approval mode in
 * the backend, so none is claimed.
 */
export type AutonomyLevel = 'assist' | 'supervised' | 'autonomous'

export function autonomyFromYolo(opts: { sessionYolo: boolean; globalYolo: boolean }): AutonomyLevel {
  if (opts.globalYolo || opts.sessionYolo) {
    return 'autonomous'
  }

  return 'supervised'
}

export const AUTONOMY_LABEL: Record<AutonomyLevel, string> = {
  assist: 'Assist — you drive, AetherOS answers',
  supervised: 'Supervised — executes with approvals',
  autonomous: 'Autonomous — auto-approves within permissions',
}

/**
 * Confirmation thresholds driven by the real permission architecture:
 * the approval gate fires on policy; the UI mirrors it. Low = no gate,
 * medium = inline approval affordance, high/destructive = explicit
 * confirmation dialog. Never inverted, never hidden.
 */
export type RiskTier = 'low' | 'medium' | 'high' | 'destructive'

export function confirmationForTier(tier: RiskTier): 'none' | 'inline' | 'explicit' | 'strong' {
  switch (tier) {
    case 'low':
      return 'none'

    case 'medium':
      return 'inline'

    case 'high':
      return 'explicit'

    case 'destructive':
      return 'strong'
  }
}
