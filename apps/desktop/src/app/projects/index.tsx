import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { notify, notifyError } from '@/store/notifications'
import { setCurrentCwd } from '@/store/session'

export function ProjectsView() {
  const navigate = useNavigate()

  // Opens a real folder picker, then starts a fresh chat rooted at that
  // folder (the next message creates the backend session in $currentCwd).
  const openFolder = async () => {
    try {
      const paths = await window.aetherosDesktop?.selectPaths({
        title: 'Open folder as project',
        directories: true
      })

      const target = paths?.[0]?.trim()

      if (!target) {
        return
      }

      setCurrentCwd(target)
      notify({ kind: 'success', title: 'Project opened', message: target })
      navigate('/')
    } catch (e) {
      notifyError(e, 'Could not open folder picker')
    }
  }

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Projects</PageTitle>
            <PageDescription>Manage your workspaces and projects</PageDescription>
          </div>
          <Button onClick={() => void openFolder()} size="sm">
            <Codicon className="mr-1.5" name="file-directory" size="0.875rem" />
            Open Folder
          </Button>
        </PageHeader>
      }
    >
      <EmptyState
        action={<Button onClick={() => void openFolder()}>Open Folder</Button>}
        description="Open a folder to add it to your projects"
        icon="project"
        title="No projects yet"
      />
    </PageShell>
  )
}

function EmptyState({ icon, title, description, action }: { icon: string; title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Codicon className="mb-3 text-(--ui-text-tertiary)" name={icon as any} size="2rem" />
      <h3 className="text-sm font-medium">{title}</h3>
      <p className="mt-1 text-xs text-(--ui-text-tertiary)">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export { EmptyState }
