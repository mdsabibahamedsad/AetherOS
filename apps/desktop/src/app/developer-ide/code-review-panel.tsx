import { useStore } from '@nanostores/react'

import { $codeReview, $filteredFindings, clearReview, setSelectedSeverity, setSortBy } from '../../store/code-review'

const severities = ['', 'critical', 'high', 'medium', 'low', 'info'] as const

export function CodeReviewPanel() {
  const review = useStore($codeReview)
  const findings = useStore($filteredFindings)

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="px-2 py-1.5 border-b border-border bg-surface-secondary">
        <div className="flex items-center justify-between">
          <span className="font-medium">Code Review</span>
          <button className="text-2xs text-foreground-secondary hover:text-foreground" onClick={() => clearReview()}>Clear</button>
        </div>
        <div className="flex gap-1 mt-1">
          {severities.map(s => (
            <button
              className={`px-1.5 py-0.5 text-2xs rounded capitalize ${
                review.selectedSeverity === s ? 'bg-accent text-white' : 'bg-surface-hover text-foreground-secondary'
              }`}
              key={s}
              onClick={() => setSelectedSeverity(s)}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2 px-2 py-1 text-2xs text-foreground-secondary border-b border-border">
        <span>{review.totalFindings} findings in {review.totalFiles} files</span>
        <select className="bg-transparent text-2xs outline-none" onChange={e => setSortBy(e.target.value as any)} value={review.sortBy}>
          <option value="severity">Severity</option>
          <option value="file">File</option>
          <option value="category">Category</option>
        </select>
      </div>
      <div className="flex-1 overflow-auto">
        {findings.map((f, i) => (
          <div className="px-3 py-1 hover:bg-surface-hover cursor-pointer" key={i}>
            <div className="flex items-center gap-1">
              <span className={`codicon codicon-${f.severity === 'critical' || f.severity === 'high' ? 'error' : f.severity === 'medium' ? 'warning' : 'info'} ${
                f.severity === 'critical' ? 'text-red-500' : f.severity === 'high' ? 'text-orange-500' : f.severity === 'medium' ? 'text-yellow-500' : 'text-blue-500'
              }`} />
              <span className="font-medium truncate text-xs">{f.message}</span>
            </div>
            <div className="text-2xs text-foreground-secondary ml-4">
              {f.file}:{f.line} — {f.category} ({f.ruleId})
            </div>
          </div>
        ))}
        {findings.length === 0 && (
          <div className="p-4 text-center text-foreground-secondary">No review findings</div>
        )}
      </div>
    </div>
  )
}
