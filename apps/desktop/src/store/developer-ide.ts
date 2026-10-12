import { atom, computed } from 'nanostores'

export type IDEMode = 'code' | 'diff' | 'review' | 'debug' | 'build' | 'test' | 'git'

export interface IDEPanel {
  id: string
  label: string
  visible: boolean
  position: 'left' | 'right' | 'bottom' | 'center'
  size: number
  order: number
}

export interface IDEState {
  mode: IDEMode
  activeProjectId: string
  activeFilePath: string
  openFilePaths: string[]
  panels: IDEPanel[]
  sidebarVisible: boolean
  bottomPanelVisible: boolean
  rightPanelVisible: boolean
  editorFontSize: number
  editorTabSize: number
  editorWordWrap: boolean
  editorMinimap: boolean
  editorLineNumbers: boolean
}

const defaultPanels: IDEPanel[] = [
  { id: 'explorer', label: 'Explorer', visible: true, position: 'left', size: 260, order: 1 },
  { id: 'search', label: 'Search', visible: false, position: 'left', size: 260, order: 2 },
  { id: 'git', label: 'Git', visible: false, position: 'left', size: 260, order: 3 },
  { id: 'debug', label: 'Debug', visible: false, position: 'left', size: 260, order: 4 },
  { id: 'extensions', label: 'Extensions', visible: false, position: 'left', size: 260, order: 5 },
  { id: 'ai-assistant', label: 'AI Assistant', visible: true, position: 'right', size: 320, order: 1 },
  { id: 'problems', label: 'Problems', visible: false, position: 'bottom', size: 200, order: 1 },
  { id: 'output', label: 'Output', visible: false, position: 'bottom', size: 200, order: 2 },
  { id: 'terminal', label: 'Terminal', visible: false, position: 'bottom', size: 200, order: 3 },
  { id: 'build', label: 'Build', visible: false, position: 'bottom', size: 200, order: 4 },
  { id: 'test', label: 'Tests', visible: false, position: 'bottom', size: 200, order: 5 },
]

export const $ide = atom<IDEState>({
  mode: 'code',
  activeProjectId: '',
  activeFilePath: '',
  openFilePaths: [],
  panels: defaultPanels,
  sidebarVisible: true,
  bottomPanelVisible: false,
  rightPanelVisible: true,
  editorFontSize: 14,
  editorTabSize: 2,
  editorWordWrap: false,
  editorMinimap: true,
  editorLineNumbers: true,
})

export const $activeFile = computed($ide, (state) => state.activeFilePath)
export const $activeProject = computed($ide, (state) => state.activeProjectId)
export const $openFiles = computed($ide, (state) => state.openFilePaths)
export const $visiblePanels = computed($ide, (state) => state.panels.filter(p => p.visible))

export function setIDEMode(mode: IDEMode) {
  const state = $ide.get()
  $ide.set({ ...state, mode })
}

export function setActiveProject(projectId: string) {
  const state = $ide.get()
  $ide.set({ ...state, activeProjectId: projectId })
}

export function openFile(filePath: string) {
  const state = $ide.get()

  if (!state.openFilePaths.includes(filePath)) {
    $ide.set({ ...state, openFilePaths: [...state.openFilePaths, filePath], activeFilePath: filePath })
  } else {
    $ide.set({ ...state, activeFilePath: filePath })
  }
}

export function closeFile(filePath: string) {
  const state = $ide.get()
  const openPaths = state.openFilePaths.filter(p => p !== filePath)
  let activeFilePath = state.activeFilePath

  if (activeFilePath === filePath) {
    activeFilePath = openPaths.length > 0 ? openPaths[openPaths.length - 1] : ''
  }

  $ide.set({ ...state, openFilePaths: openPaths, activeFilePath })
}

export function toggleSidebar() {
  const state = $ide.get()
  $ide.set({ ...state, sidebarVisible: !state.sidebarVisible })
}

export function toggleBottomPanel() {
  const state = $ide.get()
  $ide.set({ ...state, bottomPanelVisible: !state.bottomPanelVisible })
}

export function toggleRightPanel() {
  const state = $ide.get()
  $ide.set({ ...state, rightPanelVisible: !state.rightPanelVisible })
}

export function togglePanel(panelId: string) {
  const state = $ide.get()
  const panels = state.panels.map(p => p.id === panelId ? { ...p, visible: !p.visible } : p)
  const panel = panels.find(p => p.id === panelId)

  if (panel) {
    if (panel.position === 'bottom') {
      $ide.set({ ...state, panels, bottomPanelVisible: panel.visible })
    } else {
      $ide.set({ ...state, panels })
    }
  }
}

export function updateEditorSettings(settings: Partial<Pick<IDEState, 'editorFontSize' | 'editorTabSize' | 'editorWordWrap' | 'editorMinimap' | 'editorLineNumbers'>>) {
  const state = $ide.get()
  $ide.set({ ...state, ...settings })
}
