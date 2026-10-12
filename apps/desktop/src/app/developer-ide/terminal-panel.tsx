import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { $terminalReplacement, addTerminalSession, setActiveTerminal } from '../../store/terminal-replacement'

export function TerminalPanel() {
  const term = useStore($terminalReplacement)
  const [command, setCommand] = useState('')

  const handleCommand = () => {
    if (!command.trim()) {return}

    const session = {
      id: Date.now().toString(),
      name: `term-${term.sessions.length + 1}`,
      cwd: process.cwd() || '/home',
      command: command,
      status: 'running' as const,
      outputLines: 0,
      startedAt: Date.now(),
    }

    addTerminalSession(session)
    setCommand('')
  }

  return (
    <div className="flex flex-col h-full bg-gray-950 text-green-400 font-mono text-xs">
      <div className="flex items-center px-2 py-1 bg-gray-900 border-b border-gray-800 gap-1 overflow-x-auto">
        {term.sessions.map(s => (
          <button
            className={`px-2 py-0.5 text-2xs ${s.id === term.activeSessionId ? 'bg-gray-800 text-green-300' : 'text-gray-500 hover:text-gray-300'}`}
            key={s.id}
            onClick={() => setActiveTerminal(s.id)}
          >
            {s.name}
          </button>
        ))}
        <button className="ml-auto px-1 text-gray-500 hover:text-gray-300" onClick={() => addTerminalSession({
          id: Date.now().toString(), name: `term-${term.sessions.length + 1}`,
          cwd: '/home', command: '', status: 'running', outputLines: 0, startedAt: Date.now(),
        })}>
          <span className="codicon codicon-add text-xs" />
        </button>
      </div>
      <div className="flex-1 overflow-auto p-2 text-green-400/90">
        <div className="text-green-600 text-2xs mb-1">$ AetherOS IDE Terminal</div>
        {term.sessions.filter(s => s.id === term.activeSessionId).map(s => (
          <div key={s.id}>
            <div className="text-green-600">$ {s.command}</div>
            <div className="text-gray-400 italic">[Process running - output would appear here]</div>
          </div>
        ))}
        {term.sessions.length === 0 && (
          <div className="text-green-700 italic p-2">Type a command below to start a session</div>
        )}
      </div>
      <div className="p-2 border-t border-gray-800 bg-gray-900">
        <div className="flex items-center gap-1 text-green-400">
          <span>$</span>
          <input
            className="flex-1 bg-transparent outline-none text-green-300 placeholder-gray-600"
            onChange={e => setCommand(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCommand()}
            placeholder="Run a command..."
            value={command}
          />
        </div>
      </div>
    </div>
  )
}
