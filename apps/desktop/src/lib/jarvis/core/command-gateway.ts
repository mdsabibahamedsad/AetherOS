/**
 * Unified Jarvis command gateway.
 *
 * THE single entry point for every Jarvis command regardless of origin:
 * typed composer, voice transcript, quick-action chip, command palette,
 * browser/file/terminal panel shortcuts. There is no second execution path —
 * voice transcripts land here exactly like typed text.
 *
 * Flow: normalize → local client-side intent? → permission check →
 * gateway pipeline → history + result. Local intents (exit, navigate,
 * open allowlisted app/URL, system status) execute through the validated
 * local executor; everything else goes to the live gateway agent via
 * `executePipeline`. Destructive phrasing requires explicit approval first
 * (identical rule for text and voice) — approval surfaces through the
 * existing Security Center approvals UI for gateway turns, and through
 * `ApprovalRequiredError` for local actions.
 */

import { activeGateway } from '@/store/gateway'
import {
  $jarvisCommandLog,
  $jarvisExecution,
  addJarvisNotification,
  appendJarvisCommandLog,
  isJarvisExecutingState,
  type JarvisExecutionState,
  setJarvisExecution
} from '@/store/jarvis-mode'
import { $permissionPolicy, $sessionGrants } from '@/store/jarvis-permissions'

import { getCapability } from '../capabilities/registry'
import { executeLocal, type LocalExecDeps } from '../os/local-executor'
import { decideCapability, looksDestructive } from '../permissions/policy'
import type { ExecutionPlanStep } from '../types'

import { executePipeline } from './ai-core'

export type JarvisInputType = 'text' | 'voice'

export interface SubmitOpts {
  inputType: JarvisInputType
  /** Set when the user already approved this exact command (Allow once). */
  approved?: boolean
  deps: LocalExecDeps
  onStepUpdate?: (stepId: string, status: ExecutionPlanStep['status'], progress: number, result?: string) => void
  onThinkingStage?: (stage: string, label: string) => void
  onToolEvent?: (tool: string, phase: 'start' | 'complete') => void
  /** Called with the final text so the voice layer can speak it. */
  onResult?: (text: string, inputType: JarvisInputType) => void
}

export interface CommandOutcome {
  kind: 'local' | 'gateway'
  capabilityId: string | null
  response: string
  sessionId: string | null
  toolsUsed: string[]
  durationMs: number
}

/** Thrown when a command needs explicit approval before it may run. */
export class ApprovalRequiredError extends Error {
  readonly code = 'APPROVAL_REQUIRED'
  readonly capabilityId: string | null
  readonly input: string
  constructor(input: string, capabilityId: string | null, message: string) {
    super(message)
    this.name = 'ApprovalRequiredError'
    this.capabilityId = capabilityId
    this.input = input
  }
}

/** Thrown when a submit arrives while a pipeline is already in flight. The
 *  running command keeps its gateway session; the duplicate is rejected so a
 *  double-Enter/double-click can never spawn two sessions for one command. */
export class JarvisBusyError extends Error {
  readonly code = 'JARVIS_BUSY'

  constructor() {
    super('A Jarvis command is already running — press Esc to cancel it first.')
    this.name = 'JarvisBusyError'
  }
}

interface LocalMatch {
  capabilityId: string
  handler: string
  input: Record<string, string>
  run?: (deps: LocalExecDeps) => Promise<string> | string
}

const APP_IDS = ['chrome', 'youtube', 'vscode', 'spotify'] as const

/** Conservative client-side intent routing. Only exact, unambiguous commands
 *  are handled locally — everything else goes to the gateway agent. */
export function matchLocalIntent(raw: string): LocalMatch | null {
  const input = raw.trim().replace(/\s+/g, ' ')
  const lower = input.toLowerCase()

  if (/^(exit(\s+(jarvis|jarvis\s+mode))?|leave\s+jarvis|quit\s+jarvis|go\s+back|return\s+home|go\s+home)$/i.test(lower)) {
    return {
      capabilityId: 'system.navigate', handler: 'system.navigate', input: { route: '/' },
      run: deps => {
        deps.navigate('/')

        return 'Exited Jarvis mode — back at AetherOS Home. Running tasks continue in the background.'
      }
    }
  }

  const nav = lower.match(/^(open|go\s+to|show\s+me)\s+(memory|agents|automation|browser|terminal|settings|security(\s+center)?|diagnostics|home|chat|knowledge|communications)(\s+(center|panel|page|view))?$/)

  if (nav) {
    const dest = nav[2].replace(/\s+center$/, '')
    const route = dest === 'home' ? '/' : dest === 'security' ? '/security' : `/${dest}`

    return { capabilityId: 'system.navigate', handler: 'system.navigate', input: { route } }
  }

  const app = lower.match(/^open\s+([a-z0-9 .+]+)\.?$/)

  if (app) {
    const id = app[1].trim().replace(/[. ]+$/, '')
    const normalized = id === 'vs code' ? 'vscode' : id

    if ((APP_IDS as readonly string[]).includes(normalized)) {
      return { capabilityId: 'computer.launch-app', handler: 'os.launch-app', input: { appId: normalized } }
    }
  }

  const url = input.match(/^open\s+(https?:\/\/\S+)\.?$/i)

  if (url) {
    return { capabilityId: 'computer.open-url', handler: 'os.open-url', input: { url: url[1] } }
  }

  if (/^(check\s+)?(system\s+)?(health|status)$/i.test(lower) || /^system\s+status$/i.test(lower)) {
    return { capabilityId: 'system.status', handler: 'system.status', input: {} }
  }

  if (/^(what\s+model|which\s+model|show\s+(available\s+)?models)$/i.test(lower)) {
    return { capabilityId: 'models.inspect', handler: 'models.inspect', input: {} }
  }

  return null
}

function failRecord(input: string, inputType: JarvisInputType, status: JarvisExecutionState, error: string, startedAt: number) {
  appendJarvisCommandLog({
    id: `cmd-${startedAt}`,
    timestamp: startedAt,
    sessionId: null,
    input,
    inputType,
    intent: 'local',
    status,
    durationMs: Date.now() - startedAt,
    toolsUsed: [],
    result: null,
    error
  })
}

export async function submitJarvisCommand(rawInput: string, opts: SubmitOpts): Promise<CommandOutcome> {
  const input = rawInput.trim()

  if (!input) {throw new Error('Empty command.')}

  const startedAt = Date.now()
  const { inputType, deps } = opts
  const onStep = opts.onStepUpdate ?? (() => undefined)
  const onStage = opts.onThinkingStage ?? (() => undefined)

  // ---- Local fast path: validated client-side execution, no gateway needed.
  const local = matchLocalIntent(input)
  // Navigation/exit never touches a pipeline, so it stays available
  // mid-flight (leaving Jarvis must never be blocked by a running task).
  const isNavExit = local?.capabilityId === 'system.navigate'

  // ---- Duplicate-submit guard: one in-flight pipeline owns the run. The
  // exemption above plus explicit Allow-once resubmits are the only ways
  // through while a command is alive.
  if (!opts.approved && !isNavExit && isJarvisExecutingState($jarvisExecution.get().state)) {
    throw new JarvisBusyError()
  }

  if (local) {
    const capability = getCapability(local.capabilityId)

    if (capability) {
      const { decision, permission } = decideCapability(capability, {
        policy: $permissionPolicy.get(),
        sessionGrants: $sessionGrants.get(),
        inputType
      })

      if (decision === 'deny') {
        const error = `Blocked by permission policy (${permission}).`
        failRecord(input, inputType, 'FAILED', error, startedAt)
        throw new Error(error)
      }

      if (decision === 'ask' && !opts.approved) {
        failRecord(input, inputType, 'FAILED', 'Approval required.', startedAt)
        throw new ApprovalRequiredError(input, local.capabilityId, `Jarvis wants to run "${capability.name}". Approve to continue.`)
      }
    }

    setJarvisExecution({ state: 'EXECUTING', commandId: `cmd-${startedAt}`, sessionId: null, startedAt, error: null })
    onStage('executing', capability ? `Running ${capability.name}...` : 'Running...')

    try {
      const response = local.run ? await local.run(deps) : await executeLocal(local.handler, local.input, deps)
      const durationMs = Date.now() - startedAt
      setJarvisExecution({ state: 'COMPLETED', error: null })
      appendJarvisCommandLog({
        id: `cmd-${startedAt}`,
        timestamp: startedAt,
        sessionId: null,
        input,
        inputType,
        intent: 'local',
        status: 'COMPLETED',
        durationMs,
        toolsUsed: [local.capabilityId],
        result: response.slice(0, 2000),
        error: null
      })
      opts.onResult?.(response, inputType)

      return { kind: 'local', capabilityId: local.capabilityId, response, sessionId: null, toolsUsed: [local.capabilityId], durationMs }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      failRecord(input, inputType, 'FAILED', message, startedAt)
      setJarvisExecution({ state: 'FAILED', error: message })
      throw err instanceof Error ? err : new Error(message)
    }
  }

  // ---- Gateway path: destructive phrasing needs approval first (text == voice).
  if (looksDestructive(input) && !opts.approved) {
    failRecord(input, inputType, 'FAILED', 'Approval required.', startedAt)
    throw new ApprovalRequiredError(input, null, 'This looks destructive. Review the exact command, then Allow once to run it.')
  }

  const gateway = activeGateway()

  if (!gateway || gateway.connectionState !== 'open') {
    addJarvisNotification({ title: 'Gateway disconnected', message: 'Reconnect the gateway, then retry.', type: 'warning' })
  }

  const result = await executePipeline(input, onStep, onStage, { inputType, onToolEvent: opts.onToolEvent })
  // The pipeline appends the authoritative history record (real session id,
  // real tools, real duration) — mirror it so callers never see placeholders.
  const latest = $jarvisCommandLog.get()[0]
  opts.onResult?.(result.response, inputType)

  return {
    kind: 'gateway',
    capabilityId: null,
    response: result.response,
    sessionId: latest?.sessionId ?? null,
    toolsUsed: latest?.toolsUsed ?? [],
    durationMs: latest?.durationMs ?? 0
  }
}
