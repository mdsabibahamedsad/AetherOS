const { contextBridge, ipcRenderer, webUtils } = require('electron')

console.log('[startup] Preload loaded')

contextBridge.exposeInMainWorld('aetherosDesktop', {
  getConnection: profile => ipcRenderer.invoke('aetheros:connection', profile),
  revalidateConnection: () => ipcRenderer.invoke('aetheros:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('aetheros:backend:touch', profile),
  getGatewayWsUrl: profile => ipcRenderer.invoke('aetheros:gateway:ws-url', profile),
  openSessionWindow: sessionId => ipcRenderer.invoke('aetheros:window:openSession', sessionId),
  getBootProgress: () => ipcRenderer.invoke('aetheros:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('aetheros:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('aetheros:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('aetheros:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('aetheros:connection-config:test', payload),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('aetheros:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('aetheros:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('aetheros:connection-config:oauth-logout', remoteUrl),
  profile: {
    get: () => ipcRenderer.invoke('aetheros:profile:get'),
    set: name => ipcRenderer.invoke('aetheros:profile:set', name)
  },
  api: request => ipcRenderer.invoke('aetheros:api', request),
  notify: payload => ipcRenderer.invoke('aetheros:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('aetheros:requestMicrophoneAccess'),
  readFileDataUrl: filePath => ipcRenderer.invoke('aetheros:readFileDataUrl', filePath),
  readFileText: filePath => ipcRenderer.invoke('aetheros:readFileText', filePath),
  selectPaths: options => ipcRenderer.invoke('aetheros:selectPaths', options),
  writeClipboard: text => ipcRenderer.invoke('aetheros:writeClipboard', text),
  saveImageFromUrl: url => ipcRenderer.invoke('aetheros:saveImageFromUrl', url),
  saveImageBuffer: (data, ext) => ipcRenderer.invoke('aetheros:saveImageBuffer', { data, ext }),
  saveClipboardImage: () => ipcRenderer.invoke('aetheros:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('aetheros:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('aetheros:watchPreviewFile', url),
  stopPreviewFileWatch: id => ipcRenderer.invoke('aetheros:stopPreviewFileWatch', id),
  setTitleBarTheme: payload => ipcRenderer.send('aetheros:titlebar-theme', payload),
  setPreviewShortcutActive: active => ipcRenderer.send('aetheros:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('aetheros:openExternal', url),
  fetchLinkTitle: url => ipcRenderer.invoke('aetheros:fetchLinkTitle', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('aetheros:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('aetheros:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('aetheros:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('aetheros:setting:defaultProjectDir:pick')
  },
  revealLogs: () => ipcRenderer.invoke('aetheros:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('aetheros:logs:recent'),
  readDir: dirPath => ipcRenderer.invoke('aetheros:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('aetheros:fs:gitRoot', startPath),
  terminal: {
    dispose: id => ipcRenderer.invoke('aetheros:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('aetheros:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('aetheros:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('aetheros:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `aetheros:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `aetheros:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('aetheros:close-preview-requested', listener)
    return () => ipcRenderer.removeListener('aetheros:close-preview-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('aetheros:open-updates', listener)
    return () => ipcRenderer.removeListener('aetheros:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('aetheros:deep-link', listener)
    return () => ipcRenderer.removeListener('aetheros:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('aetheros:deep-link-ready'),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('aetheros:window-state-changed', listener)
    return () => ipcRenderer.removeListener('aetheros:window-state-changed', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('aetheros:preview-file-changed', listener)
    return () => ipcRenderer.removeListener('aetheros:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('aetheros:backend-exit', listener)
    return () => ipcRenderer.removeListener('aetheros:backend-exit', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('aetheros:power-resume', listener)
    return () => ipcRenderer.removeListener('aetheros:power-resume', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('aetheros:boot-progress', listener)
    return () => ipcRenderer.removeListener('aetheros:boot-progress', listener)
  },
  getVersion: () => ipcRenderer.invoke('aetheros:version'),
  uninstall: {
    summary: () => ipcRenderer.invoke('aetheros:uninstall:summary'),
    run: mode => ipcRenderer.invoke('aetheros:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('aetheros:updates:check'),
    apply: opts => ipcRenderer.invoke('aetheros:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('aetheros:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('aetheros:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('aetheros:updates:progress', listener)
      return () => ipcRenderer.removeListener('aetheros:updates:progress', listener)
    }
  },
  // Signed-package updater (UpdateManager in main). Renderer may REQUEST
  // check/download/install/rollback; main validates every call and owns
  // staging + install + rollback. No direct installer control from UI.
  signedUpdater: {
    getState: () => ipcRenderer.invoke('update:get-state'),
    getConfig: () => ipcRenderer.invoke('update:get-config'),
    setConfig: config => ipcRenderer.invoke('update:set-config', config),
    check: force => ipcRenderer.invoke('update:check', force === true),
    download: () => ipcRenderer.invoke('update:download'),
    install: opts => ipcRenderer.invoke('update:install', opts),
    rollback: () => ipcRenderer.invoke('update:rollback'),
    cancelDownload: () => ipcRenderer.invoke('update:cancel-download'),
    getHistory: () => ipcRenderer.invoke('update:get-history'),
    onStateChange: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('update:state-change', listener)
      return () => ipcRenderer.removeListener('update:state-change', listener)
    },
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('update:progress', listener)
      return () => ipcRenderer.removeListener('update:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('aetheros:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('aetheros:vscode-theme:search', query)
  },
  getSystemStats: () => ipcRenderer.invoke('aetheros:system:stats'),
  getHealthStatus: () => ipcRenderer.invoke('aetheros:system:health'),
  restartBackend: () => ipcRenderer.invoke('aetheros:backend:restart'),
  getServiceLogs: serviceId => ipcRenderer.invoke('aetheros:logs:service', serviceId),
  focusMainWindow: () => ipcRenderer.invoke('aetheros:main-window:focus'),
  // Jarvis OS surfaces: approval-gated screen capture + OS-global hotkey.
  // Narrow closures only — no raw ipcRenderer exposure.
  screenshot: source => ipcRenderer.invoke('aetheros:os:screenshot', { source: source ?? 'screen' }),
  jarvisHotkey: {
    set: accelerator => ipcRenderer.invoke('aetheros:jarvis-hotkey:set', { accelerator }),
    clear: () => ipcRenderer.invoke('aetheros:jarvis-hotkey:clear')
  },
  onJarvisFocus: callback => {
    const listener = () => callback()
    ipcRenderer.on('aetheros:jarvis:focus', listener)
    return () => ipcRenderer.removeListener('aetheros:jarvis:focus', listener)
  }
})
