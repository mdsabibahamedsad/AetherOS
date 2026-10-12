import { useStore } from '@nanostores/react'
import { useMemo } from 'react'

import { cn } from '@/lib/utils'
import { $automation } from '@/store/automation'

export function MiniMap() {
  const state = useStore($automation)
  const workflow = state.workflows.find(w => w.id === state.activeWorkflowId)

  const { nodes, viewport } = useMemo(() => {
    if (!workflow || workflow.nodes.length === 0) {return { nodes: [], viewport: { x: 0, y: 0, width: 200, height: 150 } }}

    const padding = 50
    const minX = Math.min(...workflow.nodes.map(n => n.position.x)) - padding
    const minY = Math.min(...workflow.nodes.map(n => n.position.y)) - padding
    const maxX = Math.max(...workflow.nodes.map(n => n.position.x + n.size.width)) + padding
    const maxY = Math.max(...workflow.nodes.map(n => n.position.y + n.size.height)) + padding
    const canvasW = maxX - minX
    const canvasH = maxY - minY

    const scale = Math.min(150 / canvasW, 100 / canvasH, 1)

    return {
      nodes: workflow.nodes.map(n => ({
        x: (n.position.x - minX) * scale,
        y: (n.position.y - minY) * scale,
        width: n.size.width * scale,
        height: n.size.height * scale,
        type: n.type,
      })),
      viewport: {
        x: (-state.canvasPan.x / state.canvasScale - minX) * scale,
        y: (-state.canvasPan.y / state.canvasScale - minY) * scale,
        width: (window.innerWidth / state.canvasScale) * scale,
        height: (window.innerHeight / state.canvasScale) * scale,
      },
    }
  }, [workflow, state.canvasScale, state.canvasPan])

  if (!state.showMiniMap || !workflow || workflow.nodes.length === 0) {return null}

  return (
    <div className="absolute bottom-12 right-3 overflow-hidden rounded-lg border bg-background/90 p-2 shadow-lg backdrop-blur-sm">
      <svg className="block" height={150} width={200}>
        {nodes.map(node => (
          <rect
            className={cn(
              'fill-(--ui-stroke-tertiary)/50',
              node.type === 'trigger' && 'fill-emerald-500/30',
              node.type === 'action' && 'fill-blue-500/30',
              node.type === 'condition' && 'fill-amber-500/30',
            )}
            height={Math.max(node.height, 4)}
            key={`${node.x}-${node.y}`}
            rx={2}
            width={Math.max(node.width, 4)}
            x={node.x}
            y={node.y}
          />
        ))}
        <rect
          className="opacity-50"
          fill="none"
          height={viewport.height}
          rx={2}
          stroke="var(--color-primary)"
          strokeWidth={1}
          width={viewport.width}
          x={viewport.x}
          y={viewport.y}
        />
      </svg>
    </div>
  )
}
