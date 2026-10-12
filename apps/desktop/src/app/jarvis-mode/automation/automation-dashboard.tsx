/**
 * Jarvis automation dashboard — REAL scheduled jobs from the backend.
 *
 * Lists live cron jobs (`GET /api/cron/jobs`) with pause/resume/trigger/
 * delete backed by the matching REST calls. "New automation" does not invent
 * a fake queued entry: it focuses the composer with a scheduling prompt so
 * the gateway agent creates a real job.
 */

import { memo, useCallback, useEffect, useState } from 'react'

import { Codicon } from '@/components/ui/codicon'
import {
  type CronJob,
  deleteCronJob,
  getCronJobs,
  pauseCronJob,
  resumeCronJob,
  triggerCronJob
} from '@/hermes'
import { addJarvisNotification } from '@/store/jarvis-mode'

type Filter = 'all' | 'active' | 'paused'

const FILTERS: Array<{ id: Filter; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'active', label: 'Active' },
  { id: 'paused', label: 'Paused' }
]

function JobCard({ job, onChange }: { job: CronJob; onChange: () => void }) {
  const [busy, setBusy] = useState(false)
  const paused = job.enabled === false
  const scheduleText = job.schedule_display ?? (typeof job.schedule === 'string' ? job.schedule : '')

  const act = useCallback(async (fn: () => Promise<unknown>, label: string) => {
    setBusy(true)

    try {
      await fn()
      onChange()
    } catch (err) {
      addJarvisNotification({ title: `${label} failed`, message: err instanceof Error ? err.message : String(err), type: 'error' })
    } finally {
      setBusy(false)
    }
  }, [onChange])

  return (
    <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
      <div className="flex items-center gap-2">
        <span className={`size-1.5 rounded-full ${paused ? 'bg-white/20' : 'bg-emerald-400'}`} />
        <span className="text-[13px] font-medium text-white/75 truncate flex-1">{job.name || job.id}</span>
        <span className="text-[10px] text-white/25 font-mono truncate">{scheduleText}</span>
      </div>
      {job.prompt && (
        <div className="text-[11px] text-white/35 mt-1 line-clamp-2">{job.prompt}</div>
      )}
      <div className="flex items-center gap-1.5 mt-2">
        <button
          className="px-2 py-0.5 rounded-md text-[10px] bg-white/[0.05] text-white/40 hover:text-white/70 disabled:opacity-40"
          disabled={busy}
          onClick={() => void act(() => (paused ? resumeCronJob(job.id) : pauseCronJob(job.id)), paused ? 'Resume' : 'Pause')}
        >
          {paused ? 'Resume' : 'Pause'}
        </button>
        <button
          className="px-2 py-0.5 rounded-md text-[10px] bg-white/[0.05] text-white/40 hover:text-white/70 disabled:opacity-40"
          disabled={busy}
          onClick={() => void act(() => triggerCronJob(job.id), 'Trigger')}
        >
          Run now
        </button>
        <button
          className="px-2 py-0.5 rounded-md text-[10px] bg-white/[0.05] text-white/40 hover:text-red-400 disabled:opacity-40"
          disabled={busy}
          onClick={() => void act(() => deleteCronJob(job.id), 'Delete')}
        >
          Delete
        </button>
      </div>
    </div>
  )
}

function AutomationDashboardComponent() {
  const [filter, setFilter] = useState<Filter>('all')
  const [jobs, setJobs] = useState<CronJob[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const list = await getCronJobs()
      setJobs(Array.isArray(list) ? list : [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load scheduled jobs.')
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const filtered = (jobs ?? []).filter(j => {
    if (filter === 'all') {return true}

    if (filter === 'paused') {return j.enabled === false}

    return j.enabled !== false
  })

  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-white/90">Automation</h2>
          <p className="text-[12px] text-white/30 mt-0.5">Real scheduled jobs from the backend</p>
        </div>
        <button
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium bg-[#0066ff]/20 text-[#00d4ff] border border-[#0066ff]/30 hover:bg-[#0066ff]/30 transition-all"
          onClick={() => {
            addJarvisNotification({
              title: 'New automation',
              message: 'Type e.g. "Remind me every weekday at 9am to review releases" in the composer below.',
              type: 'info'
            })
            window.dispatchEvent(new CustomEvent('jarvis:focus-composer'))
          }}
          title="The composer creates the job through the gateway agent"
        >
          <Codicon className="size-3.5" name="zap" />
          New Automation
        </button>
      </div>

      <div className="flex gap-1 mb-4">
        {FILTERS.map(f => (
          <button
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
              filter === f.id
                ? 'bg-white/[0.08] text-white/80 border border-white/[0.1]'
                : 'text-white/30 hover:text-white/50 border border-transparent'
            }`}
            key={f.id}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          aria-label="Refresh from backend"
          className="px-2 py-1.5 rounded-lg text-[11px] text-white/30 hover:text-white/60"
          onClick={() => void refresh()}
          title="Refresh from backend"
        >
          <Codicon className="size-3.5" name="refresh" />
        </button>
      </div>

      {error && (
        <div className="mb-3 rounded-lg border border-red-500/30 bg-red-500/[0.06] px-3 py-2 text-[12px] text-red-300" role="alert">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto scrollbar-dt space-y-2">
        {jobs === null && !error && <div className="text-[12px] text-white/30 px-1">Loading scheduled jobs...</div>}
        {jobs !== null && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Codicon className="size-12 text-white/[0.06] mb-3" name="run-all" />
            <span className="text-[13px] text-white/20">No {filter === 'all' ? '' : filter} jobs</span>
            <span className="text-[11px] text-white/15 mt-1">Ask Jarvis to schedule something</span>
          </div>
        )}
        {filtered.map(job => (
          <JobCard job={job} key={job.id} onChange={() => void refresh()} />
        ))}
      </div>
    </div>
  )
}

export const AutomationDashboard = memo(AutomationDashboardComponent)
