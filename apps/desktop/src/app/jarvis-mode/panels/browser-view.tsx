/**
 * Jarvis browser panel — honest about what it is.
 *
 * There is no embedded browser engine here: real browser automation runs in
 * the gateway agent (browser_* tools with streamed tool events). This panel
 * offers the two truthful actions: open a validated https URL in the system
 * browser, or hand a research/interaction goal to the Jarvis agent through
 * the universal command gateway. No fake navigation buttons.
 */

import { memo, useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Codicon } from '@/components/ui/codicon'
import { submitJarvisCommand } from '@/lib/jarvis/core/command-gateway'
import { openValidatedUrl } from '@/lib/jarvis/os/app-launcher'
import { createDesktopCommandDeps } from '@/lib/jarvis/os/local-executor'
import { addJarvisNotification } from '@/store/jarvis-mode'

function BrowserViewComponent() {
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const openExternal = useCallback(async () => {
    const target = url.trim()

    if (!target) {return}
    setError(null)

    try {
      const opened = target.match(/^https?:\/\//i)
        ? await openValidatedUrl(target, { openExternal: u => window.aetherosDesktop.openExternal(u) })
        : await openValidatedUrl(`https://www.google.com/search?q=${encodeURIComponent(target)}`, {
          openExternal: u => window.aetherosDesktop.openExternal(u)
        })

      addJarvisNotification({ title: 'Browser', message: `Opened ${opened}`, type: 'info' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not open that address.')
    }
  }, [url])

  const researchWithAgent = useCallback(async () => {
    const goal = url.trim()

    if (!goal || busy) {return}
    setError(null)
    setBusy(true)

    try {
      await submitJarvisCommand(`Research this in the browser: ${goal}`, {
        inputType: 'text',
        deps: createDesktopCommandDeps(navigate)
      })
      setUrl('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Research task failed to start.')
    } finally {
      setBusy(false)
    }
  }, [url, busy, navigate])

  return (
    <div className="h-full flex flex-col p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-white/90">Browser</h2>
        <p className="text-[12px] text-white/30 mt-0.5">Web browsing agent — runs in the gateway with live tool events</p>
      </div>

      <div className="flex items-center gap-2 p-2 rounded-xl bg-white/[0.04] border border-white/[0.06] mb-3">
        <Codicon className="size-4 text-white/20 shrink-0" name="globe" />
        <input
          className="flex-1 bg-transparent text-[13px] text-white/70 placeholder:text-white/20 outline-none"
          onChange={e => setUrl(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') {void researchWithAgent()}
          }}
          placeholder="Enter URL or research goal..."
          value={url}
        />
      </div>

      <div className="flex items-center gap-2 mb-4">
        <button
          className="rounded-lg bg-gradient-to-r from-[#0066ff] to-[#00d4ff] px-3 py-1.5 text-[12px] font-medium text-white disabled:opacity-40"
          disabled={!url.trim() || busy}
          onClick={() => void researchWithAgent()}
        >
          {busy ? 'Agent working...' : 'Research with agent'}
        </button>
        <button
          className="rounded-lg border border-white/10 px-3 py-1.5 text-[12px] text-white/50 hover:bg-white/[0.06] hover:text-white/80 disabled:opacity-40"
          disabled={!url.trim() || busy}
          onClick={() => void openExternal()}
        >
          Open in system browser
        </button>
      </div>

      {error && (
        <div className="mb-3 rounded-lg border border-red-500/30 bg-red-500/[0.06] px-3 py-2 text-[12px] text-red-300" role="alert">
          {error}
        </div>
      )}

      <div className="flex-1 rounded-xl bg-black/30 border border-white/[0.06] flex items-center justify-center">
        <div className="text-center px-6">
          <Codicon className="size-12 text-white/[0.06] mx-auto mb-3" name="globe" />
          <p className="text-[13px] text-white/20">Agent browser runs gateway-side</p>
          <p className="text-[11px] text-white/15 mt-1">Navigation, clicks, extraction and downloads stream as real tool events in the Execution Timeline</p>
        </div>
      </div>
    </div>
  )
}

export const BrowserView = memo(BrowserViewComponent)
