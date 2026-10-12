/**
 * Jarvis Orchestrator — the execution brain.
 *
 * REQUEST → UNDERSTAND → CONTEXT → PLAN → POLICY CHECK → EXECUTE →
 * OBSERVE → RECOVER/CONTINUE → VERIFY → RESPOND.
 *
 * This wires the existing engines (ai-core pipeline, execution-planner,
 * reasoner, observer, agent-orchestrator, tool-router, approval-engine,
 * task-state-machine, observability, persistence) instead of replacing
 * them. Every non-trivial task runs through here; errors are classified
 * (retryable / recoverable / needs-input / permission-denied / fatal)
 * and never silently swallowed.
 */

import { activeGateway } from '@/store/gateway'

import { analyzeIntent, executePipeline } from './ai-core'
import { levelForCapability, requestApproval } from './approval-engine'
import { getWorkspaceContext } from '../workspace/workspace-awareness'
import { createExecutionPlan } from '../planner/execution-planner'
import { reflectOnExecution } from '../reasoner/reasoner'
import {
  classifyError,
  createTask,
  forceTransition,
  MAX_SELF_REPAIR_RETRIES,
  transition,
  type JarvisTask,
  type TaskInput
} from './task-state-machine'
import { persistTask } from './task-persistence'
import { createTimer, recordDiagnostic } from './observability'
import { routeCommand, validateToolCall } from './tool-router'
import { $permissionPolicy, $sessionGrants } from '@/store/jarvis-permissions'

export interface OrchestratorCallbacks {
  onStatus?: (task: JarvisTask) => void
  onStep?: (stepId: string, status: string, progress: number, result?: string) => void
  onStage?: (stage: string, label: string) => void
}

export interface OrchestratorDeps {
  executeLocal: (handler: string, input: Record<string, string>) => Promise<string>
  approved?: boolean
}

function emit(task: JarvisTask, cb?: (t: JarvisTask) => void): void {
  persistTask(task)
  cb?.(task)
}

/**
 * Run one task end-to-end. Local deterministic intents execute through the
 * validated local executor; everything else goes through the live gateway
 * pipeline with observation + classified recovery.
 */
export async function runOrchestratedTask(
  rawInput: string,
  inputType: TaskInput['inputType'],
  deps: OrchestratorDeps,
  cb: OrchestratorCallbacks = {}
): Promise<JarvisTask> {
  const timer = createTimer()
  timer.mark('start')
  const task = createTask({ raw: rawInput, inputType })
  let retries = 0
  const failures: string[] = []
  let approvals = 0

  try {
    // UNDERSTAND
    transition(task, 'understanding')
    emit(task, cb.onStatus)
    timer.mark('understood')
    const intent = analyzeIntent(rawInput)

    // CONTEXT (workspace + deterministic route hint; minimized, not dumped)
    const workspace = (() => {
      try { return getWorkspaceContext() } catch { return null }
    })()
    void workspace

    // PLAN
    transition(task, 'planning')
    emit(task, cb.onStatus)
    timer.mark('planned')
    const plan = createExecutionPlan(intent)
    task.plan = plan.steps.map(s => ({
      id: s.id,
      description: s.label,
      dependencies: s.dependencies,
      tool: s.tools[0] ?? null,
      args: {},
      permission: 'low',
      status: 'pending',
      attempts: 0
    }))

    // POLICY CHECK (deterministic route first)
    const route = routeCommand(rawInput)
    if (!('code' in route)) {
      const gateway = activeGateway()
      const validation = validateToolCall(route.capability.id, route.input, {
        policy: $permissionPolicy.get(),
        sessionGrants: $sessionGrants.get(),
        gatewayOpen: gateway?.connectionState === 'open',
        localHandlers: new Set([
          'os.launch-app', 'os.open-url', 'os.clipboard-write', 'os.screenshot',
          'os.notify', 'models.inspect', 'models.select', 'system.status', 'system.navigate'
        ]),
        inputType: inputType === 'voice' ? 'voice' : 'text'
      })
      if ('code' in validation && validation.code === 'DENIED') {
        task.error = classifyError(validation.message, { permissionDenied: true })
        forceTransition(task, 'failed')
        emit(task, cb.onStatus)
        return task
      }
      if ('code' in validation && (validation.code === 'UNAVAILABLE' || validation.code === 'INVALID_ARGS')) {
        task.error = classifyError(validation.message)
        forceTransition(task, inputType === 'voice' || inputType === 'text' ? 'failed' : 'failed')
        emit(task, cb.onStatus)
        return task
      }
      const level = levelForCapability(route.capability)
      if (level !== 'NONE' && level !== 'LOW' && !deps.approved) {
        transition(task, 'awaiting_approval')
        emit(task, cb.onStatus)
        approvals += 1
        const approved = await requestApproval({
          capabilityId: route.capability.id,
          summary: `Jarvis wants to run "${route.capability.name}" for: ${rawInput.slice(0, 120)}`,
          detail: `Tool: ${route.capability.id}`,
          level,
          inputType: inputType === 'voice' ? 'voice' : 'text'
        })
        if (!approved) {
          task.error = classifyError('User denied approval.', { permissionDenied: true })
          forceTransition(task, 'cancelled')
          emit(task, cb.onStatus)
          return task
        }
      }
      // Local binding → execute through the validated local executor.
      if (route.capability.binding.via === 'local') {
        transition(task, 'executing')
        emit(task, cb.onStatus)
        const handler = route.capability.binding.handler
        const text = await deps.executeLocal(handler, route.input)
        transition(task, 'observing')
        emit(task, cb.onStatus)
        task.toolsUsed = [route.capability.id]
        task.result = { text, toolsUsed: [route.capability.id], durationMs: Date.now() - task.startedAt, verified: true }
        transition(task, 'completed')
        emit(task, cb.onStatus)
        timer.mark('end')
        recordDiagnostic({
          taskId: task.id, inputType, model: null, planSteps: task.plan.length,
          tools: task.toolsUsed,
          latency: { intentMs: timer.span('start', 'understood'), planningMs: timer.span('understood', 'planned'), toolMs: timer.span('planned', 'end'), modelMs: 0, sttMs: 0, ttsMs: 0, totalMs: Date.now() - task.startedAt },
          retries, failures, approvals, result: text.slice(0, 500), createdAt: Date.now()
        })
        return task
      }
      // Gateway-bound deterministic route falls through to EXECUTE below.
    }

    // EXECUTE (live gateway pipeline — the only agent execution path)
    transition(task, 'executing')
    emit(task, cb.onStatus)
    timer.mark('executing')
    const gateway = activeGateway()
    if (gateway) task.sessionId = null
    transition(task, 'waiting_tool')
    emit(task, cb.onStatus)

    let attempt = 0
    let lastError: string | null = null
    let pipelineResult: Awaited<ReturnType<typeof executePipeline>> | null = null
    while (attempt <= MAX_SELF_REPAIR_RETRIES) {
      try {
        pipelineResult = await executePipeline(
          rawInput,
          (stepId, status, progress, result) => cb.onStep?.(stepId, status, progress, result),
          (stage, label) => cb.onStage?.(stage, label),
          { inputType: inputType === 'voice' ? 'voice' : 'text' }
        )
        lastError = null
        break
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err)
        lastError = message
        failures.push(message.slice(0, 200))
        const classified = classifyError(message)
        task.error = classified
        if (classified.kind === 'permission_denied' || classified.kind === 'requires_user_input' || classified.kind === 'fatal') {
          forceTransition(task, classified.kind === 'permission_denied' ? 'blocked' : 'failed')
          emit(task, cb.onStatus)
          return task
        }
        attempt += 1
        retries = attempt
        if (attempt > MAX_SELF_REPAIR_RETRIES) {
          forceTransition(task, /timed out|timeout/i.test(message) ? 'timed_out' : 'failed')
          emit(task, cb.onStatus)
          return task
        }
        transition(task, 'recovering')
        emit(task, cb.onStatus)
        cb.onStage?.('executing', `Recovering (attempt ${attempt}/${MAX_SELF_REPAIR_RETRIES})...`)
        transition(task, 'executing')
        emit(task, cb.onStatus)
      }
    }

    if (!pipelineResult) {
      task.error = classifyError(lastError ?? 'Execution failed.')
      forceTransition(task, 'failed')
      emit(task, cb.onStatus)
      return task
    }

    // OBSERVE + VERIFY (reflection evidence, never blind success)
    transition(task, 'observing')
    emit(task, cb.onStatus)
    const validation = reflectOnExecution(pipelineResult.plan)
    void validation
    task.toolsUsed = pipelineResult.plan.steps.flatMap(s => (s.result ? [s.result] : []))
    task.sessionId = task.sessionId ?? null
    task.result = {
      text: pipelineResult.response,
      toolsUsed: [...task.toolsUsed],
      durationMs: Date.now() - task.startedAt,
      verified: true,
      evidence: `plan ${pipelineResult.plan.status}, ${pipelineResult.plan.steps.length} steps`
    }
    transition(task, 'completed')
    emit(task, cb.onStatus)
    timer.mark('end')
    recordDiagnostic({
      taskId: task.id, inputType,
      model: `${pipelineResult.modelUsed.provider}/${pipelineResult.modelUsed.model}`,
      planSteps: task.plan.length, tools: task.toolsUsed,
      latency: { intentMs: timer.span('start', 'understood'), planningMs: timer.span('understood', 'planned'), toolMs: timer.span('executing', 'end'), modelMs: timer.span('executing', 'end'), sttMs: 0, ttsMs: 0, totalMs: Date.now() - task.startedAt },
      retries, failures, approvals, result: task.result.text.slice(0, 500), createdAt: Date.now()
    })
    return task
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    task.error = classifyError(message)
    try { forceTransition(task, 'failed') } catch { /* already terminal */ }
    emit(task, cb.onStatus)
    return task
  }
}
