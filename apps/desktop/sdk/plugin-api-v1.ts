import { SDKCompatLayer } from './sdk-compatibility-layer'

export interface PluginContext {
  id: string
  name: string
  version: string
  sdkVersion: 'v1'
  api: PluginAPIV1
  log: PluginLogger
  config: PluginConfig
  hooks: PluginHooks
}

export interface PluginAPIV1 {
  system: SystemAPI
  files: FileAPI
  dialogs: DialogAPI
  notifications: NotificationAPI
  updater: UpdaterAPI
  telemetry: TelemetryAPI
  error: ErrorAPI
  migration: MigrationAPI
}

export interface SystemAPI {
  getInfo(): Promise<SystemInfo>
  getPerformance(): Promise<PerformanceMetrics>
  getEnvironment(): Record<string, string>
  getVersion(): string
}

export interface SystemInfo {
  platform: string
  arch: string
  version: string
  electronVersion: string
  chromeVersion: string
  nodeVersion: string
  cpuCores: number
  totalMemory: number
  freeMemory: number
}

export interface PerformanceMetrics {
  cpuUsage: number
  memoryUsage: number
  gpuUsage: number
  diskUsage: number
  startupTime: number
  fps: number
}

export interface FileAPI {
  read(path: string): Promise<string>
  write(path: string, data: string): Promise<void>
  delete(path: string): Promise<void>
  list(directory: string): Promise<string[]>
  exists(path: string): Promise<boolean>
  info(path: string): Promise<FileInfo>
  selectDirectory(): Promise<string | null>
  selectFile(filters?: FileFilter[]): Promise<string | null>
}

export interface FileInfo {
  size: number
  created: Date
  modified: Date
  isDirectory: boolean
  isFile: boolean
}

export interface FileFilter {
  name: string
  extensions: string[]
}

export interface DialogAPI {
  showMessage(options: MessageOptions): Promise<MessageResult>
  showError(title: string, message: string): Promise<void>
  showConfirm(title: string, message: string): Promise<boolean>
}

export interface MessageOptions {
  type: 'info' | 'warning' | 'error' | 'question'
  title: string
  message: string
  buttons?: string[]
  defaultId?: number
  cancelId?: number
}

export interface MessageResult {
  response: number
  checkboxChecked?: boolean
}

export interface NotificationAPI {
  show(title: string, body: string, options?: NotificationOptions): Promise<void>
  requestPermission(): Promise<boolean>
  getPermission(): NotificationPermission
}

export interface NotificationOptions {
  icon?: string
  silent?: boolean
  onClick?: () => void
}

export interface UpdaterAPI {
  check(): Promise<UpdateInfo | null>
  download(): Promise<void>
  install(): Promise<void>
  getStatus(): UpdateStatus
  onStatusChange(callback: (status: UpdateStatus) => void): void
}

export interface UpdateInfo {
  version: string
  releaseDate: string
  releaseNotes: string
  isCritical: boolean
}

export interface UpdateStatus {
  checking: boolean
  available: boolean
  downloading: boolean
  downloaded: boolean
  installing: boolean
  error?: string
  progress?: number
}

export interface TelemetryAPI {
  event(name: string, properties?: Record<string, string | number | boolean>): void
  metric(name: string, value: number, tags?: Record<string, string>): void
  isEnabled(): boolean
}

export interface ErrorAPI {
  report(error: Error, context?: ErrorContext): void
  getLastErrors(): ErrorReport[]
  clearErrors(): void
  getDiagnosticBundle(): Promise<DiagnosticBundle>
}

export interface ErrorContext {
  source?: string
  component?: string
  action?: string
  metadata?: Record<string, string>
}

export interface ErrorReport {
  id: string
  message: string
  stack?: string
  timestamp: number
  severity: 'info' | 'warning' | 'error' | 'critical'
  source?: string
  component?: string
  recovered: boolean
  suggestion?: string
}

export interface DiagnosticBundle {
  appVersion: string
  platform: string
  arch: string
  systemInfo: SystemInfo
  performance: PerformanceMetrics
  recentErrors: ErrorReport[]
  config: Record<string, unknown>
  environment: Record<string, string>
  timestamp: number
}

export interface MigrationAPI {
  run(name: string): Promise<MigrationResult>
  status(name?: string): Promise<MigrationStatus>
  list(): Promise<MigrationInfo[]>
  rollback(name: string): Promise<MigrationResult>
}

export interface MigrationResult {
  success: boolean
  applied: number
  rolledBack: number
  errors: string[]
  duration: number
}

export interface MigrationStatus {
  running: boolean
  lastRun?: number
  lastSuccess?: number
  lastError?: string
  pending: number
  completed: number
}

export interface MigrationInfo {
  name: string
  version: string
  description: string
  applied: boolean
  appliedAt?: string
  duration?: number
}

export interface PluginLogger {
  debug(message: string, ...args: unknown[]): void
  info(message: string, ...args: unknown[]): void
  warn(message: string, ...args: unknown[]): void
  error(message: string, ...args: unknown[]): void
}

export interface PluginConfig {
  get<T>(key: string, defaultValue?: T): T | undefined
  set<T>(key: string, value: T): void
  getAll(): Record<string, unknown>
  onChange(callback: (key: string, value: unknown) => void): void
}

export interface PluginHooks {
  onSessionStart(callback: (sessionId: string) => void): void
  onSessionEnd(callback: (sessionId: string) => void): void
  onToolCall(callback: (toolName: string, args: unknown) => void): void
  onToolResult(callback: (toolName: string, result: unknown) => void): void
  onAppStart(callback: () => void): void
  onAppQuit(callback: () => void): void
  onConfigChange(callback: (key: string, value: unknown) => void): void
  onError(callback: (error: Error) => void): void
}

const compatLayer = new SDKCompatLayer()

export function createPluginContext(plugin: { id: string; name: string; version: string }): PluginContext {
  compatLayer.registerAPIVersion('system', '1.0.0')
  compatLayer.registerAPIVersion('files', '1.0.0')
  compatLayer.registerAPIVersion('dialogs', '1.0.0')
  compatLayer.registerAPIVersion('notifications', '1.0.0')
  compatLayer.registerAPIVersion('updater', '1.0.0')
  compatLayer.registerAPIVersion('telemetry', '1.0.0')
  compatLayer.registerAPIVersion('error', '1.0.0')
  compatLayer.registerAPIVersion('migration', '1.0.0')

  const api: PluginAPIV1 = {
    system: {
      getInfo: () => Promise.resolve({ platform: '', arch: '', version: '', electronVersion: '', chromeVersion: '', nodeVersion: '', cpuCores: 0, totalMemory: 0, freeMemory: 0 }),
      getPerformance: () => Promise.resolve({ cpuUsage: 0, memoryUsage: 0, gpuUsage: 0, diskUsage: 0, startupTime: 0, fps: 0 }),
      getEnvironment: () => ({}),
      getVersion: () => '1.0.0',
    },
    files: {
      read: () => Promise.resolve(''),
      write: () => Promise.resolve(),
      delete: () => Promise.resolve(),
      list: () => Promise.resolve([]),
      exists: () => Promise.resolve(false),
      info: () => Promise.resolve({ size: 0, created: new Date(), modified: new Date(), isDirectory: false, isFile: false }),
      selectDirectory: () => Promise.resolve(null),
      selectFile: () => Promise.resolve(null),
    },
    dialogs: {
      showMessage: () => Promise.resolve({ response: 0 }),
      showError: () => Promise.resolve(),
      showConfirm: () => Promise.resolve(false),
    },
    notifications: {
      show: () => Promise.resolve(),
      requestPermission: () => Promise.resolve(true),
      getPermission: () => 'default',
    },
    updater: {
      check: () => Promise.resolve(null),
      download: () => Promise.resolve(),
      install: () => Promise.resolve(),
      getStatus: () => ({ checking: false, available: false, downloading: false, downloaded: false, installing: false }),
      onStatusChange: () => {},
    },
    telemetry: {
      event: () => {},
      metric: () => {},
      isEnabled: () => false,
    },
    error: {
      report: () => {},
      getLastErrors: () => [],
      clearErrors: () => {},
      getDiagnosticBundle: () => Promise.resolve({
        appVersion: '', platform: '', arch: '', systemInfo: { platform: '', arch: '', version: '', electronVersion: '', chromeVersion: '', nodeVersion: '', cpuCores: 0, totalMemory: 0, freeMemory: 0 },
        performance: { cpuUsage: 0, memoryUsage: 0, gpuUsage: 0, diskUsage: 0, startupTime: 0, fps: 0 },
        recentErrors: [], config: {}, environment: {}, timestamp: 0,
      }),
    },
    migration: {
      run: () => Promise.resolve({ success: true, applied: 0, rolledBack: 0, errors: [], duration: 0 }),
      status: () => Promise.resolve({ running: false, pending: 0, completed: 0 }),
      list: () => Promise.resolve([]),
      rollback: () => Promise.resolve({ success: true, applied: 0, rolledBack: 0, errors: [], duration: 0 }),
    },
  }

  return {
    id: plugin.id,
    name: plugin.name,
    version: plugin.version,
    sdkVersion: 'v1',
    api,
    log: createLogger(plugin.id),
    config: createConfig(plugin.id),
    hooks: createHooks(),
  }
}

function createLogger(_pluginId: string): PluginLogger {
  return {
    debug: (...args) => {},
    info: (...args) => {},
    warn: (...args) => {},
    error: (...args) => {},
  }
}

function createConfig(_pluginId: string): PluginConfig {
  const store: Record<string, unknown> = {}
  return {
    get: (key, defaultValue) => (store[key] as T) ?? defaultValue,
    set: (key, value) => { store[key] = value },
    getAll: () => ({ ...store }),
    onChange: () => {},
  }
}

function createHooks(): PluginHooks {
  const handlers: Record<string, Array<(...args: unknown[]) => void>> = {}
  const hook = (name: string) => (callback: (...args: unknown[]) => void) => {
    if (!handlers[name]) handlers[name] = []
    handlers[name].push(callback)
  }
  return {
    onSessionStart: hook('sessionStart'),
    onSessionEnd: hook('sessionEnd'),
    onToolCall: hook('toolCall'),
    onToolResult: hook('toolResult'),
    onAppStart: hook('appStart'),
    onAppQuit: hook('appQuit'),
    onConfigChange: hook('configChange'),
    onError: hook('error'),
  }
}
