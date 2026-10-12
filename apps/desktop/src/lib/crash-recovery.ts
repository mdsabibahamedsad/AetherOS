const MAX_RECOVERY_ATTEMPTS = 3
const RECOVERY_WINDOW_MS = 60000
const STORAGE_KEY = 'aetheros.desktop.crashRecovery'
const SAFE_MODE_KEY = 'aetheros.desktop.safeMode'
const LAST_CRASH_TIMESTAMP_KEY = 'aetheros.desktop.lastCrashTimestamp'
const CRASH_LOG_KEY = 'aetheros.desktop.crashLog'

interface CrashRecord {
  attempts: number
  lastCrash: number
  lastSessionId?: string
  crashHistory?: CrashEvent[]
}

interface CrashEvent {
  timestamp: number
  type: 'renderer' | 'main' | 'unknown'
  message?: string
  recovered: boolean
}

function loadRecord(): CrashRecord {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)

    if (raw) {return JSON.parse(raw)}
  } catch {
    // Non-fatal
  }

  return { attempts: 0, lastCrash: 0, crashHistory: [] }
}

function saveRecord(record: CrashRecord) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(record))
  } catch {
    // Non-fatal
  }
}

function addCrashEvent(event: CrashEvent) {
  const record = loadRecord()

  if (!record.crashHistory) {record.crashHistory = []}
  record.crashHistory.push(event)

  if (record.crashHistory.length > 50) {record.crashHistory = record.crashHistory.slice(-50)}
  saveRecord(record)

  try {
    window.localStorage.setItem(LAST_CRASH_TIMESTAMP_KEY, String(event.timestamp))
  } catch { /* Non-fatal */ }
}

export function recordCrash(sessionId?: string, crashType: CrashEvent['type'] = 'renderer', message?: string) {
  const record = loadRecord()
  const now = Date.now()

  if (now - record.lastCrash > RECOVERY_WINDOW_MS) {
    record.attempts = 0
  }

  record.attempts += 1
  record.lastCrash = now

  if (sessionId) {record.lastSessionId = sessionId}

  saveRecord(record)
  addCrashEvent({ timestamp: now, type: crashType, message, recovered: false })
}

export function shouldAttemptRecovery(): boolean {
  const record = loadRecord()
  const now = Date.now()

  if (now - record.lastCrash > RECOVERY_WINDOW_MS) {return true}

  return record.attempts < MAX_RECOVERY_ATTEMPTS
}

export function getCrashInfo(): { canRecover: boolean; lastSessionId?: string; attemptCount: number; crashHistory: CrashEvent[] } {
  const record = loadRecord()

  return {
    canRecover: shouldAttemptRecovery(),
    lastSessionId: record.lastSessionId,
    attemptCount: record.attempts,
    crashHistory: record.crashHistory || []
  }
}

export function clearCrashRecord() {
  saveRecord({ attempts: 0, lastCrash: 0, crashHistory: [] })
}

export function reloadApp() {
  window.location.reload()
}

export function hardReset() {
  clearCrashRecord()
  clearSafeMode()

  if (window.aetherosDesktop?.restartBackend) {
    window.aetherosDesktop.restartBackend().then(() => window.location.reload())
  } else {
    window.location.reload()
  }
}

export function isSafeMode(): boolean {
  try {
    return window.localStorage.getItem(SAFE_MODE_KEY) === 'true'
  } catch {
    return false
  }
}

export function setSafeMode(enabled: boolean) {
  try {
    if (enabled) {
      window.localStorage.setItem(SAFE_MODE_KEY, 'true')
    } else {
      window.localStorage.removeItem(SAFE_MODE_KEY)
    }
  } catch {
    // Non-fatal
  }
}

export function clearSafeMode() {
  try {
    window.localStorage.removeItem(SAFE_MODE_KEY)
  } catch {
    // Non-fatal
  }
}

export function launchSafeMode() {
  setSafeMode(true)
  clearCrashRecord()
  window.location.reload()
}

export function getCrashDiagnostics(): { attempts: number; lastCrash: number; safeMode: boolean; crashHistory: CrashEvent[] } {
  const record = loadRecord()

  return {
    attempts: record.attempts,
    lastCrash: record.lastCrash,
    safeMode: isSafeMode(),
    crashHistory: record.crashHistory || []
  }
}

export function getLastCrashTimestamp(): number | null {
  try {
    const val = window.localStorage.getItem(LAST_CRASH_TIMESTAMP_KEY)

    return val ? Number(val) : null
  } catch {
    return null
  }
}

export function logRecoverySuccess() {
  const event: CrashEvent = {
    timestamp: Date.now(),
    type: 'main',
    message: 'Recovery succeeded',
    recovered: true
  }

  addCrashEvent(event)
  const record = loadRecord()
  record.attempts = 0
  record.lastCrash = 0
  saveRecord(record)
}
