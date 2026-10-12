import { atom, computed } from 'nanostores'

export interface SearchResult {
  type: 'file' | 'symbol' | 'dependency'
  file: string
  symbol?: string
  kind?: string
  line: number
  match?: string
  score?: number
}

export interface CodeSearchState {
  query: string
  searchType: 'text' | 'symbol' | 'semantic' | 'dependency' | 'all'
  results: SearchResult[]
  isSearching: boolean
  selectedResultIndex: number
  includeNodeModules: boolean
  maxResults: number
}

export const $codeSearch = atom<CodeSearchState>({
  query: '',
  searchType: 'all',
  results: [],
  isSearching: false,
  selectedResultIndex: 0,
  includeNodeModules: false,
  maxResults: 100,
})

export const $searchResults = computed($codeSearch, (s) => s.results)
export const $selectedResult = computed($codeSearch, (s) => s.results[s.selectedResultIndex] ?? null)
export const $resultCount = computed($codeSearch, (s) => s.results.length)

export function setSearchQuery(query: string) {
  const state = $codeSearch.get()
  $codeSearch.set({ ...state, query })
}

export function setSearchType(searchType: CodeSearchState['searchType']) {
  const state = $codeSearch.get()
  $codeSearch.set({ ...state, searchType })
}

export function setSearchResults(results: SearchResult[]) {
  const state = $codeSearch.get()
  $codeSearch.set({ ...state, results, isSearching: false, selectedResultIndex: 0 })
}

export function setSearching(searching: boolean) {
  const state = $codeSearch.get()
  $codeSearch.set({ ...state, isSearching: searching })
}

export function selectNextResult() {
  const state = $codeSearch.get()
  const next = Math.min(state.selectedResultIndex + 1, state.results.length - 1)
  $codeSearch.set({ ...state, selectedResultIndex: next })
}

export function selectPreviousResult() {
  const state = $codeSearch.get()
  const prev = Math.max(state.selectedResultIndex - 1, 0)
  $codeSearch.set({ ...state, selectedResultIndex: prev })
}

export function clearSearch() {
  $codeSearch.set({
    query: '', searchType: 'all', results: [], isSearching: false,
    selectedResultIndex: 0, includeNodeModules: false, maxResults: 100,
  })
}
