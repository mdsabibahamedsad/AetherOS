# Migration System

## Architecture

The migration system provides automatic, safe data migration for all persistent state. It consists of three layers:

```
┌─────────────────────────────────────────────┐
│            Project Migration                 │
│  Settings │ Workspace │ Knowledge │ Models   │
│  Extensions │ Cloud Sync                     │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│           Database Migration Engine           │
│  Apply │ Rollback │ Backup │ Repair │ Validate│
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│           Config Migration                   │
│  Format versioning │ Schema validation        │
└─────────────────────────────────────────────┘
```

## Migration Engine (`engine/migration/`)

### Key Features

| Feature | Description |
|---------|-------------|
| **Automatic Migration** | Applies pending migrations on app start |
| **Rollback** | Reverts failed migrations to previous state |
| **Backup** | Creates backup before each migration |
| **Repair** | Validates and repairs corrupted state |
| **Validation** | Pre-migration validation of data integrity |

### Migration Lifecycle

```
Register → Validate → Backup → Apply → Verify → Complete
                                      ↓ (failure)
                                  Rollback → Restore Backup
```

### Migration State

Migrations are tracked via `localStorage` key `aetheros.migration.state`:

```typescript
interface MigrationState {
  applied: string[]        // Successfully applied migrations
  failed: string[]         // Failed migrations
  inProgress: string | null // Currently running migration
  lastRun?: string         // ISO timestamp
  lastSuccess?: string     // ISO timestamp
  lastError?: string       // Error message
}
```

## Standard Migrations

| ID | Type | Description | Dependencies |
|----|------|-------------|--------------|
| `config-v1-to-v2` | Config | Flat → namespaced config | None |
| `workspace-index-v1` | Workspace | Workspace index init | None |
| `knowledge-base-init` | Knowledge | Knowledge base init | None |
| `extension-registry-init` | Extensions | Extension registry init | config-v1-to-v2 |
| `telemetry-prefs-init` | Config | Telemetry consent state | config-v1-to-v2 |

## Project Migration (`engine/project-migration/`)

### Migration Scopes

| Scope | Required | Description |
|-------|----------|-------------|
| Settings | ✅ | User preferences and configuration |
| Workspace | ✅ | Workspace data and index |
| Knowledge | ❌ | Knowledge base entries |
| Models | ❌ | Model provider configurations |
| Extensions | ❌ | Installed extensions |
| Cloud Sync | ❌ | Cloud sync state |

## Adding New Migrations

```typescript
migrationEngine.register({
  id: 'my-migration',
  name: 'My Migration',
  type: 'config',
  version: '1.1.0',
  description: 'Description of what this migration does',
  dependsOn: ['config-v1-to-v2'],
  apply: async () => {
    // Migration logic
    return { success: true, applied: 1, rolledBack: 0, errors: [], warnings: [], duration: 50 }
  },
  rollback: async () => {
    // Rollback logic
    return { success: true, applied: 0, rolledBack: 1, errors: [], warnings: [], duration: 50 }
  },
  validate: async () => ({ valid: true, errors: [], warnings: [] }),
  backup: async () => {
    // Backup current state
  },
})
```
