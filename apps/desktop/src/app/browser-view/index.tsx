import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { EmptyState } from '@/app/projects'

export function BrowserView() {
  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Browser</PageTitle>
            <PageDescription>Web browsing and automation</PageDescription>
          </div>
        </PageHeader>
      }
    >
      <EmptyState
        description="Agent web browsing sessions will appear here"
        icon="globe"
        title="Browser automation"
      />
    </PageShell>
  )
}
