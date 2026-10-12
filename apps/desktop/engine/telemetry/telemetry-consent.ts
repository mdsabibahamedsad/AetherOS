import { telemetry } from './telemetry'

export interface ConsentDialogOptions {
  showCrashReporting: boolean
  showPerformanceMetrics: boolean
  showFeatureUsage: boolean
  requireConsent: boolean
}

const DEFAULT_OPTIONS: ConsentDialogOptions = {
  showCrashReporting: true,
  showPerformanceMetrics: true,
  showFeatureUsage: true,
  requireConsent: false,
}

export function requestTelemetryConsent(options: Partial<ConsentDialogOptions> = {}): Promise<boolean> {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  if (telemetry.getConsent().consented) {
    return Promise.resolve(true)
  }

  return new Promise((resolve) => {
    const consent = telemetry.getConsent()
    const choices = {
      enabled: consent.enabled,
      crashReporting: consent.crashReporting,
      performanceMetrics: consent.performanceMetrics,
      featureUsage: consent.featureUsage,
    }

    telemetry.updateConsent({ ...choices, consented: true })

    resolve(choices.enabled)
  })
}

export function showTelemetrySettings(): TelemetrySettings {
  const consent = telemetry.getConsent()
  return {
    telemetryEnabled: consent.enabled,
    crashReporting: consent.crashReporting,
    performanceMetrics: consent.performanceMetrics,
    featureUsage: consent.featureUsage,
    updateConsent: (updates: Partial<typeof consent>) => {
      telemetry.updateConsent(updates)
    },
    resetConsent: () => {
      telemetry.updateConsent({
        enabled: false,
        crashReporting: false,
        performanceMetrics: false,
        featureUsage: false,
        consented: false,
      })
    },
  }
}

export interface TelemetrySettings {
  telemetryEnabled: boolean
  crashReporting: boolean
  performanceMetrics: boolean
  featureUsage: boolean
  updateConsent: (updates: Partial<ReturnType<typeof telemetry.getConsent>>) => void
  resetConsent: () => void
}

export function getTelemetrySummary(): {
  enabled: boolean
  crashReports: boolean
  performanceMetrics: boolean
  featureUsage: boolean
  eventsRecorded: number
  bufferSize: number
} {
  const consent = telemetry.getConsent()
  return {
    enabled: consent.enabled,
    crashReports: consent.crashReporting,
    performanceMetrics: consent.performanceMetrics,
    featureUsage: consent.featureUsage,
    eventsRecorded: telemetry.getBufferSize(),
    bufferSize: telemetry.getBufferSize(),
  }
}
