import { useStore } from '@nanostores/react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/utils'
import {
  $voiceAssistant,
  setAssistantMinimized,
  setAssistantSize,
  setFloatingAssistantPosition,
  setShowFloatingAssistant
} from '@/store/voice-assistant'
import {
  enumerateMicrophones,
  enumerateSpeakers
} from '@/store/voice-assistant'

const ASSISTANT_SIZES = {
  compact: { width: 48, height: 48 },
  normal: { width: 320, height: 480 },
  expanded: { width: 480, height: 640 }
}

export function FloatingAssistant() {
  const state = useStore($voiceAssistant)
  const dragRef = useRef<{ startX: number; startY: number; posX: number; posY: number } | null>(null)
  const [visible, setVisible] = useState(false)
  const [transcriptLines, setTranscriptLines] = useState<string[]>([])

  useEffect(() => {
    if (state.showFloatingAssistant) {
      enumerateMicrophones()
      enumerateSpeakers()
      setVisible(true)
    } else {
      setVisible(false)
    }
  }, [state.showFloatingAssistant])

  useEffect(() => {
    if (state.transcriptBuffer) {
      setTranscriptLines(prev => [...prev, state.transcriptBuffer].slice(-50))
    }
  }, [state.transcriptBuffer])

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      posX: state.floatingAssistantPosition.x,
      posY: state.floatingAssistantPosition.y
    }
    document.addEventListener('mousemove', handleDragMove)
    document.addEventListener('mouseup', handleDragEnd)
  }, [state.floatingAssistantPosition])

  const handleDragMove = useCallback((e: MouseEvent) => {
    if (!dragRef.current) {return}
    const dx = e.clientX - dragRef.current.startX
    const dy = e.clientY - dragRef.current.startY
    setFloatingAssistantPosition({
      x: dragRef.current.posX + dx,
      y: dragRef.current.posY + dy
    })
  }, [])

  const handleDragEnd = useCallback(() => {
    dragRef.current = null
    document.removeEventListener('mousemove', handleDragMove)
    document.removeEventListener('mouseup', handleDragEnd)
  }, [handleDragMove])

  const size = ASSISTANT_SIZES[state.assistantSize]

  if (!visible || state.activationMode === 'disabled') {return null}

  return (
    <div
      className={cn(
        'fixed z-50 overflow-hidden rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-elevated) shadow-2xl backdrop-blur-xl transition-all duration-200',
        state.assistantMinimized && 'cursor-pointer'
      )}
      style={{
        left: state.floatingAssistantPosition.x,
        top: state.floatingAssistantPosition.y,
        width: state.assistantMinimized ? 48 : size.width,
        height: state.assistantMinimized ? 48 : size.height
      }}
    >
      {state.assistantMinimized ? (
        <button
          className="flex h-full w-full items-center justify-center"
          onClick={() => setAssistantMinimized(false)}
          type="button"
        >
          <span className="relative flex h-3 w-3">
            <span className={cn(
              'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
              state.processingState === 'listening' ? 'bg-green-400' :
              state.processingState === 'processing' ? 'bg-blue-400' :
              state.processingState === 'speaking' ? 'bg-purple-400' : 'bg-gray-400'
            )} />
            <span className={cn(
              'relative inline-flex h-3 w-3 rounded-full',
              state.processingState === 'listening' ? 'bg-green-500' :
              state.processingState === 'processing' ? 'bg-blue-500' :
              state.processingState === 'speaking' ? 'bg-purple-500' : 'bg-gray-500'
            )} />
          </span>
        </button>
      ) : (
        <div className="flex h-full flex-col">
          <div
            className="flex cursor-grab items-center justify-between border-b border-(--ui-stroke-tertiary) px-3 py-2 active:cursor-grabbing"
            onMouseDown={handleDragStart}
          >
            <div className="flex items-center gap-2">
              <span className={cn(
                'relative flex h-2 w-2',
                state.processingState === 'listening' && 'animate-pulse'
              )}>
                <span className={cn(
                  'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
                  state.processingState === 'listening' ? 'bg-green-400' :
                  state.processingState === 'processing' ? 'bg-blue-400' : 'bg-gray-400'
                )} />
                <span className={cn(
                  'relative inline-flex h-2 w-2 rounded-full',
                  state.processingState === 'listening' ? 'bg-green-500' :
                  state.processingState === 'processing' ? 'bg-blue-500' : 'bg-gray-500'
                )} />
              </span>
              <span className="text-xs font-medium text-(--ui-text-secondary)">
                {state.processingState === 'idle' && 'Voice Assistant'}
                {state.processingState === 'listening' && 'Listening...'}
                {state.processingState === 'processing' && 'Processing...'}
                {state.processingState === 'speaking' && 'Speaking...'}
                {state.processingState === 'error' && 'Error'}
              </span>
            </div>
            <div className="flex items-center gap-1">
              {state.assistantSize !== 'compact' && (
                <button
                  className="rounded p-1 text-(--ui-text-tertiary) hover:bg-(--ui-bg-tertiary) hover:text-(--ui-text-primary)"
                  onClick={() => setAssistantSize(state.assistantSize === 'normal' ? 'expanded' : 'normal')}
                  title={state.assistantSize === 'normal' ? 'Expand' : 'Collapse'}
                  type="button"
                >
                  <svg className="size-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    {state.assistantSize === 'normal'
                      ? <path d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
                      : <path d="M4 8V4m0 0h4M4 4l5 5m11-4V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />}
                  </svg>
                </button>
              )}
              <button
                className="rounded p-1 text-(--ui-text-tertiary) hover:bg-(--ui-bg-tertiary) hover:text-(--ui-text-primary)"
                onClick={() => setAssistantMinimized(true)}
                title="Minimize"
                type="button"
              >
                <svg className="size-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M20 12H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
                </svg>
              </button>
              <button
                className="rounded p-1 text-(--ui-text-tertiary) hover:bg-(--ui-bg-tertiary) hover:text-(--ui-text-primary)"
                onClick={() => setShowFloatingAssistant(false)}
                title="Close"
                type="button"
              >
                <svg className="size-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
                </svg>
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            {transcriptLines.length === 0 && (
              <div className="flex h-full items-center justify-center">
                <p className="text-center text-xs text-(--ui-text-tertiary)">
                  {state.activationMode === 'push_to_talk'
                    ? `Press ${state.pushToTalkKey} to speak`
                    : state.activationMode === 'voice_activation'
                    ? `Say "${state.voiceActivationKeyword}" to activate`
                    : 'Voice assistant is active'}
                </p>
              </div>
            )}
            {transcriptLines.map((line, i) => (
              <div className="mb-1 rounded bg-(--ui-bg-quaternary) px-2 py-1 text-xs text-(--ui-text-secondary)" key={i}>
                {line}
              </div>
            ))}
          </div>

          {state.assistantSize !== 'compact' && (
            <div className="border-t border-(--ui-stroke-tertiary) px-3 py-2">
              <div className="flex items-center gap-2">
                <div className="flex h-1 flex-1 overflow-hidden rounded-full bg-(--ui-bg-tertiary)">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-75"
                    style={{ width: `${state.volumeLevel * 100}%` }}
                  />
                </div>
                <span className="text-[10px] tabular-nums text-(--ui-text-tertiary)">
                  {Math.round(state.latency)}ms
                </span>
                {state.microphoneState === 'muted' && (
                  <span className="text-[10px] text-red-400">Muted</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
