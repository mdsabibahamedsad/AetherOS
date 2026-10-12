import { useStore } from '@nanostores/react'
import { useState } from 'react'

import {
  $browserPermissions, addPermissionRequest, denyPermission, grantPermission,
} from '@/store/browser-permissions'
import { $browser } from '@/store/browser-workspace'

type Suggestion = {
  label: string
  prompt: string
}

const suggestions: Suggestion[] = [
  { label: 'Summarize this page', prompt: 'Summarize this page' },
  { label: 'Extract emails', prompt: 'Extract all emails from this page' },
  { label: 'Extract links', prompt: 'Extract all links from this page' },
  { label: 'Find prices', prompt: 'Find the cheapest option on this page' },
  { label: 'Read article', prompt: 'Read this article to me' },
  { label: 'Compare pages', prompt: 'Compare these pages' },
  { label: 'Find docs', prompt: 'Find the official documentation' },
  { label: 'Analyze form', prompt: 'Find the problem in this form' },
]

export function BrowserAiAssistant() {
  const browser = useStore($browser)
  const permissions = useStore($browserPermissions)
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const handleSubmit = () => {
    if (!query.trim()) {return}
    const userMsg = { role: 'user', content: query.trim() }
    setMessages(prev => [...prev, userMsg])

    let response = ''
    const q = query.toLowerCase()

    if (q.includes('summarize') || q.includes('summary')) {
      response = `**Page Summary**\n\nCurrent page: ${browser.pageUrl || 'No active page'}\nTitle: ${browser.pageTitle || 'Untitled'}\n\nI can see the page content. Here is a summary of the key information...\n\n(This requires backend processing to analyze the actual page content.)`
    } else if (q.includes('email')) {
      response = `**Email Extraction**\n\nTo extract emails from ${browser.pageUrl || 'the current page'}, I need permission to read the page content.`
      addPermissionRequest('read_page', browser.pageUrl, 'Extract email addresses')
    } else if (q.includes('link') || q.includes('url')) {
      response = `**Link Extraction**\n\nExtracting all links from ${browser.pageUrl || 'the current page'}...\n\n(This requires backend processing to parse the DOM.)`
    } else if (q.includes('price') || q.includes('cheapest') || q.includes('compare')) {
      response = `**Price Analysis**\n\nSearching for prices and comparing options on this page...\n\n(This requires backend processing to extract and analyze pricing data.)`
    } else if (q.includes('translate')) {
      response = `**Translation**\n\nThe page content can be translated using the AI translation system.\n\nSupported target languages include: Spanish, French, German, Chinese, Japanese, and more.`
    } else if (q.includes('read') || q.includes('article')) {
      response = `**Article Reader**\n\nReading the article on ${browser.pageTitle || 'this page'}...\n\n${browser.pageTitle ? `**${browser.pageTitle}**\n\n` : ''}(The full article content would be extracted and presented here.)`
    } else if (q.includes('documentation') || q.includes('docs')) {
      response = `**Documentation Search**\n\nSearching for official documentation related to your query...\n\nI can search the web for the latest official documentation.`
    } else if (q.includes('form')) {
      response = `**Form Analysis**\n\nAnalyzing forms on ${browser.pageUrl || 'the current page'}...\n\n(This requires backend processing to inspect form elements.)`
    } else if (q.includes('search')) {
      response = `**Web Search**\n\nI'll search for "${query.replace(/search/gi, '').trim()}" using ${browser.searchProvider}.\n\nNavigate to the search results to see them.`
    } else {
      response = `**AI Browser Assistant**\n\nI can help you with the current page (${browser.pageUrl || 'no page loaded'}). Here's what I can do:\n\n- **Summarize** this page\n- **Extract** emails, links, prices\n- **Compare** products or pages\n- **Find** documentation\n- **Translate** content\n- **Analyze** forms\n- **Search** the web\n\nWhat would you like me to do?`
    }

    setMessages(prev => [...prev, { role: 'assistant', content: response }])
    setQuery('')
  }

  return (
    <div className={`${sidebarOpen ? 'w-72' : 'w-0'} border-l border-(--ui-border) bg-(--ui-surface-secondary) flex flex-col transition-all duration-200 overflow-hidden shrink-0`}>
      <div className="flex items-center justify-between px-3 py-2 border-b border-(--ui-border)">
        <span className="text-xs font-medium flex items-center gap-1">
          <span className="codicon codicon-comment-discussion" />
          AI Assistant
        </span>
        <button className="p-0.5 hover:bg-(--ui-surface-hover) rounded" onClick={() => setSidebarOpen(!sidebarOpen)}>
          <span className={`codicon codicon-${sidebarOpen ? 'panel-close' : 'panel-open'} text-xs`} />
        </button>
      </div>

      {sidebarOpen && (
        <>
          <div className="flex-1 overflow-auto p-3 space-y-2">
            {messages.length === 0 && (
              <div className="space-y-1.5">
                <p className="text-xs text-(--ui-text-tertiary) mb-2">Suggestions:</p>
                {suggestions.map(s => (
                  <button
                    className="block w-full text-left px-2 py-1.5 text-xs hover:bg-(--ui-surface-hover) rounded border border-(--ui-border)"
                    key={s.label}
                    onClick={() => { setQuery(s.prompt); setTimeout(() => handleSubmit(), 100) }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}
            {messages.map((msg, i) => (
              <div className={`text-xs ${msg.role === 'user' ? 'text-(--ui-text)' : 'text-(--ui-text-secondary)'}`} key={i}>
                {msg.role === 'user' && <span className="font-medium block mb-0.5">You:</span>}
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            ))}
          </div>

          {permissions.pendingRequests.length > 0 && (
            <div className="px-3 py-2 border-t border-(--ui-border) bg-yellow-50">
              <p className="text-xs font-medium text-yellow-800 mb-1">Permission Requested</p>
              {permissions.pendingRequests.map(req => (
                <div className="text-xs text-yellow-700 mb-1" key={req.id}>
                  <p>{req.reason}</p>
                  <p className="text-[10px] text-yellow-600">{req.url}</p>
                  <div className="flex gap-1 mt-1">
                    <button className="px-2 py-0.5 text-[10px] bg-green-600 text-white rounded hover:opacity-90"
                      onClick={() => grantPermission(req.id, 'once')}>Allow Once</button>
                    <button className="px-2 py-0.5 text-[10px] bg-blue-600 text-white rounded hover:opacity-90"
                      onClick={() => grantPermission(req.id, 'session')}>Allow Session</button>
                    <button className="px-2 py-0.5 text-[10px] bg-gray-400 text-white rounded hover:opacity-90"
                      onClick={() => denyPermission(req.id)}>Deny</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="p-2 border-t border-(--ui-border)">
            <div className="flex gap-1">
              <input
                className="flex-1 px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none"
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') {handleSubmit()} }}
                placeholder="Ask about this page..."
                type="text"
                value={query}
              />
              <button className="px-2 py-1 bg-(--ui-accent) text-white text-xs rounded hover:opacity-90" onClick={handleSubmit}>
                <span className="codicon codicon-send" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
