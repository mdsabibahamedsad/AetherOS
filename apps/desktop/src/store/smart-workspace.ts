import { atom } from 'nanostores'

export interface WorkspaceItem {
  id: string
  type: 'canvas' | 'scratchpad' | 'notes' | 'whiteboard' | 'mindmap'
  title: string
  content: string
  createdAt: number
  updatedAt: number
  tags: string[]
  pinned: boolean
  metadata: Record<string, string>
}

export interface CanvasNode {
  id: string
  type: 'text' | 'image' | 'code' | 'link' | 'note' | 'file'
  x: number
  y: number
  width: number
  height: number
  content: string
  color: string
  connections: string[]
}

export interface MindMapNode {
  id: string
  parentId: string | null
  label: string
  notes: string
  collapsed: boolean
  color: string
  children: string[]
}

export interface WhiteboardStroke {
  id: string
  type: 'pen' | 'eraser' | 'shape'
  points: { x: number; y: number; pressure: number }[]
  color: string
  width: number
  opacity: number
  metadata?: { shapeType?: string }
}

export interface SmartWorkspaceState {
  items: WorkspaceItem[]
  activeItemId: string | null
  canvasNodes: CanvasNode[]
  mindMapNodes: MindMapNode[]
  whiteboardStrokes: WhiteboardStroke[]
  scratchpadContent: string
  scratchpadHistory: { content: string; timestamp: number }[]
  bookmarks: { id: string; title: string; url: string; tags: string[] }[]
  pinnedChats: string[]
  knowledgePanelOpen: boolean
  taskPanelOpen: boolean
  notesView: 'grid' | 'list' | 'timeline'
  searchQuery: string
}

export const $smartWorkspace = atom<SmartWorkspaceState>({
  items: [],
  activeItemId: null,
  canvasNodes: [],
  mindMapNodes: [],
  whiteboardStrokes: [],
  scratchpadContent: '',
  scratchpadHistory: [],
  bookmarks: [],
  pinnedChats: [],
  knowledgePanelOpen: false,
  taskPanelOpen: false,
  notesView: 'grid',
  searchQuery: ''
})

const patch = (u: Partial<SmartWorkspaceState>) =>
  $smartWorkspace.set({ ...$smartWorkspace.get(), ...u })

export function setActiveItem(id: string | null) { patch({ activeItemId: id }) }

export function setCanvasNodes(nodes: CanvasNode[]) { patch({ canvasNodes: nodes }) }

export function addCanvasNode(node: CanvasNode) { patch({ canvasNodes: [...$smartWorkspace.get().canvasNodes, node] }) }

export function updateCanvasNode(id: string, update: Partial<CanvasNode>) {
  patch({ canvasNodes: $smartWorkspace.get().canvasNodes.map(n => n.id === id ? { ...n, ...update } : n) })
}

export function removeCanvasNode(id: string) { patch({ canvasNodes: $smartWorkspace.get().canvasNodes.filter(n => n.id !== id) }) }

export function setMindMapNodes(nodes: MindMapNode[]) { patch({ mindMapNodes: nodes }) }

export function addMindMapNode(node: MindMapNode) { patch({ mindMapNodes: [...$smartWorkspace.get().mindMapNodes, node] }) }

export function updateMindMapNode(id: string, update: Partial<MindMapNode>) {
  patch({ mindMapNodes: $smartWorkspace.get().mindMapNodes.map(n => n.id === id ? { ...n, ...update } : n) })
}

export function setWhiteboardStrokes(strokes: WhiteboardStroke[]) { patch({ whiteboardStrokes: strokes }) }

export function addWhiteboardStroke(stroke: WhiteboardStroke) { patch({ whiteboardStrokes: [...$smartWorkspace.get().whiteboardStrokes, stroke] }) }

export function undoWhiteboardStroke() { patch({ whiteboardStrokes: $smartWorkspace.get().whiteboardStrokes.slice(0, -1) }) }

export function clearWhiteboard() { patch({ whiteboardStrokes: [] }) }

export function setScratchpadContent(c: string) { patch({ scratchpadContent: c }) }

export function saveScratchpadSnapshot() {
  const state = $smartWorkspace.get()
  patch({ scratchpadHistory: [...state.scratchpadHistory, { content: state.scratchpadContent, timestamp: Date.now() }] })
}

export function restoreScratchpadSnapshot(index: number) {
  const snapshot = $smartWorkspace.get().scratchpadHistory[index]

  if (snapshot) {patch({ scratchpadContent: snapshot.content })}
}

export function addBookmark(bookmark: { id: string; title: string; url: string; tags: string[] }) {
  patch({ bookmarks: [...$smartWorkspace.get().bookmarks, bookmark] })
}

export function removeBookmark(id: string) { patch({ bookmarks: $smartWorkspace.get().bookmarks.filter(b => b.id !== id) }) }

export function toggleKnowledgePanel() { patch({ knowledgePanelOpen: !$smartWorkspace.get().knowledgePanelOpen }) }

export function toggleTaskPanel() { patch({ taskPanelOpen: !$smartWorkspace.get().taskPanelOpen }) }

export function setNotesView(view: 'grid' | 'list' | 'timeline') { patch({ notesView: view }) }

export function setSearchQuery(q: string) { patch({ searchQuery: q }) }

export function addWorkspaceItem(item: WorkspaceItem) { patch({ items: [...$smartWorkspace.get().items, item] }) }

export function updateWorkspaceItem(id: string, update: Partial<WorkspaceItem>) {
  patch({ items: $smartWorkspace.get().items.map(i => i.id === id ? { ...i, ...update } : i) })
}

export function removeWorkspaceItem(id: string) { patch({ items: $smartWorkspace.get().items.filter(i => i.id !== id) }) }

export function togglePinItem(id: string) {
  patch({ items: $smartWorkspace.get().items.map(i => i.id === id ? { ...i, pinned: !i.pinned } : i) })
}
