# AetherOS Update Rollback System

## Overview

The rollback system ensures that failed updates never leave the application in a broken state. Every update operation creates a recovery point, and rollback is automatic on health check failure.

## Rollback Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Update Manager                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Pre-Update   │  │ Health       │  │ Rollback             │  │
│  │ Snapshot     │  │ Checks       │  │ Coordinator          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌───────────┐    ┌───────────┐    ┌───────────┐
       │  Windows  │    │  macOS    │    │  Linux    │
       │ Adapter   │    │ Adapter   │    │ Adapter   │
       └───────────┘    └───────────┘    └───────────┘
```

## Pre-Update Snapshot

Before any update, the system records a complete recovery point:

```typescript
interface PreUpdateSnapshot {
  currentVersion: string;           // e.g., "1.1.0"
  stateGeneration: number;          // Durable state generation
  schemaGeneration: number;         // Database schema generation
  updateId: string;                 // Unique update identifier
  artifactHash: string;             // SHA-256 of update artifact
  recordedAt: string;               // ISO 8601 timestamp
  userDataHash?: string;            // Hash of user data (optional)
  configHash?: string;              // Hash of configuration
}
```

### Snapshot Creation
```typescript
function recordPreUpdateSnapshot(params: {
  currentVersion: string;
  stateGeneration?: number;
  schemaGeneration?: number;
  updateId: string;
  artifactHash: string;
}): PreUpdateSnapshot {
  if (!params.currentVersion || !params.updateId || !params.artifactHash) {
    throw new Error('Snapshot requires currentVersion, updateId, artifactHash');
  }
  
  return {
    currentVersion: params.currentVersion,
    stateGeneration: params.stateGeneration ?? null,
    schemaGeneration: params.schemaGeneration ?? null,
    updateId: params.updateId,
    artifactHash: params.artifactHash,
    recordedAt: new Date().toISOString(),
  };
}
```

### Snapshot Storage
- **Location**: Platform-specific backup directory
- **Format**: JSON (portable, inspectable)
- **Retention**: 5 most recent snapshots
- **Encryption**: OS keychain/DPAPI for sensitive fields

## Health Checks

### Check Categories

| Category | Checks | Critical | Timeout |
|----------|--------|----------|---------|
| **Launch** | Process starts, main window shows | Yes | 30s |
| **IPC** | Renderer↔Main communication | Yes | 10s |
| **Backend** | API/WebSocket connectivity | Yes | 15s |
| **Storage** | SQLite read/write, migrations | Yes | 10s |
| **Config** | Config valid, migrations applied | Yes | 5s |
| **Update Subsystem** | Update manager functional | Yes | 5s |
| **Extensions** | Plugins/skills load | No | 30s |
| **Network** | Update server reachable | No | 10s |

### Health Check Execution
```typescript
async function runHealthChecks(version: string): Promise<HealthCheckResult> {
  const checks: HealthCheck[] = [];
  
  // Launch check
  checks.push(await checkProcessLaunch());
  
  // IPC check
  checks.push(await checkIPCConnectivity());
  
  // Backend connectivity
  checks.push(await checkBackendConnection());
  
  // Storage integrity
  checks.push(await checkStorageIntegrity());
  
  // Config validation
  checks.push(await checkConfigValidity());
  
  // Update subsystem
  checks.push(await checkUpdateSubsystem());
  
  const criticalFailed = checks.some(c => c.critical && !c.passed);
  
  return {
    passed: !criticalFailed,
    checks,
    timestamp: new Date().toISOString(),
  };
}
```

### Health Check Timing
- **Immediate**: After install, before marking complete
- **Post-Restart**: After application restart
- **Periodic**: Every 5 minutes for 1 hour post-update
- **On-Demand**: Manual trigger via IPC

## Rollback Decision Logic

```typescript
interface RollbackDecision {
  action: 'keep' | 'rollback' | 'rollback-app-only' | 'abort';
  reason: string;
  restoreVersion?: string;
}

function rollbackDecision(params: {
  snapshot: PreUpdateSnapshot | null;
  healthCheckPassed: boolean;
  userDataChangedSince: boolean;
}): RollbackDecision {
  if (!params.snapshot) {
    return { action: 'abort', reason: 'no snapshot' };
  }
  
  if (params.healthCheckPassed) {
    return { action: 'keep', reason: 'health check passed' };
  }
  
  // Health check failed - determine rollback scope
  if (params.userDataChangedSince) {
    // User data modified since snapshot - can't safely restore
    return {
      action: 'rollback-app-only',
      reason: 'reinstall previous app build; preserve newer user data for manual merge',
      restoreVersion: params.snapshot.currentVersion,
    };
  }
  
  // Safe to fully restore
  return {
    action: 'rollback',
    reason: 'reinstall previous app build and restore snapshot state',
    restoreVersion: params.snapshot.currentVersion,
  };
}
```

### Decision Matrix

| Health Check | User Data Changed | Action |
|--------------|-------------------|--------|
| Passed | Any | Keep update |
| Failed | No | Full rollback (app + state) |
| Failed | Yes | App-only rollback (preserve user data) |
| No snapshot | Any | Abort (manual intervention) |

## Platform-Specific Rollback

### Windows (NSIS/MSI)

#### Pre-Update Backup
```powershell
# Backup current installation
$backupPath = "$env:LOCALAPPDATA\AetherOS\backups\v$currentVersion"
Copy-Item "$env:APPDATA\AetherOS" $backupPath -Recurse -Force

# Backup user data (if separate)
$stateBackup = "$env:LOCALAPPDATA\AetherOS\state-backup-$updateId"
Copy-Item "$env:APPDATA\AetherOS\state" $stateBackup -Recurse
```

#### Rollback Execution
```powershell
# 1. Uninstall current version (silent)
$uninstaller = "$env:APPDATA\AetherOS\uninstall.exe"
& $uninstaller /S

# 2. Restore previous version from backup
$prevVersion = Get-ChildItem "$env:LOCALAPPDATA\AetherOS\backups" | Sort-Object Name -Descending | Select-Object -Skip 1 -First 1
Copy-Item "$env:LOCALAPPDATA\AetherOS\backups\$prevVersion" "$env:APPDATA\AetherOS" -Recurse -Force

# 3. Run previous version's installer (repair mode)
$prevInstaller = "$env:APPDATA\AetherOS\AetherOS-Setup-$prevVersion.exe"
& $prevInstaller /REPAIR /S

# 4. Restore user state if full rollback
if ($fullRollback) {
    Copy-Item "$stateBackup" "$env:APPDATA\AetherOS\state" -Recurse -Force
}
```

### macOS (DMG/PKG)

#### Pre-Update Backup
```bash
# Backup app bundle
BACKUP_DIR="$HOME/Library/Application Support/AetherOS/backups/v$CURRENT_VERSION"
cp -R "/Applications/AetherOS.app" "$BACKUP_DIR/"

# Backup user data
STATE_BACKUP="$HOME/Library/Application Support/AetherOS/state-backup-$UPDATE_ID"
cp -R "$HOME/Library/Application Support/AetherOS/state" "$STATE_BACKUP"
```

#### Rollback Execution
```bash
# 1. Remove current app
rm -rf "/Applications/AetherOS.app"

# 2. Restore previous version
PREV_VERSION=$(ls -1 "$HOME/Library/Application Support/AetherOS/backups" | sort -V | tail -2 | head -1)
cp -R "$HOME/Library/Application Support/AetherOS/backups/$PREV_VERSION/AetherOS.app" "/Applications/"

# 3. Verify code signature
codesign --verify --deep --strict "/Applications/AetherOS.app"

# 4. Restore user state if needed
if [ "$FULL_ROLLBACK" = "true" ]; then
    cp -R "$STATE_BACKUP" "$HOME/Library/Application Support/AetherOS/state"
fi

# 5. Clear quarantine if needed
xattr -cr "/Applications/AetherOS.app"
```

### Linux (AppImage/DEB/RPM/Flatpak)

#### AppImage Rollback
```bash
# Backup current
cp "$APPIMAGE_PATH" "$APPIMAGE_PATH.backup.$UPDATE_ID"

# Restore previous
PREV_APPIMAGE=$(ls -1 "$INSTALL_DIR"/AetherOS-*.AppImage | sort -V | tail -2 | head -1)
cp "$PREV_APPIMAGE" "$APPIMAGE_PATH"
chmod +x "$APPIMAGE_PATH"
```

#### DEB/RPM Rollback
```bash
# Debian/Ubuntu
apt install --reinstall -y aetheros=$PREV_VERSION

# RHEL/Fedora
dnf reinstall -y aetheros-$PREV_VERSION
```

#### Flatpak Rollback
```bash
# Flatpak manages versions internally
flatpak update --commit=$PREV_COMMIT com.aetheros.AetherOS

# Or specific version
flatpak install --system --reinstall flathub com.aetheros.AetherOS//$PREV_VERSION
```

## Crash Loop Protection

### Detection
```typescript
interface CrashRecord {
  version: string;
  timestamp: string;
  reason: string;
}

const crashHistory: CrashRecord[] = [];

function recordCrash(version: string, reason: string): void {
  crashHistory.push({ version, timestamp: new Date().toISOString(), reason });
  
  // Keep last 20 crashes
  if (crashHistory.length > 20) crashHistory.shift();
}

function detectCrashLoop(version: string): boolean {
  const recent = crashHistory
    .filter(c => c.version === version)
    .slice(-5); // Last 5 crashes
  
  if (recent.length < 3) return false;
  
  // Check if crashes within 10 minutes
  const first = new Date(recent[0].timestamp).getTime();
  const last = new Date(recent[recent.length - 1].timestamp).getTime();
  
  return (last - first) < 10 * 60 * 1000; // 10 minutes
}
```

### Automatic Response
```typescript
async function handleCrashLoop(): Promise<void> {
  if (detectCrashLoop(currentVersion)) {
    logger.error('Crash loop detected, initiating rollback');
    
    const rollbackInfo = await adapter.getRollbackInfo();
    if (rollbackInfo.available) {
      await adapter.rollback(rollbackInfo);
      telemetry.record('crash_loop_rollback', { version: currentVersion });
    } else {
      // No rollback available - show recovery UI
      showRecoveryDialog();
    }
  }
}
```

## Migration Rollback

### Migration Framework
```typescript
interface Migration {
  id: string;
  version: string;           // Target version
  description: string;
  precondition: (currentVersion: string) => boolean;
  execute: () => Promise<void>;
  validate: () => Promise<boolean>;
  rollback: () => Promise<void>;
}

const migrations: Migration[] = [
  {
    id: 'migrate-v1.2.0-schema',
    version: '1.2.0',
    description: 'Add vector index to memory table',
    precondition: (v) => compareVersions(v, '1.2.0') < 0,
    execute: async () => { await db.exec('CREATE INDEX...') },
    validate: async () => { return await db.get('SELECT 1 FROM memory_idx') !== undefined },
    rollback: async () => { await db.exec('DROP INDEX memory_idx') },
  },
];
```

### Migration Rollback on Failure
```typescript
async function runMigrations(targetVersion: string): Promise<void> {
  const pending = migrations.filter(m => m.precondition(currentVersion));
  
  for (const migration of pending) {
    const snapshot = await createMigrationSnapshot(migration.id);
    
    try {
      await migration.execute();
      if (!await migration.validate()) {
        throw new Error('Migration validation failed');
      }
    } catch (error) {
      // Rollback this migration
      await migration.rollback();
      await restoreMigrationSnapshot(snapshot);
      throw new Error(`Migration ${migration.id} failed: ${error.message}`);
    }
  }
}
```

## User Data Protection

### Data Classification
| Data Type | Rollback Behavior |
|-----------|-------------------|
| Conversations | Never rolled back (append-only) |
| Memories | Never rolled back |
| Skills | Preserved, new skills disabled |
| Configuration | Rolled back with app |
| Cache | Cleared on rollback |
| Logs | Preserved |

### User Data Merge Strategy
```typescript
function mergeUserData(
  currentData: UserData,
  snapshotData: UserData,
  strategy: 'current-wins' | 'snapshot-wins' | 'merge'
): UserData {
  switch (strategy) {
    case 'current-wins':
      return currentData;
    case 'snapshot-wins':
      return snapshotData;
    case 'merge':
      return deepMerge(currentData, snapshotData, (key, current, snapshot) => {
        // Arrays: concatenate unique
        if (Array.isArray(current) && Array.isArray(snapshot)) {
          return [...new Set([...current, ...snapshot])];
        }
        // Objects: recursive merge
        if (isObject(current) && isObject(snapshot)) {
          return deepMerge(current, snapshot);
        }
        // Primitives: current wins
        return current;
      });
  }
}
```

## Rollback Verification

### Post-Rollback Checks
1. Application launches successfully
2. Version matches expected rollback version
3. Critical health checks pass
4. User data accessible
5. Configuration valid
6. Update subsystem functional

### Verification Flow
```typescript
async function verifyRollback(expectedVersion: string): Promise<boolean> {
  // 1. Version check
  const actualVersion = await getCurrentVersion();
  if (actualVersion !== expectedVersion) return false;
  
  // 2. Health checks
  const health = await runHealthChecks(expectedVersion);
  if (!health.passed) return false;
  
  // 3. User data accessible
  const userDataOk = await verifyUserDataAccess();
  if (!userDataOk) return false;
  
  // 4. Config valid
  const configOk = await verifyConfigIntegrity();
  if (!configOk) return false;
  
  return true;
}
```

## Rollback Testing

### Test Scenarios
| Scenario | Expected Behavior |
|----------|-------------------|
| Health check failure | Automatic rollback to previous version |
| Crash loop (3 crashes in 10min) | Automatic rollback |
| Migration failure | Migration rollback, app stays on old version |
| User data changed since snapshot | App-only rollback, user data preserved |
| No snapshot available | Abort, alert ops team |
| Rollback itself fails | Alert ops team, show recovery UI |
| Mandatory update failure | Rollback + alert ops team |

### Chaos Testing
```bash
# Test: Kill during install
timeout 5s ./installer.exe && kill $!

# Test: Power loss during install
# (Use VM snapshot/restore)

# Test: Disk full during download
# (Use loopback device with limited space)

# Test: Network partition during verify
# (Use tc/netem to partition)

# Test: Clock skew
# (Set system clock to past/future)
```

## Rollback Metrics

### Tracked Metrics
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `rollback_total` | Total rollbacks | >5/hour |
| `rollback_success_rate` | Successful rollbacks | <99% |
| `rollback_duration_seconds` | Time to complete | >300s |
| `rollback_app_only` | App-only rollbacks | >10% |
| `rollback_user_data_lost` | User data loss events | >0 |

### Rollback Investigation
When rollback rate exceeds threshold:
1. Identify common failure pattern
2. Check release for regressions
3. Verify health check sensitivity
4. Review migration scripts
5. Check platform-specific issues
6. Document root cause and fix

## Recovery UI

### User-Facing States
| State | UI | Actions |
|-------|-----|---------|
| Rollback in progress | Full-screen progress | Wait |
| Rollback complete | Toast + version info | Continue |
| Rollback failed | Error dialog + recovery options | Retry / Manual / Support |
| Manual intervention needed | Recovery wizard | Guided recovery |

### Recovery Options
1. **Retry Rollback** - Re-attempt automatic rollback
2. **Manual Reinstall** - Download and run previous installer
3. **Data Export** - Export conversations/memories to JSON
4. **Clean Install** - Full reinstall (last resort)
5. **Contact Support** - Open support ticket with logs

## Rollback Runbooks

### Runbook: Automatic Rollback Triggered
1. Check rollback metrics dashboard
2. Identify affected version and failure reason
3. Check health check logs for failure details
4. If widespread: activate kill switch for version
4. If isolated: investigate client-specific issues
5. Prepare hotfix if regression confirmed
6. Document in incident tracker

### Runbook: Rollback Failure
1. Check rollback logs for error details
2. Verify backup integrity
3. Attempt manual rollback via recovery UI
4. If manual fails: guide user through clean reinstall
5. Preserve user data via export
6. Escalate to engineering if data loss risk

### Runbook: Crash Loop Without Rollback
1. Verify crash loop detection working
2. Check if rollback snapshot exists
3. If no snapshot: investigate why not created
4. Emergency patch to prevent data loss
5. Manual rollback for affected users