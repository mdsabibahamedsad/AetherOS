
import type { Connection, WorkflowNode } from '@/store/automation'

interface ConnectionLineProps {
  connection: Connection
  sourceNode: WorkflowNode
  targetNode: WorkflowNode
  isSelected: boolean
  onClick: () => void
}

export function ConnectionLine({ connection, sourceNode, targetNode, isSelected, onClick }: ConnectionLineProps) {
  const sourceX = sourceNode.position.x + sourceNode.size.width
  const sourceY = sourceNode.position.y + sourceNode.size.height / 2
  const targetX = targetNode.position.x
  const targetY = targetNode.position.y + targetNode.size.height / 2

  const midX = (sourceX + targetX) / 2
  const path = `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      style={{ overflow: 'visible' }}
    >
      <path
        className="transition-colors"
        d={path}
        fill="none"
        stroke={isSelected ? 'var(--color-primary)' : 'var(--ui-stroke-tertiary)'}
        strokeWidth={isSelected ? 2.5 : 1.5}
      />
      <path
        className="pointer-events-auto cursor-pointer"
        d={path}
        fill="none"
        onClick={onClick}
        stroke="transparent"
        strokeWidth={12}
      />
      {isSelected && (
        <circle
          className="pointer-events-auto cursor-pointer"
          cx={targetX}
          cy={targetY}
          fill="var(--color-primary)"
          onClick={onClick}
          r={4}
        />
      )}
    </svg>
  )
}
