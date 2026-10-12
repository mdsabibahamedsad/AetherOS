import { getContext } from './context'
import type { ObserverEvent } from './observer'

export interface ReasoningResult {
  trigger: string
  confidence: number
  suggestions: ReasoningSuggestion[]
  context: string
}

export interface ReasoningSuggestion {
  type: 'action' | 'information' | 'warning' | 'question' | 'automation'
  title: string
  description: string
  priority: 'low' | 'medium' | 'high'
  action?: string
}

type ReasoningRule = {
  match: (event: ObserverEvent, ctx: ReturnType<typeof getContext>) => boolean
  generate: (event: ObserverEvent, ctx: ReturnType<typeof getContext>) => ReasoningSuggestion[]
}

const rules: ReasoningRule[] = [
  {
    match: e => e.type === 'clipboard:copy' && typeof e.data?.text === 'string' && ((e.data.text as string).includes('def ') || (e.data.text as string).includes('function ')),
    generate: (e, ctx) => [{
      type: 'information',
      title: 'Code detected in clipboard',
      description: 'Would you like me to explain or improve this code?',
      priority: 'low',
      action: 'explain_clipboard'
    }]
  },
  {
    match: e => e.type === 'project:detected',
    generate: (e, ctx) => [{
      type: 'action',
      title: `Project detected: ${e.data?.name ?? 'Unknown'}`,
      description: 'I can analyze the architecture, find bugs, or run the project.',
      priority: 'medium',
      action: 'analyze_project'
    }]
  },
  {
    match: e => e.type === 'git:commit',
    generate: (e, ctx) => [{
      type: 'action',
      title: 'New commit detected',
      description: 'Review the commit for potential issues?',
      priority: 'high',
      action: 'review_commit'
    }]
  },
  {
    match: e => e.type === 'error:occurred',
    generate: (e, ctx) => [{
      type: 'warning',
      title: 'Error detected',
      description: `${e.data?.message ?? 'An error occurred'}. I can help diagnose and fix it.`,
      priority: 'high',
      action: 'diagnose_error'
    }]
  },
  {
    match: e => e.type === 'terminal:command' && (e.data?.command as string ?? '').includes('error') || (e.data?.command as string ?? '').includes('fail'),
    generate: (e, ctx) => [{
      type: 'warning',
      title: 'Terminal error detected',
      description: 'It looks like a command failed. Need help debugging?',
      priority: 'high',
      action: 'debug_terminal'
    }]
  },
  {
    match: e => e.type === 'user:idle' && e.data != null && (e.data.duration as number) > 300_000,
    generate: (e, ctx) => {
      const suggestions: ReasoningSuggestion[] = []

      if (ctx.currentProject) {
        suggestions.push({
          type: 'action',
          title: 'Project idle for a while',
          description: 'I can run tests, check for updates, or optimize the codebase.',
          priority: 'medium',
          action: 'optimize_project'
        })
      }

      return suggestions
    }
  },
  {
    match: e => e.type === 'task:failed',
    generate: (e, ctx) => [{
      type: 'warning',
      title: 'Task failed',
      description: `${e.data?.taskName ?? 'A task'} failed. I can retry with adjustments.`,
      priority: 'high',
      action: 'retry_task'
    }]
  },
  {
    match: e => e.type === 'system:resource-high',
    generate: (e, ctx) => [{
      type: 'warning',
      title: 'High resource usage',
      description: `CPU: ${e.data?.cpu ?? '?'}%, RAM: ${e.data?.memory ?? '?'}%. I can optimize or suggest cleanup.`,
      priority: 'medium',
      action: 'optimize_resources'
    }]
  },
  {
    match: e => e.type === 'browser:url-change',
    generate: (e, ctx) => {
      const url = e.data?.url as string ?? ''

      if (url.includes('github.com')) {
        return [{
          type: 'automation',
          title: 'GitHub detected',
          description: 'I can review PRs, check issues, or browse the repository.',
          priority: 'low',
          action: 'github_assist'
        }]
      }

      return []
    }
  },
  {
    match: e => e.type === 'app:focus' && (e.data?.app as string ?? '').toLowerCase().includes('code'),
    generate: (e, ctx) => {
      if (ctx.currentProject) {
        return [{
          type: 'information',
          title: 'Working in VS Code',
          description: `I can help with ${ctx.currentProject}. Need tests, refactoring, or documentation?`,
          priority: 'low',
          action: 'code_assist'
        }]
      }

      return []
    }
  }
]

export function reason(event: ObserverEvent): ReasoningResult | null {
  const ctx = getContext()
  const matchedSuggestions: ReasoningSuggestion[] = []

  for (const rule of rules) {
    try {
      if (rule.match(event, ctx)) {
        matchedSuggestions.push(...rule.generate(event, ctx))
      }
    } catch { /* rule error */ }
  }

  if (matchedSuggestions.length === 0) {return null}

  const best = matchedSuggestions.sort((a, b) => {
    const p = { high: 3, medium: 2, low: 1 }

    return p[b.priority] - p[a.priority]
  })

  return {
    trigger: event.type,
    confidence: 0.7 + Math.random() * 0.2,
    suggestions: best.slice(0, 3),
    context: ctx.currentProject ?? 'general'
  }
}

export function getReasoningRules(): { active: number; total: number } {
  return { active: rules.length, total: rules.length }
}
