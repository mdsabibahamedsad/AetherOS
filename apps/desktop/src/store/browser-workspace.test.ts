import { beforeEach, describe, expect, it } from 'vitest'

import {
  $activeTab, $browser, $pinnedTabs, $unpinnedTabs,
  activateTab, addBookmark, addDownload, addHistoryItem, addTab, clearCompletedDownloads, clearHistory,
  closeTab, removeBookmark,
  removeDownload, setBrowserMode, setPageZoom, setTabLoading,
  togglePinTab, togglePrivateMode, toggleReaderMode, updateDownload,
  updateTabTitle, updateTabUrl,
} from './browser-workspace'

describe('browser-workspace store', () => {
  beforeEach(() => {
    $browser.set({
      mode: 'browse',
      tabs: [{ id: 'welcome', url: 'about:blank', title: 'Welcome', loading: false, pinned: false, group: '', secure: true, canGoBack: false, canGoForward: false }],
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
  })

  describe('setBrowserMode', () => {
    it('changes the browser mode', () => {
      setBrowserMode('history')
      expect($browser.get().mode).toBe('history')
      setBrowserMode('bookmarks')
      expect($browser.get().mode).toBe('bookmarks')
    })
  })

  describe('addTab', () => {
    it('adds a new tab and activates it', () => {
      const id = addTab('https://example.com')
      const state = $browser.get()
      expect(state.tabs).toHaveLength(2)
      expect(state.activeTabId).toBe(id)
      expect(state.tabs.find(t => t.id === id)?.url).toBe('https://example.com')
    })

    it('creates a blank tab by default', () => {
      const id = addTab()
      const tab = $browser.get().tabs.find(t => t.id === id)
      expect(tab?.url).toBe('about:blank')
      expect(tab?.title).toBe('New Tab')
    })

    it('creates a pinned tab', () => {
      const id = addTab('https://example.com', true)
      const tab = $browser.get().tabs.find(t => t.id === id)
      expect(tab?.pinned).toBe(true)
    })
  })

  describe('closeTab', () => {
    it('removes the tab', () => {
      const id = addTab('https://example.com')
      closeTab(id)
      expect($browser.get().tabs.find(t => t.id === id)).toBeUndefined()
    })

    it('activates another tab when closing the active one', () => {
      const id1 = addTab('https://a.com')
      const id2 = addTab('https://b.com')
      activateTab(id1)
      closeTab(id1)
      expect($browser.get().activeTabId).toBe(id2)
    })
  })

  describe('activateTab', () => {
    it('sets the active tab', () => {
      const id = addTab('https://example.com')
      activateTab(id)
      expect($browser.get().activeTabId).toBe(id)
    })
  })

  describe('togglePinTab', () => {
    it('toggles pinned state', () => {
      const id = addTab('https://example.com')
      togglePinTab(id)
      expect($browser.get().tabs.find(t => t.id === id)?.pinned).toBe(true)
      togglePinTab(id)
      expect($browser.get().tabs.find(t => t.id === id)?.pinned).toBe(false)
    })
  })

  describe('updateTabUrl', () => {
    it('updates the tab URL and sets loading', () => {
      const id = addTab()
      updateTabUrl(id, 'https://example.com')
      const tab = $browser.get().tabs.find(t => t.id === id)
      expect(tab?.url).toBe('https://example.com')
      expect(tab?.loading).toBe(true)
    })
  })

  describe('updateTabTitle', () => {
    it('updates the tab title and clears loading', () => {
      const id = addTab('https://example.com')
      updateTabTitle(id, 'Example Domain')
      const tab = $browser.get().tabs.find(t => t.id === id)
      expect(tab?.title).toBe('Example Domain')
      expect(tab?.loading).toBe(false)
    })
  })

  describe('setTabLoading', () => {
    it('sets loading state', () => {
      const id = addTab()
      setTabLoading(id, true)
      expect($browser.get().tabs.find(t => t.id === id)?.loading).toBe(true)
    })
  })

  describe('$activeTab', () => {
    it('returns the active tab', () => {
      const id = addTab('https://example.com')
      activateTab(id)
      expect($activeTab.get()?.id).toBe(id)
    })

    it('returns null when no tabs', () => {
      // Reset with empty tabs
      $browser.set({ ...$browser.get(), tabs: [], activeTabId: '' })
      expect($activeTab.get()).toBeNull()
    })
  })

  describe('toggleReaderMode', () => {
    it('toggles reader mode', () => {
      toggleReaderMode()
      expect($browser.get().readerMode).toBe(true)
      toggleReaderMode()
      expect($browser.get().readerMode).toBe(false)
    })
  })

  describe('setPageZoom', () => {
    it('sets zoom level', () => {
      setPageZoom(150)
      expect($browser.get().pageZoom).toBe(150)
    })

    it('clamps zoom to valid range', () => {
      setPageZoom(10)
      expect($browser.get().pageZoom).toBe(25)
      setPageZoom(600)
      expect($browser.get().pageZoom).toBe(500)
    })
  })

  describe('togglePrivateMode', () => {
    it('toggles private mode', () => {
      togglePrivateMode()
      expect($browser.get().privateMode).toBe(true)
      togglePrivateMode()
      expect($browser.get().privateMode).toBe(false)
    })
  })

  describe('addHistoryItem', () => {
    it('adds a new history entry', () => {
      addHistoryItem('https://example.com', 'Example')
      expect($browser.get().history).toHaveLength(1)
      expect($browser.get().history[0].url).toBe('https://example.com')
    })

    it('increments visit count for duplicate', () => {
      addHistoryItem('https://example.com', 'Example')
      addHistoryItem('https://example.com', 'Example')
      expect($browser.get().history[0].visitCount).toBe(2)
    })
  })

  describe('clearHistory', () => {
    it('clears all history', () => {
      addHistoryItem('https://example.com', 'Test')
      clearHistory()
      expect($browser.get().history).toHaveLength(0)
    })
  })

  describe('addBookmark', () => {
    it('adds a bookmark', () => {
      addBookmark('Example', 'https://example.com', 'Work', ['test'])
      expect($browser.get().bookmarks).toHaveLength(1)
      expect($browser.get().bookmarks[0].title).toBe('Example')
    })
  })

  describe('removeBookmark', () => {
    it('removes a bookmark', () => {
      addBookmark('Test', 'https://test.com')
      removeBookmark($browser.get().bookmarks[0].id)
      expect($browser.get().bookmarks).toHaveLength(0)
    })
  })

  describe('addDownload', () => {
    it('adds a download', () => {
      addDownload({
        id: 'dl1', url: 'https://example.com/file.pdf', filename: 'file.pdf',
        destination: '/downloads', totalSize: 1000, downloadedSize: 0,
        status: 'pending', mimeType: 'application/pdf', securityScanStatus: 'pending',
      })
      expect($browser.get().downloads).toHaveLength(1)
    })
  })

  describe('updateDownload', () => {
    it('updates a download', () => {
      addDownload({
        id: 'dl1', url: 'https://example.com/file.pdf', filename: 'file.pdf',
        destination: '/downloads', totalSize: 1000, downloadedSize: 0,
        status: 'pending', mimeType: 'application/pdf', securityScanStatus: 'pending',
      })
      updateDownload('dl1', { status: 'downloading', downloadedSize: 500 })
      expect($browser.get().downloads[0].status).toBe('downloading')
    })
  })

  describe('removeDownload', () => {
    it('removes a download', () => {
      addDownload({
        id: 'dl1', url: 'https://example.com/file.pdf', filename: 'file.pdf',
        destination: '/downloads', totalSize: 1000, downloadedSize: 0,
        status: 'pending', mimeType: 'application/pdf', securityScanStatus: 'pending',
      })
      removeDownload('dl1')
      expect($browser.get().downloads).toHaveLength(0)
    })
  })

  describe('clearCompletedDownloads', () => {
    it('removes completed downloads only', () => {
      addDownload({ id: 'dl1', url: 'https://a.com', filename: 'a.pdf', destination: '/d', totalSize: 100, downloadedSize: 100, status: 'completed', mimeType: '', securityScanStatus: '' })
      addDownload({ id: 'dl2', url: 'https://b.com', filename: 'b.pdf', destination: '/d', totalSize: 100, downloadedSize: 50, status: 'downloading', mimeType: '', securityScanStatus: '' })
      clearCompletedDownloads()
      expect($browser.get().downloads).toHaveLength(1)
      expect($browser.get().downloads[0].id).toBe('dl2')
    })
  })

  describe('computed atoms', () => {
    it('$pinnedTabs returns only pinned tabs', () => {
      const id1 = addTab('https://a.com', true)
      addTab('https://b.com', false)
      expect($pinnedTabs.get()).toHaveLength(1)
    })

    it('$unpinnedTabs returns only unpinned tabs', () => {
      addTab('https://a.com', true)
      const id2 = addTab('https://b.com', false)
      const unpinned = $unpinnedTabs.get()
      expect(unpinned).toHaveLength(2)
      expect(unpinned.every(t => !t.pinned)).toBe(true)
    })
  })
})
