import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useCallback, useEffect, useRef, useState } from 'react'

import { Codicon } from '@/components/ui/codicon'
import {
  $jarvisExecution,
  $jarvisVoiceTranscript,
  addJarvisCommand,
  isJarvisExecutingState,
} from '@/store/jarvis-mode'

import { VoiceControls } from '../voice/voice-controls'

interface CommandInputProps {
  onCommand: (command: string) => void
}

const SUGGESTIONS = [
  { cmd: 'Research this company', icon: 'search', desc: 'Deep research on any organization' },
  { cmd: 'Write code for a landing page', icon: 'code', desc: 'Generate production-ready code' },
  { cmd: 'Fix the bug in main.py', icon: 'tools', desc: 'Analyze and fix code issues' },
  { cmd: 'Deploy to production', icon: 'cloud', desc: 'Build and deploy your project' },
  { cmd: 'Open project', icon: 'project', desc: 'Navigate to a workspace' },
  { cmd: 'Search memory', icon: 'database', desc: 'Query knowledge graph' },
  { cmd: 'Run workflow', icon: 'run-all', desc: 'Execute an automation' },
  { cmd: 'Start browser', icon: 'globe', desc: 'Launch browser agent' },
  { cmd: 'Launch terminal', icon: 'terminal', desc: 'Open command line' },
  { cmd: 'Analyze repository', icon: 'repo', desc: 'Full repo analysis' },
  { cmd: 'Connect API', icon: 'plug', desc: 'Integrate external service' },
  { cmd: 'Generate report', icon: 'graph', desc: 'Create analytics report' },
  { cmd: 'Create automation', icon: 'zap', desc: 'Build a background job' },
  { cmd: 'Monitor website', icon: 'eye', desc: 'Track site availability' },
  { cmd: 'Summarize notifications', icon: 'bell', desc: 'Catch up on alerts' },
]

function CommandInputComponent({ onCommand }: CommandInputProps) {
  const [value, setValue] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedSuggestion, setSelectedSuggestion] = useState(-1)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const voiceTranscript = useStore($jarvisVoiceTranscript)
  const executing = isJarvisExecutingState(useStore($jarvisExecution).state)

  const filteredSuggestions = value.trim()
    ? SUGGESTIONS.filter(s => s.cmd.toLowerCase().includes(value.toLowerCase())).slice(0, 6)
    : []

  useEffect(() => {
    if (voiceTranscript) {setValue(voiceTranscript)}
  }, [voiceTranscript])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClick)

    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleSubmit = useCallback((cmd?: string) => {
    const trimmed = (cmd ?? value).trim()

    if (!trimmed) {return}

    // Duplicate-submit guard: keep the text so nothing is lost.
    if (isJarvisExecutingState($jarvisExecution.get().state)) {return}
    addJarvisCommand(trimmed)
    onCommand(trimmed)
    setValue('')
    setShowSuggestions(false)
    setSelectedSuggestion(-1)
  }, [value, onCommand])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()

      if (showSuggestions && selectedSuggestion >= 0 && filteredSuggestions[selectedSuggestion]) {
        handleSubmit(filteredSuggestions[selectedSuggestion].cmd)
      } else {
        handleSubmit()
      }

      return
    }

    if (e.key === 'ArrowDown' && showSuggestions) {
      e.preventDefault()
      setSelectedSuggestion(prev => Math.min(prev + 1, filteredSuggestions.length - 1))

      return
    }

    if (e.key === 'ArrowUp' && showSuggestions) {
      e.preventDefault()
      setSelectedSuggestion(prev => Math.max(prev - 1, 0))

      return
    }

    if (e.key === 'Escape') {
      setShowSuggestions(false)
      setSelectedSuggestion(-1)

      return
    }
  }, [showSuggestions, selectedSuggestion, filteredSuggestions, handleSubmit])

  const handleChange = useCallback((val: string) => {
    setValue(val)
    setShowSuggestions(val.trim().length > 0)
    setSelectedSuggestion(-1)
  }, [])

  return (
    <div className="relative w-full max-w-3xl mx-auto">
      {/* Suggestions dropdown */}
      <AnimatePresence>
        {showSuggestions && filteredSuggestions.length > 0 && (
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="absolute bottom-full left-0 right-0 mb-2 rounded-2xl bg-black/80 backdrop-blur-2xl border border-white/[0.08] shadow-2xl overflow-hidden"
            exit={{ opacity: 0, y: -5 }}
            initial={{ opacity: 0, y: -5 }}
            ref={suggestionsRef}
          >
            <div className="p-1.5 space-y-0.5">
              {filteredSuggestions.map((s, i) => (
                <button
                  className={`flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-left transition-all ${
                    i === selectedSuggestion
                      ? 'bg-white/[0.08] text-white'
                      : 'text-white/50 hover:bg-white/[0.04] hover:text-white/70'
                  }`}
                  key={s.cmd}
                  onClick={() => { handleSubmit(s.cmd) }}
                  onMouseEnter={() => setSelectedSuggestion(i)}
                >
                  <Codicon className="size-3.5 text-white/30 shrink-0" name={s.icon} />
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] font-medium truncate">{s.cmd}</div>
                    <div className="text-[10px] text-white/25 truncate">{s.desc}</div>
                  </div>
                  <Codicon className="size-3 text-white/20 shrink-0" name="corner-down-left" />
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Glow border */}
      <div className="absolute -inset-px rounded-2xl bg-gradient-to-r from-[#0066ff]/20 via-[#00d4ff]/20 to-[#9933ff]/20 blur-sm opacity-60" />

      {/* Input bar */}
      <div className="relative flex items-end gap-2 p-3 rounded-2xl bg-black/60 border border-white/[0.08] backdrop-blur-xl">
        {/* Voice controls submit through the same gateway as typed text. */}
        <VoiceControls />

        {/* Text input */}
        <textarea
          className="flex-1 bg-transparent text-[14px] text-white/90 placeholder:text-white/20 resize-none outline-none min-h-[36px] max-h-[120px] py-1.5"
          onChange={e => handleChange(e.target.value)}
          onFocus={() => value.trim() && setShowSuggestions(true)}
          onKeyDown={handleKeyDown}
          placeholder="Command AetherOS..."
          ref={inputRef}
          rows={1}
          style={{ fieldSizing: 'content' } as React.CSSProperties}
          value={value}
        />

        {/* Send button */}
        <motion.button
          aria-label="Send command"
          className="flex items-center justify-center size-9 rounded-xl bg-gradient-to-r from-[#0066ff] to-[#00d4ff] text-white shrink-0 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
          disabled={!value.trim() || executing}
          onClick={() => handleSubmit()}
          title={executing ? 'A command is already running — press Esc to cancel it first' : undefined}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Codicon className="size-4" name="send" />
        </motion.button>
      </div>

      {/* Quick action chips */}
      <div className="flex items-center justify-center gap-2 mt-2">
        {['Research', 'Write code', 'Fix bug', 'Deploy', 'Summarize'].map(action => (
          <button
            className="px-2.5 py-1 rounded-lg text-[11px] text-white/25 bg-white/[0.03] border border-white/[0.05] hover:text-white/50 hover:bg-white/[0.06] transition-all"
            key={action}
            onClick={() => {
              setValue(action)
              setShowSuggestions(true)
              inputRef.current?.focus()
            }}
          >
            {action}
          </button>
        ))}
      </div>
    </div>
  )
}

export const CommandInput = memo(CommandInputComponent)
