import { addHistoryEntry } from '@/store/command-center'
import type { AIAction, CommandMatch } from '@/store/command-center'

export interface VoiceCommand {
  phrase: string
  action: string
  params?: Record<string, string>
  confidence: number
}

const COMMAND_PATTERNS: { pattern: RegExp; actionId: string; extractParams?: (match: RegExpMatchArray) => Record<string, string> }[] = [
  { pattern: /^(?:open|launch|start)\s+(.+)/i, actionId: 'open-project', extractParams: (m) => ({ project: m[1] }) },
  { pattern: /^summarize\s+(?:this|document|the)/i, actionId: 'summarize-document' },
  { pattern: /^translate\s+(?:clipboard|this)/i, actionId: 'translate-clipboard' },
  { pattern: /^generate\s+code/i, actionId: 'generate-code' },
  { pattern: /^explain\s+(?:error|this)/i, actionId: 'explain-error' },
  { pattern: /^create\s+(?:task|todo)/i, actionId: 'create-task' },
  { pattern: /^search\s+(?:knowledge|for)\s+(.+)/i, actionId: 'search-knowledge', extractParams: (m) => ({ query: m[1] }) },
  { pattern: /^run\s+(?:workflow|automation)/i, actionId: 'run-workflow' },
  { pattern: /^(?:new|start)\s+(?:chat|conversation)/i, actionId: 'new-chat' },
  { pattern: /^(?:toggle|switch)\s+(?:dark|light|theme)/i, actionId: 'toggle-dark-mode' },
  { pattern: /^(?:open|show)\s+settings/i, actionId: 'open-settings' },
]

export function matchCommand(input: string, actions: AIAction[]): CommandMatch | null {
  const trimmed = input.trim().toLowerCase()

  for (const cp of COMMAND_PATTERNS) {
    const match = trimmed.match(cp.pattern)

    if (match) {
      const action = actions.find(a => a.id === cp.actionId)

      if (action) {
        return {
          action,
          confidence: 0.9,
          source: 'voice',
          input
        }
      }
    }
  }

  for (const action of actions) {
    if (!action.enabled) {continue}
    const keywords = action.command.toLowerCase().split(/\s+/)
    const matchCount = keywords.filter(k => trimmed.includes(k)).length

    if (matchCount === keywords.length) {
      return { action, confidence: 0.7, source: 'voice', input }
    }
  }

  return null
}

export function processVoiceCommand(input: string, actions: AIAction[]): CommandMatch | null {
  const match = matchCommand(input, actions)

  if (match) {
    const startTime = performance.now()
    addHistoryEntry({
      id: `cmd-${Date.now()}`,
      action: match.action.name,
      input,
      source: 'voice',
      status: 'executing',
      result: null,
      timestamp: Date.now(),
      durationMs: 0
    })

    return match
  }

  return null
}

export function getNaturalLanguageResponse(command: CommandMatch): string {
  const responses: Record<string, string> = {
    'open-project': 'Opening project...',
    'summarize-document': 'Summarizing the current document...',
    'translate-clipboard': 'Translating clipboard content...',
    'generate-code': 'Opening code generator...',
    'explain-error': 'Analyzing the current error...',
    'create-task': 'Creating a new task...',
    'search-knowledge': 'Searching knowledge base...',
    'run-workflow': 'Preparing to run workflow...',
    'launch-automation': 'Launching automation...',
    'open-settings': 'Opening settings...',
    'new-chat': 'Starting a new chat...',
    'toggle-dark-mode': 'Toggling theme...'
  }

  return responses[command.action.id] || `Executing ${command.action.name}...`
}
