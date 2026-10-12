import { useStore } from '@nanostores/react'
import { useCallback, useState } from 'react'

import { $communications, getFilteredMessages, selectConversation } from '@/store/communications'
import type { UnifiedMessage } from '@/store/communications'
import { $commsAI, classifyPriority, detectPendingRequests, extractTasks, generateDraft, generateSummary } from '@/store/communications-ai'
import type { ReplyStyle } from '@/store/communications-ai'

export function ConversationWorkspace() {
  const comms = useStore($communications)
  const selectedConv = comms.selectedConversation

  const messages = selectedConv
    ? getFilteredMessages().filter(m => m.conversationId === selectedConv)
    : []

  if (!selectedConv) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <span className="codicon codicon-comment-discussion text-3xl text-(--ui-text-tertiary)" />
          <p className="mt-2 text-sm text-(--ui-text-tertiary)">Select a conversation to view messages</p>
        </div>
      </div>
    )
  }

  return <ConversationContent conversationId={selectedConv} messages={messages} />
}

function ConversationContent({ messages, conversationId }: { messages: UnifiedMessage[]; conversationId: string }) {
  const [showAiPanel, setShowAiPanel] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [aiDraft, setAiDraft] = useState<string | null>(null)
  const commsAi = useStore($commsAI)

  const handleSummarize = useCallback(() => {
    generateSummary(messages)
    setShowAiPanel(true)
  }, [messages])

  const handleAiDraft = useCallback((style: ReplyStyle) => {
    generateDraft(messages, style)
    const draft = $commsAI.get().draftResult

    if (draft) {
      setAiDraft(draft.content)
      setReplyText(draft.content)
    }
  }, [messages])

  const urgent = classifyPriority(messages).urgent
  const tasks = extractTasks(messages)
  const pending = detectPendingRequests(messages)

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <button
          className="flex items-center gap-1 text-xs text-(--ui-text-tertiary) hover:text-foreground"
          onClick={() => selectConversation(null)}
        >
          <span className="codicon codicon-arrow-left" />
          Back to inbox
        </button>
        <div className="flex items-center gap-1">
          {urgent.length > 0 && (
            <span className="flex items-center gap-1 rounded-md bg-red-500/10 px-2 py-0.5 text-[10px] text-red-500">
              <span className="codicon codicon-warning" />
              {urgent.length} urgent
            </span>
          )}
          {tasks.length > 0 && (
            <span className="flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-500">
              <span className="codicon codicon-checklist" />
              {tasks.length} tasks
            </span>
          )}
          <button className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)" onClick={handleSummarize}>
            <span className="codicon codicon-summary" />
            Summarize
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
        {messages.map(msg => (
          <div className={`flex ${msg.direction === 'outgoing' ? 'justify-end' : 'justify-start'}`} key={msg.id}>
            <div className={`max-w-[80%] rounded-lg px-3 py-2 ${
              msg.direction === 'outgoing'
                ? 'bg-primary text-white'
                : 'bg-(--ui-bg-quaternary)'
            }`}>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-medium opacity-70">{msg.senderName}</span>
                <span className="text-[10px] opacity-50">{formatTime(msg.timestamp)}</span>
              </div>
              <p className="mt-1 text-xs">{msg.content}</p>
              {msg.attachments.length > 0 && (
                <div className="mt-1 flex gap-1">
                  {msg.attachments.map((a, i) => (
                    <span className="flex items-center gap-1 text-[10px] opacity-70" key={i}>
                      <span className={`codicon codicon-${a.type === 'image' ? 'file-media' : a.type === 'pdf' ? 'file-pdf' : 'file'}`} />
                      {a.name}
                    </span>
                  ))}
                </div>
              )}
              {msg.aiResponse && (
                <div className="mt-1 rounded bg-black/10 px-2 py-1 text-[10px] italic opacity-70">
                  AI: {msg.aiResponse}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* AI Draft Banner */}
      {aiDraft && (
        <div className="shrink-0 border-t border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-4 py-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1 text-[10px] text-(--ui-text-tertiary)">
              <span className="codicon codicon-robot" />
              AI Draft
            </span>
            <button className="text-[10px] text-(--ui-text-tertiary) hover:text-foreground" onClick={() => { setAiDraft(null); setReplyText('') }}>
              <span className="codicon codicon-close" />
            </button>
          </div>
          <p className="mt-1 text-xs italic">{aiDraft}</p>
        </div>
      )}

      {/* AI Actions */}
      {showAiPanel && (
        <div className="shrink-0 border-t border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-4 py-2">
          <div className="flex flex-wrap gap-1">
            <button className="rounded-md bg-white/10 px-2 py-1 text-[10px] hover:bg-white/20" onClick={() => handleAiDraft('professional')}>Professional Reply</button>
            <button className="rounded-md bg-white/10 px-2 py-1 text-[10px] hover:bg-white/20" onClick={() => handleAiDraft('casual')}>Casual Reply</button>
            <button className="rounded-md bg-white/10 px-2 py-1 text-[10px] hover:bg-white/20" onClick={() => handleAiDraft('friendly')}>Friendly Reply</button>
            <button className="rounded-md bg-white/10 px-2 py-1 text-[10px] hover:bg-white/20" onClick={() => handleAiDraft('short')}>Short Reply</button>
            {pending.length > 0 && (
              <span className="flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-1 text-[10px] text-amber-500">
                {pending.length} pending {pending.length === 1 ? 'request' : 'requests'}
              </span>
            )}
          </div>
          {tasks.length > 0 && (
            <details className="mt-1">
              <summary className="cursor-pointer text-[10px] text-(--ui-text-tertiary) hover:text-foreground">
                {tasks.length} task{tasks.length !== 1 ? 's' : ''} extracted
              </summary>
              <ul className="mt-1 space-y-0.5 pl-3">
                {tasks.map((t, i) => (
                  <li className="text-[10px] text-(--ui-text-tertiary)" key={i}>
                    <span className="codicon codicon-check text-[10px] text-green-500" /> {t.task} <span className="italic">— from {t.from}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {/* Reply Input */}
      <div className="shrink-0 border-t border-(--ui-stroke-tertiary) px-4 py-3">
        <div className="flex gap-2">
          <input
            className="h-8 min-w-0 flex-1 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-3 text-xs outline-none focus:border-primary"
            onChange={e => setReplyText(e.target.value)}
            placeholder="Type a reply..."
            type="text"
            value={replyText}
          />
          <button
            className="flex h-8 items-center gap-1 rounded-md px-2.5 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)"
            onClick={() => setShowAiPanel(true)}
            title="AI Assistant"
          >
            <span className="codicon codicon-robot" />
          </button>
          <button
            className="flex h-8 items-center gap-1 rounded-md bg-primary px-3 text-xs text-white disabled:opacity-50"
            disabled={!replyText.trim()}
          >
            <span className="codicon codicon-send" />
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

function formatTime(ts: string): string {
  const d = new Date(ts)

  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
