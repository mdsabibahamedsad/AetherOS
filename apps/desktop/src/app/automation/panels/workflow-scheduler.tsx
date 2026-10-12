import { useStore } from '@nanostores/react'

import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'
import {
  $automation,
  type ScheduleType,
  setWorkflowSchedule,
} from '@/store/automation'

export function WorkflowScheduler() {
  const state = useStore($automation)
  const workflow = state.workflows.find(w => w.id === state.activeWorkflowId)

  if (!workflow) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-(--ui-text-tertiary)">Select a workflow to configure scheduling</p>
      </div>
    )
  }

  const schedule = workflow.schedule

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3">
        <div className="flex items-center gap-2">
          <Codicon className="text-cyan-400" name="calendar" size="1rem" />
          <h2 className="text-base font-semibold">Workflow Schedule</h2>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-xl space-y-6">
          <div className="rounded-xl border border-(--ui-stroke-tertiary) p-5">
            <h3 className="mb-4 text-sm font-medium">Schedule Type</h3>
            <div className="grid grid-cols-4 gap-2">
              {(['manual', 'once', 'hourly', 'daily', 'weekly', 'monthly', 'cron'] as ScheduleType[]).map(type => (
                <button
                  className={cn(
                    'rounded-lg border px-3 py-2 text-center text-xs transition-all',
                    (schedule?.type === type || (!schedule && type === 'manual'))
                      ? 'border-primary/50 bg-primary/5 text-primary'
                      : 'border-(--ui-stroke-tertiary) text-(--ui-text-tertiary) hover:text-foreground'
                  )}
                  key={type}
                  onClick={() => setWorkflowSchedule(type === 'manual' ? null : { type, cronExpression: type === 'cron' ? '0 * * * *' : undefined })}
                  type="button"
                >
                  <div className="mb-1 text-sm">
                    <Codicon className="mx-auto" name={
                      type === 'manual' ? 'play' :
                      type === 'once' ? 'circle' :
                      type === 'hourly' ? 'clock' :
                      type === 'daily' ? 'calendar' :
                      type === 'weekly' ? 'calendar' :
                      type === 'monthly' ? 'calendar' :
                      'settings'
                    } size="1rem" />
                  </div>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {schedule && schedule.type !== 'manual' && (
            <>
              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-5">
                <h3 className="mb-3 text-sm font-medium">Schedule Configuration</h3>

                {schedule.type === 'cron' && (
                  <div className="space-y-3">
                    <div>
                      <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Cron Expression</label>
                      <input
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={e => setWorkflowSchedule({ ...schedule, cronExpression: e.target.value })}
                        placeholder="*/5 * * * *"
                        type="text"
                        value={schedule.cronExpression ?? ''}
                      />
                      <p className="mt-1 text-[10px] text-(--ui-text-tertiary)">Format: minute hour day month weekday</p>
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Timezone</label>
                      <input
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={e => setWorkflowSchedule({ ...schedule, timezone: e.target.value })}
                        placeholder="UTC"
                        type="text"
                        value={schedule.timezone ?? 'UTC'}
                      />
                    </div>
                  </div>
                )}

                {schedule.type === 'once' && (
                  <div>
                    <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Start Date & Time</label>
                    <input
                      className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      onChange={e => setWorkflowSchedule({ ...schedule, startDate: e.target.value })}
                      type="datetime-local"
                      value={schedule.startDate?.slice(0, 16) ?? ''}
                    />
                  </div>
                )}

                {['hourly', 'daily', 'weekly', 'monthly'].includes(schedule.type) && (
                  <>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">
                        {schedule.type === 'monthly' ? 'Day of Month' : schedule.type === 'weekly' ? 'Day of Week' : 'Interval'}
                      </label>
                      {schedule.type === 'hourly' && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-(--ui-text-tertiary)">Every</span>
                          <input
                            className="w-20 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                            min={1}
                            onChange={e => setWorkflowSchedule({ ...schedule, interval: parseInt(e.target.value) || 1 })}
                            type="number"
                            value={schedule.interval ?? 1}
                          />
                          <span className="text-xs text-(--ui-text-tertiary)">hours</span>
                        </div>
                      )}
                      {schedule.type === 'daily' && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-(--ui-text-tertiary)">Every</span>
                          <input
                            className="w-20 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                            min={1}
                            onChange={e => setWorkflowSchedule({ ...schedule, interval: parseInt(e.target.value) || 1 })}
                            type="number"
                            value={schedule.interval ?? 1}
                          />
                          <span className="text-xs text-(--ui-text-tertiary)">days</span>
                        </div>
                      )}
                      {schedule.type === 'weekly' && (
                        <div className="flex items-center gap-1">
                          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, i) => (
                            <button
                              className={cn(
                                'rounded-md px-2 py-1 text-xs font-medium transition-colors',
                                (schedule.dayOfWeek ?? []).includes(i)
                                  ? 'bg-primary/10 text-primary'
                                  : 'bg-(--ui-control-hover-background) text-(--ui-text-tertiary)'
                              )}
                              key={day}
                              onClick={() => {
                                const current = schedule.dayOfWeek ?? []
                                const next = current.includes(i) ? current.filter(d => d !== i) : [...current, i]
                                setWorkflowSchedule({ ...schedule, dayOfWeek: next })
                              }}
                              type="button"
                            >
                              {day}
                            </button>
                          ))}
                        </div>
                      )}
                      {schedule.type === 'monthly' && (
                        <input
                          className="w-20 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          max={31}
                          min={1}
                          onChange={e => setWorkflowSchedule({ ...schedule, dayOfMonth: [parseInt(e.target.value) || 1] })}
                          type="number"
                          value={schedule.dayOfMonth?.[0] ?? 1}
                        />
                      )}
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Time</label>
                      <input
                        className="w-32 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={e => setWorkflowSchedule({ ...schedule, startDate: `2024-01-01T${e.target.value}:00` })}
                        type="time"
                        value={schedule.startDate?.slice(11, 16) ?? '09:00'}
                      />
                    </div>
                  </>
                )}

                {schedule.type !== 'cron' && schedule.type !== 'once' && (
                  <>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Start Date</label>
                      <input
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={e => setWorkflowSchedule({ ...schedule, startDate: e.target.value })}
                        type="date"
                        value={schedule.startDate?.slice(0, 10) ?? ''}
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">End Date (optional)</label>
                      <input
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={e => setWorkflowSchedule({ ...schedule, endDate: e.target.value })}
                        type="date"
                        value={schedule.endDate?.slice(0, 10) ?? ''}
                      />
                    </div>
                  </>
                )}
              </div>

              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-5">
                <h3 className="mb-3 text-sm font-medium">Retry Policy</h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Max Retries</label>
                      <input
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        max={10}
                        min={0}
                        onChange={e => {}}
                        type="number"
                        value={workflow.retryPolicy.maxRetries}
                      />
                    </div>
                    <div className="flex-1">
                      <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Retry Delay</label>
                      <input
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        min={0}
                        onChange={e => {}}
                        type="number"
                        value={workflow.retryPolicy.retryDelay}
                      />
                    </div>
                    <div className="flex-1">
                      <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Max Duration (s)</label>
                      <input
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        min={0}
                        onChange={e => {}}
                        type="number"
                        value={workflow.retryPolicy.maxDuration}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {(!schedule || schedule.type === 'manual') && (
            <div className="rounded-xl border border-dashed border-(--ui-stroke-tertiary) p-8 text-center">
              <Codicon className="mx-auto mb-2 text-(--ui-text-tertiary)" name="play" size="2rem" />
              <p className="text-sm text-(--ui-text-tertiary)">Manual only</p>
              <p className="text-xs text-(--ui-text-tertiary) mt-1">This workflow will only run when triggered manually</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
