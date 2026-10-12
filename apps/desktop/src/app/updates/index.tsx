import { useStore } from '@nanostores/react'
import { useEffect } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { $updateStatus, applyUpdates, checkUpdates, startUpdatePoller, stopUpdatePoller } from '@/store/updates'

export function UpdatesView() {
  const updateState = useStore($updateStatus)

  useEffect(() => {
    startUpdatePoller()

    return () => stopUpdatePoller()
  }, [])

  const isAvailable = updateState?.supported && (updateState?.behind ?? 0) > 0

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Updates</PageTitle>
            <PageDescription>Check for updates and manage update preferences</PageDescription>
          </div>
          <Button className="text-xs" onClick={() => checkUpdates()} size="sm" variant="outline">
            <Codicon className="mr-1" name="refresh" size="0.75rem" />
            Check for Updates
          </Button>
        </PageHeader>
      }
    >
      <div className="space-y-4">
        <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
          <div className="flex items-center gap-3">
            <Codicon className="text-(--ui-text-tertiary)" name={isAvailable ? "cloud-download" : "check"} size="1.5rem" />
            <div>
              <h3 className="text-sm font-medium">
                {isAvailable ? 'Update Available' : 'AetherOS is up to date'}
              </h3>
              <p className="mt-0.5 text-xs text-(--ui-text-tertiary)">
                {isAvailable
                  ? `${updateState?.behind ?? 0} commits behind ${updateState?.branch ?? 'main'}`
                  : `Running ${updateState?.currentBranch ?? 'main'} (${(updateState?.currentSha ?? 'unknown').slice(0, 8)})`}
              </p>
            </div>
            {isAvailable && (
              <Button className="ml-auto" onClick={() => applyUpdates()} size="sm">
                Install Update
              </Button>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
          <h3 className="text-sm font-medium">Update Channel</h3>
          <p className="mt-1 text-xs text-(--ui-text-tertiary)">
            Choose your update frequency. Stable releases are recommended for most users.
          </p>
          <div className="mt-3 flex gap-2">
            {['stable', 'beta', 'canary'].map(channel => (
              <Button
                className="text-xs capitalize"
                key={channel}
                onClick={() => window.aetherosDesktop?.updates?.setBranch?.(channel)}
                size="sm"
                variant={updateState?.branch === channel ? 'default' : 'outline'}
              >
                {channel}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </PageShell>
  )
}
