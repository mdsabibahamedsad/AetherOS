import { useStore } from '@nanostores/react'
import { useState } from 'react'

import {
  $aiCoding, $pendingChanges, $totalChanges,
  addMessage, approveSelectedChanges, deselectAllChanges, rejectAllChanges,
  selectAllChanges, setAIMode, setAIProcessing,
  setCurrentRequest, toggleChangeSelection,
} from '../../store/ai-coding-assistant'

const modes = ['ask', 'suggest', 'edit', 'agent', 'review', 'autonomous'] as const

export function AIAssistant() {
  const ai = useStore($aiCoding)
  const pending = useStore($pendingChanges)
  const totals = useStore($totalChanges)
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (!input.trim()) {return}
    addMessage({ id: Date.now().toString(), role: 'user', content: input, timestamp: Date.now() })
    setAIProcessing(true)
    setCurrentRequest(input)
    setInput('')
    setTimeout(() => {
      addMessage({
        id: (Date.now() + 1).toString(), role: 'assistant', content: `I'll help you with: "${input}"`,
        timestamp: Date.now(),
      })
      setAIProcessing(false)
    }, 1000)
  }

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="flex flex-wrap gap-0.5 p-2 border-b border-border">
        {modes.map(m => (
          <button
            className={`px-2 py-0.5 text-2xs rounded capitalize ${
              ai.mode === m ? 'bg-accent text-white' : 'bg-surface-hover text-foreground-secondary hover:text-foreground'
            }`}
            key={m}
            onClick={() => setAIMode(m)}
          >
            {m}
          </button>
        ))}
      </div>

      {pending.length > 0 && (
        <div className="bg-yellow-500/10 border-b border-yellow-500/30 p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="font-medium text-yellow-600 text-2xs">{totals.total} changes pending</span>
            <div className="flex gap-1">
              <button className="text-2xs text-accent hover:underline" onClick={() => selectAllChanges()}>Select All</button>
              <button className="text-2xs text-foreground-secondary hover:underline" onClick={() => deselectAllChanges()}>Deselect</button>
            </div>
          </div>
          <div className="flex gap-1">
            <button className="px-2 py-0.5 text-2xs bg-green-600 text-white rounded hover:bg-green-700" onClick={() => approveSelectedChanges()}>
              Approve Selected
            </button>
            <button className="px-2 py-0.5 text-2xs bg-red-600 text-white rounded hover:bg-red-700" onClick={() => rejectAllChanges()}>
              Reject All
            </button>
          </div>
          <div className="mt-1 space-y-0.5 max-h-24 overflow-auto">
            {pending.slice(0, 5).map(c => (
              <div className="flex items-center gap-1 text-2xs" key={c.id}>
                <input checked={c.selected} className="accent-accent" onChange={() => toggleChangeSelection(c.id)} type="checkbox" />
                <span className="codicon codicon-file" />
                <span className="truncate flex-1">{c.filePath}</span>
                <span className={`px-1 rounded ${c.riskLevel === 'high' ? 'bg-red-500/20 text-red-500' : c.riskLevel === 'medium' ? 'bg-yellow-500/20 text-yellow-500' : 'bg-green-500/20 text-green-500'}`}>
                  {c.linesAdded}+ / {c.linesRemoved}-
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto p-2 space-y-2">
        {ai.conversation.length === 0 && (
          <div className="text-center text-foreground-secondary py-8">
            <span className="codicon codicon-comment-discussion text-2xl block mb-2" />
            <p className="text-xs">How can I help you code?</p>
            <p className="text-2xs mt-1">Ask questions, generate code, or review changes</p>
          </div>
        )}
        {ai.conversation.map(msg => (
          <div className={`p-2 rounded ${msg.role === 'user' ? 'bg-accent/10 ml-4' : 'bg-surface-hover mr-4'}`} key={msg.id}>
            <div className="text-2xs text-foreground-secondary mb-1">{msg.role === 'user' ? 'You' : 'AI'}</div>
            <div className="text-xs whitespace-pre-wrap">{msg.content}</div>
          </div>
        ))}
        {ai.isProcessing && (
          <div className="text-foreground-secondary italic text-2xs p-2">AI is processing...</div>
        )}
      </div>

      <div className="p-2 border-t border-border">
        <div className="flex gap-1">
          <input
            className="flex-1 px-2 py-1.5 text-xs bg-surface border border-border rounded outline-none focus:border-accent placeholder-foreground-secondary"
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
            placeholder={ai.mode === 'ask' ? 'Ask anything...' : `Describe the ${ai.mode}...`}
            value={input}
          />
          <button className="px-2 py-1 bg-accent text-white rounded hover:bg-accent-hover disabled:opacity-50" disabled={ai.isProcessing || !input.trim()} onClick={handleSend}>
            <span className="codicon codicon-send text-xs" />
          </button>
        </div>
        <div className="text-2xs text-foreground-secondary mt-1">
          Mode: <span className="font-medium capitalize">{ai.mode}</span>
          {ai.contextFiles.length > 0 && <> &middot; {ai.contextFiles.length} context files</>}
        </div>
      </div>
    </div>
  )
}
