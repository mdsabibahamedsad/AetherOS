import { useCallback, useEffect, useRef, useState } from 'react'

import { mediaStreamUrl } from '@/lib/media'
import { cn } from '@/lib/utils'

export interface AudioPlayerProps {
  src: string
  fileName?: string
  className?: string
  autoPlay?: boolean
  onEnded?: () => void
}

type PlayState = 'idle' | 'loading' | 'playing' | 'paused' | 'ended'

export function AudioPlayer({ src, fileName, className, autoPlay, onEnded }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null)
  const ctxRef = useRef<AudioContext | null>(null)
  const rafRef = useRef<number>(0)

  const [playState, setPlayState] = useState<PlayState>('idle')
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [playbackRate, setPlaybackRate] = useState(1)
  const [error, setError] = useState<string | null>(null)

  const streamUrl = src.startsWith('blob:') || src.startsWith('data:') ? src : mediaStreamUrl(src)

  const drawWaveform = useCallback(() => {
    if (!canvasRef.current || !analyserRef.current) {return}
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}

    const analyser = analyserRef.current
    const bufferLength = analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    analyser.getByteTimeDomainData(dataArray)

    ctx.fillStyle = 'transparent'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.lineWidth = 2
    ctx.strokeStyle = 'var(--ui-accent, #6366f1)'
    ctx.beginPath()

    const sliceWidth = canvas.width / bufferLength
    let x = 0

    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0
      const y = (v * canvas.height) / 2

      if (i === 0) {ctx.moveTo(x, y)}
      else {ctx.lineTo(x, y)}

      x += sliceWidth
    }

    ctx.lineTo(canvas.width, canvas.height / 2)
    ctx.stroke()

    rafRef.current = requestAnimationFrame(drawWaveform)
  }, [])

  const setupAnalyser = useCallback(() => {
    if (!audioRef.current) {return}

    try {
      if (!ctxRef.current) {
        ctxRef.current = new AudioContext()
      }

      const ctx = ctxRef.current
      const source = ctx.createMediaElementSource(audioRef.current)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyser.connect(ctx.destination)
      analyserRef.current = analyser
      sourceRef.current = source
      drawWaveform()
    } catch {
      // Analyser not supported; playback works without waveform
    }
  }, [drawWaveform])

  const togglePlay = useCallback(() => {
    if (!audioRef.current) {return}

    if (playState === 'playing') {
      audioRef.current.pause()
    } else {
      audioRef.current.play().catch(() => setError('Playback failed'))
    }
  }, [playState])

  const handleSeek = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || !duration) {return}
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = (e.clientX - rect.left) / rect.width
    audioRef.current.currentTime = ratio * duration
  }, [duration])

  useEffect(() => {
    const audio = audioRef.current

    if (!audio) {return}

    const onLoad = () => {
      setDuration(audio.duration)
      setPlayState('idle')
      setError(null)
    }

    const onPlay = () => {
      setPlayState('playing')
      setupAnalyser()
    }

    const onPause = () => setPlayState('paused')

    const onEnded = () => {
      setPlayState('ended')
      onEnded?.()
    }

    const onTimeUpdate = () => setCurrentTime(audio.currentTime)
    const onError = () => setError('Failed to load audio')

    audio.addEventListener('loadedmetadata', onLoad)
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('ended', onEnded)
    audio.addEventListener('timeupdate', onTimeUpdate)
    audio.addEventListener('error', onError)

    if (autoPlay) {
      audio.play().catch(() => {})
    }

    return () => {
      audio.removeEventListener('loadedmetadata', onLoad)
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('ended', onEnded)
      audio.removeEventListener('timeupdate', onTimeUpdate)
      audio.removeEventListener('error', onError)

      if (rafRef.current) {cancelAnimationFrame(rafRef.current)}

      if (ctxRef.current) {ctxRef.current.close()}
    }
  }, [autoPlay, onEnded, setupAnalyser])

  const formatTime = (t: number) => {
    const m = Math.floor(t / 60)
    const s = Math.floor(t % 60)

    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className={cn('flex flex-col gap-2 rounded-lg border p-3', className)}>
      <div className="flex items-center gap-2 text-xs text-(--ui-text-tertiary)">{fileName || 'Audio'}</div>

      <canvas className="h-8 w-full rounded" height={32} ref={canvasRef} width={300} />

      <div
        className="relative h-1 cursor-pointer rounded-full bg-(--ui-stroke-tertiary)"
        onClick={handleSeek}
      >
        <div
          className="absolute left-0 top-0 h-full rounded-full bg-(--ui-accent, #6366f1) transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-(--ui-text-tertiary)">{formatTime(currentTime)}</span>

        <button
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-full transition-colors',
            playState === 'playing'
              ? 'bg-(--ui-accent, #6366f1) text-white'
              : 'bg-(--ui-stroke-tertiary) hover:bg-(--ui-stroke-secondary)'
          )}
          disabled={playState === 'loading' || !!error}
          onClick={togglePlay}
          type="button"
        >
          {playState === 'playing' ? (
            <svg fill="currentColor" height="14" viewBox="0 0 14 14" width="14">
              <rect height="10" rx="1" width="3.5" x="2" y="2" />
              <rect height="10" rx="1" width="3.5" x="8.5" y="2" />
            </svg>
          ) : (
            <svg fill="currentColor" height="14" viewBox="0 0 14 14" width="14">
              <polygon points="3,1 13,7 3,13" />
            </svg>
          )}
        </button>

        <span className="text-xs text-(--ui-text-tertiary)">{formatTime(duration)}</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <button
            className="text-(--ui-text-tertiary) hover:text-foreground"
            onClick={() => {
              const next = Math.max(0.25, playbackRate - 0.25)
              setPlaybackRate(next)

              if (audioRef.current) {audioRef.current.playbackRate = next}
            }}
            type="button"
          >
            <svg fill="none" height="12" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 12 12" width="12">
              <path d="M6 2L2 6l4 4" />
            </svg>
          </button>
          <span className="min-w-[2rem] text-center text-xs tabular-nums text-(--ui-text-secondary)">
            {playbackRate}x
          </span>
          <button
            className="text-(--ui-text-tertiary) hover:text-foreground"
            onClick={() => {
              const next = Math.min(4, playbackRate + 0.25)
              setPlaybackRate(next)

              if (audioRef.current) {audioRef.current.playbackRate = next}
            }}
            type="button"
          >
            <svg fill="none" height="12" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 12 12" width="12">
              <path d="M6 10L10 6 6 2" />
            </svg>
          </button>
        </div>

        <div className="flex flex-1 items-center gap-1">
          <svg fill="none" height="12" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 12 12" width="12">
            <path d="M1 4.5v3M3.5 3v6M6 1.5v9M8.5 3v6M11 4.5v3" opacity={volume > 0.5 ? 1 : 0.3} />
          </svg>
          <input
            className="h-1 flex-1 cursor-pointer accent-(--ui-accent, #6366f1)"
            max={1}
            min={0}
            onChange={e => {
              const v = parseFloat(e.target.value)
              setVolume(v)

              if (audioRef.current) {audioRef.current.volume = v}
            }}
            step={0.01}
            type="range"
            value={volume}
          />
        </div>
      </div>

      {error && <div className="text-xs text-(--ui-error)">{error}</div>}

      <audio preload="metadata" ref={audioRef} src={streamUrl} />
    </div>
  )
}
