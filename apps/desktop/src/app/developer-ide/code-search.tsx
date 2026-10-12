import { useStore } from '@nanostores/react'

import { $codeSearch, $resultCount, $searchResults, setSearchQuery, setSearchType } from '../../store/code-search'

const searchTypes = [
  { id: 'text' as const, label: 'Text' },
  { id: 'symbol' as const, label: 'Symbol' },
  { id: 'semantic' as const, label: 'Semantic' },
  { id: 'dependency' as const, label: 'Dependency' },
  { id: 'all' as const, label: 'All' },
]

export function CodeSearch() {
  const search = useStore($codeSearch)
  const results = useStore($searchResults)
  const count = useStore($resultCount)

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="p-2">
        <div className="relative">
          <span className="codicon codicon-search absolute left-2 top-1/2 -translate-y-1/2 text-foreground-secondary text-xs" />
          <input
            className="w-full pl-7 pr-2 py-1 text-xs bg-surface border border-border rounded placeholder-foreground-secondary outline-none focus:border-accent"
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search code..."
            value={search.query}
          />
        </div>
        <div className="flex gap-0.5 mt-1">
          {searchTypes.map(t => (
            <button
              className={`px-1.5 py-0.5 text-2xs rounded ${search.searchType === t.id ? 'bg-accent text-white' : 'bg-surface-hover text-foreground-secondary hover:text-foreground'}`}
              key={t.id}
              onClick={() => setSearchType(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      {count > 0 && (
        <div className="px-2 py-1 text-2xs text-foreground-secondary border-t border-border">
          {count} results
        </div>
      )}
      <div className="flex-1 overflow-auto">
        {results.slice(0, 50).map((r, i) => (
          <div
            className={`px-2 py-1 cursor-pointer hover:bg-surface-hover ${
              search.selectedResultIndex === i ? 'bg-surface-hover' : ''
            }`}
            key={i}
          >
            <div className="flex items-center gap-1">
              <span className={`codicon codicon-${r.type === 'file' ? 'file' : r.type === 'symbol' ? 'symbol-method' : 'package'} text-2xs`} />
              <span className="font-medium truncate text-xs">{r.symbol || r.file}</span>
            </div>
            <div className="text-2xs text-foreground-secondary truncate">{r.file}:{r.line}</div>
            {r.kind && <div className="text-2xs text-foreground-secondary">Kind: {r.kind}</div>}
          </div>
        ))}
        {search.query && count === 0 && !search.isSearching && (
          <div className="p-3 text-center text-foreground-secondary text-2xs">No results found</div>
        )}
      </div>
    </div>
  )
}
