import { addJarvisNotification } from '@/store/jarvis-mode'

// ─── Automation Rules ─────────────────────────────────────────────────────────

export interface AutomationTrigger {
  type: 'schedule' | 'event' | 'threshold' | 'webhook' | 'command'
  config: Record<string, unknown>
}

export interface AutomationAction {
  type: 'prompt' | 'notify' | 'exec' | 'email' | 'webhook'
  config: Record<string, unknown>
}

export interface AutomationRule {
  id: string
  name: string
  description: string
  enabled: boolean
  trigger: AutomationTrigger
  actions: AutomationAction[]
  lastRun?: number
  runCount: number
  createdAt: number
}

const rules = new Map<string, AutomationRule>()
let ruleCounter = 0

// ─── Rule Management ──────────────────────────────────────────────────────────

export function createRule(config: {
  name: string
  description: string
  trigger: AutomationTrigger
  actions: AutomationAction[]
}): AutomationRule {
  const rule: AutomationRule = {
    id: `auto-${++ruleCounter}`,
    name: config.name,
    description: config.description,
    enabled: true,
    trigger: config.trigger,
    actions: config.actions,
    runCount: 0,
    createdAt: Date.now()
  }

  rules.set(rule.id, rule)

  return rule
}

export function updateRule(id: string, updates: Partial<Pick<AutomationRule, 'enabled' | 'name' | 'description' | 'trigger' | 'actions'>>) {
  const rule = rules.get(id)

  if (!rule) {return null}
  Object.assign(rule, updates)

  return rule
}

export function deleteRule(id: string): boolean {
  return rules.delete(id)
}

export function getRule(id: string): AutomationRule | undefined {
  return rules.get(id)
}

export function listRules(): AutomationRule[] {
  return Array.from(rules.values())
}

// ─── Rule Execution ───────────────────────────────────────────────────────────

export async function executeRule(id: string) {
  const rule = rules.get(id)

  if (!rule || !rule.enabled) {return}

  rule.lastRun = Date.now()
  rule.runCount++

  for (const action of rule.actions) {
    try {
      await executeAction(action)
    } catch (err) {
      addJarvisNotification({
        title: 'Automation Error',
        message: `Rule "${rule.name}" action failed: ${err}`,
        type: 'error'
      })
    }
  }
}

async function executeAction(action: AutomationAction) {
  switch (action.type) {
    case 'notify':
      addJarvisNotification({
        title: (action.config.title as string) ?? 'Automation',
        message: (action.config.message as string) ?? 'Notification from automation rule',
        type: 'info'
      })

      break

    case 'prompt':
      // Would submit to the AI pipeline
      break

    case 'exec':
      // Would execute shell command
      break
  }
}

// ─── Natural Language Rule Parsing ────────────────────────────────────────────

export function parseNaturalLanguageRule(input: string): Partial<AutomationRule> | null {
  const lower = input.toLowerCase()

  // Schedule patterns
  const scheduleMatch = lower.match(/every\s+(morning|evening|hour|day|week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)/i)

  if (scheduleMatch) {
    const freq = scheduleMatch[1]

    return {
      name: `Scheduled: ${freq}`,
      trigger: { type: 'schedule', config: { frequency: freq } },
      actions: [{ type: 'prompt', config: { message: input } }]
    }
  }

  // Threshold patterns
  const thresholdMatch = lower.match(/(?:if|when|notify).*?(cpu|ram|memory|disk|gpu).*?(exceed|above|over|greater)\s*(\d+)/i)

  if (thresholdMatch) {
    return {
      name: `Monitor: ${thresholdMatch[1]}`,
      trigger: { type: 'threshold', config: { metric: thresholdMatch[1], operator: '>', value: parseInt(thresholdMatch[3]) } },
      actions: [{ type: 'notify', config: { title: 'Threshold Alert', message: `${thresholdMatch[1]} exceeded ${thresholdMatch[3]}%` } }]
    }
  }

  // Watch patterns
  const watchMatch = lower.match(/watch\s+(this\s+)?(folder|file|website|server|logs)/i)

  if (watchMatch) {
    return {
      name: `Watch: ${watchMatch[2]}`,
      trigger: { type: 'event', config: { target: watchMatch[2] } },
      actions: [{ type: 'notify', config: { title: 'Change Detected', message: `Change detected in ${watchMatch[2]}` } }]
    }
  }

  // Email patterns
  const emailMatch = lower.match(/email\s+me\s+(?:every|on)\s+(.+)/i)

  if (emailMatch) {
    return {
      name: `Email: ${emailMatch[1]}`,
      trigger: { type: 'schedule', config: { frequency: emailMatch[1] } },
      actions: [{ type: 'email', config: { subject: 'Scheduled Report', body: input } }]
    }
  }

  return null
}

// ─── Initialize with Common Rules ─────────────────────────────────────────────

export function initializeAutomation() {
  createRule({
    name: 'Health Check',
    description: 'Monitor system health every 5 minutes',
    trigger: { type: 'schedule', config: { interval: 300000 } },
    actions: [{ type: 'exec', config: { command: 'health-check' } }]
  })

  createRule({
    name: 'Memory Cleanup',
    description: 'Clean old memory entries daily',
    trigger: { type: 'schedule', config: { frequency: 'daily' } },
    actions: [{ type: 'exec', config: { command: 'memory-cleanup' } }]
  })
}
