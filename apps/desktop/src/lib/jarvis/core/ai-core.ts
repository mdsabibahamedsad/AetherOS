import { activeGateway } from '@/store/gateway'
import {
  addJarvisAgent,
  addJarvisNotification,
  appendJarvisCommandLog,
  type JarvisInputType,
  setJarvisExecution,
  updateJarvisAgent
} from '@/store/jarvis-mode'
import { clearAllPrompts, setApprovalRequest, setSecretRequest, setSudoRequest } from '@/store/prompts'

import { createExecutionPlan } from '../planner/execution-planner'
import { analyzeContext, generateSuggestions, reflectOnExecution } from '../reasoner/reasoner'
import type { ExecutionPlan, ExecutionPlanStep, Intent, IntentType } from '../types'
import { buildContextPrompt, trackCommand } from '../workspace/workspace-awareness'

const INTENT_PATTERNS: Record<IntentType, RegExp[]> = {
  code: [/\b(write|create|build|generate|fix|refactor|debug|implement|code|program|script|function|class|component|module|landing.page)\b/i],
  research: [/\b(research|investigate|find|discover|learn|analyze|explore|lookup|search|study|what.is|tell.me.about)\b/i],
  deploy: [/\b(deploy|publish|release|ship|launch|push|upload|host)\b/i],
  automate: [/\b(automate|schedule|monitor|watch|trigger|cron|background|recurring|every|notify)\b/i],
  search: [/\b(search|find|locate|grep|filter|query|look\s*up)\b/i],
  'file-operation': [/\b(read|write|copy|move|delete|rename|create|open|save|file|folder|directory)\b/i],
  terminal: [/\b(run|execute|shell|bash|command|terminal|pipe|install|npm|pip|apt|brew)\b/i],
  browser: [/\b(browse|open\s*url|website|scrape|crawl|fetch|download|page)\b/i],
  database: [/\b(database|sql|query|table|schema|migration|backup|restore|mongo|postgres|mysql)\b/i],
  'memory-query': [/\b(remember|recall|what.*did.*i|previously|last\s*time|before|history|what.have.i)\b/i],
  system: [/\b(status|health|stats|performance|cpu|ram|memory|disk|uptime|restart|stop|start)\b/i],
  chat: [],
  unknown: []
}

export function analyzeIntent(input: string): Intent {
  const lower = input.toLowerCase()
  let bestType: IntentType = 'chat'
  let bestConfidence = 0.3

  for (const [type, patterns] of Object.entries(INTENT_PATTERNS)) {
    let hits = 0

    for (const pattern of patterns) {
      if (pattern.test(lower)) {hits += 1}
    }

    if (hits > 0) {
      // Deterministic heuristic: base 0.65 + 0.05 per distinct pattern hit,
      // capped at 0.95. No randomness — the same input always scores the same.
      const confidence = Math.min(0.95, 0.65 + hits * 0.05)

      if (confidence > bestConfidence) {
        bestConfidence = confidence
        bestType = type as IntentType
      }
    }
  }

  const requiresTools: string[] = []

  if (bestType === 'code') {requiresTools.push('terminal', 'read_file', 'write_file', 'patch')}

  if (bestType === 'research') {requiresTools.push('web_search', 'web_extract')}

  if (bestType === 'browser') {requiresTools.push('browser_navigate', 'browser_click')}

  if (bestType === 'terminal') {requiresTools.push('terminal')}

  if (bestType === 'file-operation') {requiresTools.push('read_file', 'write_file', 'search_files')}

  if (bestType === 'deploy') {requiresTools.push('terminal', 'read_file')}

  if (bestType === 'database') {requiresTools.push('terminal')}

  return {
    type: bestType,
    confidence: bestConfidence,
    entities: extractEntities(input),
    context: [buildContextPrompt()],
    requiresTools
  }
}

function extractEntities(input: string): Record<string, string> {
  const entities: Record<string, string> = {}
  const fileMatch = input.match(/(?:file|folder|directory)\s+([^\s]+)/i)

  if (fileMatch) {entities.file = fileMatch[1]}
  const urlMatch = input.match(/(https?:\/\/[^\s]+)/i)

  if (urlMatch) {entities.url = urlMatch[1]}
  const projectMatch = input.match(/(?:project|repo)\s+['"]?([^'"\s]+)['"]?/i)

  if (projectMatch) {entities.project = projectMatch[1]}

  return entities
}

export interface PipelineResult {
  plan: ExecutionPlan
  response: string
  artifacts: string[]
  memoryUpdates: string[]
  reflection: ReturnType<typeof reflectOnExecution>
  suggestions: ReturnType<typeof generateSuggestions>
  modelUsed: { provider: string; model: string }
}

export class GatewayUnavailableError extends Error {
  readonly code = 'GATEWAY_UNAVAILABLE'
  readonly retryable = true
  constructor(message = 'Aetheros gateway is not connected. Reconnect, then retry the command.') {
    super(message)
    this.name = 'GatewayUnavailableError'
  }
}

export class JarvisCancelledError extends Error {
  readonly code = 'CANCELLED'
  readonly retryable = false
  constructor() {
    super('Command cancelled.')
    this.name = 'JarvisCancelledError'
  }
}

let cancelRequested = false
let lastJarvisSessionId: string | null = null
let lastJarvisTools: string[] = []

export function cancelJarvisPipeline(): void {
  cancelRequested = true
}

interface SessionCreateResponse {
  session_id: string
  stored_session_id?: string | null
  info?: { provider?: string; model?: string }
}

const PIPELINE_TIMEOUT_MS = 180_000

function throwIfCancelled(): void {
  if (cancelRequested) {
    cancelRequested = false
    setJarvisExecution({ state: 'CANCELLED', error: 'Command cancelled.' })
    throw new JarvisCancelledError()
  }
}

/**
 * Real command pipeline: intent is analyzed locally, but execution ALWAYS
 * goes through the live Aetheros gateway (session.create + prompt.submit +
 * streaming events). No simulated delays, no random progress, no fabricated
 * responses. When the gateway is unavailable the pipeline reports UNAVAILABLE
 * with an actionable error instead of fake success.
 *
 * Progress and stages are driven ONLY by real gateway events: tool.start /
 * tool.complete move plan steps, approval.request parks into the shared
 * Security Center approvals store (the agent blocks until the user responds),
 * and message.complete ends the turn.
 */
export interface PipelineOpts {
  inputType?: JarvisInputType
  onToolEvent?: (tool: string, phase: 'start' | 'complete') => void
}

export async function executePipeline(
  input: string,
  onStepUpdate: (stepId: string, status: ExecutionPlanStep['status'], progress: number, result?: string) => void,
  onThinkingStage: (stage: string, label: string) => void,
  opts: PipelineOpts = {}
): Promise<PipelineResult> {
  const commandId = `cmd-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const startedAt = Date.now()
  const inputType = opts.inputType ?? 'text'
  cancelRequested = false
  trackCommand(input)

  setJarvisExecution({ state: 'SUBMITTED', commandId, sessionId: null, startedAt, error: null })

  // Track this run as a real agent entry (running → completed/failed with
  // real timing). Completed entries stay visible as history — they are never
  // auto-removed or progress-faked.
  const agentId = `agent-${commandId}`
  addJarvisAgent({
    id: agentId,
    name: 'Jarvis task',
    type: 'custom',
    status: 'running',
    currentTask: input.slice(0, 120),
    startedAt,
    sessionId: undefined
  })

  const fail = (state: 'FAILED' | 'TIMEOUT' | 'UNAVAILABLE' | 'CANCELLED', error: string, intentType: string, plan?: ExecutionPlan): never => {
    setJarvisExecution({ state, error })
    updateJarvisAgent(agentId, { status: state === 'CANCELLED' ? 'idle' : 'error', currentTask: error.slice(0, 160) })
    appendJarvisCommandLog({
      id: commandId,
      timestamp: startedAt,
      sessionId: lastJarvisSessionId,
      input,
      inputType,
      intent: intentType,
      status: state,
      durationMs: Date.now() - startedAt,
      toolsUsed: [...lastJarvisTools],
      result: null,
      error
    })
    lastJarvisTools = []

    if (plan) {
      plan.status = 'failed'
      plan.endTime = Date.now()
    }

    addJarvisNotification({ title: 'Task Failed', message: error.slice(0, 160), type: 'error' })
    throw state === 'CANCELLED' ? new JarvisCancelledError() : new Error(error)
  }

  try {
    setJarvisExecution({ state: 'PARSING' })
    onThinkingStage('understanding', 'Analyzing intent and context...')
    const intent = analyzeIntent(input)
    throwIfCancelled()

    const reasoningContext = analyzeContext(intent)
    const suggestions = generateSuggestions(reasoningContext)

    setJarvisExecution({ state: 'PLANNING' })
    onThinkingStage('planning', 'Creating execution plan...')
    const plan = createExecutionPlan(intent)

    for (const step of plan.steps) {
      onStepUpdate(step.id, step.status, 0)
    }

    throwIfCancelled()

    const gateway = activeGateway()

    if (!gateway || gateway.connectionState !== 'open') {
      setJarvisExecution({ state: 'UNAVAILABLE', error: 'Gateway is not connected.' })
      updateJarvisAgent(agentId, { status: 'error', currentTask: 'Gateway is not connected.' })
      appendJarvisCommandLog({
        id: commandId,
        timestamp: startedAt,
        sessionId: null,
        input,
        inputType,
        intent: intent.type,
        status: 'UNAVAILABLE',
        durationMs: Date.now() - startedAt,
        toolsUsed: [],
        result: null,
        error: 'Aetheros gateway is not connected. Check Gateway status and reconnect.'
      })
      throw new GatewayUnavailableError()
    }

    setJarvisExecution({ state: 'EXECUTING' })
    onThinkingStage('executing', 'Submitting to Aetheros gateway...')

    for (const step of plan.steps) {
      if (step.status !== 'completed') {
        step.status = 'running'
        onStepUpdate(step.id, 'running', 5)
      }
    }

    const created = await gateway.request<SessionCreateResponse>('session.create', { cols: 96 })
    const sessionId = created.session_id
    lastJarvisSessionId = sessionId
    updateJarvisAgent(agentId, { sessionId })
    setJarvisExecution({ state: 'EXECUTING', sessionId })

    const modelUsed = {
      provider: created.info?.provider ?? 'gateway',
      model: created.info?.model ?? 'default'
    }

    setJarvisExecution({ state: 'STREAMING' })
    onThinkingStage('executing', 'Agent is working — streaming live output...')

    const stream = await submitAndStream(gateway, sessionId, input, {
      onDelta: collected => {
        onThinkingStage('executing', collected.slice(-120) || 'Streaming agent output...')
      },
      // Every step transition below is a real gateway tool event — no timers,
      // no synthetic percentage ticks.
      onToolStart: tool => {
        opts.onToolEvent?.(tool, 'start')
        onThinkingStage('using-tools', `Using ${tool}...`)
        const active = plan.steps.find(s => s.status === 'running') ?? plan.steps.find(s => s.status !== 'completed')

        if (active) {
          active.status = 'running'
          active.progress = 50
          active.result = tool
          onStepUpdate(active.id, 'running', 50, tool)
        }
      },
      onToolComplete: tool => {
        opts.onToolEvent?.(tool, 'complete')
        const active = plan.steps.find(s => s.status === 'running')

        if (active) {
          active.status = 'completed'
          active.progress = 100
          active.endTime = Date.now()
          onStepUpdate(active.id, 'completed', 100, tool)
        }
      },
      onApproval: label => {
        onThinkingStage('executing', label)
      }
    })

    throwIfCancelled()

    for (const step of plan.steps) {
      step.status = 'completed'
      step.progress = 100
      step.endTime = Date.now()
      onStepUpdate(step.id, 'completed', 100, 'Done')
    }

    plan.status = 'completed'
    plan.endTime = Date.now()

    const validation = reflectOnExecution(plan)
    onThinkingStage('complete', 'Complete')

    const durationMs = Date.now() - startedAt
    setJarvisExecution({ state: 'COMPLETED', error: null })
    updateJarvisAgent(agentId, { status: 'completed', currentTask: 'Done' })
    appendJarvisCommandLog({
      id: commandId,
      timestamp: startedAt,
      sessionId,
      input,
      inputType,
      intent: intent.type,
      status: 'COMPLETED',
      durationMs,
      toolsUsed: [...stream.toolsUsed],
      result: stream.text.slice(0, 2000),
      error: null
    })
    lastJarvisTools = []

    addJarvisNotification({
      title: 'Task Complete',
      message: `Finished "${input.slice(0, 60)}" in ${(durationMs / 1000).toFixed(1)}s`,
      type: 'success'
    })

    return {
      plan,
      response: stream.text || '(The agent completed without text output.)',
      artifacts: [],
      memoryUpdates: [],
      reflection: validation,
      suggestions,
      modelUsed
    }
  } catch (err) {
    if (err instanceof GatewayUnavailableError || err instanceof JarvisCancelledError) {
      updateJarvisAgent(agentId, {
        status: err instanceof JarvisCancelledError ? 'idle' : 'error',
        currentTask: err.message.slice(0, 160)
      })
      throw err
    }

    const message = err instanceof Error ? err.message : String(err)

    if (/timed out|timeout/i.test(message)) {
      setJarvisExecution({ state: 'TIMEOUT', error: message })
      appendJarvisCommandLog({
        id: commandId, timestamp: startedAt, sessionId: lastJarvisSessionId, input,
        inputType, intent: 'unknown', status: 'TIMEOUT', durationMs: Date.now() - startedAt,
        toolsUsed: [...lastJarvisTools], result: null, error: message
      })
      lastJarvisTools = []
      throw new Error(message)
    }

    // Intent was parsed before the throw in most paths; keep honest accounting.
    return fail('FAILED', message || 'Command execution failed.', 'unknown')
  }
}

interface StreamResult {
  text: string
  toolsUsed: string[]
}

interface StreamCallbacks {
  onDelta: (collected: string) => void
  onToolStart: (tool: string) => void
  onToolComplete: (tool: string) => void
  onApproval: (label: string) => void
}

async function submitAndStream(
  gateway: NonNullable<ReturnType<typeof activeGateway>>,
  sessionId: string,
  text: string,
  cb: StreamCallbacks
): Promise<StreamResult> {
  let collected = ''
  const toolsUsed = new Set<string>()
  let settled = false

  return new Promise<StreamResult>((resolve, reject) => {
    const timer = setTimeout(() => {
      if (settled) {return}
      settled = true
      cleanup()
      setJarvisExecution({ state: 'TIMEOUT', error: 'Agent response timed out.' })
      reject(new Error(`Agent response timed out after ${Math.round(PIPELINE_TIMEOUT_MS / 1000)}s.`))
    }, PIPELINE_TIMEOUT_MS)

    const off = gateway.onEvent(event => {
      if (settled) {return}

      if (event.session_id && event.session_id !== sessionId) {return}
      const payload = (event.payload ?? {}) as Record<string, unknown>

      if (cancelRequested) {
        settled = true
        clearTimeout(timer)
        cleanup()
        setJarvisExecution({ state: 'CANCELLED', error: 'Command cancelled.' })
        reject(new JarvisCancelledError())

        return
      }

      if (event.type === 'message.delta' || event.type === 'thinking.delta' || event.type === 'reasoning.delta') {
        const delta = typeof payload.delta === 'string' ? payload.delta
          : typeof payload.text === 'string' ? payload.text : ''

        if (delta) {
          collected += delta
          cb.onDelta(collected)
        }
      } else if (event.type === 'tool.start') {
        const name = typeof payload.tool === 'string' ? payload.tool
          : typeof payload.name === 'string' ? payload.name : 'tool'

        toolsUsed.add(name)
        lastJarvisTools = [...toolsUsed]
        cb.onToolStart(name)
      } else if (event.type === 'tool.complete') {
        const name = typeof payload.tool === 'string' ? payload.tool : null

        if (name) {
          toolsUsed.add(name)
          cb.onToolComplete(name)
        }

        lastJarvisTools = [...toolsUsed]
      } else if (event.type === 'approval.request') {
        // Dangerous-command approval. The agent thread blocks until the user
        // responds via the shared approvals store — park it there (visible in
        // Security Center) and say so instead of stalling silently.
        const command = typeof payload.command === 'string' ? payload.command : ''
        const description = typeof payload.description === 'string' ? payload.description : 'dangerous command'
        setApprovalRequest({
          allowPermanent: payload.allow_permanent !== false,
          command,
          description,
          sessionId
        })
        lastJarvisTools = [...toolsUsed]
        cb.onApproval(`Waiting for your approval: ${command || description}`.slice(0, 140))
        addJarvisNotification({ title: 'Approval needed', message: (command || description).slice(0, 160), type: 'warning' })
      } else if (event.type === 'sudo.request') {
        const requestId = typeof payload.request_id === 'string' ? payload.request_id : ''

        if (requestId) {
          setSudoRequest({ requestId, sessionId })
          cb.onApproval('Waiting for sudo password...')
          addJarvisNotification({ title: 'Sudo password needed', message: 'The agent is waiting for your sudo password.', type: 'warning' })
        }
      } else if (event.type === 'secret.request') {
        const requestId = typeof payload.request_id === 'string' ? payload.request_id : ''

        if (requestId) {
          setSecretRequest({
            requestId,
            envVar: typeof payload.env_var === 'string' ? payload.env_var : '',
            prompt: typeof payload.prompt === 'string' ? payload.prompt : '',
            sessionId
          })
          cb.onApproval('Waiting for a credential...')
        }
      } else if (event.type === 'message.complete') {
        const finalText = typeof payload.text === 'string' && payload.text ? payload.text
          : typeof payload.message === 'string' && payload.message ? payload.message : collected

        if (finalText && !collected) {collected = finalText}
        settled = true
        clearTimeout(timer)
        cleanup()
        clearAllPrompts(sessionId)
        resolve({ text: collected, toolsUsed: [...toolsUsed] })
      } else if (event.type === 'error') {
        settled = true
        clearTimeout(timer)
        cleanup()
        clearAllPrompts(sessionId)
        const message = typeof payload.message === 'string' ? payload.message : 'Agent reported an error.'
        reject(new Error(message))
      }
    })

    const cleanup = () => {
      clearTimeout(timer)
      clearInterval(fallback)
      off()
    }

    // session.info running:false is the authoritative turn-end signal when the
    // backend sends no message.complete (e.g. tool-only turns). Poll it as a
    // fallback completion path.
    const fallback = setInterval(async () => {
      if (settled) {return}

      if (cancelRequested) {return}

      try {
        const info = await gateway.request<{ running?: boolean; last_message?: string }>('session.info', {
          session_id: sessionId
        })

        if (info && info.running === false && collected) {
          settled = true
          cleanup()
          resolve({ text: collected, toolsUsed: [...toolsUsed] })
        }
      } catch {
        // Ignore — the event path remains authoritative.
      }
    }, 3000)

    gateway.request('prompt.submit', { session_id: sessionId, text }).catch(err => {
      if (settled) {return}
      settled = true
      cleanup()
      reject(err instanceof Error ? err : new Error(String(err)))
    })
  })
}
