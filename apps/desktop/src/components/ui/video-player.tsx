import { useCallback, useRef, useState } from 'react'

import { mediaStreamUrl } from '@/lib/media'
import { cn } from '@/lib/utils'

export interface VideoPlayerProps {
  src: string
  fileName?: string
  className?: string
  poster?: string
  autoPlay?: boolean
  controls?: boolean
  onEnded?: () => void
}

export function VideoPlayer({
  src,
  fileName,
  className,
  poster,
  autoPlay,
  controls: showControls = true,
  onEnded
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const [playState, setPlayState] = useState<'idle' | 'loading' | 'playing' | 'paused' | 'ended'>('idle')
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const streamUrl = src.startsWith('blob:') || src.startsWith('data:') ? src : mediaStreamUrl(src)

  const togglePlay = useCallback(() => {
    if (!videoRef.current) {return}

    if (playState === 'playing') {
      videoRef.current.pause()
    } else {
      videoRef.current.play().catch(() => setError('Playback failed'))
    }
  }, [playState])

  const handleSeek = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!videoRef.current || !duration) {return}
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = (e.clientX - rect.left) / rect.width
    videoRef.current.currentTime = ratio * duration
  }, [duration])

  const toggleFullscreen = useCallback(async () => {
    if (!containerRef.current) {return}

    try {
      if (isFullscreen) {
        await document.exitFullscreen()
      } else {
        await containerRef.current.requestFullscreen()
      }
    } catch {
      // Fullscreen not available
    }
  }, [isFullscreen])

  const formatTime = (t: number) => {
    const h = Math.floor(t / 3600)
    const m = Math.floor((t % 3600) / 60)
    const s = Math.floor(t % 60)

    if (h > 0) {return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`}

    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-lg border bg-black',
        isFullscreen && 'fixed inset-0 z-50',
        className
      )}
      ref={containerRef}
    >
      <video
        className="h-full w-full object-contain"
        onDurationChange={e => setDuration(e.currentTarget.duration)}
        onEnded={() => {
          setPlayState('ended')
          onEnded?.()
        }}
        onError={() => setError('Failed to load video')}
        onLoadedMetadata={() => {
          if (autoPlay) {videoRef.current?.play().catch(() => {})}
        }}
        onPause={() => setPlayState('paused')}
        onPlay={() => setPlayState('playing')}
        onTimeUpdate={e => setCurrentTime(e.currentTarget.currentTime)}
        poster={poster}
        preload="metadata"
        ref={videoRef}
        src={streamUrl}
      />

      {playState === 'idle' && !poster && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20">
          <button
            className="flex h-12 w-12 items-center justify-center rounded-full bg-(--ui-accent, #6366f1) text-white opacity-80 transition-opacity hover:opacity-100"
            onClick={togglePlay}
            type="button"
          >
            <svg fill="currentColor" height="20" viewBox="0 0 20 20" width="20">
              <polygon points="5,2 17,10 5,18" />
            </svg>
          </button>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-sm text-red-400">
          {error}
        </div>
      )}

      {showControls && (
        <div className="absolute inset-x-0 bottom-0 flex flex-col gap-1 bg-gradient-to-t from-black/80 to-transparent p-3 opacity-0 transition-opacity group-hover:opacity-100">
          <div
            className="relative h-1 cursor-pointer rounded-full bg-white/30"
            onClick={handleSeek}
          >
            <div
              className="absolute left-0 top-0 h-full rounded-full bg-(--ui-accent, #6366f1)"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                className="text-white hover:text-(--ui-accent, #6366f1)"
                onClick={togglePlay}
                type="button"
              >
                {playState === 'playing' ? (
                  <svg fill="currentColor" height="16" viewBox="0 0 16 16" width="16">
                    <rect height="12" rx="1" width="4" x="3" y="2" />
                    <rect height="12" rx="1" width="4" x="9" y="2" />
                  </svg>
                ) : (
                  <svg fill="currentColor" height="16" viewBox="0 0 16 16" width="16">
                    <polygon points="4,2 14,8 4,14" />
                  </svg>
                )}
              </button>

              <span className="text-xs text-white/80">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                <svg fill="none" height="12" stroke="white" strokeWidth="1.5" viewBox="0 0 12 12" width="12">
                  <path d="M1 4.5v3M3.5 3v6M6 1.5v9M8.5 3v6M11 4.5v3" opacity={volume > 0.5 ? 1 : 0.3} />
                </svg>
                <input
                  className="h-1 w-16 cursor-pointer accent-(--ui-accent, #6366f1)"
                  max={1}
                  min={0}
                  onChange={e => {
                    const v = parseFloat(e.target.value)
                    setVolume(v)

                    if (videoRef.current) {videoRef.current.volume = v}
                  }}
                  step={0.01}
                  type="range"
                  value={volume}
                />
              </div>

              <button
                className="text-white/80 hover:text-white"
                onClick={toggleFullscreen}
                type="button"
              >
                <svg fill="none" height="14" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 14 14" width="14">
                  <path d="M2 5V2h3M9 2h3v3M12 9v3H9M5 12H2V9" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {fileName && (
        <div className="absolute left-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white/80">
          {fileName}
        </div>
      )}
    </div>
  )
}
