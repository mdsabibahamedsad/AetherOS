import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { EmptyState } from '@/app/projects'

export function HistoryView() {
  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>History</PageTitle>
            <PageDescription>Session history and activity log</PageDescription>
          </div>
        </PageHeader>
      }
    >
      <EmptyState
        description="Past conversations and agent activity will appear here"
        icon="history"
        title="Session history"
      />
    </PageShell>
  )
}
