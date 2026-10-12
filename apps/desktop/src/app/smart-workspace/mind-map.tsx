import { useStore } from '@nanostores/react'
import { useCallback, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  $smartWorkspace,
  addMindMapNode,
  type MindMapNode,
  removeCanvasNode,
  updateMindMapNode
} from '@/store/smart-workspace'

let _nextId = 1
const genId = () => `mm-${Date.now()}-${_nextId++}`

const NODE_COLORS = [
  '#60a5fa', '#a78bfa', '#34d399', '#f472b6',
  '#fbbf24', '#fb923c', '#f87171', '#818cf8',
  '#2dd4bf', '#f59e0b'
]

export function MindMap() {
  const state = useStore($smartWorkspace)
  const containerRef = useRef<HTMLDivElement>(null)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [dragging, setDragging] = useState<string | null>(null)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0, nodeX: 0, nodeY: 0 })
  const [editing, setEditing] = useState<string | null>(null)

  const handleWheel = useCallback((e: { deltaY: number; preventDefault: () => void }) => {
    e.preventDefault()
    setZoom(z => Math.max(0.1, Math.min(3, z * (e.deltaY > 0 ? 0.9 : 1.1))))
  }, [])

  const addChild = useCallback((parentId: string | null) => {
    const depth = parentId ? getDepth(parentId, state.mindMapNodes) + 1 : 0
    const color = NODE_COLORS[depth % NODE_COLORS.length]
    addMindMapNode({
      id: genId(),
      parentId,
      label: 'New Node',
      notes: '',
      collapsed: false,
      color,
      children: []
    })
  }, [state.mindMapNodes])

  const getDepth = (id: string, nodes: MindMapNode[]): number => {
    const node = nodes.find(n => n.id === id)

    if (!node || !node.parentId) {return 0}

    return 1 + getDepth(node.parentId, nodes)
  }

  const handleNodeDragStart = useCallback((nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setDragging(nodeId)
    setDragStart({ x: e.clientX, y: e.clientY, nodeX: 0, nodeY: 0 })
    document.addEventListener('mousemove', handleNodeDragMove)
    document.addEventListener('mouseup', handleNodeDragEnd)
  }, [])

  const handleNodeDragMove = useCallback((e: MouseEvent) => {
    if (!dragging) {return}
    const dx = (e.clientX - dragStart.x) / zoom
    const dy = (e.clientY - dragStart.y) / zoom
    updateMindMapNode(dragging, {
      label: getNodeLabel(dragging) + ' '
    })
  }, [dragging, dragStart, zoom])

  const handleNodeDragEnd = useCallback(() => {
    setDragging(null)
    document.removeEventListener('mousemove', handleNodeDragMove)
    document.removeEventListener('mouseup', handleNodeDragEnd)
  }, [handleNodeDragMove])

  const getNodeLabel = (id: string): string => {
    return state.mindMapNodes.find(n => n.id === id)?.label ?? ''
  }

  const renderNode = (node: MindMapNode, depth: number) => {
    const children = state.mindMapNodes.filter(n => n.parentId === node.id && !n.collapsed)
    const indent = 180
    const nodeHeight = 44
    const childGap = 12

    const totalChildrenHeight = children.length > 0
      ? children.reduce((sum, _, i) => sum + getSubtreeHeight(children[i].id) + childGap, 0) - childGap
      : 0

    return (
      <div className="flex" key={node.id} style={{ marginLeft: depth > 0 ? indent : 0 }}>
        <div className="flex flex-col items-center">
          {depth > 0 && (
            <div className="h-6 w-px bg-(--ui-stroke-tertiary)" />
          )}
          <div
            className={cn(
              'group relative flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium shadow-sm transition-shadow hover:shadow-md',
              editing === node.id ? 'border-primary' : 'border-(--ui-stroke-tertiary)'
            )}
            style={{ borderLeftColor: node.color, borderLeftWidth: 3 }}
          >
            {editing === node.id ? (
              <input
                autoFocus
                className="w-24 bg-transparent text-xs outline-none"
                defaultValue={node.label}
                onBlur={e => {
                  updateMindMapNode(node.id, { label: e.target.value || node.label })
                  setEditing(null)
                }}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    updateMindMapNode(node.id, { label: (e.target as HTMLInputElement).value || node.label })
                    setEditing(null)
                  }
                }}
              />
            ) : (
              <span onDoubleClick={() => setEditing(node.id)}>
                {node.label}
              </span>
            )}
            <div className="ml-2 hidden gap-1 group-hover:flex">
              <button
                className="rounded p-0.5 text-(--ui-text-tertiary) hover:bg-(--ui-bg-tertiary) hover:text-foreground"
                onClick={e => { e.stopPropagation(); addChild(node.id) }}
                title="Add Child"
                type="button"
              >
                <svg className="size-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
                </svg>
              </button>
              {node.children.length > 0 && (
                <button
                  className="rounded p-0.5 text-(--ui-text-tertiary) hover:bg-(--ui-bg-tertiary) hover:text-foreground"
                  onClick={e => { e.stopPropagation(); updateMindMapNode(node.id, { collapsed: !node.collapsed }) }}
                  title={node.collapsed ? 'Expand' : 'Collapse'}
                  type="button"
                >
                  <svg className="size-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    {node.collapsed
                      ? <path d="M4 8l8 8 8-8" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
                      : <path d="M20 16l-8-8-8 8" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />}
                  </svg>
                </button>
              )}
              <button
                className="rounded p-0.5 text-red-400 hover:bg-red-500/10"
                onClick={e => { e.stopPropagation(); removeCanvasNode(node.id) }}
                title="Delete"
                type="button"
              >
                <svg className="size-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
                </svg>
              </button>
            </div>
          </div>
        </div>
        {children.length > 0 && (
          <div className="flex flex-col gap-3" style={{ marginTop: -totalChildrenHeight / 2 }}>
            {children.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  const getSubtreeHeight = (nodeId: string): number => {
    const node = state.mindMapNodes.find(n => n.id === nodeId)

    if (!node) {return 44}
    const children = state.mindMapNodes.filter(n => n.parentId === nodeId && !n.collapsed)

    if (children.length === 0) {return 44}

    return children.reduce((sum, c) => sum + getSubtreeHeight(c.id) + 12, 0) - 12 + 44
  }

  const rootNodes = state.mindMapNodes.filter(n => !n.parentId)

  return (
    <div
      className="relative h-full overflow-auto"
      onWheel={handleWheel}
      ref={containerRef}
    >
      <div
        className="min-h-full p-8"
        style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}
      >
        {rootNodes.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <svg className="mx-auto mb-3 size-12 text-(--ui-text-tertiary)/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} />
              </svg>
              <p className="text-sm text-(--ui-text-tertiary)">
                Click the button below to add your first node
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {rootNodes.map(node => renderNode(node, 0))}
          </div>
        )}
      </div>

      <div className="absolute bottom-4 left-4 flex items-center gap-1 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-elevated) p-1 shadow-sm">
        <Button onClick={() => setZoom(z => Math.max(0.1, z / 1.2))} size="icon-xs" variant="ghost">
          <svg className="size-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d="M20 12H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
          </svg>
        </Button>
        <span className="min-w-[3ch] text-center text-[0.6875rem] font-medium tabular-nums text-(--ui-text-tertiary)">
          {Math.round(zoom * 100)}%
        </span>
        <Button onClick={() => setZoom(z => Math.min(3, z * 1.2))} size="icon-xs" variant="ghost">
          <svg className="size-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
          </svg>
        </Button>
      </div>

      <div className="absolute right-4 top-4">
        <Button onClick={() => addChild(null)} size="sm">
          <svg className="mr-1.5 size-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
          </svg>
          Add Root Node
        </Button>
      </div>
    </div>
  )
}
