import { atom, computed } from 'nanostores'

export type AIEditingMode = 'ask' | 'suggest' | 'edit' | 'agent' | 'review' | 'autonomous'

export interface AIConversationMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  files?: string[]
  codeBlocks?: Array<{ language: string; code: string; filePath?: string }>
}

export interface AICodeChange {
  id: string
  filePath: string
  originalContent: string
  newContent: string
  linesAdded: number
  linesRemoved: number
  riskLevel: 'low' | 'medium' | 'high'
  reason: string
  agentModel: string
  agentProvider: string
  permissionStatus: 'pending' | 'approved' | 'rejected'
  selected: boolean
}

export interface AICodingAssistantState {
  mode: AIEditingMode
  isProcessing: boolean
  currentRequest: string
  conversation: AIConversationMessage[]
  pendingChanges: AICodeChange[]
  appliedChanges: AICodeChange[]
  rejectedChanges: AICodeChange[]
  selectedModel: string
  selectedProvider: string
  contextFiles: string[]
  showChangePreview: boolean
  streamingResponse: string
  error: string | null
}

export const $aiCoding = atom<AICodingAssistantState>({
  mode: 'ask',
  isProcessing: false,
  currentRequest: '',
  conversation: [],
  pendingChanges: [],
  appliedChanges: [],
  rejectedChanges: [],
  selectedModel: 'gpt-4o',
  selectedProvider: 'openai',
  contextFiles: [],
  showChangePreview: false,
  streamingResponse: '',
  error: null,
})

export const $aiMode = computed($aiCoding, (s) => s.mode)
export const $pendingChanges = computed($aiCoding, (s) => s.pendingChanges.filter(c => c.permissionStatus === 'pending'))
export const $selectedChanges = computed($aiCoding, (s) => s.pendingChanges.filter(c => c.selected))
export const $totalChanges = computed($aiCoding, (s) => ({ total: s.pendingChanges.length, added: s.pendingChanges.reduce((a, c) => a + c.linesAdded, 0), removed: s.pendingChanges.reduce((a, c) => a + c.linesRemoved, 0) }))

export function setAIMode(mode: AIEditingMode) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, mode, error: null })
}

export function setAIProcessing(processing: boolean) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, isProcessing: processing })
}

export function addMessage(message: AIConversationMessage) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, conversation: [...state.conversation, message], currentRequest: '' })
}

export function setCurrentRequest(request: string) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, currentRequest: request })
}

export function setStreamingResponse(text: string) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, streamingResponse: text })
}

export function addChange(change: AICodeChange) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, pendingChanges: [...state.pendingChanges, change], showChangePreview: true })
}

export function addChanges(changes: AICodeChange[]) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, pendingChanges: [...state.pendingChanges, ...changes], showChangePreview: true })
}

export function toggleChangeSelection(changeId: string) {
  const state = $aiCoding.get()
  const pendingChanges = state.pendingChanges.map(c => c.id === changeId ? { ...c, selected: !c.selected } : c)
  $aiCoding.set({ ...state, pendingChanges })
}

export function selectAllChanges() {
  const state = $aiCoding.get()
  const pendingChanges = state.pendingChanges.map(c => ({ ...c, selected: true }))
  $aiCoding.set({ ...state, pendingChanges })
}

export function deselectAllChanges() {
  const state = $aiCoding.get()
  const pendingChanges = state.pendingChanges.map(c => ({ ...c, selected: false }))
  $aiCoding.set({ ...state, pendingChanges })
}

export function approveChange(changeId: string) {
  const state = $aiCoding.get()
  const change = state.pendingChanges.find(c => c.id === changeId)

  if (change) {
    const pendingChanges = state.pendingChanges.filter(c => c.id !== changeId)
    const appliedChanges = [...state.appliedChanges, { ...change, permissionStatus: 'approved' as const }]
    $aiCoding.set({ ...state, pendingChanges, appliedChanges })
  }
}

export function approveSelectedChanges() {
  const state = $aiCoding.get()
  const toApprove = state.pendingChanges.filter(c => c.selected)
  const pendingChanges = state.pendingChanges.filter(c => !c.selected)
  const appliedChanges = [...state.appliedChanges, ...toApprove.map(c => ({ ...c, permissionStatus: 'approved' as const }))]
  $aiCoding.set({ ...state, pendingChanges, appliedChanges })
}

export function rejectChange(changeId: string) {
  const state = $aiCoding.get()
  const change = state.pendingChanges.find(c => c.id === changeId)

  if (change) {
    const pendingChanges = state.pendingChanges.filter(c => c.id !== changeId)
    const rejectedChanges = [...state.rejectedChanges, { ...change, permissionStatus: 'rejected' as const }]
    $aiCoding.set({ ...state, pendingChanges, rejectedChanges })
  }
}

export function rejectAllChanges() {
  const state = $aiCoding.get()
  const rejectedChanges = [...state.rejectedChanges, ...state.pendingChanges.map(c => ({ ...c, permissionStatus: 'rejected' as const }))]
  $aiCoding.set({ ...state, pendingChanges: [], rejectedChanges })
}

export function applyChanges(changes: AICodeChange[]) {
  const state = $aiCoding.get()
  const changeIds = new Set(changes.map(c => c.id))
  const pendingChanges = state.pendingChanges.filter(c => !changeIds.has(c.id))
  const appliedChanges = [...state.appliedChanges, ...changes.map(c => ({ ...c, permissionStatus: 'approved' as const }))]
  $aiCoding.set({ ...state, pendingChanges, appliedChanges })
}

export function revertChange(changeId: string) {
  const state = $aiCoding.get()
  const appliedChanges = state.appliedChanges.filter(c => c.id !== changeId)
  $aiCoding.set({ ...state, appliedChanges })
}

export function setShowChangePreview(show: boolean) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, showChangePreview: show })
}

export function setAIContextFiles(files: string[]) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, contextFiles: files })
}

export function setAIError(error: string | null) {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, error })
}

export function clearAIConversation() {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, conversation: [], streamingResponse: '', error: null })
}

export function clearAIChanges() {
  const state = $aiCoding.get()
  $aiCoding.set({ ...state, pendingChanges: [], appliedChanges: [], rejectedChanges: [], showChangePreview: false })
}
