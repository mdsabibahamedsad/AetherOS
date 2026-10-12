import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useJarvisVoice } from '@/lib/jarvis/voice/use-jarvis-voice'
import {
  $jarvisCommandHistory,
  $jarvisCommandIndex,
  $jarvisExecution,
  $jarvisOrbState,
  addJarvisCommand,
  addJarvisNotification,
  isJarvisExecutingState,
  setJarvisOrbState
} from '@/store/jarvis-mode'
import { $micPermission, $voiceError, $voiceInterim, $voiceState } from '@/store/jarvis-voice'

import { GlassPanel } from '../shared/glass-panel'

interface CommandBarProps {
  onCommand?: (command: string) => void
}

const SUGGESTIONS = [
  'Build my app',
  'Deploy to production',
  'Summarize documents',
  'Analyze repository',
  'Fix bugs in main.py',
  'Generate presentation',
  'Monitor server health',
  'Search memory',
  'Create automation',
  'Research competitors',
  'Write unit tests',
  'Optimize database'
]

function CommandBarComponent({ onCommand }: CommandBarProps) {
  const [input, setInput] = useState('')
  const [focused, setFocused] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [suggestionIdx, setSuggestionIdx] = useState(-1)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const navigate = useNavigate()
  const voice = useJarvisVoice(navigate)
  const voiceState = useStore($voiceState)
  const voiceError = useStore($voiceError)
  const interim = useStore($voiceInterim)
  const micPermission = useStore($micPermission)
  const listening = voiceState === 'LISTENING'
  const transcribing = voiceState === 'TRANSCRIBING'
  const commandHistory = useStore($jarvisCommandHistory)
  const commandIdx = useStore($jarvisCommandIndex)
  const orbState = useStore($jarvisOrbState)
  const executing = isJarvisExecutingState(useStore($jarvisExecution).state)
  void commandIdx

  // OS-global hotkey / Ctrl+Space lands here: focus the composer.
  useEffect(() => {
    const focus = () => inputRef.current?.focus()
    window.addEventListener('jarvis:focus-composer', focus)

    return () => window.removeEventListener('jarvis:focus-composer', focus)
  }, [])

  // Live interim transcript display while capturing.
  useEffect(() => {
    if (listening && interim) {
      setInput(interim)
    }
  }, [listening, interim])

  const filteredSuggestions = input.trim()
    ? SUGGESTIONS.filter(s => s.toLowerCase().includes(input.toLowerCase())).slice(0, 6)
    : focused ? SUGGESTIONS.slice(0, 6) : []

  const handleSend = useCallback(() => {
    const cmd = input.trim()

    if (!cmd) {return}

    // Duplicate-submit guard: keep the text so nothing is lost; the running
    // command owns the pipeline until it settles or Esc cancels it.
    if (isJarvisExecutingState($jarvisExecution.get().state)) {return}
    addJarvisCommand(cmd)
    setJarvisOrbState('thinking')
    onCommand?.(cmd)
    setInput('')
    setShowSuggestions(false)
  }, [input, onCommand])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (showSuggestions && filteredSuggestions.length > 0) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSuggestionIdx(prev => Math.min(prev + 1, filteredSuggestions.length - 1));

 return }

      if (e.key === 'ArrowUp') { e.preventDefault(); setSuggestionIdx(prev => Math.max(prev - 1, 0));

 return }

      if (e.key === 'Tab') { e.preventDefault();

 if (suggestionIdx >= 0) { setInput(filteredSuggestions[suggestionIdx]); setShowSuggestions(false); setSuggestionIdx(-1) };

 return }
    }

    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend();

 return }

    if (e.key === 'ArrowUp' && !input) {
      const hist = commandHistory

      if (hist.length > 0) { setInput(hist[0]); }

      return
    }

    if (e.key === 'Escape') { setShowSuggestions(false); inputRef.current?.blur();

 return }
  }, [showSuggestions, filteredSuggestions, suggestionIdx, input, commandHistory, handleSend])

  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); setDragging(true) }, [])
  const handleDragLeave = useCallback(() => setDragging(false), [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    const files = Array.from(e.dataTransfer.files)

    if (files.length > 0) {
      const names = files.map(f => f.name).join(', ')
      setInput(prev => prev + ` [${names}]`)
      addJarvisNotification({ title: 'Files Dropped', message: `${files.length} file(s) attached`, type: 'info' })
    }

    const text = e.dataTransfer.getData('text')

    if (text) {setInput(prev => prev + text)}
  }, [])

  const autoResize = useCallback(() => {
    const el = inputRef.current

    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`
    }
  }, [])

  useEffect(() => { autoResize() }, [input, autoResize])

  return (
    <div className="relative px-4 pb-4">
      {/* Drag & drop overlay */}
      <AnimatePresence>
        {dragging && (
          <motion.div
            animate={{ opacity: 1 }}
            className="absolute inset-0 rounded-2xl border-2 border-dashed border-[#00d4ff]/40 bg-[#00d4ff]/5 flex items-center justify-center z-20"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <div className="text-center">
              <span className="codicon codicon-file-add text-3xl text-[#00d4ff]/40" />
              <div className="text-[13px] text-white/40 mt-2">Drop files, images, or code here</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Suggestions dropdown */}
      <AnimatePresence>
        {showSuggestions && filteredSuggestions.length > 0 && (
          <motion.div
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className="absolute bottom-full left-4 right-4 mb-2 rounded-xl bg-black/80 backdrop-blur-2xl border border-white/[0.08] overflow-hidden shadow-2xl"
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
          >
            <div className="py-1">
              {filteredSuggestions.map((s, i) => (
                <button
                  className={`w-full flex items-center gap-3 px-3 py-2 text-left text-[13px] transition-all
                    ${i === suggestionIdx ? 'bg-white/[0.08] text-white' : 'text-white/50 hover:bg-white/[0.04] hover:text-white/70'}`}
                  key={s}
                  onClick={() => { setInput(s); setShowSuggestions(false); inputRef.current?.focus() }}
                  onMouseEnter={() => setSuggestionIdx(i)}
                >
                  <span className="codicon codicon-sparkle text-sm text-white/20" />
                  {s}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input bar */}
      <GlassPanel
        className={`p-2 rounded-2xl transition-all duration-300
          ${dragging ? 'ring-2 ring-[#00d4ff]/40' : focused ? 'ring-1 ring-white/[0.08]' : ''}
          ${listening ? 'shadow-[0_0_20px_rgba(0,212,255,0.1)]' : ''}`}
        glow={orbState === 'listening' || listening ? 'cyan' : 'none'}
        intensity="heavy"
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {/* Voice button: real capture through the shared voice hook.
            Click toggles a single utterance; hold for push-to-talk. */}
        <button
          aria-label={listening ? 'Stop listening' : 'Start voice command'}
          className={`flex items-center justify-center size-9 rounded-xl transition-all shrink-0
            ${listening ? 'bg-emerald-500/20 text-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.3)]' : 'text-white/30 hover:text-white/60 hover:bg-white/[0.06]'}`}
          onClick={() => {
            if (listening || transcribing) {voice.stop()}
            else {void voice.start()}
          }}
          onMouseDown={() => {
            if (!listening && !transcribing) {void voice.start()}
          }}
          onMouseUp={() => {
            if (listening) {voice.stop()}
          }}
          title={micPermission === 'denied' ? 'Microphone access is disabled — open system privacy settings' : 'Voice command (same pipeline as typed text)'}
        >
          <span className="codicon codicon-microphone text-lg" />
        </button>

        {/* Textarea */}
        <div className="flex-1 relative">
          <textarea
            className="w-full bg-transparent text-[13px] text-white/70 placeholder:text-white/15 outline-none resize-none py-2 px-1 max-h-[120px] leading-relaxed"
            onBlur={() => setTimeout(() => { setFocused(false); setShowSuggestions(false) }, 200)}
            onChange={e => { setInput(e.target.value); setShowSuggestions(true); setSuggestionIdx(-1) }}
            onFocus={() => { setFocused(true); setShowSuggestions(true) }}
            onKeyDown={handleKeyDown}
            placeholder={listening ? 'Listening... speak now' : transcribing ? 'Transcribing...' : 'Command your mission...'}
            ref={inputRef}
            rows={1}
            value={input}
          />
          {listening && (
            <div className="flex items-center gap-1 mt-1" role="status">
              <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] text-emerald-400/60">Listening — microphone is live</span>
            </div>
          )}
          {transcribing && (
            <div className="flex items-center gap-1 mt-1" role="status">
              <span className="size-1.5 rounded-full bg-sky-400 animate-pulse" />
              <span className="text-[10px] text-sky-400/60">Transcribing...</span>
            </div>
          )}
          {voiceState === 'ERROR' && voiceError && (
            <div className="flex items-center gap-1 mt-1" role="alert">
              <span className="size-1.5 rounded-full bg-red-400" />
              <span className="text-[10px] text-red-400/80">{voiceError}</span>
            </div>
          )}
        </div>

        {/* Attachment button */}
        <button
          aria-label="Attach files"
          className="flex items-center justify-center size-9 rounded-xl text-white/30 hover:text-white/60 hover:bg-white/[0.06] transition-all shrink-0"
          title="Attach files"
        >
          <span className="codicon codicon-attach text-lg" />
        </button>

        {/* Send button */}
        <button
          aria-label="Send command"
          className={`flex items-center justify-center size-9 rounded-xl transition-all shrink-0
            ${input.trim()
              ? 'bg-gradient-to-r from-[#0066ff] to-[#00d4ff] text-white shadow-[0_0_12px_rgba(0,102,255,0.3)] hover:shadow-[0_0_20px_rgba(0,102,255,0.4)]'
              : 'bg-white/[0.04] text-white/20'}`}
          disabled={!input.trim() || executing}
          onClick={handleSend}
          title={executing ? 'A command is already running — press Esc to cancel it first' : undefined}
        >
          <span className="codicon codicon-send text-sm" />
        </button>
      </GlassPanel>

      {/* Quick action chips */}
      <div className="flex items-center gap-2 mt-2 px-1">
        {['Build', 'Deploy', 'Analyze', 'Monitor'].map(chip => (
          <GlassPanel
            border={false}
            className="overflow-hidden"
            glow="none"
            intensity="light"
            key={chip}
          >
            <button
              className="px-2.5 py-1 rounded-lg text-[10px] font-medium text-white/20 hover:text-white/40 transition-all cursor-pointer"
              onClick={() => { setInput(chip + ' '); inputRef.current?.focus() }}
            >
              {chip}
            </button>
          </GlassPanel>
        ))}
        <div className="flex-1" />
        <div className="text-[9px] text-white/10">
          {voiceState !== 'IDLE' && voiceState !== 'CANCELLED' ? `🎤 ${voiceState.toLowerCase()}` : 'Ctrl+K to search · Ctrl+Space to focus'}
        </div>
      </div>
    </div>
  )
}

export const CommandBar = memo(CommandBarComponent)
