import { atom, computed } from 'nanostores'

export interface Breakpoint {
  id: string
  file: string
  line: number
  condition: string
  enabled: boolean
  hitCount: number
}

export interface StackFrame {
  id: string
  name: string
  file: string
  line: number
  column: number
}

export interface DebugVariable {
  name: string
  value: string
  type: string
  reference: number
  children?: DebugVariable[]
}

export interface DebuggerState {
  isRunning: boolean
  isPaused: boolean
  sessionId: string
  program: string
  language: string
  breakpoints: Breakpoint[]
  stackFrames: StackFrame[]
  variables: DebugVariable[]
  watches: Array<{ expression: string; value: string }>
  exception: { message: string; file: string; line: number } | null
  output: string[]
}

export const $debugger = atom<DebuggerState>({
  isRunning: false,
  isPaused: false,
  sessionId: '',
  program: '',
  language: '',
  breakpoints: [],
  stackFrames: [],
  variables: [],
  watches: [],
  exception: null,
  output: [],
})

export const $breakpoints = computed($debugger, (s) => s.breakpoints)
export const $currentStackFrame = computed($debugger, (s) => s.stackFrames[0] ?? null)
export const $debugStatus = computed($debugger, (s) => s.isPaused ? 'paused' : s.isRunning ? 'running' : 'stopped')

export function setDebugSession(sessionId: string, program: string, language: string) {
  const state = $debugger.get()
  $debugger.set({ ...state, sessionId, program, language, isRunning: true, isPaused: false, output: [] })
}

export function addBreakpoint(bp: Breakpoint) {
  const state = $debugger.get()
  $debugger.set({ ...state, breakpoints: [...state.breakpoints, bp] })
}

export function removeBreakpoint(breakpointId: string) {
  const state = $debugger.get()
  $debugger.set({ ...state, breakpoints: state.breakpoints.filter(b => b.id !== breakpointId) })
}

export function toggleBreakpoint(breakpointId: string) {
  const state = $debugger.get()
  const breakpoints = state.breakpoints.map(b => b.id === breakpointId ? { ...b, enabled: !b.enabled } : b)
  $debugger.set({ ...state, breakpoints })
}

export function updateStack(stack: StackFrame[]) {
  const state = $debugger.get()
  $debugger.set({ ...state, stackFrames: stack })
}

export function updateVariables(variables: DebugVariable[]) {
  const state = $debugger.get()
  $debugger.set({ ...state, variables })
}

export function addWatch(expression: string) {
  const state = $debugger.get()
  $debugger.set({ ...state, watches: [...state.watches, { expression, value: '' }] })
}

export function removeWatch(index: number) {
  const state = $debugger.get()
  const watches = state.watches.filter((_, i) => i !== index)
  $debugger.set({ ...state, watches })
}

export function updateWatchValue(index: number, value: string) {
  const state = $debugger.get()
  const watches = state.watches.map((w, i) => i === index ? { ...w, value } : w)
  $debugger.set({ ...state, watches })
}

export function setException(exception: { message: string; file: string; line: number } | null) {
  const state = $debugger.get()
  $debugger.set({ ...state, exception })
}

export function addDebugOutput(line: string) {
  const state = $debugger.get()
  $debugger.set({ ...state, output: [...state.output, line] })
}

export function pauseDebugger() {
  const state = $debugger.get()
  $debugger.set({ ...state, isPaused: true })
}

export function resumeDebugger() {
  const state = $debugger.get()
  $debugger.set({ ...state, isPaused: false })
}

export function endDebugSession() {
  $debugger.set({
    isRunning: false, isPaused: false, sessionId: '', program: '', language: '',
    breakpoints: [], stackFrames: [], variables: [], watches: [], exception: null, output: [],
  })
}
