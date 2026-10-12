const assert = require('node:assert/strict')
const test = require('node:test')

const {
  SUPPORT_LEVELS,
  capabilityError,
  capabilityStatus,
  detectLinuxSession,
  linuxCapabilities
} = require('./linux-session.cjs')

test('detectLinuxSession is not applicable off Linux', () => {
  assert.equal(detectLinuxSession({ env: { DISPLAY: ':0' }, platform: 'win32' }).applicable, false)
  assert.equal(detectLinuxSession({ env: {}, platform: 'darwin' }).sessionType, null)
})

test('detectLinuxSession classifies X11, forwarded X11, Wayland, WSLg, headless', () => {
  assert.equal(detectLinuxSession({ env: { DISPLAY: ':0' }, platform: 'linux' }).sessionType, 'x11')
  assert.equal(detectLinuxSession({ env: { DISPLAY: ':1' }, platform: 'linux' }).sessionType, 'x11')
  assert.equal(
    detectLinuxSession({ env: { DISPLAY: 'localhost:10.0' }, platform: 'linux' }).sessionType,
    'x11-forwarded'
  )
  assert.equal(
    detectLinuxSession({ env: { WAYLAND_DISPLAY: 'wayland-0' }, platform: 'linux' }).sessionType,
    'wayland'
  )
  assert.equal(
    detectLinuxSession({ env: { XDG_SESSION_TYPE: 'wayland' }, platform: 'linux' }).sessionType,
    'wayland'
  )
  assert.equal(
    detectLinuxSession({ env: { WSL_DISTRO_NAME: 'Ubuntu', DISPLAY: ':0' }, platform: 'linux' }).sessionType,
    'wslg'
  )
  assert.equal(
    detectLinuxSession({ env: { WSL_DISTRO_NAME: 'Ubuntu', WAYLAND_DISPLAY: 'wayland-0' }, platform: 'linux' })
      .sessionType,
    'wslg'
  )
  assert.equal(detectLinuxSession({ env: {}, platform: 'linux' }).sessionType, 'headless')
})

test('XDG_SESSION_TYPE=x11 without DISPLAY still reports x11 (not headless)', () => {
  assert.equal(detectLinuxSession({ env: { XDG_SESSION_TYPE: 'x11' }, platform: 'linux' }).sessionType, 'x11')
})

test('SSH sessions surface a remoteReason but keep their session type', () => {
  const info = detectLinuxSession({
    env: { SSH_CONNECTION: '1.2.3.4 5 6.7.8.9 22', DISPLAY: ':0' },
    platform: 'linux'
  })
  assert.equal(info.sessionType, 'x11')
  assert.equal(info.remoteReason, 'ssh-session')

  const forwarded = detectLinuxSession({ env: { DISPLAY: 'localhost:10.0' }, platform: 'linux' })
  assert.equal(forwarded.sessionType, 'x11-forwarded')
  assert.equal(forwarded.remoteReason, 'x11-forwarding')
})

test('capability matrix only uses defined support levels', () => {
  for (const sessionType of ['x11', 'x11-forwarded', 'wayland', 'wslg', 'headless']) {
    const info = { applicable: true, sessionType, remoteReason: null }
    for (const status of Object.values(linuxCapabilities(info))) {
      assert.ok(SUPPORT_LEVELS.includes(status.level), `${sessionType}: unknown level ${status.level}`)
    }
  }
})

test('X11 is fully native; headless is fully unsupported with structured errors', () => {
  const x11 = { applicable: true, sessionType: 'x11', remoteReason: null }
  for (const [cap, status] of Object.entries(linuxCapabilities(x11))) {
    assert.equal(status.level, 'native', `${cap} should be native on x11`)
    assert.equal(capabilityError(cap, x11), null)
  }

  const headless = { applicable: true, sessionType: 'headless', remoteReason: null }
  for (const [cap, status] of Object.entries(linuxCapabilities(headless))) {
    assert.equal(status.level, 'unsupported', `${cap} should be unsupported headless`)
    const err = capabilityError(cap, headless)
    assert.equal(err.code, 'capability_unavailable')
    assert.equal(err.details.capability, cap)
    assert.match(err.message, /unavailable/)
  }
})

test('Wayland capture/input/window management are explicitly unsupported, clipboard/tray limited', () => {
  const wayland = { applicable: true, sessionType: 'wayland', remoteReason: null }
  for (const cap of ['screen_capture', 'input_synthesis', 'window_management']) {
    assert.equal(capabilityStatus(cap, wayland).level, 'unsupported')
    assert.equal(capabilityError(cap, wayland).details.reason.length > 0, true)
  }
  assert.equal(capabilityStatus('clipboard', wayland).level, 'limited')
  assert.equal(capabilityError('clipboard', wayland), null)
  assert.equal(capabilityStatus('notifications', wayland).level, 'native')
})

test('off-Linux callers get native statuses and no errors (module is inert elsewhere)', () => {
  const na = { applicable: false, sessionType: null, remoteReason: null }
  assert.deepEqual(capabilityStatus('screen_capture', na), { level: 'native', reason: null })
  assert.equal(capabilityError('screen_capture', na), null)
})

test('unknown capabilities produce an explicit unknown_capability error', () => {
  const err = capabilityError('teleportation', { applicable: true, sessionType: 'x11', remoteReason: null })
  assert.equal(err.code, 'unknown_capability')
})
