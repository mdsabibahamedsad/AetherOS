/**
 * Jarvis memory panel — a real interface to the agent memory subsystem.
 *
 * There is no direct memory REST API for the renderer; recall and store run
 * through the universal command gateway (the agent's memory provider answers
 * from real stored memories). Results shown here are genuine gateway
 * responses for this session — never sample entries.
 */

import { memo, useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Codicon } from '@/components/ui/codicon'
import { submitJarvisCommand } from '@/lib/jarvis/core/command-gateway'
import { createDesktopCommandDeps } from '@/lib/jarvis/os/local-executor'

interface MemoryResult {
  id: string
  query: string
  text: string
  at: number
}

function MemoryViewComponent() {
  const [searchQuery, setSearchQuery] = useState('')
  const [rememberText, setRememberText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<MemoryResult[]>([])
  const navigate = useNavigate()

  const run = useCallback(async (command: string) => {
    setBusy(true)
    setError(null)

    try {
      const outcome = await submitJarvisCommand(command, {
        inputType: 'text',
        deps: createDesktopCommandDeps(navigate)
      })

      if (outcome.kind === 'gateway') {
        setResults(prev => [{
          id: `mem-${Date.now()}`,
          query: command,
          text: outcome.response,
          at: Date.now()
        }, ...prev].slice(0, 20))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Memory request failed.')
    } finally {
      setBusy(false)
    }
  }, [navigate])

  const recall = useCallback(() => {
    const q = searchQuery.trim()

    if (q && !busy) {void run(`Recall from memory: ${q}`)}
  }, [searchQuery, busy, run])

  const remember = useCallback(() => {
    const fact = rememberText.trim()

    if (fact && !busy) {
      void run(`Remember this: ${fact}`).then(() => setRememberText(''))
    }
  }, [rememberText, busy, run])

  return (
    <div className="h-full flex flex-col p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white/90">Memory</h2>
        <p className="text-[12px] text-white/30 mt-0.5">Agent memory — recall and store through the live gateway</p>
      </div>

      <div className="relative mb-2">
        <Codicon className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-white/20" name="search" />
        <input
          className="w-full pl-9 pr-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-[13px] text-white/70 placeholder:text-white/20 outline-none focus:border-[#00d4ff]/40 transition-colors"
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') {recall()}
          }}
          placeholder="Recall memories..."
          value={searchQuery}
        />
      </div>

      <div className="flex gap-2 mb-4">
        <input
          className="flex-1 px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-[13px] text-white/70 placeholder:text-white/20 outline-none focus:border-[#00d4ff]/40 transition-colors"
          onChange={e => setRememberText(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') {remember()}
          }}
          placeholder="Remember something..."
          value={rememberText}
        />
        <button
          className="rounded-xl bg-gradient-to-r from-[#0066ff] to-[#00d4ff] px-3 py-2 text-[12px] font-medium text-white disabled:opacity-40"
          disabled={!rememberText.trim() || busy}
          onClick={remember}
        >
          Remember
        </button>
      </div>

      {error && (
        <div className="mb-3 rounded-lg border border-red-500/30 bg-red-500/[0.06] px-3 py-2 text-[12px] text-red-300" role="alert">
          {error}
        </div>
      )}

      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] text-white/25 uppercase tracking-wider">Results</span>
        <div className="flex-1 h-px bg-white/[0.06]" />
        <span className="text-[10px] text-white/20">{results.length} items</span>
      </div>

      <div className="space-y-2 flex-1 overflow-y-auto scrollbar-dt">
        {busy && <div className="text-[12px] text-white/30 px-1">Asking the agent...</div>}
        {results.map(res => (
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]" key={res.id}>
            <div className="text-[11px] text-[#00d4ff]/70 truncate">{res.query}</div>
            <div className="text-[12px] text-white/60 mt-1 whitespace-pre-wrap">{res.text.slice(0, 1200)}</div>
          </div>
        ))}
        {!busy && results.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Codicon className="size-10 text-white/[0.06] mb-3" name="database" />
            <span className="text-[13px] text-white/20">No recalls yet this session</span>
            <span className="text-[11px] text-white/15 mt-1">Search above — the agent answers from real stored memory</span>
          </div>
        )}
      </div>
    </div>
  )
}

export const MemoryView = memo(MemoryViewComponent)
