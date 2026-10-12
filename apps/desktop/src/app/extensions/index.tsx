
import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { EmptyState } from '@/app/projects'

function ExtensionsList() {
  return (
    <EmptyState
      description="Install and manage AetherOS extensions"
      icon="extensions"
      title="Extensions"
    />
  )
}

function MarketplaceView() {
  return (
    <EmptyState
      description="Browse the extensions marketplace"
      icon="package"
      title="Marketplace"
    />
  )
}

function McpView() {
  return (
    <EmptyState
      description="Manage Model Context Protocol servers"
      icon="server"
      title="MCP Servers"
    />
  )
}

export function ExtensionsView() {
  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Extensions</PageTitle>
            <PageDescription>Extend AetherOS with plugins and MCP servers</PageDescription>
          </div>
        </PageHeader>
      }
    >
      <ExtensionsList />
    </PageShell>
  )
}

export { MarketplaceView, McpView }
