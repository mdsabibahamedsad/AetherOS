import { atom, computed } from 'nanostores'

export type BrowserMode = 'browse' | 'automation' | 'research' | 'history' | 'bookmarks' | 'downloads' | 'settings'

export interface BrowserTab {
  id: string
  url: string
  title: string
  loading: boolean
  pinned: boolean
  group: string
  secure: boolean
  canGoBack: boolean
  canGoForward: boolean
}

export interface BookmarkItem {
  id: string
  title: string
  url: string
  folder: string
  tags: string[]
  createdAt: string
}

export interface HistoryItem {
  id: string
  url: string
  title: string
  visitTime: string
  visitCount: number
}

export interface DownloadItem {
  id: string
  url: string
  filename: string
  destination: string
  totalSize: number
  downloadedSize: number
  status: 'pending' | 'downloading' | 'paused' | 'completed' | 'failed' | 'cancelled'
  mimeType: string
  securityScanStatus: string
}

export interface BrowserState {
  mode: BrowserMode
  tabs: BrowserTab[]
  activeTabId: string
  sidebarOpen: boolean
  readerMode: boolean
  pageZoom: number
  privateMode: boolean
  sidebarWidth: number
  searchQuery: string
  searchProvider: string
  searchSuggestions: string[]
  searchHistory: string[]
  bookmarks: BookmarkItem[]
  history: HistoryItem[]
  downloads: DownloadItem[]
  pageTitle: string
  pageUrl: string
  pageLoading: boolean
}

const defaultTabs: BrowserTab[] = [
  { id: 'welcome', url: 'about:blank', title: 'Welcome', loading: false, pinned: false, group: '', secure: true, canGoBack: false, canGoForward: false },
]

export const $browser = atom<BrowserState>({
  mode: 'browse',
  tabs: defaultTabs,
  activeTabId: 'welcome',
  sidebarOpen: true,
  readerMode: false,
  pageZoom: 100,
  privateMode: false,
  sidebarWidth: 280,
  searchQuery: '',
  searchProvider: 'Google',
  searchSuggestions: [],
  searchHistory: [],
  bookmarks: [],
  history: [],
  downloads: [],
  pageTitle: '',
  pageUrl: '',
  pageLoading: false,
})

export const $activeTab = computed($browser, (state) =>
  state.tabs.find(t => t.id === state.activeTabId) ?? null
)

export const $pinnedTabs = computed($browser, (state) =>
  state.tabs.filter(t => t.pinned)
)

export const $unpinnedTabs = computed($browser, (state) =>
  state.tabs.filter(t => !t.pinned)
)

export const $tabGroups = computed($browser, (state) => {
  const groups: Record<string, BrowserTab[]> = {}

  for (const tab of state.tabs) {
    const g = tab.group || '_ungrouped'

    if (!groups[g]) {groups[g] = []}
    groups[g].push(tab)
  }

  return groups
})

export const $activeDownloads = computed($browser, (state) =>
  state.downloads.filter(d => d.status === 'downloading' || d.status === 'pending')
)

export function setBrowserMode(mode: BrowserMode) {
  const state = $browser.get()
  $browser.set({ ...state, mode })
}

export function addTab(url = 'about:blank', pinned = false): string {
  const state = $browser.get()
  const id = `tab_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

  const tab: BrowserTab = {
    id,
    url,
    title: url === 'about:blank' ? 'New Tab' : url,
    loading: url !== 'about:blank',
    pinned,
    group: '',
    secure: url.startsWith('https://'),
    canGoBack: false,
    canGoForward: false,
  }

  $browser.set({ ...state, tabs: [...state.tabs, tab], activeTabId: id, pageLoading: tab.loading })

  return id
}

export function closeTab(tabId: string) {
  const state = $browser.get()
  const tabs = state.tabs.filter(t => t.id !== tabId)
  let activeTabId = state.activeTabId

  if (activeTabId === tabId) {
    const idx = state.tabs.findIndex(t => t.id === tabId)

    if (tabs.length > 0) {
      activeTabId = tabs[Math.min(idx, tabs.length - 1)].id
    }
  }

  $browser.set({ ...state, tabs, activeTabId })
}

export function activateTab(tabId: string) {
  const state = $browser.get()
  const tab = state.tabs.find(t => t.id === tabId)

  if (tab) {
    $browser.set({ ...state, activeTabId: tabId, pageUrl: tab.url, pageTitle: tab.title, pageLoading: tab.loading })
  }
}

export function duplicateTab(tabId: string) {
  const state = $browser.get()
  const original = state.tabs.find(t => t.id === tabId)

  if (!original) {return}
  const newId = addTab(original.url, false)
  const tabs = $browser.get().tabs
  const updated = tabs.map(t => t.id === newId ? { ...t, title: original.title } : t)
  $browser.set({ ...$browser.get(), tabs: updated })
}

export function togglePinTab(tabId: string) {
  const state = $browser.get()
  const tabs = state.tabs.map(t => t.id === tabId ? { ...t, pinned: !t.pinned } : t)
  $browser.set({ ...state, tabs })
}

export function updateTabUrl(tabId: string, url: string) {
  const state = $browser.get()
  const tabs = state.tabs.map(t => t.id === tabId ? { ...t, url, loading: true, secure: url.startsWith('https://') } : t)
  $browser.set({ ...state, tabs, pageUrl: url, pageLoading: true })
}

export function updateTabTitle(tabId: string, title: string) {
  const state = $browser.get()
  const tabs = state.tabs.map(t => t.id === tabId ? { ...t, title, loading: false } : t)
  $browser.set({ ...state, tabs, pageTitle: title, pageLoading: false })
}

export function updateTabNavState(tabId: string, canGoBack: boolean, canGoForward: boolean) {
  const state = $browser.get()
  const tabs = state.tabs.map(t => t.id === tabId ? { ...t, canGoBack, canGoForward } : t)
  $browser.set({ ...state, tabs })
}

export function setTabLoading(tabId: string, loading: boolean) {
  const state = $browser.get()
  const tabs = state.tabs.map(t => t.id === tabId ? { ...t, loading } : t)
  $browser.set({ ...state, tabs, pageLoading: loading })
}

export function toggleReaderMode() {
  const state = $browser.get()
  $browser.set({ ...state, readerMode: !state.readerMode })
}

export function setPageZoom(zoom: number) {
  const state = $browser.get()
  $browser.set({ ...state, pageZoom: Math.max(25, Math.min(500, zoom)) })
}

export function togglePrivateMode() {
  const state = $browser.get()
  $browser.set({ ...state, privateMode: !state.privateMode })
}

export function setSidebarOpen(open: boolean) {
  const state = $browser.get()
  $browser.set({ ...state, sidebarOpen: open })
}

export function setSearchQuery(query: string) {
  const state = $browser.get()
  $browser.set({ ...state, searchQuery: query })
}

export function setSearchProvider(provider: string) {
  const state = $browser.get()
  $browser.set({ ...state, searchProvider: provider })
}

export function addHistoryItem(url: string, title: string) {
  const state = $browser.get()
  const existing = state.history.find(h => h.url === url)

  if (existing) {
    const history = state.history.map(h =>
      h.id === existing.id ? { ...h, visitCount: h.visitCount + 1, visitTime: new Date().toISOString() } : h
    )

    $browser.set({ ...state, history })
  } else {
    const item: HistoryItem = {
      id: `hist_${Date.now()}`,
      url,
      title,
      visitTime: new Date().toISOString(),
      visitCount: 1,
    }

    $browser.set({ ...state, history: [item, ...state.history].slice(0, 10000) })
  }
}

export function clearHistory() {
  const state = $browser.get()
  $browser.set({ ...state, history: [] })
}

export function addBookmark(title: string, url: string, folder = '', tags: string[] = []) {
  const state = $browser.get()

  const bm: BookmarkItem = {
    id: `bm_${Date.now()}`,
    title,
    url,
    folder,
    tags,
    createdAt: new Date().toISOString(),
  }

  $browser.set({ ...state, bookmarks: [...state.bookmarks, bm] })
}

export function removeBookmark(bookmarkId: string) {
  const state = $browser.get()
  $browser.set({ ...state, bookmarks: state.bookmarks.filter(b => b.id !== bookmarkId) })
}

export function addDownload(item: DownloadItem) {
  const state = $browser.get()
  $browser.set({ ...state, downloads: [...state.downloads, item] })
}

export function updateDownload(id: string, updates: Partial<DownloadItem>) {
  const state = $browser.get()
  const downloads = state.downloads.map(d => d.id === id ? { ...d, ...updates } : d)
  $browser.set({ ...state, downloads })
}

export function removeDownload(id: string) {
  const state = $browser.get()
  $browser.set({ ...state, downloads: state.downloads.filter(d => d.id !== id) })
}

export function clearCompletedDownloads() {
  const state = $browser.get()
  $browser.set({ ...state, downloads: state.downloads.filter(d => d.status !== 'completed') })
}

export function navigateBack() {
  const tab = $activeTab.get()

  if (tab?.canGoBack) {
    updateTabNavState(tab.id, false, true)
  }
}

export function navigateForward() {
  const tab = $activeTab.get()

  if (tab?.canGoForward) {
    updateTabNavState(tab.id, true, false)
  }
}

export function refreshPage() {
  const tab = $activeTab.get()

  if (tab) {
    setTabLoading(tab.id, true)
    setTimeout(() => setTabLoading(tab.id, false), 500)
  }
}
