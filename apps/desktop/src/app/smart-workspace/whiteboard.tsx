import { useStore } from '@nanostores/react'
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconArrowUpRight,
  IconCircle,
  IconDownload,
  IconEraser,
  IconMinus,
  IconPencil,
  IconPointer,
  IconSparkles,
  IconSquare,
  IconTrash
} from '@tabler/icons-react'
import { type MouseEvent as ReactMouseEvent, useCallback, useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  $smartWorkspace,
  addWhiteboardStroke,
  clearWhiteboard,
  undoWhiteboardStroke,
  type WhiteboardStroke
} from '@/store/smart-workspace'

type Tool = 'pen' | 'eraser' | 'rectangle' | 'circle' | 'line' | 'arrow' | 'select'

const TOOLS: { id: Tool; icon: typeof IconPencil; label: string }[] = [
  { id: 'select', icon: IconPointer, label: 'Select' },
  { id: 'pen', icon: IconPencil, label: 'Pen' },
  { id: 'eraser', icon: IconEraser, label: 'Eraser' },
  { id: 'rectangle', icon: IconSquare, label: 'Rectangle' },
  { id: 'circle', icon: IconCircle, label: 'Circle' },
  { id: 'line', icon: IconMinus, label: 'Line' },
  { id: 'arrow', icon: IconArrowUpRight, label: 'Arrow' }
]

const COLORS = [
  '#ffffff', '#000000', '#ef4444', '#f97316', '#eab308',
  '#22c55e', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899'
]

const STROKE_WIDTHS = [2, 4, 6, 10, 16]

export function Whiteboard() {
  const state = useStore($smartWorkspace)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [tool, setTool] = useState<Tool>('pen')
  const [color, setColor] = useState('#ffffff')
  const [strokeWidth, setStrokeWidth] = useState(4)
  const [isDrawing, setIsDrawing] = useState(false)
  const [currentPoints, setCurrentPoints] = useState<{ x: number; y: number; pressure: number }[]>([])
  const [currentShape, setCurrentShape] = useState<{ startX: number; startY: number; endX: number; endY: number } | null>(null)
  const [redoStack, setRedoStack] = useState<WhiteboardStroke[]>([])

  const getCanvasPoint = useCallback((clientX: number, clientY: number) => {
    const rect = canvasRef.current!.getBoundingClientRect()

    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
      pressure: 0.5
    }
  }, [])

  const redraw = useCallback(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#1a1a2e'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    const allStrokes = state.whiteboardStrokes

    for (const stroke of allStrokes) {
      if (stroke.type === 'pen' || stroke.type === 'eraser') {
        if (stroke.points.length < 2) {continue}
        ctx.beginPath()
        ctx.strokeStyle = stroke.type === 'eraser' ? '#1a1a2e' : stroke.color
        ctx.lineWidth = stroke.type === 'eraser' ? stroke.width * 3 : stroke.width
        ctx.lineCap = 'round'
        ctx.lineJoin = 'round'
        ctx.globalAlpha = stroke.opacity

        ctx.moveTo(stroke.points[0].x, stroke.points[0].y)

        for (let i = 1; i < stroke.points.length; i++) {
          const p = stroke.points[i]
          ctx.lineTo(p.x, p.y)
        }

        ctx.stroke()
        ctx.globalAlpha = 1
      } else if (stroke.type === 'shape') {
        if (stroke.points.length < 2) {continue}
        ctx.beginPath()
        ctx.strokeStyle = stroke.color
        ctx.lineWidth = stroke.width
        ctx.globalAlpha = stroke.opacity

        const p1 = stroke.points[0]
        const p2 = stroke.points[stroke.points.length - 1]

        ctx.beginPath()

        if (stroke.metadata?.shapeType === 'rectangle') {
          ctx.strokeRect(
            Math.min(p1.x, p2.x),
            Math.min(p1.y, p2.y),
            Math.abs(p2.x - p1.x),
            Math.abs(p2.y - p1.y)
          )
        } else if (stroke.metadata?.shapeType === 'circle') {
          const cx = (p1.x + p2.x) / 2
          const cy = (p1.y + p2.y) / 2
          const rx = Math.abs(p2.x - p1.x) / 2
          const ry = Math.abs(p2.y - p1.y) / 2
          ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2)
          ctx.stroke()
        } else if (stroke.metadata?.shapeType === 'line' || stroke.metadata?.shapeType === 'arrow') {
          ctx.moveTo(p1.x, p1.y)
          ctx.lineTo(p2.x, p2.y)
          ctx.stroke()

          if (stroke.metadata?.shapeType === 'arrow') {
            const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x)
            const headLen = 10
            ctx.beginPath()
            ctx.moveTo(p2.x, p2.y)
            ctx.lineTo(p2.x - headLen * Math.cos(angle - 0.4), p2.y - headLen * Math.sin(angle - 0.4))
            ctx.moveTo(p2.x, p2.y)
            ctx.lineTo(p2.x - headLen * Math.cos(angle + 0.4), p2.y - headLen * Math.sin(angle + 0.4))
            ctx.stroke()
          }
        }

        ctx.stroke()
        ctx.globalAlpha = 1
      }
    }
  }, [state.whiteboardStrokes])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current

    if (!canvas || !container) {return}

    canvas.width = container.clientWidth
    canvas.height = container.clientHeight
    redraw()
  }, [redraw])

  useEffect(() => {
    if (!isDrawing) {redraw()}
  }, [state.whiteboardStrokes, isDrawing, redraw])

  const handlePointerDown = useCallback(
    (e: ReactMouseEvent<HTMLCanvasElement>) => {
      const point = getCanvasPoint(e.clientX, e.clientY)
      setIsDrawing(true)
      setCurrentPoints([point])

      if (tool !== 'pen' && tool !== 'eraser' && tool !== 'select') {
        setCurrentShape({ startX: point.x, startY: point.y, endX: point.x, endY: point.y })
      }
    },
    [getCanvasPoint, tool]
  )

  const handlePointerMove = useCallback(
    (e: ReactMouseEvent<HTMLCanvasElement>) => {
      if (!isDrawing) {return}
      const point = getCanvasPoint(e.clientX, e.clientY)

      if (tool === 'pen' || tool === 'eraser') {
        setCurrentPoints(prev => [...prev, point])
        const canvas = canvasRef.current

        if (!canvas) {return}
        const ctx = canvas.getContext('2d')

        if (!ctx) {return}

        const pts = [...state.whiteboardStrokes.flatMap(s => s.points), ...currentPoints, point]

        redraw()
        ctx.beginPath()
        ctx.strokeStyle = tool === 'eraser' ? '#1a1a2e' : color
        ctx.lineWidth = tool === 'eraser' ? strokeWidth * 3 : strokeWidth
        ctx.lineCap = 'round'
        ctx.lineJoin = 'round'
        ctx.moveTo(currentPoints[currentPoints.length - 1]?.x || point.x, currentPoints[currentPoints.length - 1]?.y || point.y)
        ctx.lineTo(point.x, point.y)
        ctx.stroke()
      } else if (currentShape && tool !== 'select') {
        setCurrentShape(prev => prev ? { ...prev, endX: point.x, endY: point.y } : null)
        redraw()
        const canvas = canvasRef.current

        if (!canvas) {return}
        const ctx = canvas.getContext('2d')

        if (!ctx) {return}

        ctx.beginPath()
        ctx.strokeStyle = color
        ctx.lineWidth = strokeWidth
        ctx.globalAlpha = 0.8

        if (tool === 'rectangle') {
          ctx.strokeRect(
            Math.min(currentShape.startX, point.x),
            Math.min(currentShape.startY, point.y),
            Math.abs(point.x - currentShape.startX),
            Math.abs(point.y - currentShape.startY)
          )
        } else if (tool === 'circle') {
          const cx = (currentShape.startX + point.x) / 2
          const cy = (currentShape.startY + point.y) / 2
          const rx = Math.abs(point.x - currentShape.startX) / 2
          const ry = Math.abs(point.y - currentShape.startY) / 2
          ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2)
          ctx.stroke()
        } else {
          ctx.moveTo(currentShape.startX, currentShape.startY)
          ctx.lineTo(point.x, point.y)
          ctx.stroke()

          if (tool === 'arrow') {
            const angle = Math.atan2(point.y - currentShape.startY, point.x - currentShape.startX)
            const headLen = 10
            ctx.beginPath()
            ctx.moveTo(point.x, point.y)
            ctx.lineTo(point.x - headLen * Math.cos(angle - 0.4), point.y - headLen * Math.sin(angle - 0.4))
            ctx.moveTo(point.x, point.y)
            ctx.lineTo(point.x - headLen * Math.cos(angle + 0.4), point.y - headLen * Math.sin(angle + 0.4))
            ctx.stroke()
          }
        }

        ctx.globalAlpha = 1
      }
    },
    [isDrawing, tool, color, strokeWidth, currentPoints, currentShape, state.whiteboardStrokes, redraw, getCanvasPoint]
  )

  const handlePointerUp = useCallback(() => {
    if (!isDrawing || (!currentPoints.length && !currentShape)) {
      setIsDrawing(false)

      return
    }

    if ((tool === 'pen' || tool === 'eraser') && currentPoints.length > 1) {
      addWhiteboardStroke({
        id: `stroke-${Date.now()}`,
        type: tool === 'eraser' ? 'eraser' : 'pen',
        points: currentPoints,
        color: tool === 'eraser' ? '#1a1a2e' : color,
        width: strokeWidth,
        opacity: 1
      })
    } else if (currentShape && tool !== 'select') {
      const shapeMap: Record<string, 'rectangle' | 'circle' | 'line' | 'arrow'> = {
        rectangle: 'rectangle',
        circle: 'circle',
        line: 'line',
        arrow: 'arrow'
      }

      addWhiteboardStroke({
        id: `shape-${Date.now()}`,
        type: 'shape',
        points: [
          { x: currentShape.startX, y: currentShape.startY, pressure: 0.5 },
          { x: currentShape.endX, y: currentShape.endY, pressure: 0.5 }
        ],
        color,
        width: strokeWidth,
        opacity: 0.8,
        metadata: { shapeType: shapeMap[tool] || 'line' }
      })
    }

    setCurrentPoints([])
    setCurrentShape(null)
    setIsDrawing(false)
    setRedoStack([])
  }, [isDrawing, currentPoints, currentShape, tool, color, strokeWidth])

  const handleUndo = useCallback(() => {
    if (!state.whiteboardStrokes.length) {return}
    const last = state.whiteboardStrokes[state.whiteboardStrokes.length - 1]
    setRedoStack(prev => [...prev, last])
    undoWhiteboardStroke()
  }, [state.whiteboardStrokes])

  const handleRedo = useCallback(() => {
    if (!redoStack.length) {return}
    const stroke = redoStack[redoStack.length - 1]
    addWhiteboardStroke(stroke)
    setRedoStack(prev => prev.slice(0, -1))
  }, [redoStack])

  const handleClear = useCallback(() => {
    clearWhiteboard()
    setRedoStack([])
  }, [])

  const handleExport = useCallback(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const link = document.createElement('a')
    link.download = 'whiteboard.png'
    link.href = canvas.toDataURL('image/png')
    link.click()
  }, [])

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary) px-3 py-1.5">
        {TOOLS.map(t => {
          const ToolIcon = t.icon

          return (
            <Button
              key={t.id}
              onClick={() => setTool(t.id)}
              size="icon-xs"
              title={t.label}
              variant={tool === t.id ? 'default' : 'ghost'}
            >
              <ToolIcon className="size-3.5" />
            </Button>
          )
        })}
        <div className="mx-2 h-4 w-px bg-(--ui-stroke-tertiary)" />
        <div className="flex items-center gap-1">
          {COLORS.map(c => (
            <button
              aria-label={c}
              className={cn(
                'size-4 rounded-full border transition-transform',
                color === c ? 'scale-125 border-foreground' : 'border-transparent hover:scale-110'
              )}
              key={c}
              onClick={() => setColor(c)}
              style={{ backgroundColor: c }}
              type="button"
            />
          ))}
        </div>
        <div className="mx-2 h-4 w-px bg-(--ui-stroke-tertiary)" />
        <div className="flex items-center gap-1">
          {STROKE_WIDTHS.map(w => (
            <button
              aria-label={`${w}px`}
              className={cn(
                'flex items-center justify-center rounded px-1.5 py-1 transition-colors hover:bg-accent',
                strokeWidth === w && 'bg-accent'
              )}
              key={w}
              onClick={() => setStrokeWidth(w)}
              type="button"
            >
              <div className="rounded-full bg-foreground" style={{ width: w, height: w }} />
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-1">
          <Button aria-label="Undo" disabled={!state.whiteboardStrokes.length} onClick={handleUndo} size="icon-xs" title="Undo" variant="ghost">
            <IconArrowBackUp className="size-3.5" />
          </Button>
          <Button aria-label="Redo" disabled={!redoStack.length} onClick={handleRedo} size="icon-xs" title="Redo" variant="ghost">
            <IconArrowForwardUp className="size-3.5" />
          </Button>
          <Button aria-label="Clear" disabled={!state.whiteboardStrokes.length} onClick={handleClear} size="icon-xs" title="Clear" variant="ghost">
            <IconTrash className="size-3.5" />
          </Button>
          <Button aria-label="Export PNG" disabled={!state.whiteboardStrokes.length} onClick={handleExport} size="icon-xs" title="Export PNG" variant="ghost">
            <IconDownload className="size-3.5" />
          </Button>
          <Button aria-label="Ask AI" onClick={() => {}} size="icon-xs" title="Ask AI" variant="ghost">
            <IconSparkles className="size-3.5 text-primary" />
          </Button>
        </div>
      </div>

      <div
        className={cn(
          'min-h-0 flex-1 cursor-crosshair',
          tool === 'select' && 'cursor-default',
          tool === 'eraser' && 'cursor-cell'
        )}
        ref={containerRef}
      >
        <canvas
          className="block h-full w-full"
          onMouseDown={handlePointerDown}
          onMouseLeave={handlePointerUp}
          onMouseMove={handlePointerMove}
          onMouseUp={handlePointerUp}
          ref={canvasRef}
        />
      </div>
    </div>
  )
}
