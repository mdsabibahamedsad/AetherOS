import { useStore } from '@nanostores/react'
import { memo, useEffect, useRef } from 'react'

import { $jarvisOrbState, type OrbState } from '@/store/jarvis-mode'

function AuroraLayer() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!canvas || !ctx) {return}

    let animId: number
    let time = 0
    let w = 0, h = 0

    const resize = () => {
      w = canvas.width = window.innerWidth * (window.devicePixelRatio || 1)
      h = canvas.height = window.innerHeight * (window.devicePixelRatio || 1)
      canvas.style.width = window.innerWidth + 'px'
      canvas.style.height = window.innerHeight + 'px'
      ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1)
    }

    resize()
    window.addEventListener('resize', resize)

    const draw = () => {
      time += 0.003
      ctx.clearRect(0, 0, w, h)

      const auroras = [
        { x: w * 0.3, y: h * 0.15, color1: 'rgba(0, 212, 255, 0.03)', color2: 'rgba(153, 51, 255, 0.02)', speed: 0.5 },
        { x: w * 0.7, y: h * 0.25, color1: 'rgba(0, 102, 255, 0.02)', color2: 'rgba(0, 212, 255, 0.015)', speed: 0.3 },
        { x: w * 0.5, y: h * 0.1, color1: 'rgba(153, 51, 255, 0.02)', color2: 'rgba(0, 212, 255, 0.01)', speed: 0.4 },
      ]

      for (const aurora of auroras) {
        const gradient = ctx.createRadialGradient(
          aurora.x + Math.sin(time * aurora.speed) * 100,
          aurora.y + Math.cos(time * aurora.speed * 0.7) * 50,
          0,
          aurora.x + Math.sin(time * aurora.speed) * 100,
          aurora.y + Math.cos(time * aurora.speed * 0.7) * 50,
          400,
        )

        gradient.addColorStop(0, aurora.color1)
        gradient.addColorStop(0.5, aurora.color2)
        gradient.addColorStop(1, 'transparent')
        ctx.fillStyle = gradient
        ctx.fillRect(0, 0, window.innerWidth, window.innerHeight)
      }

      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => { cancelAnimationFrame(animId); window.removeEventListener('resize', resize) }
  }, [])

  return <canvas className="fixed inset-0 pointer-events-none" ref={canvasRef} style={{ zIndex: 0 }} />
}

function ConstellationLayer() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!canvas || !ctx) {return}

    const stars: Array<{ x: number; y: number; size: number; speed: number; phase: number; brightness: number }> = []
    const STAR_COUNT = 100
    const CONNECTION_DIST = 150
    let animId: number
    let w = 0, h = 0

    const resize = () => {
      w = canvas.width = window.innerWidth
      h = canvas.height = window.innerHeight
      stars.length = 0

      for (let i = 0; i < STAR_COUNT; i++) {
        stars.push({
          x: Math.random() * w,
          y: Math.random() * h,
          size: 0.5 + Math.random() * 1.5,
          speed: 0.2 + Math.random() * 0.3,
          phase: Math.random() * Math.PI * 2,
          brightness: 0.2 + Math.random() * 0.4,
        })
      }
    }

    resize()
    window.addEventListener('resize', resize)

    let time = 0

    const draw = () => {
      time += 0.01
      ctx.clearRect(0, 0, w, h)

      for (let i = 0; i < stars.length; i++) {
        const s = stars[i]
        const twinkle = Math.sin(time * s.speed + s.phase) * 0.3 + 0.7
        const alpha = s.brightness * twinkle * 0.4

        ctx.beginPath()
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`
        ctx.fill()

        for (let j = i + 1; j < stars.length; j++) {
          const other = stars[j]
          const dx = other.x - s.x
          const dy = other.y - s.y
          const dist = Math.sqrt(dx * dx + dy * dy)

          if (dist < CONNECTION_DIST) {
            ctx.beginPath()
            ctx.moveTo(s.x, s.y)
            ctx.lineTo(other.x, other.y)
            ctx.strokeStyle = `rgba(255, 255, 255, ${(1 - dist / CONNECTION_DIST) * 0.06})`
            ctx.lineWidth = 0.3
            ctx.stroke()
          }
        }
      }

      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => { cancelAnimationFrame(animId); window.removeEventListener('resize', resize) }
  }, [])

  return <canvas className="fixed inset-0 pointer-events-none" ref={canvasRef} style={{ zIndex: 1 }} />
}

function PulseRingLayer({ state }: { state: OrbState }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const ringsRef = useRef<Array<{ x: number; y: number; radius: number; maxRadius: number; opacity: number; color: string; speed: number }>>([])

  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!canvas || !ctx) {return}
    let animId: number

    const COLORS: Record<OrbState, string> = {
      idle: '#00d4ff', listening: '#00d4ff', thinking: '#a78bfa', planning: '#0066ff',
      executing: '#22c55e', speaking: '#00d4ff', searching: '#f59e0b', coding: '#0066ff',
      error: '#ef4444', success: '#22c55e',
    }

    const cx = window.innerWidth / 2
    const cy = window.innerHeight / 2

    if (state !== 'idle') {
      ringsRef.current.push({
        x: cx, y: cy, radius: 140, maxRadius: Math.min(window.innerWidth, window.innerHeight) * 0.4,
        opacity: 0.3, color: COLORS[state], speed: 0.5 + Math.random() * 0.5,
      })

      if (ringsRef.current.length > 20) {ringsRef.current = ringsRef.current.slice(-20)}
    }

    const draw = () => {
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)

      ringsRef.current = ringsRef.current.filter(r => r.opacity > 0.01)

      for (const ring of ringsRef.current) {
        ring.radius += ring.speed * 2
        ring.opacity *= 0.98

        ctx.beginPath()
        ctx.arc(ring.x, ring.y, ring.radius, 0, Math.PI * 2)
        ctx.strokeStyle = ring.color
        ctx.globalAlpha = ring.opacity * 0.3
        ctx.lineWidth = 1
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(ring.x, ring.y, ring.radius * 0.8, 0, Math.PI * 2)
        ctx.strokeStyle = ring.color
        ctx.globalAlpha = ring.opacity * 0.1
        ctx.lineWidth = 0.5
        ctx.stroke()
        ctx.globalAlpha = 1
      }

      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => cancelAnimationFrame(animId)
  }, [state])

  return <canvas className="fixed inset-0 pointer-events-none" ref={canvasRef} style={{ zIndex: 2 }} />
}

function BackgroundSystemComponent() {
  const orbState = useStore($jarvisOrbState)

  return (
    <>
      <AuroraLayer />
      <ConstellationLayer />
      <PulseRingLayer state={orbState} />
    </>
  )
}

export const BackgroundSystem = memo(BackgroundSystemComponent)
