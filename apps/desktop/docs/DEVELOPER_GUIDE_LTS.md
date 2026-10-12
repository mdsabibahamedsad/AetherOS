# LTS Developer Guide

## Working with LTS

### Channel Selection
```typescript
import { ltsConfig } from './lts/lts-config'

// Read current channel
const channel = ltsConfig.channel

// Configure
ltsConfig.autoUpdate = true
ltsConfig.allowedChannels = ['stable', 'lts']
```

### Release Management
```typescript
import { releaseManager } from './engine/release/release-manager'

// Plan a release
const plan = releaseManager.generateReleasePlan('minor', '1.0.0', [
  'Added: New feature',
  'Fixed: Bug fix',
])

// Generate changelog
const changelog = releaseManager.generateChangelog(plan.nextVersion, plan.changes, plan.type)

// Validate
const validation = releaseManager.validateRelease(plan)
```

## Working with the SDK

### Creating a Plugin (SDK v1)
```typescript
import { createPluginContext } from './sdk/plugin-api-v1'

const ctx = createPluginContext({
  id: 'my-plugin',
  name: 'My Plugin',
  version: '1.0.0',
})

// Register lifecycle hooks
ctx.hooks.onSessionStart(async (sessionId) => {
  ctx.log.info('Session started:', sessionId)
})

// Use APIs
const info = await ctx.api.system.getInfo()
ctx.api.notifications.show('Info', `Running on ${info.platform}`)
```

### Checking Compatibility
```typescript
import { checkPluginCompatibility } from './sdk/deprecation-manager'

const result = checkPluginCompatibility('1.0.0', '1.0.0')
if (!result.compatible) {
  console.error('Plugin incompatible:', result.errors)
}
```

### Generating Compat Report
```typescript
import { generateCompatReport } from './sdk/sdk-compatibility-layer'

const report = generateCompatReport('1.0.0', '1.0.0')
console.log(`Compat level: ${report.level}`)
```

## Working with Migrations

### Registering a Migration
```typescript
import { migrationEngine } from './engine/migration/migration-engine'

migrationEngine.register({
  id: 'my-migration',
  name: 'My Migration',
  type: 'config',
  version: '1.1.0',
  description: 'Description',
  dependsOn: ['config-v1-to-v2'],
  apply: async () => ({ success: true, applied: 1, rolledBack: 0, errors: [], warnings: [], duration: 50 }),
  rollback: async () => ({ success: true, applied: 0, rolledBack: 1, errors: [], warnings: [], duration: 50 }),
  validate: async () => ({ valid: true, errors: [], warnings: [] }),
  backup: async () => {},
})
```

### Running Migrations
```typescript
// Apply all pending
await migrationEngine.applyAllPending()

// Apply specific
await migrationEngine.applyMigration('my-migration')

// Rollback
await migrationEngine.rollbackMigration('my-migration')

// Check status
const state = migrationEngine.getState()
```

## Working with Telemetry

### Tracking Events
```typescript
import { telemetry } from './engine/telemetry/telemetry'

// Track feature usage
telemetry.trackEvent('feature_used', { feature: 'my-feature' })

// Track performance
telemetry.trackMetric('response_time', 150)

// Track error
telemetry.trackCrash(new Error('Something failed'))
```

### Consent Management
```typescript
import { requestTelemetryConsent } from './engine/telemetry/telemetry-consent'

// Request consent
const consented = await requestTelemetryConsent()

// Update consent
telemetry.updateConsent({ crashReporting: true })
```

## Working with Performance Monitoring

```typescript
import { performanceMonitor } from './engine/performance/performance-monitor'

// Start collection
performanceMonitor.startCollection(30000) // every 30 seconds

// Get latest snapshot
const snapshot = performanceMonitor.getLatest()

// Get history
const history = performanceMonitor.getRecentSnapshots(50)

// Stop collection
performanceMonitor.stopCollection()
```

## Working with Security Maintenance

```typescript
import { securityScheduler } from './engine/security-maintenance/security-maintenance'

// Run all security tasks
const report = await securityScheduler.runAllTasks()
console.log(`Security score: ${report.score}`)

// Run specific task
await securityScheduler.runTask('dependency-update')

// Check if task is due
if (securityScheduler.isTaskDue('security-scan')) {
  await securityScheduler.runTask('security-scan')
}
```

## npm Scripts Reference

| Script | Engine | Description |
|--------|--------|-------------|
| `lts:status` | LTS | Show current LTS configuration |
| `sdk:test` | SDK | Run SDK compatibility tests |
| `sdk:compat` | SDK | Generate compatibility report |
| `engine:migrate` | Migration | Apply all pending migrations |
| `engine:telemetry:status` | Telemetry | Show telemetry status |
| `engine:perf:start` | Performance | Start performance monitoring |
| `engine:deps:audit` | Dependency | Run dependency audit |
| `engine:security:scan` | Security | Run all security tasks |
| `engine:release:plan` | Release | Generate release plan |
| `engine:test:all` | Testing | Run all continuous test suites |
| `engine:backward:check` | Compatibility | Check backward compatibility |
| `engine:project:migrate` | Migration | Run project migration |
