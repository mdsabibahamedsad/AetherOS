import {
  addJarvisJob,
  addJarvisNotification,
  type JarvisAutomationJob,
  updateJarvisJob
} from '@/store/jarvis-mode'

import type { BackgroundJob, JobLog } from '../types'

// ─── Background Job Manager ───────────────────────────────────────────────────

const jobs = new Map<string, BackgroundJob>()
let jobCounter = 0
const MAX_CONCURRENT_JOBS = 5

export function createBackgroundJob(config: {
  name: string
  type: BackgroundJob['type']
  maxRetries?: number
}): BackgroundJob {
  const job: BackgroundJob = {
    id: `bg-${++jobCounter}`,
    name: config.name,
    type: config.type,
    status: 'queued',
    progress: 0,
    startTime: Date.now(),
    logs: [],
    retryCount: 0,
    maxRetries: config.maxRetries ?? 3
  }

  jobs.set(job.id, job)

  const storeJob: JarvisAutomationJob = {
    id: job.id,
    name: job.name,
    status: 'queued',
    type: job.type === 'ai-task' ? 'triggered' : job.type === 'scheduled' ? 'scheduled' : 'background'
  }

  addJarvisJob(storeJob)

  addJarvisNotification({
    title: 'Job Queued',
    message: `${job.name} has been queued`,
    type: 'info'
  })

  return job
}

export function startJob(jobId: string) {
  const job = jobs.get(jobId)

  if (!job) {return}

  job.status = 'running'
  job.startTime = Date.now()
  addJobLog(jobId, 'info', 'Job started')

  updateJarvisJob(jobId, { status: 'running', startedAt: job.startTime })
}

export function updateJobProgress(jobId: string, progress: number, log?: string) {
  const job = jobs.get(jobId)

  if (!job) {return}

  job.progress = Math.min(100, Math.max(0, progress))

  if (log) {addJobLog(jobId, 'info', log)}

  // Calculate ETA
  const elapsed = Date.now() - job.startTime
  const rate = job.progress / elapsed
  const remaining = rate > 0 ? (100 - job.progress) / rate : undefined

  updateJarvisJob(jobId, {
    progress: job.progress,
    eta: remaining ? Date.now() + remaining : undefined
  })
}

export function completeJob(jobId: string, result?: string) {
  const job = jobs.get(jobId)

  if (!job) {return}

  job.status = 'completed'
  job.progress = 100
  job.endTime = Date.now()
  job.result = result

  addJobLog(jobId, 'info', 'Job completed successfully')

  updateJarvisJob(jobId, {
    status: 'completed',
    progress: 100,
    completedAt: job.endTime
  })

  addJarvisNotification({
    title: 'Job Complete',
    message: `${job.name} finished successfully`,
    type: 'success'
  })
}

export function failJob(jobId: string, error: string, retry = true) {
  const job = jobs.get(jobId)

  if (!job) {return}

  addJobLog(jobId, 'error', `Failed: ${error}`)

  if (retry && job.retryCount < job.maxRetries) {
    job.retryCount++
    job.status = 'queued'
    job.progress = 0
    addJobLog(jobId, 'warn', `Retrying (${job.retryCount}/${job.maxRetries})...`)

    updateJarvisJob(jobId, { status: 'queued', progress: 0 })

    // Auto-retry after delay
    setTimeout(() => startJob(jobId), 2000 * job.retryCount)
  } else {
    job.status = 'failed'
    job.error = error
    job.endTime = Date.now()

    updateJarvisJob(jobId, { status: 'failed', error })

    addJarvisNotification({
      title: 'Job Failed',
      message: `${job.name}: ${error}`,
      type: 'error'
    })
  }
}

export function pauseJob(jobId: string) {
  const job = jobs.get(jobId)

  if (!job || job.status !== 'running') {return}

  job.status = 'paused'
  job.cancelToken?.abort()
  addJobLog(jobId, 'info', 'Job paused')

  updateJarvisJob(jobId, { status: 'paused' })
}

export function resumeJob(jobId: string) {
  const job = jobs.get(jobId)

  if (!job || job.status !== 'paused') {return}

  job.cancelToken = new AbortController()
  startJob(jobId)
  addJobLog(jobId, 'info', 'Job resumed')
}

export function cancelJob(jobId: string) {
  const job = jobs.get(jobId)

  if (!job) {return}

  job.cancelToken?.abort()
  job.status = 'cancelled'
  job.endTime = Date.now()
  addJobLog(jobId, 'info', 'Job cancelled')

  updateJarvisJob(jobId, { status: 'failed' })
}

export function retryJob(jobId: string) {
  const job = jobs.get(jobId)

  if (!job || job.status !== 'failed') {return}

  job.retryCount = 0
  job.error = undefined
  job.progress = 0
  job.cancelToken = new AbortController()

  startJob(jobId)
  addJobLog(jobId, 'info', 'Job retried')
}

export function getJob(jobId: string): BackgroundJob | undefined {
  return jobs.get(jobId)
}

export function getAllJobs(): BackgroundJob[] {
  return Array.from(jobs.values())
}

export function getRunningJobs(): BackgroundJob[] {
  return Array.from(jobs.values()).filter(j => j.status === 'running')
}

export function getJobCount(): { total: number; running: number; queued: number; failed: number } {
  const all = Array.from(jobs.values())

  return {
    total: all.length,
    running: all.filter(j => j.status === 'running').length,
    queued: all.filter(j => j.status === 'queued').length,
    failed: all.filter(j => j.status === 'failed').length
  }
}

function addJobLog(jobId: string, level: JobLog['level'], message: string) {
  const job = jobs.get(jobId)

  if (!job) {return}

  job.logs.push({
    timestamp: Date.now(),
    level,
    message
  })

  // Keep only last 200 logs
  if (job.logs.length > 200) {
    job.logs = job.logs.slice(-200)
  }
}
