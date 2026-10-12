import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useEffect, useRef } from 'react'

import { $jarvisOrbState, $jarvisThinkingLabel, $jarvisThinkingStage, type OrbState, type ThinkingStage } from '@/store/jarvis-mode'

import { GlassPanel } from '../shared/glass-panel'

interface StageDef {
  stage: ThinkingStage | OrbState
  label: string
  icon: string
  color: string
}

const STAGES: StageDef[] = [
  { stage: 'understanding', label: 'Understanding', icon: 'search', color: '#00d4ff' },
  { stage: 'planning', label: 'Planning', icon: 'list-flat', color: '#0066ff' },
  { stage: 'searching', label: 'Researching', icon: 'database', color: '#a78bfa' },
  { stage: 'executing', label: 'Executing', icon: 'play', color: '#22c55e' },
  { stage: 'validating', label: 'Testing', icon: 'pass', color: '#f59e0b' },
  { stage: 'complete', label: 'Completed', icon: 'check', color: '#22c55e' },
]

function FlowLineCanvas({ currentIdx }: { currentIdx: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const LINE_COUNT = STAGES.length - 1

  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}
    const dpr = window.devicePixelRatio || 1
    canvas.width = 12 * dpr
    canvas.height = (LINE_COUNT * 44 + 28) * dpr
    ctx.scale(dpr, dpr)

    let animId: number
    let t = 0

    const draw = () => {
      t += 0.02
      const w = 12
      const h = LINE_COUNT * 44 + 28
      ctx.clearRect(0, 0, w, h)

      for (let i = 0; i < LINE_COUNT; i++) {
        const y = i * 44 + 28
        const past = i < currentIdx
        const isCurrent = i === currentIdx
        const cx = w / 2

        if (past) {
          ctx.beginPath()
          ctx.moveTo(cx, 0)
          ctx.lineTo(cx, y)
          ctx.strokeStyle = 'rgba(52, 211, 153, 0.25)'
          ctx.lineWidth = 1.5
          ctx.stroke()
        } else if (isCurrent) {
          const flow = (Math.sin(t + i * 0.5) * 0.5 + 0.5)

          ctx.beginPath()
          ctx.moveTo(cx, 0)
          ctx.lineTo(cx, y)
          ctx.strokeStyle = `rgba(0, 212, 255, ${0.15 + flow * 0.25})`
          ctx.lineWidth = 1.5
          ctx.stroke()

          const dotY = 0 + (y - 0) * flow
          ctx.beginPath()
          ctx.arc(cx, dotY, 2, 0, Math.PI * 2)
          ctx.fillStyle = '#00d4ff'
          ctx.shadowColor = '#00d4ff'
          ctx.shadowBlur = 8
          ctx.fill()
          ctx.shadowBlur = 0
        } else {
          ctx.beginPath()
          ctx.moveTo(cx, 0)
          ctx.lineTo(cx, y)
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)'
          ctx.lineWidth = 1
          ctx.stroke()
        }
      }

      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => cancelAnimationFrame(animId)
  }, [currentIdx])

  return (
    <canvas
      className="absolute left-[18px] top-0 pointer-events-none"
      ref={canvasRef}
      style={{ width: 12, height: LINE_COUNT * 44 + 28 }}
    />
  )
}

function TimelineStage({ stage, idx, currentIdx, past, isCurrent, currentLabel }: {
  stage: StageDef; idx: number; currentIdx: number; past: boolean; isCurrent: boolean; currentLabel: string
}) {
  return (
    <div className="flex items-center gap-3">
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        <motion.div
          animate={isCurrent ? { scale: [1, 1.3, 1] } : {}}
          className={`size-3 rounded-full border-2 flex items-center justify-center transition-all duration-500 relative
            ${isCurrent ? 'border-[#00d4ff] bg-[#00d4ff]/20' : past ? 'border-emerald-400 bg-emerald-400/20' : 'border-white/[0.1] bg-transparent'}`}
          transition={isCurrent ? { duration: 2, repeat: Infinity } : {}}
        >
          {past && <div className="size-1.5 rounded-full bg-emerald-400" />}
          {isCurrent && <div className="size-1.5 rounded-full bg-[#00d4ff]" />}
        </motion.div>
        {idx < STAGES.length - 1 && (
          <div className="w-0.5 h-8" />
        )}
      </div>

      {/* Content */}
      <div className={`pb-2 ${idx === STAGES.length - 1 ? '' : 'pb-4'}`}>
        <div className="flex items-center gap-2">
          <span className={`text-[12px] font-medium transition-all duration-300
            ${isCurrent ? 'text-white/80' : past ? 'text-white/40' : 'text-white/15'}`}>
            {stage.label}
          </span>
          {past && (
            <span className="codicon codicon-check text-[10px] text-emerald-400" />
          )}
          {isCurrent && (
            <motion.span
              animate={{ opacity: [0.4, 1, 0.4] }}
              className="text-[10px] text-[#00d4ff]"
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              ●
            </motion.span>
          )}
        </div>
        {isCurrent && currentLabel && (
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="text-[10px] text-white/25 mt-1 font-mono"
            initial={{ opacity: 0, y: -4 }}
            key={currentLabel}
          >
            {currentLabel}
          </motion.div>
        )}
      </div>
    </div>
  )
}

export function ExecutionTimelineComponent() {
  const thinkingStage = useStore($jarvisThinkingStage)
  const orbState = useStore($jarvisOrbState)
  const currentLabel = useStore($jarvisThinkingLabel)

  const isIdle = thinkingStage === 'idle' && orbState === 'idle'

  if (isIdle) {return null}

  const effectiveStage = thinkingStage !== 'idle' ? thinkingStage : orbState === 'executing' ? 'executing' : orbState === 'success' ? 'complete' : 'understanding'
  const currentIdx = STAGES.findIndex(s => s.stage === effectiveStage)

  return (
    <AnimatePresence>
      <motion.div
        animate={{ opacity: 1, x: 0 }}
        className="fixed left-[calc(228px+24px)] bottom-24 z-50"
        exit={{ opacity: 0, x: -20 }}
        initial={{ opacity: 0, x: -20 }}
      >
        <GlassPanel className="p-4 rounded-2xl shadow-2xl" glow="cyan" intensity="heavy">
          <div className="text-[9px] uppercase tracking-[0.2em] text-white/15 font-medium mb-4">Execution Timeline</div>
          <div className="relative">
            <FlowLineCanvas currentIdx={currentIdx} />
            {STAGES.map((stage, i) => (
              <TimelineStage
                currentIdx={currentIdx}
                currentLabel={currentLabel}
                idx={i}
                isCurrent={i === currentIdx}
                key={stage.stage}
                past={i < currentIdx}
                stage={stage}
              />
            ))}
          </div>
        </GlassPanel>
      </motion.div>
    </AnimatePresence>
  )
}

export const ExecutionTimeline = memo(ExecutionTimelineComponent)
