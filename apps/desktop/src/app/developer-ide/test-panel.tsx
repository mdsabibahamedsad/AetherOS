import { useStore } from '@nanostores/react'

import { $filteredSuites, $testRunner, $testSummary, setTestRunning, toggleShowOnlyFailed, toggleSuite } from '../../store/test-runner'

export function TestPanel() {
  const test = useStore($testRunner)
  const summary = useStore($testSummary)
  const suites = useStore($filteredSuites)

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="flex items-center justify-between px-2 py-1 border-b border-border bg-surface-secondary">
        <div className="flex items-center gap-2">
          <button className="px-2 py-0.5 text-2xs bg-accent text-white rounded hover:bg-accent-hover" onClick={() => setTestRunning(true)}>Run All</button>
          <button className={`px-2 py-0.5 text-2xs rounded ${test.showOnlyFailed ? 'bg-red-500/20 text-red-500' : 'bg-surface-hover text-foreground-secondary'}`} onClick={() => toggleShowOnlyFailed()}>
            Failed Only
          </button>
        </div>
        <div className="flex items-center gap-2 text-2xs">
          <span className="text-green-500">{summary.passed} passed</span>
          <span className="text-red-500">{summary.failed} failed</span>
          <span className="text-foreground-secondary">{summary.total} total</span>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        {suites.length === 0 ? (
          <div className="p-4 text-center text-foreground-secondary">No tests found</div>
        ) : (
          suites.map(su => (
            <div key={su.id}>
              <div
                className="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-surface-hover"
                onClick={() => toggleSuite(su.id)}
              >
                <span className={`codicon codicon-chevron-${su.expanded ? 'down' : 'right'} text-2xs`} />
                <span className="codicon codicon-beaker text-xs" />
                <span className="flex-1">{su.name}</span>
                <span className="text-green-500 text-2xs">{su.passed}</span>
                {su.failed > 0 && <span className="text-red-500 text-2xs">{su.failed}</span>}
              </div>
              {su.expanded && su.tests.map(t => (
                <div className="flex items-center gap-2 px-6 py-0.5 text-2xs" key={t.id}>
                  <span className={`codicon codicon-${t.status === 'passed' ? 'check' : t.status === 'failed' ? 'x' : 'circle-outline'} ${
                    t.status === 'passed' ? 'text-green-500' : t.status === 'failed' ? 'text-red-500' : 'text-foreground-secondary'
                  }`} />
                  <span className="truncate">{t.name}</span>
                  <span className="text-foreground-secondary">{t.duration}ms</span>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
