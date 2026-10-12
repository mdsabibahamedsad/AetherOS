import { atom, computed } from 'nanostores'

export interface TerminalSession {
  id: string
  name: string
  cwd: string
  command: string
  status: 'running' | 'completed' | 'failed'
  outputLines: number
  startedAt: number
}

export interface TerminalReplacementState {
  sessions: TerminalSession[]
  activeSessionId: string
  showTerminal: boolean
  terminalHeight: number
}

export const $terminalReplacement = atom<TerminalReplacementState>({
  sessions: [],
  activeSessionId: '',
  showTerminal: false,
  terminalHeight: 200,
})

export const $activeTerminal = computed($terminalReplacement, (s) => s.sessions.find(t => t.id === s.activeSessionId) ?? null)

export function addTerminalSession(session: TerminalSession) {
  const state = $terminalReplacement.get()
  $terminalReplacement.set({ ...state, sessions: [...state.sessions, session], activeSessionId: session.id })
}

export function setActiveTerminal(sessionId: string) {
  const state = $terminalReplacement.get()
  $terminalReplacement.set({ ...state, activeSessionId: sessionId })
}

export function removeTerminalSession(sessionId: string) {
  const state = $terminalReplacement.get()
  const sessions = state.sessions.filter(s => s.id !== sessionId)
  $terminalReplacement.set({
    ...state, sessions,
    activeSessionId: state.activeSessionId === sessionId ? (sessions[0]?.id ?? '') : state.activeSessionId,
  })
}

export function toggleTerminal() {
  const state = $terminalReplacement.get()
  $terminalReplacement.set({ ...state, showTerminal: !state.showTerminal })
}

export function setTerminalHeight(height: number) {
  const state = $terminalReplacement.get()
  $terminalReplacement.set({ ...state, terminalHeight: height })
}
