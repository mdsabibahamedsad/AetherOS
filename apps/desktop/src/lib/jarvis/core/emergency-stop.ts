/**
 * Global Jarvis emergency stop.
 *
 * Cancels the active pipeline, voice I/O, pending approvals and queued
 * background work without killing the AetherOS application or the gateway.
 */

import { cancelJarvisPipeline } from './ai-core'
import { cancelApprovalsFor, pendingApprovals } from './approval-engine'

export interface StopReport {
  pipeline: boolean
  voice: boolean
  approvals: number
  at: number
}

export function stopJarvis(opts: {
  cancelVoice: () => void
  cancelBackground: () => number
}): StopReport {
  try { cancelJarvisPipeline() } catch { /* noop */ }
  let voice = false
  try { opts.cancelVoice(); voice = true } catch { /* noop */ }
  let approvals = 0
  try {
    approvals = pendingApprovals().length
  } catch { /* noop */ }
  cancelApprovalsFor('emergency-stop')
  let background = 0
  try { background = opts.cancelBackground() } catch { /* noop */ }
  void background
  try { window.speechSynthesis?.cancel() } catch { /* noop */ }
  return { pipeline: true, voice, approvals, at: Date.now() }
}
