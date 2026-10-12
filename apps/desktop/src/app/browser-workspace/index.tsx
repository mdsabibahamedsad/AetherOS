import { useStore } from '@nanostores/react'
import { type ElementType, type KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatBytes } from '@/lib/format-bytes'
import { formatTimestamp } from '@/lib/format-timestamp'
import {
  $activeTab, $browser, $pinnedTabs, $unpinnedTabs,
  activateTab, addBookmark, addHistoryItem, addTab,
  type BrowserMode, type BrowserTab, clearCompletedDownloads, clearHistory, closeTab,
  duplicateTab, navigateBack, navigateForward,
  refreshPage, removeBookmark, removeDownload,
  setBrowserMode, setPageZoom, setSearchProvider, setTabLoading,
  togglePinTab, togglePrivateMode, toggleReaderMode,
  updateTabNavState, updateTabTitle, updateTabUrl,
} from '@/store/browser-workspace'

import { BrowserAiAssistant } from './ai-assistant'
import { BrowserAutomationBuilder } from './automation-builder'

const modes: { id: BrowserMode; label: string; icon: string }[] = [
  { id: 'browse', label: 'Browse', icon: 'globe' },
  { id: 'automation', label: 'Automation', icon: 'run-all' },
  { id: 'research', label: 'Research', icon: 'book' },
  { id: 'history', label: 'History', icon: 'history' },
  { id: 'bookmarks', label: 'Bookmarks', icon: 'bookmark' },
  { id: 'downloads', label: 'Downloads', icon: 'cloud-download' },
  { id: 'settings', label: 'Settings', icon: 'gear' },
]

const searchProviders = ['Google', 'Bing', 'DuckDuckGo', 'Brave']

export function BrowserView() {
  const browser = useStore($browser)
  const activeTab = useStore($activeTab)
  const pinnedTabs = useStore($pinnedTabs)
  const unpinnedTabs = useStore($unpinnedTabs)

  const [urlInput, setUrlInput] = useState('')
  const [showProviderMenu, setShowProviderMenu] = useState(false)
  const [controlState, setControlState] = useState<'user' | 'agent' | 'approval' | 'blocked' | 'untrusted'>('user')

  const handleUrlSubmit = useCallback(() => {
    let url = urlInput.trim()

    if (!url) {return}

    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = `https://${url}`
    }

    if (activeTab) {
      updateTabUrl(activeTab.id, url)
      updateTabTitle(activeTab.id, url)
      addHistoryItem(url, url)
      setTabLoading(activeTab.id, true)
      setTimeout(() => {
        updateTabTitle(activeTab.id, url)
        setTabLoading(activeTab.id, false)
      }, 1500)
    }
  }, [urlInput, activeTab])

  const handleSearch = useCallback((query: string) => {
    if (!query.trim()) {return}
    const provider = browser.searchProvider.toLowerCase()

    const searchUrl = provider === 'google' ? `https://www.google.com/search?q=${encodeURIComponent(query)}`
      : provider === 'bing' ? `https://www.bing.com/search?q=${encodeURIComponent(query)}`
      : provider === 'duckduckgo' ? `https://duckduckgo.com/?q=${encodeURIComponent(query)}`
      : provider === 'brave' ? `https://search.brave.com/search?q=${encodeURIComponent(query)}`
      : `https://www.google.com/search?q=${encodeURIComponent(query)}`

    if (activeTab) {
      updateTabUrl(activeTab.id, searchUrl)
      addHistoryItem(searchUrl, query)
      setTabLoading(activeTab.id, true)
      setTimeout(() => {
        updateTabTitle(activeTab.id, query)
        setTabLoading(activeTab.id, false)
      }, 1500)
    }
  }, [activeTab, browser.searchProvider])

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleUrlSubmit()
    }
  }, [handleUrlSubmit])

  if (browser.mode === 'automation') {
    return (
      <div className="flex flex-col h-full">
        <BrowserAutomationToolbar />
        <BrowserAutomationBuilder />
      </div>
    )
  }

  if (browser.mode === 'settings') {
    return <BrowserSettingsView />
  }

  return (
    <div className="flex flex-col h-full">
      <BrowserNavigationBar
        canGoBack={activeTab?.canGoBack ?? false}
        canGoForward={activeTab?.canGoForward ?? false}
        controlState={controlState}
        loading={activeTab?.loading ?? false}
        onBack={navigateBack}
        onForward={navigateForward}
        onKeyDown={handleKeyDown}
        onRefresh={refreshPage}
        onSearch={handleSearch}
        onUrlSubmit={handleUrlSubmit}
        provider={browser.searchProvider}
        providers={searchProviders}
        setControlState={setControlState}
        setProvider={setSearchProvider}
        setShowProviderMenu={setShowProviderMenu}
        setUrlInput={setUrlInput}
        showProviderMenu={showProviderMenu}
        urlInput={urlInput}
      />

      <BrowserTabBar
        activeTabId={browser.activeTabId}
        controlState={controlState}
        onClose={closeTab}
        onDuplicate={duplicateTab}
        onNewTab={() => addTab()}
        onPin={togglePinTab}
        onSelect={activateTab}
        tabs={unpinnedTabs}
      />

      {browser.mode === 'research' && <ResearchToolbar />}

      <div className="flex flex-1 overflow-hidden">
        <div className="flex flex-1 flex flex-col overflow-hidden bg-white">
          {browser.mode === 'browse' && (
            <WebView
              loading={activeTab?.loading ?? false}
              readerMode={browser.readerMode}
              url={activeTab?.url ?? ''}
            />
          )}
          {browser.mode === 'research' && <ResearchView />}
          {browser.mode === 'history' && <HistoryView />}
          {browser.mode === 'bookmarks' && <BookmarksView />}
          {browser.mode === 'downloads' && <DownloadsView />}
        </div>

        <BrowserAiAssistant />
      </div>
    </div>
  )
}

type ControlState = 'user' | 'agent' | 'approval' | 'blocked' | 'untrusted'

const CONTROL_LABEL: Record<ControlState, string> = {
  user: 'You control the browser',
  agent: 'Agent is driving',
  approval: 'Waiting for your approval',
  blocked: 'Blocked by policy',
  untrusted: 'Untrusted page',
}

function BrowserAutomationToolbar() {
  return (
    <div className="flex items-center gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-2">
      <span className="text-xs font-medium">Browser automation</span>
      <span className="text-[0.65rem] text-(--ui-text-tertiary)">Agent-driven runs execute through backend tools.</span>
      <span className="flex-1" />
      <Button onClick={() => setBrowserMode('browse')} size="sm" variant="secondary">
        Back to browse
      </Button>
    </div>
  )
}

function BrowserSettingsView() {
  const browser = useStore($browser)

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6">
      <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)">Browser settings</h2>
      <div className="flex items-center gap-3">
        <span className="w-32 text-xs">Search provider</span>
        <Select onValueChange={setSearchProvider} value={browser.searchProvider}>
          <SelectTrigger className="h-8 w-48 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {['Google', 'Bing', 'DuckDuckGo', 'Brave'].map(p => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center gap-3">
        <span className="w-32 text-xs">Page zoom</span>
        <Button onClick={() => setPageZoom(Math.max(50, browser.pageZoom - 10))} size="sm" variant="outline">
          −
        </Button>
        <span className="text-xs tabular-nums">{browser.pageZoom}%</span>
        <Button onClick={() => setPageZoom(Math.min(200, browser.pageZoom + 10))} size="sm" variant="outline">
          +
        </Button>
      </div>
      <div className="flex items-center gap-3">
        <span className="w-32 text-xs">Reader mode</span>
        <Button onClick={() => toggleReaderMode()} size="sm" variant={browser.readerMode ? 'secondary' : 'outline'}>
          {browser.readerMode ? 'On' : 'Off'}
        </Button>
      </div>
      <div className="flex items-center gap-3">
        <span className="w-32 text-xs">Private mode</span>
        <Button onClick={() => togglePrivateMode()} size="sm" variant={browser.privateMode ? 'secondary' : 'outline'}>
          {browser.privateMode ? 'On' : 'Off'}
        </Button>
      </div>
    </div>
  )
}

function BrowserNavigationBar(props: {
  canGoBack: boolean
  canGoForward: boolean
  loading: boolean
  controlState: ControlState
  setControlState: (s: ControlState) => void
  onBack: () => void
  onForward: () => void
  onKeyDown: (e: KeyboardEvent<HTMLInputElement>) => void
  onRefresh: () => void
  onSearch: (q: string) => void
  onUrlSubmit: () => void
  provider: string
  providers: string[]
  setProvider: (p: string) => void
  setShowProviderMenu: (v: boolean) => void
  setUrlInput: (v: string) => void
  showProviderMenu: boolean
  urlInput: string
}) {
  const {
    canGoBack, canGoForward, loading, controlState, onBack, onForward,
    onKeyDown, onRefresh, onSearch, onUrlSubmit, provider, providers,
    setProvider, setUrlInput, urlInput,
  } = props

  const [search, setSearch] = useState('')

  return (
    <div className="flex items-center gap-1.5 border-b border-(--ui-stroke-tertiary) px-3 py-2">
      <Button aria-label="Back" disabled={!canGoBack} onClick={onBack} size="icon" variant="ghost">
        <span className="codicon codicon-chevron-left" />
      </Button>
      <Button aria-label="Forward" disabled={!canGoForward} onClick={onForward} size="icon" variant="ghost">
        <span className="codicon codicon-chevron-right" />
      </Button>
      <Button aria-label="Refresh" onClick={onRefresh} size="icon" variant="ghost">
        <span className="codicon codicon-refresh" />
      </Button>
      <Input
        className="h-8 flex-1 font-mono text-xs"
        onChange={e => setUrlInput(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Enter URL, or search below"
        value={urlInput}
      />
      <Button onClick={onUrlSubmit} size="sm" variant="secondary">
        Go
      </Button>
      <Input
        className="h-8 w-40 text-xs"
        onChange={e => setSearch(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter') {onSearch(search)}
        }}
        placeholder={`Search ${provider}`}
        value={search}
      />
      <Select onValueChange={setProvider} value={provider}>
        <SelectTrigger className="h-8 w-32 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {providers.map(p => (
            <SelectItem key={p} value={p}>
              {p}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Badge
        className="text-[0.55rem]"
        title={CONTROL_LABEL[controlState]}
        variant={controlState === 'user' ? 'outline' : controlState === 'approval' ? 'warn' : 'destructive'}
      >
        {controlState}
      </Badge>
    </div>
  )
}

function BrowserTabBar(props: {
  activeTabId: string
  onClose: (id: string) => void
  onDuplicate: (id: string) => void
  onNewTab: () => void
  onPin: (id: string) => void
  onSelect: (id: string) => void
  tabs: BrowserTab[]
  controlState: ControlState
}) {
  const { activeTabId, onClose, onDuplicate, onNewTab, onPin, onSelect, tabs } = props

  return (
    <div className="flex items-center gap-1 overflow-x-auto border-b border-(--ui-stroke-tertiary) px-2 py-1" role="tablist">
      {tabs.map(t => (
        <div
          aria-selected={t.id === activeTabId}
          className={`flex max-w-48 items-center gap-1 rounded-md px-2 py-1 text-xs ${t.id === activeTabId ? 'bg-accent' : 'hover:bg-accent/50'}`}
          key={t.id}
          role="tab"
        >
          <button className="min-w-0 flex-1 truncate text-left" onClick={() => onSelect(t.id)} title={t.url} type="button">
            <span className={`codicon ${t.loading ? 'codicon-loading' : t.secure ? 'codicon-lock' : 'codicon-shield'} mr-1`} />
            {t.title || t.url || 'New tab'}
          </button>
          <button aria-label={`Pin ${t.title}`} className="opacity-60 hover:opacity-100" onClick={() => onPin(t.id)} type="button">
            <span className="codicon codicon-pin" />
          </button>
          <button aria-label={`Duplicate ${t.title}`} className="opacity-60 hover:opacity-100" onClick={() => onDuplicate(t.id)} type="button">
            <span className="codicon codicon-copy" />
          </button>
          <button aria-label={`Close ${t.title}`} className="opacity-60 hover:opacity-100" onClick={() => onClose(t.id)} type="button">
            <span className="codicon codicon-close" />
          </button>
        </div>
      ))}
      <Button aria-label="New tab" onClick={onNewTab} size="sm" variant="ghost">
        +
      </Button>
    </div>
  )
}

function ResearchToolbar() {
  return (
    <div className="flex items-center gap-2 border-b border-(--ui-stroke-tertiary) bg-accent/30 px-3 py-1.5 text-xs">
      <span className="font-medium">Research mode</span>
      <span className="text-(--ui-text-tertiary)">Visited pages below become citable sources.</span>
      <span className="flex-1" />
      <Button onClick={() => setBrowserMode('browse')} size="sm" variant="ghost">
        Exit research
      </Button>
    </div>
  )
}

// Real page rendering through Electron's <webview> (webviewTag is enabled on
// app windows). Loading events drive the tab store; an empty URL shows an
// honest empty state instead of a fake page. Rendered via a dynamic tag so no
// global JSX augmentation is needed.
const WebviewTag = 'webview' as unknown as ElementType

function WebView({ loading, readerMode, url }: { loading: boolean; readerMode: boolean; url: string }) {
  const ref = useRef<unknown>(null)
  const activeTab = useStore($activeTab)
  const activeTabId = activeTab?.id

  useEffect(() => {
    const el = ref.current as unknown as {
      addEventListener?: (name: string, fn: () => void) => void
      removeEventListener?: (name: string, fn: () => void) => void
    } | null

    if (!el?.addEventListener || !activeTabId) {return}
    const start = () => setTabLoading(activeTabId, true)

    const stop = () => {
      setTabLoading(activeTabId, false)
      updateTabNavState(activeTabId, true, false)
    }

    el.addEventListener('did-start-loading', start)
    el.addEventListener('did-stop-loading', stop)

    return () => {
      el.removeEventListener?.('did-start-loading', start)
      el.removeEventListener?.('did-stop-loading', stop)
    }
  }, [activeTabId])

  if (!url || url === 'about:blank') {
    return (
      <EmptyState description="Enter a URL above to browse. Agent-driven pages appear here when automation runs." icon="globe" title="No page loaded" />
    )
  }

  return (
    <div className="relative h-full w-full">
      {readerMode && (
        <div className="absolute left-2 top-2 z-10 rounded bg-accent px-2 py-0.5 text-[0.6rem]">Reader mode</div>
      )}
      {loading && (
        <div className="absolute left-2 top-2 z-10 rounded bg-accent px-2 py-0.5 text-[0.6rem]">Loading…</div>
      )}
      <WebviewTag className="h-full w-full" partition="persist:aetheros-browser" ref={ref} src={url} />
    </div>
  )
}

function ResearchView() {
  const browser = useStore($browser)
  const sources = browser.history.slice(0, 20)

  return (
    <div className="mx-auto max-w-3xl space-y-2 p-6">
      <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)">Research sources</h2>
      {sources.length === 0 ? (
        <EmptyState description="Pages you visit in research mode are listed here as citable sources." icon="book" title="No sources yet" />
      ) : (
        sources.map(s => (
          <div className="rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-xs" key={s.id}>
            <div className="truncate font-medium">{s.title || s.url}</div>
            <div className="truncate font-mono text-(--ui-text-tertiary)">{s.url}</div>
            <div className="text-(--ui-text-tertiary)">visited {formatTimestamp(s.visitTime)} · {s.visitCount}x</div>
          </div>
        ))
      )}
    </div>
  )
}

function HistoryView() {
  const browser = useStore($browser)

  return (
    <div className="mx-auto max-w-3xl space-y-2 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)">History</h2>
        <Button onClick={() => clearHistory()} size="sm" variant="ghost">
          Clear
        </Button>
      </div>
      {browser.history.length === 0 ? (
        <EmptyState description="Visited pages appear here." icon="history" title="No history" />
      ) : (
        browser.history.map(h => (
          <div className="flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-xs" key={h.id}>
            <div className="min-w-0 flex-1 truncate">
              <span className="font-medium">{h.title || h.url}</span>
              <span className="ml-2 font-mono text-(--ui-text-tertiary)">{h.url}</span>
            </div>
            <span className="shrink-0 text-(--ui-text-tertiary)">{formatTimestamp(h.visitTime)}</span>
          </div>
        ))
      )}
    </div>
  )
}

function BookmarksView() {
  const browser = useStore($browser)
  const [title, setTitle] = useState('')
  const [url, setUrl] = useState('')

  return (
    <div className="mx-auto max-w-3xl space-y-2 p-6">
      <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)">Bookmarks</h2>
      <div className="flex gap-2">
        <Input className="h-8 flex-1 text-xs" onChange={e => setTitle(e.target.value)} placeholder="Title" value={title} />
        <Input className="h-8 flex-1 font-mono text-xs" onChange={e => setUrl(e.target.value)} placeholder="https://…" value={url} />
        <Button
          disabled={!url.trim()}
          onClick={() => {
            addBookmark(title.trim() || url.trim(), url.trim())
            setTitle('')
            setUrl('')
          }}
          size="sm"
          variant="secondary"
        >
          Add
        </Button>
      </div>
      {browser.bookmarks.length === 0 ? (
        <EmptyState description="Save pages for quick access." icon="bookmark" title="No bookmarks" />
      ) : (
        browser.bookmarks.map(b => (
          <div className="flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-xs" key={b.id}>
            <div className="min-w-0 flex-1 truncate">
              <span className="font-medium">{b.title}</span>
              <span className="ml-2 font-mono text-(--ui-text-tertiary)">{b.url}</span>
            </div>
            <Button onClick={() => removeBookmark(b.id)} size="sm" variant="ghost">
              Remove
            </Button>
          </div>
        ))
      )}
    </div>
  )
}

function DownloadsView() {
  const browser = useStore($browser)

  return (
    <div className="mx-auto max-w-3xl space-y-2 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)">Downloads</h2>
        <Button onClick={() => clearCompletedDownloads()} size="sm" variant="ghost">
          Clear completed
        </Button>
      </div>
      {browser.downloads.length === 0 ? (
        <EmptyState description="Files downloaded through the browser appear here with verification status." icon="cloud-download" title="No downloads" />
      ) : (
        browser.downloads.map(d => (
          <div className="rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-xs" key={d.id}>
            <div className="flex items-center gap-2">
              <span className="min-w-0 flex-1 truncate font-medium">{d.filename}</span>
              <Badge variant="outline">{d.status}</Badge>
              <Button onClick={() => removeDownload(d.id)} size="sm" variant="ghost">
                Remove
              </Button>
            </div>
            <div className="mt-1 truncate font-mono text-(--ui-text-tertiary)">{d.url}</div>
            <div className="text-(--ui-text-tertiary)">
              {formatBytes(d.downloadedSize)} / {formatBytes(d.totalSize)} · scan: {d.securityScanStatus || 'pending'}
            </div>
          </div>
        ))
      )}
    </div>
  )
}