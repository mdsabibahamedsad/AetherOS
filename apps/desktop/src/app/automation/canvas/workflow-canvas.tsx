import { useStore } from '@nanostores/react'
import { type DragEvent, type MouseEvent as ReactMouseEvent, type WheelEvent as ReactWheelEvent, useCallback, useEffect, useRef, useState } from 'react'

import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'
import {
  $automation,
  type ActionKind,
  addConnection,
  addNode,
  type ConditionKind,
  type NodeType,
  type Position,
  selectAll,
  selectConnection,
  selectNode,
  setCanvasPan,
  setCanvasScale,
  setEditingNode,
  setNodePosition,
  setShowNodePalette,
  type TriggerKind,
} from '@/store/automation'

import { CanvasNode } from './canvas-node'
import { ConnectionLine } from './connection-line'
import { MiniMap } from './mini-map'

export function WorkflowCanvas() {
  const state = useStore($automation)
  const canvasRef = useRef<HTMLDivElement>(null)
  const [isPanning, setIsPanning] = useState(false)
  const [panStart, setPanStart] = useState<Position>({ x: 0, y: 0 })
  const [draggingNode, setDraggingNode] = useState<string | null>(null)
  const [dragStart, setDragStart] = useState<Position>({ x: 0, y: 0 })
  const [nodeDragStart, setNodeDragStart] = useState<Position>({ x: 0, y: 0 })
  const [connecting, setConnecting] = useState<{ nodeId: string; portId: string } | null>(null)
  const [connectionEnd, setConnectionEnd] = useState<Position | null>(null)
  const [dropHighlight, setDropHighlight] = useState(false)

  const workflow = state.workflows.find(w => w.id === state.activeWorkflowId)
  const nodeMap = new Map(workflow?.nodes.map(n => [n.id, n]) ?? [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '=') { e.preventDefault(); setCanvasScale(Math.min(3, state.canvasScale + 0.1)) }

      if ((e.metaKey || e.ctrlKey) && e.key === '-') { e.preventDefault(); setCanvasScale(Math.max(0.1, state.canvasScale - 0.1)) }

      if ((e.metaKey || e.ctrlKey) && e.key === '0') { e.preventDefault(); setCanvasScale(1) }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [state.canvasScale])

  const handleWheel = useCallback((e: ReactWheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault()
      const delta = -e.deltaY * 0.001
      setCanvasScale(Math.max(0.1, Math.min(3, state.canvasScale + delta)))
    } else {
      setCanvasPan({ x: state.canvasPan.x - e.deltaX, y: state.canvasPan.y - e.deltaY })
    }
  }, [state.canvasScale, state.canvasPan])

  const handleMouseDown = useCallback((e: ReactMouseEvent) => {
    if (e.target === canvasRef.current || (e.target as HTMLElement).closest('[data-canvas-bg]')) {
      if (e.button === 0 || e.button === 1) {
        setIsPanning(true)
        setPanStart({ x: e.clientX - state.canvasPan.x, y: e.clientY - state.canvasPan.y })
      }
    }
  }, [state.canvasPan])

  const handleMouseMove = useCallback((e: ReactMouseEvent) => {
    if (isPanning) {
      setCanvasPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y })
    }

    if (draggingNode) {
      const dx = e.clientX - dragStart.x
      const dy = e.clientY - dragStart.y
      const snappedX = state.snapToGrid ? Math.round((nodeDragStart.x + dx) / state.gridSize) * state.gridSize : nodeDragStart.x + dx
      const snappedY = state.snapToGrid ? Math.round((nodeDragStart.y + dy) / state.gridSize) * state.gridSize : nodeDragStart.y + dy
      setNodePosition(draggingNode, { x: snappedX, y: snappedY })
    }

    if (connecting) {
      const rect = canvasRef.current?.getBoundingClientRect()

      if (rect) {
        setConnectionEnd({ x: (e.clientX - rect.left - state.canvasPan.x) / state.canvasScale, y: (e.clientY - rect.top - state.canvasPan.y) / state.canvasScale })
      }
    }
  }, [isPanning, panStart, draggingNode, dragStart, nodeDragStart, connecting, state.canvasScale, state.canvasPan, state.snapToGrid, state.gridSize])

  const handleMouseUp = useCallback(() => {
    setIsPanning(false)
    setDraggingNode(null)

    if (connecting) {
      setConnecting(null)
      setConnectionEnd(null)
    }
  }, [connecting])

  const handleNodeDragStart = useCallback((nodeId: string, e: ReactMouseEvent) => {
    e.stopPropagation()
    setDraggingNode(nodeId)
    setDragStart({ x: e.clientX, y: e.clientY })
    const node = nodeMap.get(nodeId)

    if (node) {setNodeDragStart({ x: node.position.x, y: node.position.y })}
  }, [nodeMap])

  const handlePortMouseDown = useCallback((nodeId: string, portId: string, e: ReactMouseEvent) => {
    e.stopPropagation()
    setConnecting({ nodeId, portId })
    const rect = canvasRef.current?.getBoundingClientRect()

    if (rect) {
      setConnectionEnd({ x: (e.clientX - rect.left - state.canvasPan.x) / state.canvasScale, y: (e.clientY - rect.top - state.canvasPan.y) / state.canvasScale })
    }
  }, [state.canvasPan, state.canvasScale])

  const handleCanvasDrop = useCallback((e: DragEvent) => {
    e.preventDefault()
    setDropHighlight(false)
    const data = e.dataTransfer.getData('application/aetheros-node')

    if (!data || !canvasRef.current) {return}

    try {
      const { type, kind, label } = JSON.parse(data) as { type: NodeType; kind: TriggerKind | ActionKind | ConditionKind; label: string }
      const rect = canvasRef.current.getBoundingClientRect()
      const x = (e.clientX - rect.left - state.canvasPan.x) / state.canvasScale
      const y = (e.clientY - rect.top - state.canvasPan.y) / state.canvasScale
      const snappedX = state.snapToGrid ? Math.round(x / state.gridSize) * state.gridSize : x
      const snappedY = state.snapToGrid ? Math.round(y / state.gridSize) * state.gridSize : y
      addNode(type, kind, label, { x: snappedX, y: snappedY })
    } catch { }
  }, [state.canvasScale, state.canvasPan, state.snapToGrid, state.gridSize])

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    setDropHighlight(true)
  }, [])

  const handleDragLeave = useCallback(() => setDropHighlight(false), [])

  const handlePortMouseUp = useCallback((targetNodeId: string, targetPortId: string) => {
    if (connecting && connecting.nodeId !== targetNodeId) {
      const sourcePortIsOutput = connecting.portId.endsWith('-out')
      const targetPortIsInput = targetPortId.endsWith('-in')

      if (sourcePortIsOutput && targetPortIsInput) {
        addConnection(connecting.nodeId, connecting.portId, targetNodeId, targetPortId)
      }
    }

    setConnecting(null)
    setConnectionEnd(null)
  }, [connecting])

  const canvasStyle = {
    transform: `translate(${state.canvasPan.x}px, ${state.canvasPan.y}px) scale(${state.canvasScale})`,
    transformOrigin: '0 0',
  }

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div
        className={cn('absolute inset-0 cursor-grab', (isPanning || state.isPanning) && 'cursor-grabbing', dropHighlight && 'bg-primary/5')}
        data-canvas-bg
        onContextMenu={e => { e.preventDefault(); selectAll() }}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleCanvasDrop}
        onMouseDown={handleMouseDown}
        onMouseLeave={handleMouseUp}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        ref={canvasRef}
        style={{
          backgroundImage: state.snapToGrid ? `radial-gradient(circle, rgba(128,128,128,0.15) 1px, transparent 1px)` : undefined,
          backgroundSize: `${state.gridSize * state.canvasScale}px ${state.gridSize * state.canvasScale}px`,
          backgroundPosition: `${state.canvasPan.x}px ${state.canvasPan.y}px`,
        }}
      >
        <div className="absolute" style={canvasStyle}>
          {workflow?.connections.map(conn => {
            const source = nodeMap.get(conn.sourceNodeId)
            const target = nodeMap.get(conn.targetNodeId)

            if (!source || !target) {return null}

            return (
              <ConnectionLine
                connection={conn}
                isSelected={state.selectedConnectionIds.includes(conn.id)}
                key={conn.id}
                onClick={() => selectConnection(conn.id)}
                sourceNode={source}
                targetNode={target}
              />
            )
          })}

          {connecting && connectionEnd && (() => {
            const sourceNode = nodeMap.get(connecting.nodeId)

            if (!sourceNode) {return null}

            return (
              <svg className="pointer-events-none absolute inset-0 h-full w-full" style={{ overflow: 'visible' }}>
                <line
                  stroke="var(--color-primary)"
                  strokeDasharray="5,5"
                  strokeWidth={2}
                  x1={sourceNode.position.x + sourceNode.size.width}
                  x2={connectionEnd.x}
                  y1={sourceNode.position.y + sourceNode.size.height / 2}
                  y2={connectionEnd.y}
                />
              </svg>
            )
          })()}

          {workflow?.nodes.map(node => (
            <CanvasNode
              isEditing={state.editingNodeId === node.id}
              isSelected={state.selectedNodeIds.includes(node.id)}
              key={node.id}
              node={node}
              onDoubleClick={() => setEditingNode(node.id)}
              onDragStart={(e) => handleNodeDragStart(node.id, e)}
              onPortMouseDown={(portId, e) => handlePortMouseDown(node.id, portId, e)}
              onPortMouseUp={(portId) => handlePortMouseUp(node.id, portId)}
              onSelect={(multi) => selectNode(node.id, multi)}
            />
          ))}
        </div>
      </div>

      <div className="absolute bottom-3 left-3 flex items-center gap-1 rounded-lg border bg-background/80 px-2 py-1 backdrop-blur-sm">
        <button className="rounded p-0.5 text-(--ui-text-tertiary) hover:text-foreground" onClick={() => setCanvasScale(state.canvasScale - 0.1)} type="button">
          <Codicon name="zoom-out" size="0.875rem" />
        </button>
        <span className="min-w-[3rem] text-center text-xs tabular-nums text-(--ui-text-tertiary)">
          {Math.round(state.canvasScale * 100)}%
        </span>
        <button className="rounded p-0.5 text-(--ui-text-tertiary) hover:text-foreground" onClick={() => setCanvasScale(state.canvasScale + 0.1)} type="button">
          <Codicon name="zoom-in" size="0.875rem" />
        </button>
        <span className="mx-1 text-(--ui-stroke-tertiary)">|</span>
        <button className="rounded p-0.5 text-xs text-(--ui-text-tertiary) hover:text-foreground" onClick={() => setCanvasScale(1)} type="button">
          Reset
        </button>
      </div>

      <div className="absolute bottom-3 right-3 flex items-center gap-1">
        <button
          className={cn('rounded-lg border px-2 py-1 text-xs backdrop-blur-sm transition-colors', state.showNodePalette ? 'bg-primary/10 text-primary border-primary/20' : 'bg-background/80 text-(--ui-text-tertiary) border-(--ui-stroke-tertiary)')}
          onClick={() => setShowNodePalette(!state.showNodePalette)}
          type="button"
        >
          <Codicon className="mr-1 inline" name="add" size="0.75rem" />
          Nodes
        </button>
      </div>

      <MiniMap />
    </div>
  )
}
