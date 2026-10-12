import { useStore } from '@nanostores/react'
import { motion } from 'motion/react'
import { memo, useEffect, useRef } from 'react'

import { $jarvisActiveAgentCount, $jarvisEngineActive, $jarvisOrbState, $jarvisRunningJobCount, $jarvisSystemStatus } from '@/store/jarvis-mode'

const RING_SIZE = 340
const RING_RADIUS = 155
const RING_WIDTH = 2.5

interface Segment {
  label: string
  value: number
  max: number
  color: string
  glowColor: string
}

function StatusRingComponent() {
  const status = useStore($jarvisSystemStatus)
  const agentCount = useStore($jarvisActiveAgentCount)
  const jobCount = useStore($jarvisRunningJobCount)
  const engineActive = useStore($jarvisEngineActive)
  const orbState = useStore($jarvisOrbState)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const segmentsRef = useRef<Segment[] | null>(null)

  const segments: Segment[] = [
    { label: 'CPU', value: status.cpu, max: 100, color: status.cpu > 80 ? '#ef4444' : '#22c55e', glowColor: status.cpu > 80 ? '#ef4444' : '#22c55e' },
    { label: 'RAM', value: status.memory.percent, max: 100, color: status.memory.percent > 80 ? '#ef4444' : '#00d4ff', glowColor: status.memory.percent > 80 ? '#ef4444' : '#00d4ff' },
    { label: 'GPU', value: status.gpu?.percent ?? 0, max: 100, color: '#9933ff', glowColor: '#9933ff' },
    { label: 'GW', value: status.gateway === 'connected' ? 100 : 0, max: 100, color: status.gateway === 'connected' ? '#22c55e' : '#ef4444', glowColor: status.gateway === 'connected' ? '#22c55e' : '#ef4444' },
    { label: 'AGT', value: agentCount * 25, max: 100, color: '#0066ff', glowColor: '#0066ff' },
    { label: 'JOB', value: jobCount * 25, max: 100, color: '#f59e0b', glowColor: '#f59e0b' },
    { label: 'M', value: engineActive ? 100 : 0, max: 100, color: engineActive ? '#22c55e' : '#64748b', glowColor: engineActive ? '#22c55e' : '#64748b' },
    { label: 'UPT', value: Math.min(status.uptime / 3600 * 10, 100), max: 100, color: '#00d4ff', glowColor: '#00d4ff' },
  ]

  segmentsRef.current = segments

  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}
    const dpr = window.devicePixelRatio || 1
    canvas.width = RING_SIZE * dpr
    canvas.height = RING_SIZE * dpr
    ctx.scale(dpr, dpr)

    let animId: number
    let currentValues = segments.map(() => 0)
    const targetValues = segments.map(s => s.value)

    const draw = () => {
      ctx.clearRect(0, 0, RING_SIZE, RING_SIZE)
      const cx = RING_SIZE / 2
      const cy = RING_SIZE / 2

      for (let i = 0; i < segments.length; i++) {
        const s = segments[i]
        currentValues[i] += (targetValues[i] - currentValues[i]) * 0.05
        const value = currentValues[i]
        const startAngle = (i / segments.length) * Math.PI * 2 - Math.PI / 2
        const endAngle = startAngle + (value / 100) * (Math.PI * 2 / segments.length) * 0.8

        ctx.beginPath()
        ctx.arc(cx, cy, RING_RADIUS, startAngle, startAngle + (Math.PI * 2 / segments.length) * 0.8)
        ctx.strokeStyle = 'rgba(255,255,255,0.04)'
        ctx.lineWidth = RING_WIDTH
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(cx, cy, RING_RADIUS, startAngle, endAngle)
        ctx.strokeStyle = s.color
        ctx.lineWidth = RING_WIDTH
        ctx.shadowColor = s.glowColor
        ctx.shadowBlur = value > 0 ? 8 : 0
        ctx.stroke()
        ctx.shadowBlur = 0

        if (value > 0) {
          const dotAngle = endAngle
          const dx = Math.cos(dotAngle) * RING_RADIUS
          const dy = Math.sin(dotAngle) * RING_RADIUS
          ctx.beginPath()
          ctx.arc(cx + dx, cy + dy, 2, 0, Math.PI * 2)
          ctx.fillStyle = s.color
          ctx.shadowColor = s.glowColor
          ctx.shadowBlur = 10
          ctx.fill()
          ctx.shadowBlur = 0
        }

        const midAngle = startAngle + (Math.PI * 2 / segments.length / 2)
        const labelRadius = RING_RADIUS - 18
        const lx = cx + Math.cos(midAngle) * labelRadius
        const ly = cy + Math.sin(midAngle) * labelRadius

        ctx.fillStyle = 'rgba(255,255,255,0.25)'
        ctx.font = '8px monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(s.label, lx, ly)
      }

      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => cancelAnimationFrame(animId)
  }, [segments])

  return (
    <motion.div
      animate={{ opacity: orbState === 'idle' ? 0.6 : orbState === 'error' ? 0.4 : 0.8 }}
      className="absolute inset-0 flex items-center justify-center pointer-events-none"
      transition={{ duration: 0.5 }}
    >
      <canvas ref={canvasRef} style={{ width: RING_SIZE, height: RING_SIZE }} />
    </motion.div>
  )
}

export const StatusRing = memo(StatusRingComponent)
