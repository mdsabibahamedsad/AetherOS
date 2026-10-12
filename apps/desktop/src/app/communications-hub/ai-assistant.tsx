import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { $communications, getFilteredMessages } from '@/store/communications'
import { $commsAI, classifyPriority, clearAssistantHistory, detectPendingRequests, extractTasks, generateDraft, generateSummary, setAssistantMode, setCustomInstructions, setDraftStyle, setTargetLanguage } from '@/store/communications-ai'
import type { ReplyStyle } from '@/store/communications-ai'

const STYLES: { id: ReplyStyle; label: string }[] = [
  { id: 'professional', label: 'Professional' },
  { id: 'casual', label: 'Casual' },
  { id: 'friendly', label: 'Friendly' },
  { id: 'short', label: 'Short' },
  { id: 'detailed', label: 'Detailed' },
]

export function CommsAIAssistant() {
  const commsAi = useStore($commsAI)
  const comms = useStore($communications)
  const messages = getFilteredMessages()
  const [customPrompt, setCustomPrompt] = useState('')

  const priority = classifyPriority(messages)
  const tasks = extractTasks(messages)
  const pendingRequests = detectPendingRequests(messages)

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <h2 className="text-sm font-semibold">AI Message Assistant</h2>
        <button className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)" onClick={clearAssistantHistory}>
          <span className="codicon codicon-clear-all" />
          Clear History
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-2">
          <button className="rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left text-xs hover:bg-(--ui-row-hover-background)" onClick={() => { generateDraft(messages); setAssistantMode('draft') }}>
            <span className="codicon codicon-comment text-sm" />
            <p className="mt-1 font-medium">Draft Reply</p>
            <p className="text-(--ui-text-tertiary)">Generate a professional reply</p>
          </button>
          <button className="rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left text-xs hover:bg-(--ui-row-hover-background)" onClick={() => { generateSummary(messages); setAssistantMode('summarize') }}>
            <span className="codicon codicon-summary text-sm" />
            <p className="mt-1 font-medium">Summarize</p>
            <p className="text-(--ui-text-tertiary)">Summarize conversations</p>
          </button>
          <button className="rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left text-xs hover:bg-(--ui-row-hover-background)" onClick={() => setAssistantMode('analyze')}>
            <span className="codicon codicon-warning text-sm" />
            <p className="mt-1 font-medium">Analyze Priority</p>
            <p className="text-(--ui-text-tertiary)">Find urgent & important messages</p>
          </button>
          <button className="rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left text-xs hover:bg-(--ui-row-hover-background)" onClick={() => setAssistantMode('compose')}>
            <span className="codicon codicon-edit text-sm" />
            <p className="mt-1 font-medium">Compose Message</p>
            <p className="text-(--ui-text-tertiary)">Write a new message from scratch</p>
          </button>
        </div>

        {/* Priority Summary */}
        {commsAi.mode === 'analyze' && (
          <div className="space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
            <h3 className="text-xs font-medium">Message Priority Analysis</h3>
            {priority.urgent.length > 0 && (
              <div>
                <p className="flex items-center gap-1 text-xs font-medium text-red-500">
                  <span className="codicon codicon-warning" /> Urgent ({priority.urgent.length})
                </p>
                <ul className="mt-1 space-y-0.5 pl-4">
                  {priority.urgent.map(m => (
                    <li className="text-xs text-(--ui-text-tertiary)" key={m.id}>{m.senderName}: {m.content.substring(0, 80)}...</li>
                  ))}
                </ul>
              </div>
            )}
            {priority.important.length > 0 && (
              <div>
                <p className="flex items-center gap-1 text-xs font-medium text-amber-500">
                  <span className="codicon codicon-star-full" /> Important ({priority.important.length})
                </p>
              </div>
            )}
            {priority.spam.length > 0 && (
              <p className="text-xs text-(--ui-text-tertiary)">{priority.spam.length} potential spam messages detected</p>
            )}
            {pendingRequests.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-medium">Pending Requests</p>
                <ul className="mt-1 space-y-0.5 pl-4">
                  {pendingRequests.map((r, i) => (
                    <li className="text-xs text-(--ui-text-tertiary)" key={i}>• {r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Draft Area */}
        {commsAi.mode === 'draft' && (
          <div className="space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
            <div className="flex flex-wrap gap-1">
              {STYLES.map(s => (
                <button
                  className={`rounded-md px-2 py-1 text-[10px] ${commsAi.selectedStyle === s.id ? 'bg-primary text-white' : 'bg-(--ui-bg-quaternary) text-(--ui-text-tertiary)'}`}
                  key={s.id}
                  onClick={() => setDraftStyle(s.id)}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <input
              className="h-7 w-full rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setCustomInstructions(e.target.value)}
              placeholder="Custom instructions (optional)" type="text"
              value={commsAi.customInstructions}
            />
            {commsAi.draftResult && (
              <div className="rounded-md bg-(--ui-bg-quaternary) p-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-(--ui-text-tertiary)">{commsAi.draftResult.toneNotes}</span>
                  <span className="rounded-md bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-500">Requires approval</span>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-xs">{commsAi.draftResult.content}</p>
              </div>
            )}
            <button
              className="h-7 w-full rounded-md bg-primary text-xs text-white"
              onClick={() => generateDraft(messages, commsAi.selectedStyle, commsAi.customInstructions, commsAi.targetLanguage)}
            >
              <span className="codicon codicon-sparkle" /> Generate Draft
            </button>
          </div>
        )}

        {/* Summary */}
        {commsAi.mode === 'summarize' && commsAi.currentSummary && (
          <div className="space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
            <h3 className="flex items-center gap-1 text-xs font-medium">
              <span className="codicon codicon-summary" /> Conversation Summary
            </h3>
            <p className="text-xs text-(--ui-text-tertiary)">{commsAi.currentSummary.summary}</p>
            {commsAi.currentSummary.keyPoints.length > 0 && (
              <div>
                <p className="text-[10px] font-medium text-(--ui-text-tertiary)">Key Points</p>
                <ul className="mt-1 space-y-0.5 pl-3">
                  {commsAi.currentSummary.keyPoints.map((p, i) => (
                    <li className="text-xs text-(--ui-text-tertiary)" key={i}>• {p}</li>
                  ))}
                </ul>
              </div>
            )}
            {commsAi.currentSummary.actionItems.length > 0 && (
              <div>
                <p className="text-[10px] font-medium text-(--ui-text-tertiary)">Action Items</p>
                <ul className="mt-1 space-y-0.5 pl-3">
                  {commsAi.currentSummary.actionItems.map((a, i) => (
                    <li className="flex items-center gap-1 text-xs" key={i}>
                      <span className="codicon codicon-check text-green-500" /> {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-[10px] text-(--ui-text-tertiary)">
              Sentiment: {commsAi.currentSummary.sentiment} | {commsAi.currentSummary.messageCount} messages | {commsAi.currentSummary.participants.join(', ')}
            </p>
          </div>
        )}

        {/* History */}
        {commsAi.history.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-medium">Assistant History</h3>
            {commsAi.history.map((h, i) => (
              <div className={`rounded-lg p-2 text-xs ${h.role === 'assistant' ? 'bg-(--ui-bg-quaternary)' : 'bg-primary/10'}`} key={i}>
                <div className="flex items-center gap-1 text-[10px] text-(--ui-text-tertiary)">
                  <span className={`codicon codicon-${h.role === 'assistant' ? 'robot' : 'person'}`} />
                  {h.role === 'assistant' ? 'AI Assistant' : 'You'}
                  <span className="ml-auto">{new Date(h.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="mt-0.5">{h.content}</p>
              </div>
            ))}
          </div>
        )}

        {/* Tasks */}
        {tasks.length > 0 && (
          <div className="rounded-lg border border-(--ui-stroke-tertiary) p-3">
            <h3 className="flex items-center gap-1 text-xs font-medium">
              <span className="codicon codicon-checklist" /> Extracted Tasks ({tasks.length})
            </h3>
            <ul className="mt-1 space-y-0.5 pl-3">
              {tasks.map((t, i) => (
                <li className="text-xs text-(--ui-text-tertiary)" key={i}>• {t.task} <span className="italic">— {t.from}</span></li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Compose */}
      {commsAi.mode === 'compose' && (
        <div className="shrink-0 border-t border-(--ui-stroke-tertiary) p-4">
          <textarea
            className="w-full resize-none rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-2 text-xs outline-none focus:border-primary"
            placeholder="Write your message here... or ask AI to help compose it"
            rows={4}
          />
          <div className="mt-2 flex items-center justify-between">
            <input
              className="h-7 w-48 rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setTargetLanguage(e.target.value)}
              placeholder="Translate to language (optional)" type="text"
              value={commsAi.targetLanguage}
            />
            <div className="flex gap-2">
              <button className="rounded-md bg-(--ui-bg-quaternary) px-3 py-1.5 text-xs">Preview</button>
              <button className="rounded-md bg-primary px-3 py-1.5 text-xs text-white">Send</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
