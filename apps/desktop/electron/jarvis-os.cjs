'use strict'

/**
 * jarvis-os.cjs — main-process OS surfaces for Jarvis Mode.
 *
 * Two narrow capabilities, both behind validated IPC (see the
 * `aetheros:os:*` handlers in main.cjs):
 *
 * 1. screenshot — one-shot screen/window capture via desktopCapturer.
 *    The renderer permission policy requires explicit per-capture approval
 *    before this is ever invoked. Returns a bounded PNG data URL.
 * 2. jarvis-hotkey — OS-global shortcut (default CommandOrControl+Space)
 *    that focuses the app and tells the renderer to open/focus Jarvis.
 *    Registration failures are reported, never silent.
 *
 * Pure validation + thin electron wrappers. Electron modules are injected
 * so this file is unit-testable with node:test (no display needed).
 */

const ACCELERATOR_RE = /^(?:(?:CommandOrControl|Control|Command|Alt|Option|Shift|Super)(?:\+(?:CommandOrControl|Control|Command|Alt|Option|Shift|Super))*)?\+?[A-Za-z0-9]$|^(?:CommandOrControl|Control|Command|Alt|Option|Shift|Super)\+Space$|^F(?:[1-9]|1[0-9]|2[0-4])$/

const SINGLE_KEY_RE = /^[A-Za-z0-9]$/

function normalizeAccelerator(raw) {
  if (typeof raw !== 'string') {return null}
  const value = raw.trim()
  if (!value) {return null}

  // Canonical single-key and F-key forms.
  if (SINGLE_KEY_RE.test(value) || /^F(?:[1-9]|1[0-9]|2[0-4])$/.test(value)) {return value}

  const parts = value.split('+').map(p => p.trim()).filter(Boolean)
  if (parts.length < 2) {return null}

  const key = parts[parts.length - 1]
  const mods = parts.slice(0, -1)
  const validMods = new Set(['CommandOrControl', 'Control', 'Ctrl', 'Command', 'Cmd', 'Alt', 'Option', 'Shift', 'Super', 'Meta'])

  if (!/^(Space|[A-Za-z0-9])$/.test(key)) {return null}
  if (!mods.every(m => validMods.has(m))) {return null}

  const canon = mod => {
    if (mod === 'Ctrl') {return 'Control'}
    if (mod === 'Cmd') {return 'Command'}
    if (mod === 'Meta') {return 'Super'}
    return mod
  }

  return [...mods.map(canon), key === ' ' ? 'Space' : key].join('+')
}

function isValidAccelerator(raw) {
  const normalized = normalizeAccelerator(raw)
  if (!normalized) {return null}
  return ACCELERATOR_RE.test(normalized) ? normalized : null
}

async function captureScreenshot(deps, source) {
  const kind = source === 'window' ? 'window' : 'screen'

  if (typeof deps.desktopCapturer?.getSources !== 'function') {
    throw new Error('Screen capture is not available in this environment.')
  }

  const sources = await deps.desktopCapturer.getSources({
    types: [kind],
    thumbnailSize: { width: 1600, height: 1000 }
  })

  const first = Array.isArray(sources) ? sources[0] : null
  if (!first || typeof first.thumbnail?.toDataURL !== 'function' || first.thumbnail.isEmpty()) {
    throw new Error(`No ${kind} capture source is available.`)
  }

  const dataUrl = first.thumbnail.toDataURL()
  if (typeof dataUrl !== 'string' || !dataUrl.startsWith('data:image')) {
    throw new Error('Screen capture produced no image data.')
  }

  return dataUrl
}

function setJarvisHotkey(deps, accelerator) {
  const normalized = isValidAccelerator(accelerator)
  if (!normalized) {
    return { ok: false, error: `Invalid shortcut "${accelerator}". Use e.g. CommandOrControl+Space.` }
  }

  const { globalShortcut, mainWindow } = deps
  if (typeof globalShortcut?.register !== 'function') {
    return { ok: false, error: 'Global shortcuts are not available in this environment.' }
  }

  try {
    globalShortcut.unregisterAll()
  } catch {
    // Best effort — a stale registration must not block the new one.
  }

  let registered = false
  try {
    registered = globalShortcut.register(normalized, () => {
      try {
        if (mainWindow && !mainWindow.isDestroyed()) {
          if (mainWindow.isMinimized()) {mainWindow.restore()}
          mainWindow.show()
          mainWindow.focus()
          mainWindow.webContents.send('aetheros:jarvis:focus')
        }
      } catch {
        // Never throw out of a global shortcut callback.
      }
    })
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : 'Shortcut registration failed.' }
  }

  if (!registered) {
    return { ok: false, error: `The shortcut "${normalized}" could not be registered (it may be taken by another app).` }
  }

  return { ok: true, accelerator: normalized }
}

function clearJarvisHotkey(deps) {
  try {
    deps.globalShortcut?.unregisterAll()
  } catch {
    // Best effort.
  }
}

module.exports = {
  ACCELERATOR_RE,
  captureScreenshot,
  clearJarvisHotkey,
  isValidAccelerator,
  normalizeAccelerator,
  setJarvisHotkey
}
