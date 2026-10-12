import { useEffect, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'

export function LogsView() {
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  const fetchLogs = async () => {
    setLoading(true)

    try {
      const recent = await window.aetherosDesktop?.getRecentLogs?.()

      if (recent?.lines) {setLogs(recent.lines)}
    } catch {
      // Non-fatal
    }

    setLoading(false)
  }

  useEffect(() => {
    fetchLogs()
  }, [])

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Logs</PageTitle>
            <PageDescription>Application and agent logs</PageDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              className="text-xs"
              onClick={() => window.aetherosDesktop?.revealLogs?.()}
              size="sm"
              variant="outline"
            >
              <Codicon className="mr-1" name="folder-opened" size="0.75rem" />
              Reveal in Finder
            </Button>
            <Button className="text-xs" onClick={fetchLogs} size="sm" variant="outline">
              <Codicon className="mr-1" name="refresh" size="0.75rem" />
              Refresh
            </Button>
          </div>
        </PageHeader>
      }
    >
      <div className="space-y-1">
        {loading ? (
          <p className="py-8 text-center text-xs text-(--ui-text-tertiary)">Loading logs...</p>
        ) : logs.length === 0 ? (
          <p className="py-8 text-center text-xs text-(--ui-text-tertiary)">No log entries</p>
        ) : (
          logs.map((line, i) => (
            <div className="font-mono text-[0.625rem] leading-5 text-(--ui-text-tertiary)" key={i}>
              {line}
            </div>
          ))
        )}
      </div>
    </PageShell>
  )
}
