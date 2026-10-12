import { atom } from 'nanostores'

export type CommandSource = 'voice' | 'keyboard' | 'mouse' | 'menu' | 'shortcut'
export type CommandStatus = 'pending' | 'executing' | 'completed' | 'failed'

export interface AIAction {
  id: string
  name: string
  description: string
  category: 'project' | 'document' | 'code' | 'search' | 'automation' | 'utility' | 'custom'
  icon: string
  command: string
  shortcut: string
  requiresConfirmation: boolean
  enabled: boolean
}

export interface CommandMatch {
  action: AIAction
  confidence: number
  source: CommandSource
  input: string
}

export interface CommandHistoryEntry {
  id: string
  action: string
  input: string
  source: CommandSource
  status: CommandStatus
  result: string | null
  timestamp: number
  durationMs: number
}

export interface CommandCenterState {
  isOpen: boolean
  query: string
  matches: CommandMatch[]
  actions: AIAction[]
  history: CommandHistoryEntry[]
  activeCommand: CommandMatch | null
  voiceCommandEnabled: boolean
  keyboardShortcutsEnabled: boolean
  naturalLanguageEnabled: boolean
  customCommandsEnabled: boolean
  recentCommands: string[]
  learningMode: boolean
}

export const $commandCenter = atom<CommandCenterState>({
  isOpen: false,
  query: '',
  matches: [],
  actions: [],
  history: [],
  activeCommand: null,
  voiceCommandEnabled: true,
  keyboardShortcutsEnabled: true,
  naturalLanguageEnabled: true,
  customCommandsEnabled: true,
  recentCommands: [],
  learningMode: false
})

const patch = (u: Partial<CommandCenterState>) =>
  $commandCenter.set({ ...$commandCenter.get(), ...u })

export function setIsOpen(o: boolean) { patch({ isOpen: o }) }

export function setQuery(q: string) { patch({ query: q }) }

export function setMatches(m: CommandMatch[]) { patch({ matches: m }) }

export function setActions(a: AIAction[]) { patch({ actions: a }) }

export function addHistoryEntry(e: CommandHistoryEntry) { patch({ history: [...$commandCenter.get().history, e] }) }

export function setActiveCommand(c: CommandMatch | null) { patch({ activeCommand: c }) }

export function setVoiceCommandEnabled(e: boolean) { patch({ voiceCommandEnabled: e }) }

export function setKeyboardShortcutsEnabled(e: boolean) { patch({ keyboardShortcutsEnabled: e }) }

export function setNaturalLanguageEnabled(e: boolean) { patch({ naturalLanguageEnabled: e }) }

export function setCustomCommandsEnabled(e: boolean) { patch({ customCommandsEnabled: e }) }

export function addRecentCommand(c: string) {
  const recent = $commandCenter.get().recentCommands
  patch({ recentCommands: [c, ...recent.filter(r => r !== c)].slice(0, 20) })
}

export function setLearningMode(l: boolean) { patch({ learningMode: l }) }

export const DEFAULT_ACTIONS: AIAction[] = [
  { id: 'open-project', name: 'Open Project', description: 'Open a project or workspace', category: 'project', icon: 'folder', command: 'open project', shortcut: 'Ctrl+O', requiresConfirmation: false, enabled: true },
  { id: 'summarize-document', name: 'Summarize Document', description: 'Summarize the current document or selection', category: 'document', icon: 'file-text', command: 'summarize', shortcut: 'Ctrl+Shift+S', requiresConfirmation: false, enabled: true },
  { id: 'translate-clipboard', name: 'Translate Clipboard', description: 'Translate clipboard content', category: 'utility', icon: 'globe', command: 'translate clipboard', shortcut: 'Ctrl+Shift+T', requiresConfirmation: false, enabled: true },
  { id: 'generate-code', name: 'Generate Code', description: 'Generate code from description', category: 'code', icon: 'code', command: 'generate code', shortcut: 'Ctrl+Shift+G', requiresConfirmation: false, enabled: true },
  { id: 'explain-error', name: 'Explain Error', description: 'Explain the current error or exception', category: 'code', icon: 'alert-circle', command: 'explain error', shortcut: 'Ctrl+Shift+E', requiresConfirmation: false, enabled: true },
  { id: 'create-task', name: 'Create Task', description: 'Create a new task or todo', category: 'project', icon: 'check-square', command: 'create task', shortcut: 'Ctrl+Shift+N', requiresConfirmation: false, enabled: true },
  { id: 'search-knowledge', name: 'Search Knowledge', description: 'Search knowledge base and documentation', category: 'search', icon: 'search', command: 'search knowledge', shortcut: 'Ctrl+Shift+K', requiresConfirmation: false, enabled: true },
  { id: 'run-workflow', name: 'Run Workflow', description: 'Run an automation workflow', category: 'automation', icon: 'play', command: 'run workflow', shortcut: 'Ctrl+Shift+W', requiresConfirmation: true, enabled: true },
  { id: 'launch-automation', name: 'Launch Automation', description: 'Launch a saved automation', category: 'automation', icon: 'zap', command: 'launch automation', shortcut: 'Ctrl+Shift+A', requiresConfirmation: true, enabled: true },
  { id: 'open-settings', name: 'Open Settings', description: 'Open AetherOS settings', category: 'utility', icon: 'settings', command: 'open settings', shortcut: 'Ctrl+,', requiresConfirmation: false, enabled: true },
  { id: 'new-chat', name: 'New Chat', description: 'Start a new chat session', category: 'utility', icon: 'message-square', command: 'new chat', shortcut: 'Ctrl+N', requiresConfirmation: false, enabled: true },
  { id: 'toggle-dark-mode', name: 'Toggle Dark Mode', description: 'Toggle between light and dark themes', category: 'utility', icon: 'moon', command: 'toggle theme', shortcut: 'Ctrl+Shift+D', requiresConfirmation: false, enabled: true },
]
