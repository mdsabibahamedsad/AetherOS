# AetherOS Desktop API Reference

This document describes the preload bridge API exposed to the renderer process via `window.__HERMES_PRELOAD_API__`.

## Overview

The preload bridge uses Electron's `contextBridge` to safely expose a curated set of native APIs to the renderer process. All IPC communication is validated against an allowlist.

## API Surface

The full API surface consists of ~56 exports organized into the following categories:

### Process & App (`process.*`)

| Method | Type | Description |
|--------|------|-------------|
| `platform` | string | `win32`, `darwin`, `linux` |
| `arch` | string | `x64`, `arm64` |
| `versions` | object | Node, Chrome, Electron, V8 versions |
| `env` | object | Safe subset of environment variables |
| `cwd` | string | Current working directory |
| `argv` | string[] | Command line arguments |
| `getAppPath()` | string | Application path |
| `getPath(name)` | string | System path (home, appData, userData, etc.) |

### Window Management (`window.*`)

| Method | Type | Description |
|--------|------|-------------|
| `minimize()` | void | Minimize window |
| `maximize()` | void | Maximize window |
| `unmaximize()` | void | Restore window |
| `close()` | void | Close window |
| `isMaximized()` | boolean | Check if window is maximized |
| `isFullScreen()` | boolean | Check if window is full-screen |
| `setFullScreen(flag)` | void | Toggle full-screen |
| `focus()` | void | Focus window |
| `reload()` | void | Reload renderer |
| `openDevTools()` | void | Open DevTools (dev only) |
| `showOpenDialog(options)` | Promise | Native file open dialog |
| `showSaveDialog(options)` | Promise | Native file save dialog |

### File System (`fs.*`)

| Method | Description |
|--------|-------------|
| `readFile(path)` | Read file (validated path) |
| `writeFile(path, data)` | Write file (validated path) |
| `deleteFile(path)` | Delete file (validated path) |
| `readDirectory(path)` | List directory contents |
| `createDirectory(path)` | Create directory |
| `fileExists(path)` | Check file existence |
| `getFileInfo(path)` | File stats (size, modified, etc.) |
| `selectDirectory()` | Open native directory picker |
| `getRecentFiles()` | Recently opened files |

### Shell (`shell.*`)

| Method | Description |
|--------|-------------|
| `openPath(path)` | Open file in OS default application |
| `openExternal(url)` | Open URL in default browser |
| `showItemInFolder(path)` | Reveal file in file manager |
| `beep()` | System beep |
| `writeClipboard(text)` | Write to system clipboard |
| `readClipboard()` | Read from system clipboard |

### Config (`config.*`)

| Method | Description |
|--------|-------------|
| `get(key)` | Get configuration value |
| `set(key, value)` | Set configuration value |
| `getAll()` | Get entire configuration |
| `reset()` | Reset configuration to defaults |
| `onChange(callback)` | Subscribe to config changes |

### Dialogs (`dialog.*`)

| Method | Description |
|--------|-------------|
| `showMessageBox(options)` | Show native message box |
| `showErrorBox(title, content)` | Show native error dialog |

### Updates (`updater.*`)

| Method | Description |
|--------|-------------|
| `checkForUpdates()` | Check for updates |
| `downloadUpdate()` | Download available update |
| `installUpdate()` | Install downloaded update |
| `getUpdateStatus()` | Get current update status |
| `onUpdateStatus(callback)` | Subscribe to update status changes |

### IPC (`ipc.*`)

| Method | Description |
|--------|-------------|
| `send(channel, ...args)` | Send IPC message to main process |
| `invoke(channel, ...args)` | Invoke IPC handler (request-response) |
| `on(channel, callback)` | Listen for IPC events from main process |
| `once(channel, callback)` | Listen for single IPC event |

### Diagnostic (`diagnostics.*`)

| Method | Description |
|--------|-------------|
| `getSystemInfo()` | System diagnostic information |
| `getPerformanceMetrics()` | CPU, memory, GPU metrics |
| `exportDiagnostics()` | Export full diagnostics package |
| `runHealthCheck()` | Run system health checks |

### Notifications (`notify.*`)

| Method | Description |
|--------|-------------|
| `showNotification(title, body)` | Show OS notification |
| `requestPermission()` | Request notification permission |

## IPC Channels

### Predefined Channels

| Channel | Direction | Description |
|---------|-----------|-------------|
| `hermes:window-state` | Main → Renderer | Window state changes |
| `hermes:config-changed` | Main → Renderer | Config value changes |
| `hermes:update-available` | Main → Renderer | Update availability |
| `hermes:update-progress` | Main → Renderer | Download progress |
| `hermes:menu-action` | Main → Renderer | Menu action triggered |
| `hermes:crash-report` | Main → Renderer | Crash information |
| `hermes:open-file` | Main → Renderer | File open request |

### Custom Channels
Custom channel names must match pattern: `^[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+$`
All custom channels must be registered in the main process allowlist.

## Error Handling

All async methods return Promises. Errors are caught and returned as structured objects:

```typescript
interface APIError {
  code: string;
  message: string;
  stack?: string;
}
```

## Security

- All file paths are validated against path traversal attacks
- IPC channels are validated against an allowlist
- No direct access to Node.js APIs
- Context isolation is enabled
- `nodeIntegration` is disabled
