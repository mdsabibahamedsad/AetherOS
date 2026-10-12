import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useEffect, useRef, useState } from 'react'

import { $jarvisOrbState, $jarvisSystemStatus, type OrbState } from '@/store/jarvis-mode'

interface OrbConfig {
  scale: number
  ringSpeed: number
  particleSpeed: number
  glowOpacity: number
  color: string
  particleColor: string
}

const ORB_CONFIG: Record<OrbState, OrbConfig> = {
  idle: { scale: 1, ringSpeed: 0.3, particleSpeed: 0.15, glowOpacity: 0.25, color: '#00d4ff', particleColor: 'rgba(0,212,255,0.4)' },
  listening: { scale: 1.05, ringSpeed: 1, particleSpeed: 0.5, glowOpacity: 0.6, color: '#00d4ff', particleColor: 'rgba(0,212,255,0.6)' },
  thinking: { scale: 0.92, ringSpeed: 2.5, particleSpeed: 0.9, glowOpacity: 0.85, color: '#a78bfa', particleColor: 'rgba(167,139,250,0.6)' },
  planning: { scale: 0.96, ringSpeed: 1.8, particleSpeed: 0.6, glowOpacity: 0.7, color: '#0066ff', particleColor: 'rgba(0,102,255,0.5)' },
  executing: { scale: 1.02, ringSpeed: 3, particleSpeed: 1.2, glowOpacity: 0.9, color: '#22c55e', particleColor: 'rgba(34,197,94,0.6)' },
  speaking: { scale: 1.03, ringSpeed: 0.8, particleSpeed: 0.4, glowOpacity: 0.7, color: '#00d4ff', particleColor: 'rgba(0,212,255,0.5)' },
  searching: { scale: 0.95, ringSpeed: 2, particleSpeed: 1, glowOpacity: 0.65, color: '#f59e0b', particleColor: 'rgba(245,158,11,0.5)' },
  coding: { scale: 0.94, ringSpeed: 1.5, particleSpeed: 0.8, glowOpacity: 0.7, color: '#0066ff', particleColor: 'rgba(0,102,255,0.5)' },
  error: { scale: 1.05, ringSpeed: 0.5, particleSpeed: 0.2, glowOpacity: 0.9, color: '#ef4444', particleColor: 'rgba(239,68,68,0.6)' },
  success: { scale: 1.08, ringSpeed: 3.5, particleSpeed: 1.5, glowOpacity: 1, color: '#22c55e', particleColor: 'rgba(34,197,94,0.7)' },
}

const ORB_SIZE = 280

function EnergyRings({ config, time }: { config: OrbConfig; time: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const RING_COUNT = 4
  const RING_RADIUS = [110, 125, 140, 158]

  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}
    const dpr = window.devicePixelRatio || 1
    canvas.width = ORB_SIZE * dpr
    canvas.height = ORB_SIZE * dpr
    ctx.scale(dpr, dpr)

    let animId: number

    const draw = () => {
      ctx.clearRect(0, 0, ORB_SIZE, ORB_SIZE)
      const speed = config.ringSpeed * 0.02

      for (let i = 0; i < RING_COUNT; i++) {
        const radius = RING_RADIUS[i]
        const rotation = time * speed * (i % 2 === 0 ? 1 : -1) + (i * Math.PI) / RING_COUNT
        const opacity = 0.15 + (i / RING_COUNT) * 0.2
        const width = 1 + Math.sin(time * 0.001 + i) * 0.5

        ctx.save()
        ctx.translate(ORB_SIZE / 2, ORB_SIZE / 2)
        ctx.rotate(rotation)
        ctx.beginPath()
        ctx.arc(0, 0, radius, 0, Math.PI * 1.5)
        ctx.strokeStyle = config.color
        ctx.globalAlpha = opacity
        ctx.lineWidth = width
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(0, 0, radius - 3, Math.PI * 1.5, Math.PI * 2)
        ctx.strokeStyle = config.color
        ctx.globalAlpha = opacity * 0.5
        ctx.lineWidth = width * 0.5
        ctx.stroke()
        ctx.restore()
      }

      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => cancelAnimationFrame(animId)
  }, [config])

  return <canvas className="absolute inset-0 size-full" ref={canvasRef} style={{ width: ORB_SIZE, height: ORB_SIZE }} />
}

function OrbParticles({ config, time }: { config: OrbConfig; time: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const PARTICLE_COUNT = 60
  const particlesRef = useRef<Array<{ x: number; y: number; vx: number; vy: number; size: number; phase: number }> | null>(null)

  if (!particlesRef.current) {
    particlesRef.current = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: (Math.random() - 0.5) * 200,
      y: (Math.random() - 0.5) * 200,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: 1 + Math.random() * 2,
      phase: Math.random() * Math.PI * 2,
    }))
  }

  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}
    const dpr = window.devicePixelRatio || 1
    canvas.width = ORB_SIZE * dpr
    canvas.height = ORB_SIZE * dpr
    ctx.scale(dpr, dpr)

    const particles = particlesRef.current!
    let animId: number

    const draw = () => {
      ctx.clearRect(0, 0, ORB_SIZE, ORB_SIZE)
      const cx = ORB_SIZE / 2
      const cy = ORB_SIZE / 2
      const speed = config.particleSpeed * 0.3

      for (const p of particles) {
        p.x += p.vx * speed
        p.y += p.vy * speed
        const dist = Math.sqrt(p.x * p.x + p.y * p.y)
        const maxDist = 95

        if (dist > maxDist) {
          p.x *= maxDist / dist
          p.y *= maxDist / dist
          p.vx *= -0.5
          p.vy *= -0.5
        }

        const alpha = (1 - dist / maxDist) * 0.6 * config.glowOpacity
        const pulse = Math.sin(time * 0.002 + p.phase) * 0.3 + 0.7

        ctx.beginPath()
        ctx.arc(cx + p.x, cy + p.y, p.size * pulse, 0, Math.PI * 2)
        ctx.fillStyle = config.particleColor.replace('0.', String(Math.max(0.1, alpha)))
        ctx.fill()

        if (dist < 60) {
          for (const other of particles) {
            if (other === p) {continue}
            const ox = other.x - p.x
            const oy = other.y - p.y
            const odist = Math.sqrt(ox * ox + oy * oy)

            if (odist < 40) {
              ctx.beginPath()
              ctx.moveTo(cx + p.x, cy + p.y)
              ctx.lineTo(cx + other.x, cy + other.y)
              ctx.strokeStyle = config.color
              ctx.globalAlpha = (1 - odist / 40) * 0.1 * config.glowOpacity
              ctx.lineWidth = 0.5
              ctx.stroke()
              ctx.globalAlpha = 1
            }
          }
        }
      }

      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => cancelAnimationFrame(animId)
  }, [config])

  return <canvas className="absolute inset-0 size-full" ref={canvasRef} style={{ width: ORB_SIZE, height: ORB_SIZE }} />
}

function OrbGlow({ config }: { config: OrbConfig }) {
  return (
    <motion.div
      animate={{
        boxShadow: [
          `0 0 40px ${config.color}${Math.round(config.glowOpacity * 15).toString(16).padStart(2, '0')}, 0 0 80px ${config.color}${Math.round(config.glowOpacity * 8).toString(16).padStart(2, '0')}, 0 0 160px ${config.color}${Math.round(config.glowOpacity * 4).toString(16).padStart(2, '0')}`,
          `0 0 50px ${config.color}${Math.round(config.glowOpacity * 20).toString(16).padStart(2, '0')}, 0 0 100px ${config.color}${Math.round(config.glowOpacity * 10).toString(16).padStart(2, '0')}, 0 0 200px ${config.color}${Math.round(config.glowOpacity * 5).toString(16).padStart(2, '0')}`,
          `0 0 40px ${config.color}${Math.round(config.glowOpacity * 15).toString(16).padStart(2, '0')}, 0 0 80px ${config.color}${Math.round(config.glowOpacity * 8).toString(16).padStart(2, '0')}, 0 0 160px ${config.color}${Math.round(config.glowOpacity * 4).toString(16).padStart(2, '0')}`,
        ],
      }}
      className="absolute inset-0 rounded-full"
      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
}

function OrbCore({ config }: { config: OrbConfig }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <motion.div
        animate={{
          scale: [1, 1.05, 1],
          opacity: [0.6, 0.9, 0.6],
        }}
        className="rounded-full"
        style={{
          width: 100,
          height: 100,
          background: `radial-gradient(circle at 35% 35%, ${config.color}40, ${config.color}20 40%, transparent 70%)`,
        }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        animate={{
          scale: [0.8, 1.2, 0.8],
          opacity: [0.3, 0.7, 0.3],
        }}
        className="absolute rounded-full"
        style={{
          width: 60,
          height: 60,
          background: `radial-gradient(circle, ${config.color}60, transparent 70%)`,
        }}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      />
      <div
        className="absolute rounded-full"
        style={{
          width: 30,
          height: 30,
          background: config.color,
          boxShadow: `0 0 20px ${config.color}, 0 0 40px ${config.color}80`,
          opacity: 0.8,
        }}
      />
    </div>
  )
}

function StateLabel({ state, config }: { state: OrbState; config: OrbConfig }) {
  const LABELS: Record<OrbState, string> = {
    idle: 'STANDBY', listening: 'LISTENING', thinking: 'THINKING', planning: 'PLANNING',
    executing: 'EXECUTING', speaking: 'SPEAKING', searching: 'SEARCHING', coding: 'CODING',
    error: 'ERROR', success: 'SUCCESS',
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="absolute -bottom-10 left-1/2 -translate-x-1/2 text-center"
        exit={{ opacity: 0, y: -4 }}
        initial={{ opacity: 0, y: 8 }}
        key={state}
        transition={{ duration: 0.2 }}
      >
        <motion.div
          animate={{ textShadow: [`0 0 8px ${config.color}80`, `0 0 16px ${config.color}40`, `0 0 8px ${config.color}80`] }}
          className="text-[10px] font-semibold tracking-[0.2em]"
          style={{ color: config.color }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          {LABELS[state]}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

function AiOrbComponent() {
  const orbState = useStore($jarvisOrbState)
  const status = useStore($jarvisSystemStatus)
  const config = ORB_CONFIG[orbState]
  const time = useAnimationTime()

  return (
    <motion.div
      animate={{
        scale: config.scale,
      }}
      className="relative flex items-center justify-center select-none"
      style={{ width: ORB_SIZE, height: ORB_SIZE + 40 }}
      transition={{ type: 'spring', stiffness: 250, damping: 18 }}
    >
      <div className="relative" style={{ width: ORB_SIZE, height: ORB_SIZE }}>
        <OrbGlow config={config} />
        <EnergyRings config={config} time={time} />
        <OrbParticles config={config} time={time} />
        <OrbCore config={config} />
        <div className="absolute -bottom-14 left-1/2 -translate-x-1/2 flex gap-4 text-[8px] text-white/20 tracking-wider">
          <span>CPU {Math.round(status.cpu)}%</span>
          <span>RAM {Math.round(status.memory.percent)}%</span>
        </div>
      </div>
      <StateLabel config={config} state={orbState} />
    </motion.div>
  )
}

function useAnimationTime() {
  const [time, setTime] = useState(0)
  const startRef = useRef(Date.now())

  useEffect(() => {
    let id: number

    const tick = () => {
      setTime(Date.now() - startRef.current)
      id = requestAnimationFrame(tick)
    }

    id = requestAnimationFrame(tick)

    return () => cancelAnimationFrame(id)
  }, [])

  return time
}

export const AiOrb = memo(AiOrbComponent)
