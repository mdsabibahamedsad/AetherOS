import { useStore } from '@nanostores/react'

import { StatusDot } from '@/components/status-dot'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Loader2, RefreshCw } from '@/lib/icons'
import {
  $serviceSync,
  getRecentHistory,
  setAutoSync,
  setGlobalSyncEnabled,
  setSyncInterval,
  type SyncJobConfig,
  toggleSyncJob,
  triggerSyncNow
} from '@/store/service-sync'
import type { ConnectedServiceInfo } from '@/store/services'

interface SyncManagerProps {
  syncStatus: string
  services: ConnectedServiceInfo[]
}

export function SyncManager({ syncStatus, services }: SyncManagerProps) {
  const sync = useStore($serviceSync)

  const enabledJobs = sync.jobs.filter(j => j.enabled)
  const disabledJobs = sync.jobs.filter(j => !j.enabled)

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center gap-4 rounded-lg border border-(--ui-stroke-tertiary) px-4 py-3">
        <StatusDot tone={syncStatus === 'error' ? 'bad' : syncStatus === 'syncing' ? 'warn' : 'good'} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium capitalize">Overall Sync: {syncStatus}</p>
          <p className="text-xs text-(--ui-text-tertiary)">
            {sync.activeRuns.length} active runs · {enabledJobs.length} jobs enabled · {sync.history.length} recent runs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            aria-label="Global sync toggle"
            checked={sync.globalSyncEnabled}
            onCheckedChange={setGlobalSyncEnabled}
            size="xs"
          />
          <span className="text-xs text-(--ui-text-tertiary)">Global Sync</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-xs text-(--ui-text-tertiary)">
          <Switch
            aria-label="Auto-sync"
            checked={sync.autoSync}
            onCheckedChange={setAutoSync}
            size="xs"
          />
          Auto-sync
        </label>
        <label className="flex items-center gap-2 text-xs text-(--ui-text-tertiary)">
          Interval
          <select
            className="rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 py-0.5 text-xs"
            onChange={e => setSyncInterval(Number(e.target.value))}
            value={sync.syncIntervalMs}
          >
            <option value={60000}>1 min</option>
            <option value={300000}>5 min</option>
            <option value={600000}>10 min</option>
            <option value={1800000}>30 min</option>
            <option value={3600000}>1 hour</option>
          </select>
        </label>
      </div>

      {sync.activeRuns.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold">Active Runs</h3>
          <div className="space-y-1">
            {sync.activeRuns.map(run => {
              const job = sync.jobs.find(j => j.id === run.jobId)

              return (
                <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2" key={run.id}>
                  <Loader2 className="size-3.5 animate-spin text-primary" />
                  <span className="min-w-0 flex-1 text-sm font-medium">{job?.name ?? run.jobId}</span>
                  <span className="text-xs text-(--ui-text-tertiary)">Started {new Date(run.startedAt).toLocaleTimeString()}</span>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {enabledJobs.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold">Enabled Sync Jobs ({enabledJobs.length})</h3>
          <div className="space-y-1">
            {enabledJobs.map(job => (
              <SyncJobRow job={job} key={job.id} services={services} />
            ))}
          </div>
        </section>
      )}

      <section>
        <h3 className="mb-2 text-sm font-semibold text-(--ui-text-tertiary)">
          Available Sync Jobs ({disabledJobs.length})
        </h3>
        <div className="space-y-1">
          {disabledJobs.map(job => (
            <SyncJobRow job={job} key={job.id} services={services} />
          ))}
        </div>
      </section>

      {sync.history.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold">Recent Runs</h3>
          <div className="max-h-48 space-y-0.5 overflow-y-auto rounded-lg border border-(--ui-stroke-tertiary) p-2">
            {getRecentHistory(30).map(run => {
              const job = sync.jobs.find(j => j.id === run.jobId)

              return (
                <div className="flex items-center gap-2 px-2 py-1 text-xs" key={run.id}>
                  <StatusDot tone={run.status === 'success' ? 'good' : run.status === 'error' ? 'bad' : 'warn'} />
                  <span className="min-w-0 flex-1 truncate">{job?.name ?? run.jobId}</span>
                  <span className="text-(--ui-text-tertiary)">{run.completedAt ? new Date(run.completedAt).toLocaleTimeString() : '...'}</span>
                  <span className="font-mono text-(--ui-text-tertiary)">{run.itemsProcessed} items</span>
                  <Badge variant={run.status === 'success' ? 'default' : run.status === 'error' ? 'destructive' : 'muted'}>
                    {run.status}
                  </Badge>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {sync.jobs.length === 0 && (
        <p className="py-8 text-center text-xs text-(--ui-text-tertiary)">No sync jobs configured</p>
      )}
    </div>
  )
}

function SyncJobRow({ job, services }: { job: SyncJobConfig; services: ConnectedServiceInfo[] }) {
  const service = services.find(s => s.id === job.serviceId)

  return (
    <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 transition-colors hover:bg-(--chrome-action-hover)">
      <StatusDot tone={job.lastStatus === 'success' ? 'good' : job.lastStatus === 'error' ? 'bad' : 'muted'} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{job.name}</span>
          {service && <Badge variant="outline">{service.name}</Badge>}
        </div>
        <p className="text-xs text-(--ui-text-tertiary)">{job.description}</p>
        {job.lastRunAt && (
          <p className="text-[0.65rem] text-(--ui-text-tertiary)">
            Last run: {new Date(job.lastRunAt).toLocaleString()} · {job.itemsSynced} items synced
          </p>
        )}
      </div>
      <div className="flex items-center gap-1">
        <Button disabled={!job.enabled} onClick={() => triggerSyncNow(job.id)} size="xs" variant="ghost">
          <RefreshCw className="size-3" />
          Sync
        </Button>
        <Switch
          aria-label={`${job.enabled ? 'Disable' : 'Enable'} ${job.name}`}
          checked={job.enabled}
          onCheckedChange={() => toggleSyncJob(job.id)}
          size="xs"
        />
      </div>
    </div>
  )
}
