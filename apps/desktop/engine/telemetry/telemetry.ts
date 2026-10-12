export type TelemetryEventType = 'app_start' | 'app_quit' | 'crash' | 'error' | 'feature_used' | 'update_installed' | 'migration_completed' | 'extension_loaded' | 'extension_failed' | 'performance_metric'

export interface TelemetryEvent {
  id: string
  type: TelemetryEventType
  timestamp: number
  sessionId: string
  properties?: Record<string, string | number | boolean>
  metrics?: Record<string, number>
}

export interface TelemetryConsent {
  enabled: boolean
  crashReporting: boolean
  performanceMetrics: boolean
  featureUsage: boolean
  consented: boolean
  consentedAt?: string
  updatedAt?: string
}

const TELEMETRY_CONSENT_KEY = 'aetheros.telemetry.consent'

class TelemetryManager {
  private consent: TelemetryConsent = {
    enabled: false,
    crashReporting: false,
    performanceMetrics: false,
    featureUsage: false,
    consented: false,
  }

  private buffer: TelemetryEvent[] = []
  private maxBufferSize = 50
  private flushInterval = 300000
  private intervalId: ReturnType<typeof setInterval> | null = null
  private currentSessionId: string = ''

  constructor() {
    this.loadConsent()
  }

  getConsent(): TelemetryConsent {
    return { ...this.consent }
  }

  updateConsent(updates: Partial<TelemetryConsent>) {
    this.consent = { ...this.consent, ...updates, updatedAt: new Date().toISOString() }
    if (updates.consented) {
      this.consent.consentedAt = this.consent.consentedAt || new Date().toISOString()
    }
    this.saveConsent()
    if (this.consent.enabled) {
      this.startFlushInterval()
    } else {
      this.stopFlushInterval()
    }
  }

  isEnabled(): boolean {
    return this.consent.enabled
  }

  isCrashReportingEnabled(): boolean {
    return this.consent.enabled && this.consent.crashReporting
  }

  isPerformanceMetricsEnabled(): boolean {
    return this.consent.enabled && this.consent.performanceMetrics
  }

  setSessionId(sessionId: string) {
    this.currentSessionId = sessionId
  }

  track(event: TelemetryEvent) {
    if (!this.consent.enabled) return
    this.buffer.push(event)
    if (this.buffer.length >= this.maxBufferSize) {
      this.flush()
    }
  }

  trackEvent(type: TelemetryEventType, properties?: Record<string, string | number | boolean>) {
    this.track({
      id: generateTelemetryId(),
      type,
      timestamp: Date.now(),
      sessionId: this.currentSessionId,
      properties,
    })
  }

  trackMetric(name: string, value: number, tags?: Record<string, string>) {
    if (!this.consent.performanceMetrics) return
    this.track({
      id: generateTelemetryId(),
      type: 'performance_metric',
      timestamp: Date.now(),
      sessionId: this.currentSessionId,
      properties: { metric: name, ...tags },
      metrics: { [name]: value },
    })
  }

  trackCrash(error: Error) {
    if (!this.consent.crashReporting) return
    this.track({
      id: generateTelemetryId(),
      type: 'crash',
      timestamp: Date.now(),
      sessionId: this.currentSessionId,
      properties: {
        message: error.message?.substring(0, 200) ?? '',
        name: error.name ?? 'Error',
      },
    })
  }

  trackAppStart() {
    this.trackEvent('app_start', { version: '1.0.0', platform: navigator.platform })
  }

  trackAppQuit() {
    this.trackEvent('app_quit', { uptime: Math.round(performance.now() / 1000) })
  }

  getBuffer(): TelemetryEvent[] {
    return [...this.buffer]
  }

  getBufferSize(): number {
    return this.buffer.length
  }

  flush(): Promise<void> {
    if (this.buffer.length === 0) return Promise.resolve()

    const events = [...this.buffer]
    this.buffer = []

    return this.sendEvents(events).catch(() => {
      this.buffer.unshift(...events)
    })
  }

  private async sendEvents(events: TelemetryEvent[]): Promise<void> {
    const payload = {
      clientId: getAnonymousClientId(),
      sessionId: this.currentSessionId,
      events,
      sentAt: new Date().toISOString(),
    }

    if (process.env.NODE_ENV === 'development') {
      console.debug('[Telemetry] Would send:', payload)
      return
    }

    try {
      const response = await fetch('https://telemetry.aetheros.dev/v1/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true,
      })
      if (!response.ok) {
        console.warn('[Telemetry] Send failed:', response.status)
      }
    } catch {
      // Silently fail — telemetry should never disrupt the app
    }
  }

  private startFlushInterval() {
    this.stopFlushInterval()
    this.intervalId = setInterval(() => this.flush(), this.flushInterval)
  }

  private stopFlushInterval() {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
    }
  }

  private loadConsent() {
    try {
      const raw = window.localStorage.getItem(TELEMETRY_CONSENT_KEY)
      if (raw) {
        this.consent = JSON.parse(raw)
      }
    } catch {
      this.consent = { enabled: false, crashReporting: false, performanceMetrics: false, featureUsage: false, consented: false }
    }
  }

  private saveConsent() {
    try {
      window.localStorage.setItem(TELEMETRY_CONSENT_KEY, JSON.stringify(this.consent))
    } catch {
      console.error('Failed to save telemetry consent')
    }
  }
}

let telemetryIdCounter = 0
function generateTelemetryId(): string {
  return `tel_${Date.now()}_${++telemetryIdCounter}`
}

function getAnonymousClientId(): string {
  let id = window.localStorage.getItem('aetheros.clientId')
  if (!id) {
    id = `client_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`
    window.localStorage.setItem('aetheros.clientId', id)
  }
  return id
}

export const telemetry = new TelemetryManager()
