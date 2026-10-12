import { useStore } from '@nanostores/react'
import {
  IconCode,
  IconFileText,
  IconGripVertical,
  IconHome,
  IconLayoutDashboard,
  IconLink,
  IconMaximize,
  IconMinus,
  IconPhoto,
  IconPlus,
  IconSparkles,
  IconSticker,
  IconTextSize,
  IconTrash
} from '@tabler/icons-react'
import {
  type MouseEvent as ReactMouseEvent,
  useCallback,
  useEffect,
  useRef,
  useState
} from 'react'

import { Button } from '@/components/ui/button'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuTrigger
} from '@/components/ui/context-menu'
import { cn } from '@/lib/utils'
import {
  $smartWorkspace,
  addCanvasNode,
  type CanvasNode,
  removeCanvasNode,
  updateCanvasNode
} from '@/store/smart-workspace'

let _nextId = 1
const genId = () => `cn-${Date.now()}-${_nextId++}`

const NODE_COLORS: Record<CanvasNode['type'], string> = {
  text: '#60a5fa',
  image: '#a78bfa',
  code: '#34d399',
  link: '#f472b6',
  note: '#fbbf24',
  file: '#fb923c'
}

const NODE_LABELS: Record<CanvasNode['type'], string> = {
  text: 'Text',
  image: 'Image',
  code: 'Code',
  link: 'Link',
  note: 'Note',
  file: 'File'
}

const MINI_MAP_SIZE = 160
const MINI_MAP_PADDING = 8
const GRID_SIZE = 24

export function AICanvas() {
  const state = useStore($smartWorkspace)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const miniMapRef = useRef<HTMLCanvasElement>(null)

  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [panning, setPanning] = useState(false)
  const [panStart, setPanStart] = useState({ x: 0, y: 0 })
  const [offsetStart, setOffsetStart] = useState({ x: 0, y: 0 })
  const [draggingNode, setDraggingNode] = useState<string | null>(null)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0, nodeX: 0, nodeY: 0 })
  const [connecting, setConnecting] = useState<string | null>(null)
  const [connectEnd, setConnectEnd] = useState({ x: 0, y: 0 })

  const worldToScreen = useCallback(
    (wx: number, wy: number) => ({
      x: wx * zoom + offset.x,
      y: wy * zoom + offset.y
    }),
    [zoom, offset]
  )

  const screenToWorld = useCallback(
    (sx: number, sy: number) => ({
      x: (sx - offset.x) / zoom,
      y: (sy - offset.y) / zoom
    }),
    [zoom, offset]
  )

  const drawGrid = useCallback(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}

    const { width, height } = canvas
    ctx.clearRect(0, 0, width, height)

    const startX = offset.x % (GRID_SIZE * zoom)
    const startY = offset.y % (GRID_SIZE * zoom)

    ctx.strokeStyle = 'rgba(128,128,128,0.08)'
    ctx.lineWidth = 1
    ctx.beginPath()

    for (let x = startX; x < width; x += GRID_SIZE * zoom) {
      ctx.moveTo(x, 0)
      ctx.lineTo(x, height)
    }

    for (let y = startY; y < height; y += GRID_SIZE * zoom) {
      ctx.moveTo(0, y)
      ctx.lineTo(width, y)
    }

    ctx.stroke()
  }, [offset, zoom])

  const drawConnections = useCallback(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}

    const nodes = $smartWorkspace.get().canvasNodes
    const nodeMap = new Map(nodes.map(n => [n.id, n]))

    ctx.strokeStyle = 'rgba(128,128,128,0.3)'
    ctx.lineWidth = 2
    ctx.setLineDash([])

    for (const node of nodes) {
      for (const connId of node.connections) {
        const target = nodeMap.get(connId)

        if (!target) {continue}

        const from = worldToScreen(node.x + node.width / 2, node.y + node.height / 2)
        const to = worldToScreen(target.x + target.width / 2, target.y + target.height / 2)

        ctx.beginPath()
        ctx.moveTo(from.x, from.y)
        const cpx = (from.x + to.x) / 2
        ctx.quadraticCurveTo(cpx, from.y, cpx, (from.y + to.y) / 2)
        ctx.quadraticCurveTo(cpx, to.y, to.x, to.y)
        ctx.stroke()

        const angle = Math.atan2(to.y - from.y, to.x - from.x)
        const headLen = 8
        ctx.beginPath()
        ctx.moveTo(to.x, to.y)
        ctx.lineTo(to.x - headLen * Math.cos(angle - 0.4), to.y - headLen * Math.sin(angle - 0.4))
        ctx.moveTo(to.x, to.y)
        ctx.lineTo(to.x - headLen * Math.cos(angle + 0.4), to.y - headLen * Math.sin(angle + 0.4))
        ctx.stroke()
      }
    }
  }, [worldToScreen])

  const drawMiniMap = useCallback(() => {
    const canvas = miniMapRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}

    const nodes = $smartWorkspace.get().canvasNodes
    ctx.clearRect(0, 0, MINI_MAP_SIZE, MINI_MAP_SIZE)

    ctx.fillStyle = 'rgba(0,0,0,0.04)'
    ctx.fillRect(0, 0, MINI_MAP_SIZE, MINI_MAP_SIZE)

    if (!nodes.length) {return}

    const minX = Math.min(...nodes.map(n => n.x))
    const minY = Math.min(...nodes.map(n => n.y))
    const maxX = Math.max(...nodes.map(n => n.x + n.width))
    const maxY = Math.max(...nodes.map(n => n.y + n.height))

    const rangeX = maxX - minX || 1
    const rangeY = maxY - minY || 1
    const scale = Math.min((MINI_MAP_SIZE - MINI_MAP_PADDING * 2) / rangeX, (MINI_MAP_SIZE - MINI_MAP_PADDING * 2) / rangeY, 0.5)

    for (const node of nodes) {
      const nx = MINI_MAP_PADDING + (node.x - minX) * scale
      const ny = MINI_MAP_PADDING + (node.y - minY) * scale
      const nw = node.width * scale
      const nh = node.height * scale

      ctx.fillStyle = NODE_COLORS[node.type] || '#666'
      ctx.globalAlpha = 0.6
      ctx.fillRect(nx, ny, Math.max(nw, 2), Math.max(nh, 2))
    }

    ctx.globalAlpha = 1
    ctx.strokeStyle = 'rgba(0,102,255,0.4)'
    ctx.lineWidth = 1
    const vx = MINI_MAP_PADDING + (-offset.x / zoom - minX) * scale
    const vy = MINI_MAP_PADDING + (-offset.y / zoom - minY) * scale
    const vw = (containerRef.current?.clientWidth || 800) / zoom * scale
    const vh = (containerRef.current?.clientHeight || 600) / zoom * scale
    ctx.strokeRect(vx, vy, vw, vh)
  }, [offset, zoom])

  useEffect(() => {
    drawGrid()
    drawConnections()
    drawMiniMap()
  }, [drawGrid, drawConnections, drawMiniMap])

  useEffect(() => {
    const container = containerRef.current

    if (!container) {return}

    const resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        const canvas = canvasRef.current

        if (!canvas) {continue}
        canvas.width = entry.contentRect.width
        canvas.height = entry.contentRect.height
        drawGrid()
        drawConnections()
        drawMiniMap()
      }
    })

    resizeObserver.observe(container)

    return () => resizeObserver.disconnect()
  }, [drawGrid, drawConnections, drawMiniMap])

  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const container = containerRef.current

    if (!container) {return}

    canvas.width = container.clientWidth
    canvas.height = container.clientHeight
  }, [])

  const handleWheel = useCallback(
    (e: { deltaY: number; clientX: number; clientY: number; preventDefault: () => void }) => {
      e.preventDefault()
      const factor = e.deltaY > 0 ? 0.9 : 1.1
      const newZoom = Math.max(0.1, Math.min(5, zoom * factor))

      const mx = e.clientX - containerRef.current!.getBoundingClientRect().left
      const my = e.clientY - containerRef.current!.getBoundingClientRect().top

      setOffset({
        x: mx - (mx - offset.x) * (newZoom / zoom),
        y: my - (my - offset.y) * (newZoom / zoom)
      })
      setZoom(newZoom)
    },
    [zoom, offset]
  )

  const handleMouseDown = useCallback(
    (e: ReactMouseEvent) => {
      if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
        setPanning(true)
        setPanStart({ x: e.clientX, y: e.clientY })
        setOffsetStart({ ...offset })
        e.preventDefault()
      }
    },
    [offset]
  )

  const handleMouseMove = useCallback(
    (e: ReactMouseEvent) => {
      if (panning) {
        setOffset({
          x: offsetStart.x + (e.clientX - panStart.x),
          y: offsetStart.y + (e.clientY - panStart.y)
        })
      }
    },
    [panning, panStart, offsetStart]
  )

  const handleMouseUp = useCallback(() => {
    setPanning(false)
    setDraggingNode(null)
    setConnecting(null)
  }, [])

  const handleNodeDragStart = useCallback(
    (nodeId: string, e: ReactMouseEvent) => {
      e.stopPropagation()
      const node = state.canvasNodes.find(n => n.id === nodeId)

      if (!node) {return}
      setDraggingNode(nodeId)
      setDragStart({ x: e.clientX, y: e.clientY, nodeX: node.x, nodeY: node.y })
    },
    [state.canvasNodes]
  )

  const handleNodeDrag = useCallback(
    (e: ReactMouseEvent) => {
      if (!draggingNode) {return}
      const dx = (e.clientX - dragStart.x) / zoom
      const dy = (e.clientY - dragStart.y) / zoom
      updateCanvasNode(draggingNode, {
        x: dragStart.nodeX + dx,
        y: dragStart.nodeY + dy
      })
    },
    [draggingNode, dragStart, zoom]
  )

  const handleConnectStart = useCallback((nodeId: string, e: ReactMouseEvent) => {
    e.stopPropagation()
    setConnecting(nodeId)
    const rect = containerRef.current!.getBoundingClientRect()
    setConnectEnd({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }, [])

  const handleConnectMove = useCallback((e: ReactMouseEvent) => {
    if (!connecting) {return}
    const rect = containerRef.current!.getBoundingClientRect()
    setConnectEnd({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }, [connecting])

  const handleConnectEnd = useCallback(
    (targetId: string) => {
      if (!connecting || connecting === targetId) {
        setConnecting(null)

        return
      }

      const node = state.canvasNodes.find(n => n.id === connecting)

      if (node && !node.connections.includes(targetId)) {
        updateCanvasNode(connecting, { connections: [...node.connections, targetId] })
      }

      setConnecting(null)
    },
    [connecting, state.canvasNodes]
  )

  const addNode = useCallback(
    (type: CanvasNode['type']) => {
      const center = screenToWorld(containerRef.current!.clientWidth / 2, containerRef.current!.clientHeight / 2)
      addCanvasNode({
        id: genId(),
        type,
        x: center.x - 80,
        y: center.y - 30,
        width: 160,
        height: 60,
        content: `New ${NODE_LABELS[type]}`,
        color: NODE_COLORS[type],
        connections: []
      })
    },
    [screenToWorld]
  )

  const zoomToFit = useCallback(() => {
    const nodes = state.canvasNodes

    if (!nodes.length) {
      setZoom(1)
      setOffset({ x: 0, y: 0 })

      return
    }

    const container = containerRef.current

    if (!container) {return}

    const minX = Math.min(...nodes.map(n => n.x))
    const minY = Math.min(...nodes.map(n => n.y))
    const maxX = Math.max(...nodes.map(n => n.x + n.width))
    const maxY = Math.max(...nodes.map(n => n.y + n.height))

    const cw = container.clientWidth
    const ch = container.clientHeight
    const padding = 80
    const scale = Math.min((cw - padding * 2) / (maxX - minX || 1), (ch - padding * 2) / (maxY - minY || 1), 2)

    setZoom(scale)
    setOffset({
      x: (cw - (maxX + minX) * scale) / 2,
      y: (ch - (maxY + minY) * scale) / 2
    })
  }, [state.canvasNodes])

  const resetZoom = useCallback(() => {
    setZoom(1)
    setOffset({ x: 0, y: 0 })
  }, [])

  return (
    <div
      className="relative h-full overflow-hidden"
      onContextMenu={e => e.preventDefault()}
      ref={containerRef}
    >
      <canvas
        className="absolute inset-0"
        onMouseDown={handleMouseDown}
        onMouseLeave={handleMouseUp}
        onMouseMove={e => {
          handleMouseMove(e)
          handleNodeDrag(e)
          handleConnectMove(e)
        }}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        ref={canvasRef}
      />

      <div
        className="absolute"
        style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`, transformOrigin: '0 0' }}
      >
        {state.canvasNodes.map(node => (
          <ContextMenu key={node.id}>
            <ContextMenuTrigger asChild>
              <div
                className="absolute cursor-move select-none"
                onMouseDown={e => handleNodeDragStart(node.id, e)}
                onMouseUp={() => {
                  if (connecting) {handleConnectEnd(node.id)}
                }}
                style={{
                  left: node.x,
                  top: node.y,
                  width: node.width,
                  height: node.height
                }}
              >
                <div
                  className={cn(
                    'flex h-full flex-col overflow-hidden rounded-lg border shadow-sm transition-shadow hover:shadow-md',
                    'bg-(--ui-bg-elevated)'
                  )}
                  style={{ borderColor: node.color }}
                >
                  <div
                    className="flex items-center gap-1.5 px-2 py-1 text-[0.625rem] font-medium uppercase tracking-wider"
                    style={{ backgroundColor: `${node.color}15`, color: node.color }}
                  >
                    <IconGripVertical className="size-2.5 shrink-0 opacity-50" />
                    {NODE_LABELS[node.type]}
                  </div>
                  <div className="flex min-h-0 flex-1 items-center px-2 text-xs text-foreground">
                    {node.content}
                  </div>
                </div>
              </div>
            </ContextMenuTrigger>
            <ContextMenuContent>
              <ContextMenuItem onClick={() => updateCanvasNode(node.id, { content: prompt('Edit content:', node.content) || node.content })}>
                <IconTextSize className="mr-2 size-3.5" />
                Edit
              </ContextMenuItem>
              <ContextMenuSub>
                <ContextMenuSubTrigger>
                  <IconLink className="mr-2 size-3.5" />
                  Connect to
                </ContextMenuSubTrigger>
                <ContextMenuSubContent>
                  {state.canvasNodes
                    .filter(n => n.id !== node.id && !node.connections.includes(n.id))
                    .map(n => (
                      <ContextMenuItem key={n.id} onClick={() => handleConnectEnd(n.id)}>
                        {NODE_LABELS[n.type]}: {n.content.slice(0, 24)}
                      </ContextMenuItem>
                    ))}
                  {state.canvasNodes.filter(n => n.id !== node.id && !node.connections.includes(n.id)).length === 0 && (
                    <ContextMenuItem disabled>No unconnected nodes</ContextMenuItem>
                  )}
                </ContextMenuSubContent>
              </ContextMenuSub>
              <ContextMenuSeparator />
              <ContextMenuItem className="text-destructive" onClick={() => removeCanvasNode(node.id)}>
                <IconTrash className="mr-2 size-3.5" />
                Delete
              </ContextMenuItem>
            </ContextMenuContent>
          </ContextMenu>
        ))}

        {connecting && (
          <svg className="pointer-events-none absolute inset-0" style={{ overflow: 'visible' }}>
            <line
              stroke="#60a5fa"
              strokeDasharray="6 3"
              strokeWidth={2}
              x1={state.canvasNodes.find(n => n.id === connecting)!.x + 80}
              x2={(connectEnd.x - offset.x) / zoom}
              y1={state.canvasNodes.find(n => n.id === connecting)!.y + 30}
              y2={(connectEnd.y - offset.y) / zoom}
            />
          </svg>
        )}
      </div>

      <div className="absolute bottom-4 left-4 flex items-center gap-1 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-elevated) p-1 shadow-sm">
        <Button onClick={() => setZoom(z => Math.max(0.1, z / 1.2))} size="icon-xs" variant="ghost">
          <IconMinus className="size-3.5" />
        </Button>
        <span className="min-w-[3ch] text-center text-[0.6875rem] font-medium tabular-nums text-muted-foreground">
          {Math.round(zoom * 100)}%
        </span>
        <Button aria-label="Zoom in" onClick={() => setZoom(z => Math.min(5, z * 1.2))} size="icon-xs" variant="ghost">
          <IconPlus className="size-3.5" />
        </Button>
        <div className="mx-0.5 h-4 w-px bg-(--ui-stroke-tertiary)" />
        <Button aria-label="Fit to view" onClick={zoomToFit} size="icon-xs" title="Fit to view" variant="ghost">
          <IconMaximize className="size-3.5" />
        </Button>
        <Button aria-label="Reset view" onClick={resetZoom} size="icon-xs" title="Reset view" variant="ghost">
          <IconHome className="size-3.5" />
        </Button>
      </div>

      <div className="absolute bottom-4 right-4 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-elevated) p-1 shadow-sm">
        <canvas height={MINI_MAP_SIZE} ref={miniMapRef} width={MINI_MAP_SIZE} />
      </div>

      <div className="absolute right-4 top-4 flex flex-col gap-1 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-elevated) p-1 shadow-sm">
        <ContextMenu>
          <ContextMenuTrigger asChild>
            <Button aria-label="Add node" size="icon-xs" variant="ghost">
              <IconPlus className="size-3.5" />
            </Button>
          </ContextMenuTrigger>
          <ContextMenuContent>
            {(Object.keys(NODE_COLORS) as CanvasNode['type'][]).map(type => {
              const Icon = type === 'text' ? IconTextSize : type === 'code' ? IconCode : type === 'image' ? IconPhoto : type === 'link' ? IconLink : type === 'note' ? IconSticker : IconFileText

              return (
                <ContextMenuItem key={type} onClick={() => addNode(type)}>
                  <Icon className="mr-2 size-3.5" style={{ color: NODE_COLORS[type] }} />
                  {NODE_LABELS[type]}
                </ContextMenuItem>
              )
            })}
            <ContextMenuSeparator />
            <ContextMenuItem onClick={() => {
              addNode('text')
              window.setTimeout(() => {
                updateCanvasNode(
                  $smartWorkspace.get().canvasNodes[$smartWorkspace.get().canvasNodes.length - 1]?.id,
                  { content: 'AI-generated content will appear here' }
                )
              }, 100)
            }}>
              <IconSparkles className="mr-2 size-3.5 text-primary" />
              Ask AI
            </ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>
      </div>

      {(state.canvasNodes.length === 0) && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <IconLayoutDashboard className="mx-auto mb-3 size-12 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              Right-click or use the <IconPlus className="inline size-3" /> button to add nodes
            </p>
            <p className="mt-1 text-xs text-muted-foreground/60">
              Drag to pan · Scroll to zoom · Drag nodes to reposition
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
