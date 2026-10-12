/**
 * Jarvis terminal panel — a REAL PTY session, not a mock.
 *
 * Spawns through the same main-process PTY IPC as the main terminal
 * (`aetheros:terminal:start/write/dispose` + data/exit subscriptions).
 * Output streams live, the exit code is reported from the real process event,
 * and Kill disposes the PTY. For agent-driven command execution with
 * approvals, ask Jarvis in the composer instead.
 */

import '@xterm/xterm/css/xterm.css'

import { FitAddon } from '@xterm/addon-fit'
import { Unicode11Addon } from '@xterm/addon-unicode11'
import { Terminal } from '@xterm/xterm'
import { memo, useCallback, useEffect, useRef, useState } from 'react'

type TermStatus = 'starting' | 'open' | 'exited' | 'unavailable'

function TerminalViewComponent() {
  const hostRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)
  const sessionRef = useRef<string | null>(null)
  const [status, setStatus] = useState<TermStatus>('starting')
  const [exitCode, setExitCode] = useState<number | null>(null)
  const [sessionKey, setSessionKey] = useState(0)

  useEffect(() => {
    const host = hostRef.current
    const api = window.aetherosDesktop?.terminal

    if (!host || !api) {
      setStatus('unavailable')

      return
    }

    let disposed = false
    const cleanups: Array<() => void> = []

    const term = new Terminal({
      convertEol: true,
      cursorBlink: true,
      fontFamily: "'Cascadia Code', 'JetBrains Mono', Menlo, monospace",
      fontSize: 12,
      scrollback: 2000,
      theme: { background: '#00000000' }
    })

    const fit = new FitAddon()
    term.loadAddon(fit)
    term.loadAddon(new Unicode11Addon())
    term.unicode.activeVersion = '11'
    term.open(host)
    fit.fit()
    termRef.current = term

    const onResize = () => {
      try { fit.fit() } catch { /* host hidden */ }
    }

    window.addEventListener('resize', onResize)
    cleanups.push(() => window.removeEventListener('resize', onResize))

    void api.start({ cols: term.cols, rows: term.rows }).then(
      session => {
        if (disposed) {
          void api.dispose(session.id).catch(() => undefined)

          return
        }

        sessionRef.current = session.id
        setStatus('open')
        term.onData(data => {
          if (sessionRef.current) {void api.write(sessionRef.current, data).catch(() => undefined)}
        })
        cleanups.push(api.onData(session.id, payload => {
          if (!disposed) {term.write(payload)}
        }))
        cleanups.push(api.onExit(session.id, payload => {
          if (disposed) {return}
          sessionRef.current = null
          const code = typeof payload?.code === 'number' ? payload.code : null
          setExitCode(code)
          setStatus('exited')
          term.write(`\r\n[process exited${code !== null ? ` with code ${code}` : ''}]\r\n`)
        }))
      },
      () => {
        if (!disposed) {setStatus('unavailable')}
      }
    )

    return () => {
      disposed = true
      cleanups.forEach(fn => {
        try { fn() } catch { /* noop */ }
      })

      const id = sessionRef.current
      sessionRef.current = null

      if (id) {void api.dispose(id).catch(() => undefined)}

      try { term.dispose() } catch { /* noop */ }
      termRef.current = null
    }
  }, [sessionKey])

  const kill = useCallback(() => {
    const api = window.aetherosDesktop?.terminal
    const id = sessionRef.current

    if (api && id) {
      sessionRef.current = null
      void api.dispose(id).catch(() => undefined)
    }
  }, [])

  const restart = useCallback(() => {
    setExitCode(null)
    setStatus('starting')
    setSessionKey(k => k + 1)
  }, [])

  return (
    <div className="h-full flex flex-col p-6">
      <div className="mb-3 flex items-center gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white/90">Terminal</h2>
          <p className="text-[12px] text-white/30 mt-0.5">
            {status === 'open' ? 'Live shell — real process, real exit codes'
              : status === 'starting' ? 'Starting shell...'
              : status === 'exited' ? `Shell exited${exitCode !== null ? ` (code ${exitCode})` : ''}`
              : 'Terminal IPC unavailable in this environment'}
          </p>
        </div>
        <div className="flex-1" />
        {status === 'open' && (
          <button
            className="rounded-lg border border-red-500/30 px-2.5 py-1 text-[11px] text-red-300 hover:bg-red-500/10"
            onClick={kill}
          >
            Kill
          </button>
        )}
        {status === 'exited' && (
          <button
            className="rounded-lg border border-white/10 px-2.5 py-1 text-[11px] text-white/50 hover:bg-white/[0.06]"
            onClick={restart}
          >
            Restart
          </button>
        )}
      </div>

      <div className="flex-1 min-h-0 rounded-xl bg-black/40 border border-white/[0.06] overflow-hidden p-2">
        <div className="size-full" key={sessionKey} ref={hostRef} />
      </div>
    </div>
  )
}

export const TerminalView = memo(TerminalViewComponent)
