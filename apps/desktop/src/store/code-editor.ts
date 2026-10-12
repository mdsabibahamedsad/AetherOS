import { atom, computed } from 'nanostores'

export interface EditorTab {
  filePath: string
  fileName: string
  language: string
  isModified: boolean
  cursorPosition: { line: number; column: number }
  scrollPosition: { top: number; left: number }
  selections: Array<{ startLine: number; startCol: number; endLine: number; endCol: number }>
  isReadOnly: boolean
}

export interface EditorDiff {
  filePath: string
  originalContent: string
  modifiedContent: string
  linesAdded: number
  linesRemoved: number
}

export interface EditorSearchState {
  query: string
  replaceText: string
  isRegex: boolean
  matchCase: boolean
  matchWholeWord: boolean
  results: Array<{ line: number; column: number; length: number; text: string }>
  currentMatchIndex: number
}

export interface CodeEditorState {
  tabs: EditorTab[]
  activeTabPath: string
  splitView: boolean
  splitDirection: 'horizontal' | 'vertical'
  secondaryTabPath: string
  diff: EditorDiff | null
  search: EditorSearchState
  showMinimap: boolean
  showLineNumbers: boolean
  bracketMatching: boolean
  codeFolding: boolean
  formatOnSave: boolean
}

export const $codeEditor = atom<CodeEditorState>({
  tabs: [],
  activeTabPath: '',
  splitView: false,
  splitDirection: 'vertical',
  secondaryTabPath: '',
  diff: null,
  search: { query: '', replaceText: '', isRegex: false, matchCase: false, matchWholeWord: false, results: [], currentMatchIndex: 0 },
  showMinimap: true,
  showLineNumbers: true,
  bracketMatching: true,
  codeFolding: true,
  formatOnSave: false,
})

export const $activeTab = computed($codeEditor, (s) => s.tabs.find(t => t.filePath === s.activeTabPath) ?? null)
export const $openTabs = computed($codeEditor, (s) => s.tabs)
export const $editorDiff = computed($codeEditor, (s) => s.diff)

export function openEditorTab(filePath: string, fileName: string, language: string) {
  const state = $codeEditor.get()
  const existing = state.tabs.find(t => t.filePath === filePath)

  if (existing) {
    $codeEditor.set({ ...state, activeTabPath: filePath })
  } else {
    const tab: EditorTab = { filePath, fileName, language, isModified: false, cursorPosition: { line: 1, column: 1 }, scrollPosition: { top: 0, left: 0 }, selections: [], isReadOnly: false }
    $codeEditor.set({ ...state, tabs: [...state.tabs, tab], activeTabPath: filePath })
  }
}

export function closeEditorTab(filePath: string) {
  const state = $codeEditor.get()
  const tabs = state.tabs.filter(t => t.filePath !== filePath)
  let activeTabPath = state.activeTabPath

  if (activeTabPath === filePath) {
    activeTabPath = tabs.length > 0 ? tabs[tabs.length - 1].filePath : ''
  }

  $codeEditor.set({ ...state, tabs, activeTabPath })
}

export function setActiveTab(filePath: string) {
  const state = $codeEditor.get()
  $codeEditor.set({ ...state, activeTabPath: filePath })
}

export function setTabModified(filePath: string, isModified: boolean) {
  const state = $codeEditor.get()
  const tabs = state.tabs.map(t => t.filePath === filePath ? { ...t, isModified } : t)
  $codeEditor.set({ ...state, tabs })
}

export function updateCursorPosition(filePath: string, position: { line: number; column: number }) {
  const state = $codeEditor.get()
  const tabs = state.tabs.map(t => t.filePath === filePath ? { ...t, cursorPosition: position } : t)
  $codeEditor.set({ ...state, tabs })
}

export function toggleSplitView() {
  const state = $codeEditor.get()
  $codeEditor.set({ ...state, splitView: !state.splitView })
}

export function setDiff(diff: EditorDiff | null) {
  const state = $codeEditor.get()
  $codeEditor.set({ ...state, diff })
}

export function setSearchState(search: Partial<EditorSearchState>) {
  const state = $codeEditor.get()
  $codeEditor.set({ ...state, search: { ...state.search, ...search } })
}

export function clearSearch() {
  const state = $codeEditor.get()
  $codeEditor.set({ ...state, search: { query: '', replaceText: '', isRegex: false, matchCase: false, matchWholeWord: false, results: [], currentMatchIndex: 0 } })
}

export function updateEditorConfig(config: Partial<Pick<CodeEditorState, 'showMinimap' | 'showLineNumbers' | 'bracketMatching' | 'codeFolding' | 'formatOnSave'>>) {
  const state = $codeEditor.get()
  $codeEditor.set({ ...state, ...config })
}
