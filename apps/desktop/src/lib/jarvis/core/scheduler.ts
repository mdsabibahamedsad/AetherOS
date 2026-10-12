export interface ScheduledJob {
  id: string
  name: string
  interval: number
  action: string
  lastRun?: number
  nextRun: number
  enabled: boolean
  running: boolean
  runCount: number
}

const jobs: Map<string, ScheduledJob> = new Map()
let tickerId: ReturnType<typeof setInterval> | null = null
let counter = 0
const listeners = new Map<string, Set<() => void>>()

function nextId(): string {
  return `sched_${++counter}_${Date.now().toString(36)}`
}

export function schedule(name: string, intervalMs: number, action: string): ScheduledJob {
  const job: ScheduledJob = {
    id: nextId(),
    name,
    interval: intervalMs,
    action,
    nextRun: Date.now() + intervalMs,
    enabled: true,
    running: false,
    runCount: 0
  }

  jobs.set(job.id, job)

  return job
}

export function unschedule(jobId: string): void {
  jobs.delete(jobId)
}

export function onTick(jobId: string, handler: () => void): () => void {
  if (!listeners.has(jobId)) {listeners.set(jobId, new Set())}
  listeners.get(jobId)!.add(handler)

  return () => listeners.get(jobId)?.delete(handler)
}

export function getJobs(): ScheduledJob[] {
  return Array.from(jobs.values())
}

export function getJob(jobId: string): ScheduledJob | undefined {
  return jobs.get(jobId)
}

export function enableJob(jobId: string): void {
  const job = jobs.get(jobId)

  if (job) { job.enabled = true; job.nextRun = Date.now() + job.interval }
}

export function disableJob(jobId: string): void {
  const job = jobs.get(jobId)

  if (job) {job.enabled = false}
}

export function runJobNow(jobId: string): void {
  const job = jobs.get(jobId)

  if (job) {job.nextRun = 0}
}

function tick(): void {
  const now = Date.now()
  jobs.forEach(job => {
    if (!job.enabled || job.running || job.nextRun > now) {return}
    job.running = true
    job.lastRun = now
    job.runCount++
    job.nextRun = now + job.interval

    listeners.get(job.id)?.forEach(h => {
      try { h() } catch { /* handler error */ }
    })

    job.running = false
  })
}

export function startScheduler(intervalMs = 1000): void {
  if (tickerId) {return}
  tickerId = setInterval(tick, intervalMs)
}

export function stopScheduler(): void {
  if (tickerId) { clearInterval(tickerId); tickerId = null }
}

export function seedDefaultJobs(): void {
  schedule('Memory Cleanup', 3600_000, 'memory:cleanup')
  schedule('Health Check', 300_000, 'system:health-check')
  schedule('Context Refresh', 60_000, 'context:refresh')
  schedule('Observer Report', 600_000, 'observer:report')
}
