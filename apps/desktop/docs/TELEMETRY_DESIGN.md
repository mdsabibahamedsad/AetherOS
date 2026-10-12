# Telemetry Design

## Philosophy

Telemetry in AetherOS Desktop follows strict privacy-by-design principles:

1. **Opt-in only** — No telemetry is collected without explicit user consent
2. **Transparency** — All collected data is visible to the user
3. **Minimal** — Only what's needed for improvement
4. **Anonymous** — No personally identifiable information
5. **Secure** — TLS 1.3 transport, no third-party sharing

## Consent Model

```
First Launch → Consent Prompt → Opt In / Opt Out
                                    ↓
                            Configurable Settings
                            ├── Crash Reporting
                            ├── Performance Metrics
                            └── Feature Usage
```

### Consent States

| State | Behavior |
|-------|----------|
| Not asked | Show consent dialog on first launch |
| Consented | Collect enabled types |
| Declined | No collection |
| Updated | Respect current settings |

## Data Collected

### Required (always collected, no consent needed)
- Application version
- Operating system platform
- CPU architecture

### Optional (requires consent)

**Crash Reports (opt-in)**
- Stack trace at crash point
- App version and build
- System info (OS, architecture, memory)
- **Never:** File contents, credentials, personal data

**Performance Metrics (opt-in)**
- Startup time
- Memory usage
- CPU usage
- FPS
- Extension load times
- **Never:** Individual keystrokes, screen captures, file contents

**Feature Usage (opt-in)**
- Feature activation counts
- Feature duration
- Extension failures
- **Never:** Personal files, workspace content, model inputs/outputs

## Architecture

```
┌────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  TelemetryManager  │────►│  Event Buffer     │────►│  HTTPS Endpoint │
│  - Consent store   │     │  (max 50 events)  │     │  v1/events      │
│  - Session ID      │     │  Flush every 5min  │     │                 │
│  - Event tracking  │     └──────────────────┘     └─────────────────┘
└────────────────────┘
```

### Flush Behavior
- Buffer flushes when it reaches 50 events
- Automatic flush every 5 minutes
- Manual flush on app quit (`keepalive: true`)
- Failed sends are re-queued silently

## Data Flow

```
User Action → TelemetryManager.track() → Buffer → Flush
                                                    ↓
                                            POST /v1/events
                                            Headers: Content-Type: application/json
                                            Body: { clientId, sessionId, events }
```

## Privacy Controls

### User Settings
```typescript
interface TelemetryConsent {
  enabled: boolean           // Master toggle
  crashReporting: boolean    // Crash report collection
  performanceMetrics: boolean // Performance data
  featureUsage: boolean      // Feature usage stats
  consented: boolean         // Has user responded?
}
```

### Data Retention
- Telemetry events: 90 days
- Crash reports: 180 days
- Aggregated metrics: Indefinite (anonymized)

### User Rights
- View collected data in Settings → Privacy
- Export telemetry data
- Delete all telemetry data
- Opt out at any time
- Disable specific data types

## Security

- All telemetry sent over HTTPS (TLS 1.3)
- No PII in event payloads
- Client ID is anonymized (random UUID, no device fingerprinting)
- Session ID is ephemeral (regenerated on restart)
- Events are never linked to user accounts

## Implementation

```typescript
// Track a feature usage event
telemetry.trackEvent('feature_used', { feature: 'resource-manager', duration: 120 })

// Track a performance metric
telemetry.trackMetric('startup_time', 2340)

// Track a crash
telemetry.trackCrash(error)

// Get current consent
const consent = telemetry.getConsent()

// Update consent
telemetry.updateConsent({ enabled: true, crashReporting: true })
```
