import { type MouseEvent as ReactMouseEvent } from 'react'

import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'
import {
  getNodeIcon,
  getNodeLabel,
  type WorkflowNode,
} from '@/store/automation'

interface CanvasNodeProps {
  node: WorkflowNode
  isSelected: boolean
  isEditing: boolean
  onSelect: (multi: boolean) => void
  onDragStart: (e: ReactMouseEvent) => void
  onPortMouseDown: (portId: string, e: ReactMouseEvent) => void
  onPortMouseUp: (portId: string) => void
  onDoubleClick: () => void
}

const TYPE_COLORS: Record<string, string> = {
  trigger: 'border-emerald-500/50 bg-emerald-500/5',
  action: 'border-blue-500/50 bg-blue-500/5',
  condition: 'border-amber-500/50 bg-amber-500/5',
  variable: 'border-purple-500/50 bg-purple-500/5',
  timer: 'border-cyan-500/50 bg-cyan-500/5',
  loop: 'border-violet-500/50 bg-violet-500/5',
  switch: 'border-orange-500/50 bg-orange-500/5',
  merge: 'border-pink-500/50 bg-pink-500/5',
  split: 'border-rose-500/50 bg-rose-500/5',
}

const TYPE_ICON_COLORS: Record<string, string> = {
  trigger: 'text-emerald-400',
  action: 'text-blue-400',
  condition: 'text-amber-400',
  variable: 'text-purple-400',
  timer: 'text-cyan-400',
  loop: 'text-violet-400',
  switch: 'text-orange-400',
  merge: 'text-pink-400',
  split: 'text-rose-400',
}

const STATUS_DOTS: Record<string, string> = {
  idle: 'bg-(--ui-stroke-tertiary)',
  running: 'bg-blue-400 animate-pulse',
  completed: 'bg-green-400',
  failed: 'bg-red-400',
  skipped: 'bg-amber-400',
  waiting: 'bg-cyan-400',
}

export function CanvasNode({ node, isSelected, isEditing, onSelect, onDragStart, onPortMouseDown, onPortMouseUp, onDoubleClick }: CanvasNodeProps) {
  const icon = getNodeIcon(node.type, node.kind as string)
  const label = getNodeLabel(node.type, node.kind as string)

  const handleClick = (e: ReactMouseEvent) => {
    onSelect(e.shiftKey)
  }

  const handlePortMouseDown = (portId: string, e: ReactMouseEvent) => {
    e.stopPropagation()
    onPortMouseDown(portId, e)
  }

  return (
    <div
      className={cn(
        'absolute rounded-xl border-2 transition-shadow',
        TYPE_COLORS[node.type] || 'border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background)',
        isSelected && 'ring-2 ring-primary/50 shadow-lg shadow-primary/10',
        isEditing && 'ring-2 ring-primary shadow-xl',
      )}
      onClick={handleClick}
      onDoubleClick={onDoubleClick}
      onMouseDown={onDragStart}
      style={{
        left: node.position.x,
        top: node.position.y,
        width: node.size.width,
        height: node.size.height,
      }}
    >
      <div className="flex h-full items-center gap-2 px-3">
        <div className={cn('flex items-center gap-1.5 flex-1 min-w-0')}>
          <span className={cn('text-sm', TYPE_ICON_COLORS[node.type] || 'text-(--ui-text-tertiary)')}>
            <Codicon name={icon as any} size="1rem" />
          </span>
          <span className="truncate text-xs font-medium text-foreground">{label}</span>
        </div>

        <span className={cn('inline-block h-2 w-2 rounded-full', STATUS_DOTS[node.status] || STATUS_DOTS.idle)} />

        {node.error && (
          <span className="text-red-400" title={node.error}>
            <Codicon name="warning" size="0.875rem" />
          </span>
        )}
      </div>

      {node.ports.filter(p => p.type === 'input').map(port => (
        <div
          className="absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2"
          key={port.id}
        >
          <div
            className={cn(
              'h-3 w-3 cursor-crosshair rounded-full border-2 transition-all hover:scale-125 hover:border-primary border-(--ui-stroke-tertiary) bg-background'
            )}
            onMouseDown={e => handlePortMouseDown(port.id, e)}
            onMouseUp={() => onPortMouseUp(port.id)}
            title={port.label}
          />
        </div>
      ))}

      {node.ports.filter(p => p.type === 'output').map(port => (
        <div
          className="absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2"
          key={port.id}
        >
          <div
            className={cn(
              'h-3 w-3 cursor-crosshair rounded-full border-2 transition-all hover:scale-125 hover:border-primary border-(--ui-stroke-tertiary) bg-background'
            )}
            onMouseDown={e => handlePortMouseDown(port.id, e)}
            onMouseUp={() => onPortMouseUp(port.id)}
            title={port.label}
          />
        </div>
      ))}

      {node.type === 'condition' && (
        <div className="absolute right-0 top-[75%] translate-x-1/2 -translate-y-1/2">
          <div
            className="h-3 w-3 cursor-crosshair rounded-full border-2 border-amber-400/50 bg-background transition-all hover:scale-125 hover:border-amber-400"
            onMouseDown={e => {
              e.stopPropagation()
              const port = node.ports.find(p => p.id.endsWith('-false'))

              if (port) {handlePortMouseDown(port.id, e)}
            }}
            title="False"
          />
        </div>
      )}
    </div>
  )
}
