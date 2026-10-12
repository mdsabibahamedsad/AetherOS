import { atom } from 'nanostores'

export type LogSeverity = 'info' | 'warn' | 'error' | 'debug'
export type LogCategory = 'voice' | 'stt' | 'tts' | 'ocr' | 'screen' | 'camera' | 'performance'

export interface VoiceLogEntry {
  id: string
  timestamp: number
  category: LogCategory
  severity: LogSeverity
  message: string
  details?: Record<string, unknown>
  durationMs?: number
}

export interface VoiceLoggingState {
  entries: VoiceLogEntry[]
  enabled: boolean
  maxEntries: number
  filterCategory: LogCategory | 'all'
  filterSeverity: LogSeverity | 'all'
  autoExport: boolean
}

export const $voiceLogging = atom<VoiceLoggingState>({
  entries: [],
  enabled: true,
  maxEntries: 1000,
  filterCategory: 'all',
  filterSeverity: 'all',
  autoExport: false
})

const patch = (u: Partial<VoiceLoggingState>) =>
  $voiceLogging.set({ ...$voiceLogging.get(), ...u })

let _idCounter = 0

export function addLogEntry(entry: Omit<VoiceLogEntry, 'id'>) {
  const state = $voiceLogging.get()

  if (!state.enabled) {return}
  const id = `vl-${Date.now()}-${_idCounter++}`
  const newEntry: VoiceLogEntry = { ...entry, id }
  const entries = [newEntry, ...state.entries].slice(0, state.maxEntries)
  patch({ entries })
}

export function clearLogs() { patch({ entries: [] }) }

export function setLoggingEnabled(e: boolean) { patch({ enabled: e }) }

export function setMaxEntries(m: number) { patch({ maxEntries: m }) }

export function setFilterCategory(c: LogCategory | 'all') { patch({ filterCategory: c }) }

export function setFilterSeverity(s: LogSeverity | 'all') { patch({ filterSeverity: s }) }

export function setAutoExport(a: boolean) { patch({ autoExport: a }) }

export function getFilteredEntries(): VoiceLogEntry[] {
  const state = $voiceLogging.get()

  return state.entries.filter(e => {
    if (state.filterCategory !== 'all' && e.category !== state.filterCategory) {return false}

    if (state.filterSeverity !== 'all' && e.severity !== state.filterSeverity) {return false}

    return true
  })
}
