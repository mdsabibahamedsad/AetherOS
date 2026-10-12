'use strict'

// Unit tests for electron/jarvis-os.cjs (node:test — no display needed).
const { test } = require('node:test')
const assert = require('node:assert/strict')

const {
  captureScreenshot,
  clearJarvisHotkey,
  isValidAccelerator,
  normalizeAccelerator,
  setJarvisHotkey
} = require('./jarvis-os.cjs')

test('accelerator validation accepts sane shortcuts and rejects junk', () => {
  assert.equal(normalizeAccelerator('CommandOrControl+Space'), 'CommandOrControl+Space')
  assert.equal(normalizeAccelerator('Ctrl+Space'), 'Control+Space')
  assert.equal(isValidAccelerator('CommandOrControl+Space'), 'CommandOrControl+Space')
  assert.equal(isValidAccelerator('F9'), 'F9')
  assert.equal(isValidAccelerator(''), null)
  assert.equal(isValidAccelerator(null), null)
  assert.equal(isValidAccelerator('not a shortcut'), null)
  assert.equal(isValidAccelerator('rm -rf /'), null)
  assert.equal(isValidAccelerator('CommandOrControl+Delete'), null)
  assert.equal(isValidAccelerator(';;'), null)
})

test('hotkey registration reports failures instead of failing silently', () => {
  const calls = []
  const fakeWindow = {
    destroyed: false,
    isDestroyed: () => false,
    isMinimized: () => false,
    restore: () => calls.push('restore'),
    show: () => calls.push('show'),
    focus: () => calls.push('focus'),
    webContents: { send: channel => calls.push(`send:${channel}`) }
  }
  const fakeShortcut = {
    registered: new Map(),
    unregisterAll() {},
    register(accel, fn) { this.registered.set(accel, fn); return true }
  }

  const ok = setJarvisHotkey({ globalShortcut: fakeShortcut, mainWindow: fakeWindow }, 'CommandOrControl+Space')
  assert.equal(ok.ok, true)
  assert.equal(ok.accelerator, 'CommandOrControl+Space')

  fakeShortcut.registered.get('CommandOrControl+Space')()
  assert.deepEqual(calls, ['show', 'focus', 'send:aetheros:jarvis:focus'])

  const bad = setJarvisHotkey({ globalShortcut: fakeShortcut, mainWindow: fakeWindow }, 'rm -rf /')
  assert.equal(bad.ok, false)
  assert.match(bad.error, /Invalid shortcut/)

  const taken = setJarvisHotkey({
    globalShortcut: { unregisterAll() {}, register: () => false },
    mainWindow: fakeWindow
  }, 'F9')
  assert.equal(taken.ok, false)
  assert.match(taken.error, /could not be registered/)

  clearJarvisHotkey({ globalShortcut: fakeShortcut })
})

test('screenshot validates source and surfaces typed errors', async () => {
  await assert.rejects(
    captureScreenshot({}, 'screen'),
    /not available/
  )

  await assert.rejects(
    captureScreenshot({ desktopCapturer: { getSources: async () => [] } }, 'screen'),
    /No screen capture source/
  )

  const dataUrl = 'data:image/png;base64,AAA'
  const out = await captureScreenshot({
    desktopCapturer: {
      getSources: async ({ types }) => {
        assert.deepEqual(types, ['window'])
        return [{ thumbnail: { isEmpty: () => false, toDataURL: () => dataUrl } }]
      }
    }
  }, 'window')
  assert.equal(out, dataUrl)

  await assert.rejects(
    captureScreenshot({
      desktopCapturer: {
        getSources: async () => [{ thumbnail: { isEmpty: () => true, toDataURL: () => '' } }]
      }
    }, 'bogus-source-xyz'),
    /No screen capture source/
  )
})
