import { searchMemory } from '../memory/memory-graph'
import type { ExecutionPlan, ExecutionPlanStep, Intent } from '../types'
import { getWorkspaceContext } from '../workspace/workspace-awareness'

export interface ReasoningContext {
  intent: Intent
  plan: ExecutionPlan
  memoryHits: number
  workspaceContext: string
  currentStep: string | null
  previousErrors: string[]
  conversationHistory: string[]
}

export interface ReasoningSuggestion {
  type: 'optimization' | 'warning' | 'insight' | 'alternative'
  message: string
  confidence: number
}

export function analyzeContext(intent: Intent): ReasoningContext {
  const memoryResults = searchMemory(intent.type, 5)
  const workspaceCtx = getWorkspaceContext()
  const ctxParts: string[] = []

  if (workspaceCtx.cwd) {ctxParts.push(`cwd: ${workspaceCtx.cwd}`)}

  if (workspaceCtx.gitRoot) {ctxParts.push(`git: ${workspaceCtx.gitRoot}`)}

  if (workspaceCtx.branch) {ctxParts.push(`branch: ${workspaceCtx.branch}`)}

  return {
    intent,
    plan: null as any,
    memoryHits: memoryResults.length,
    workspaceContext: ctxParts.join(', '),
    currentStep: null,
    previousErrors: [],
    conversationHistory: []
  }
}

export function generateSuggestions(context: ReasoningContext): ReasoningSuggestion[] {
  const suggestions: ReasoningSuggestion[] = []

  if (context.memoryHits > 0) {
    suggestions.push({
      type: 'insight',
      message: `Found ${context.memoryHits} relevant memories from previous sessions`,
      confidence: 0.8
    })
  }

  if (context.intent.type === 'code' && context.workspaceContext) {
    suggestions.push({
      type: 'optimization',
      message: 'Workspace context detected — using existing project structure',
      confidence: 0.9
    })
  }

  if (context.previousErrors.length > 0) {
    suggestions.push({
      type: 'warning',
      message: `${context.previousErrors.length} previous errors detected — applying learned patterns`,
      confidence: 0.7
    })
  }

  if (context.intent.type === 'research') {
    suggestions.push({
      type: 'insight',
      message: 'Research task detected — will cross-reference multiple sources',
      confidence: 0.85
    })
  }

  return suggestions
}

export function validateStep(step: ExecutionPlanStep, result?: string): { valid: boolean; issues: string[] } {
  const issues: string[] = []

  if (step.status === 'failed' && step.error) {
    issues.push(step.error)
  }

  if (step.status === 'completed' && !result && step.tools.length > 0) {
    issues.push('Step completed but no result was produced')
  }

  if (step.progress < 100 && step.status === 'completed') {
    issues.push('Step marked complete before reaching 100% progress')
  }

  return { valid: issues.length === 0, issues }
}

export function reflectOnExecution(plan: ExecutionPlan): {
  passed: number
  failed: number
  warnings: string[]
  improvements: string[]
} {
  const failed = plan.steps.filter(s => s.status === 'failed')
  const passed = plan.steps.filter(s => s.status === 'completed')
  const warnings: string[] = []
  const improvements: string[] = []

  if (failed.length > 0) {
    warnings.push(`${failed.length} step(s) failed during execution`)
    failed.forEach(f => improvements.push(`Retry step "${f.label}" with different approach`))
  }

  const totalTime = plan.endTime ? plan.endTime - plan.startTime : Date.now() - plan.startTime

  if (totalTime > 30000) {
    improvements.push('Execution took longer than expected — consider parallel execution')
  }

  return {
    passed: passed.length,
    failed: failed.length,
    warnings,
    improvements
  }
}

export function generateSmartSuggestion(intent: Intent): string {
  const ctx = analyzeContext(intent)
  const suggestions = generateSuggestions(ctx)

  if (suggestions.length > 0) {
    return suggestions[0].message
  }

  return ''
}
