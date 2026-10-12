/**
 * VoiceControls — thin view over the shared voice hook.
 *
 * There is exactly one voice implementation (`useJarvisVoice`): transcripts
 * captured here are submitted to the universal command gateway with
 * `inputType: 'voice'`. The waveform renders the LIVE microphone level from
 * an AnalyserNode — when no capture is active it renders idle dots, never a
 * fake animation.
 */

import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Codicon } from '@/components/ui/codicon'
import { getVoiceMicLevel, useJarvisVoice } from '@/lib/jarvis/voice/use-jarvis-voice'
import { $jarvisVoiceTranscript } from '@/store/jarvis-mode'
import { $voiceError, $voiceState } from '@/store/jarvis-voice'

function VoiceVisualizer({ live }: { live: boolean }) {
  const [, setTick] = useState(0)
  const levelRef = useRef(0)

  useEffect(() => {
    if (!live) {return}

    let raf = 0

    const loop = () => {
      levelRef.current = getVoiceMicLevel()
      setTick(t => t + 1)
      raf = requestAnimationFrame(loop)
    }

    raf = requestAnimationFrame(loop)

    return () => cancelAnimationFrame(raf)
  }, [live])

  return (
    <div aria-label={live ? 'Microphone level' : 'Microphone idle'} className="flex items-center justify-center gap-0.5 h-8 px-4" role="img">
      {Array.from({ length: 24 }, (_, i) => {
        const falloff = 1 - Math.abs(i - 11.5) / 14
        const height = live ? Math.max(3, levelRef.current * 28 * falloff + 2) : 3

        return (
          <div
            className="w-0.5 rounded-full bg-[#00d4ff] transition-[height] duration-75"
            key={i}
            style={{ height, opacity: live ? 0.4 + levelRef.current * 0.6 : 0.2 }}
          />
        )
      })}
    </div>
  )
}

function VoiceControlsComponent() {
  const navigate = useNavigate()
  const voice = useJarvisVoice(navigate)
  const voiceState = useStore($voiceState)
  const voiceError = useStore($voiceError)
  const voiceTranscript = useStore($jarvisVoiceTranscript)
  const live = voiceState === 'LISTENING'

  useEffect(() => () => voice.cancel(), [voice])

  const handleToggle = useCallback(() => {
    if (live || voiceState === 'TRANSCRIBING') {voice.stop()}
    else {void voice.start()}
  }, [live, voiceState, voice])

  return (
    <div className="relative">
      <AnimatePresence>
        {(live || voiceState === 'TRANSCRIBING') && (
          <motion.div
            animate={{ opacity: 1, scale: 1 }}
            className="absolute -top-24 left-1/2 -translate-x-1/2 bg-black/80 backdrop-blur-xl border border-[#00d4ff]/30 rounded-2xl p-4 shadow-lg shadow-[#00d4ff]/10"
            exit={{ opacity: 0, scale: 0.9 }}
            initial={{ opacity: 0, scale: 0.9 }}
          >
            <div className="flex flex-col items-center gap-2">
              <div className="flex items-center gap-2">
                <motion.div
                  animate={{ scale: [1, 1.3, 1], opacity: [0.8, 0.3, 0.8] }}
                  className="size-2 rounded-full bg-[#00d4ff]"
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                <span className="text-[11px] text-white/50 font-medium">
                  {live ? 'Listening... microphone is live' : 'Transcribing...'}
                </span>
              </div>
              <VoiceVisualizer live={live} />
              {voiceTranscript && (
                <div className="text-[12px] text-white/60 max-w-[200px] text-center truncate">
                  "{voiceTranscript}"
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {voiceState === 'ERROR' && voiceError && (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-red-500/30 bg-red-500/10 px-2 py-1 text-[10px] text-red-300" role="alert">
          {voiceError}
        </div>
      )}

      <button
        aria-label={live ? 'Stop listening' : 'Start voice command'}
        className={`flex items-center justify-center size-9 rounded-xl transition-all shrink-0 ${
          live
            ? 'bg-[#00d4ff]/30 text-[#00d4ff] border border-[#00d4ff]/50 shadow-[0_0_12px_#00d4ff40]'
            : 'bg-white/[0.05] text-white/30 hover:text-white/60 border border-transparent'
        }`}
        onClick={handleToggle}
        title="Voice command (same pipeline as typed text)"
      >
        <Codicon
          className={`size-4 ${live ? 'animate-pulse' : ''}`}
          name="mic"
        />
      </button>
    </div>
  )
}

export const VoiceControls = memo(VoiceControlsComponent)
