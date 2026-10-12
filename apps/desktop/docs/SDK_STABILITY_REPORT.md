# SDK Stability Report

## SDK v1 — Stability Assessment

### API Surface

The SDK v1 exposes 25 API features across 8 core API groups:

| Group | APIs | Stability | Deprecated |
|-------|------|-----------|------------|
| System | `getInfo`, `getPerformance`, `getEnvironment`, `getVersion` | ✅ Stable | 0 |
| Files | `read`, `write`, `delete`, `list`, `exists`, `info`, `selectDirectory`, `selectFile` | ✅ Stable | 0 |
| Dialogs | `showMessage`, `showError`, `showConfirm` | ✅ Stable | 0 |
| Notifications | `show`, `requestPermission`, `getPermission` | ✅ Stable | 0 |
| Updater | `check`, `download`, `install`, `getStatus`, `onStatusChange` | ✅ Stable | 0 |
| Telemetry | `event`, `metric`, `isEnabled` | ✅ Stable | 0 |
| Error | `report`, `getLastErrors`, `clearErrors`, `getDiagnosticBundle` | ✅ Stable | 0 |
| Migration | `run`, `status`, `list`, `rollback` | ✅ Stable | 0 |

### Compatibility Guarantees

| Guarantee | SDK v1 | SDK v2 (future) |
|-----------|--------|-----------------|
| Backward compatible | Full | Via compat layer |
| Deprecation notice | 2 minor versions | 2 minor versions |
| Removal notice | 2 minor versions | 2 minor versions |
| Migration guide | Provided | Provided |
| API surface freeze | ✅ | ❌ (new APIs added) |

### Deprecation Status

- **Active deprecations:** 0
- **Removed APIs:** 0
- **Pending deprecations:** 0

### Plugin Compatibility

All SDK v1 plugins are guaranteed compatible within the app version range `1.0.0` to `1.9999.9999`.

### Testing

- **Unit tests:** Plugin API surface, compatibility layer, version comparison
- **Integration tests:** Plugin lifecycle, config persistence
- **Compat tests:** Cross-version plugin loading

### Recommendations

1. Maintain zero active deprecations for all SDK v1 APIs
2. Before deprecating any API, ensure migration path is documented
3. Before introducing SDK v2, create the compatibility layer and test it against all v1 plugins
4. Run the plugin compatibility test suite before every stable release
