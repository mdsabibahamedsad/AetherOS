// Linux display-session detection and honest capability reporting.
//
// Pure + dependency-free (injectable env/platform) so it is unit-testable on
// any OS and callable before app ready, mirroring bootstrap-platform.cjs.
//
// Design rule (Master Prompt 31 / AGENTS.md): capabilities that cannot be
// implemented reliably on a session type return structured errors — never
// silent success. Wayland capture/input/window-management stay explicitly
// UNSUPPORTED until portal-based implementations are validated on real
// compositors.

const SUPPORT_LEVELS = ['native', 'limited', 'unsupported']

function detectLinuxSession(options = {}) {
  const env = options.env ?? process.env
  const platform = options.platform ?? process.platform
  if (platform !== 'linux') {
    return { applicable: false, sessionType: null, remoteReason: null }
  }

  const isWsl = Boolean(env.WSL_DISTRO_NAME || env.WSL_INTEROP)
  const waylandDisplay = String(env.WAYLAND_DISPLAY || '').trim()
  const xdgSessionType = String(env.XDG_SESSION_TYPE || '')
    .trim()
    .toLowerCase()
  const display = String(env.DISPLAY || '').trim()

  // A DISPLAY like "localhost:10.0" means X11 forwarding; ":0" is local.
  let forwarded = false
  if (display.includes(':') && display.split(':')[0]) forwarded = true

  const sshSession = Boolean(env.SSH_CONNECTION || env.SSH_CLIENT || env.SSH_TTY)

  let sessionType
  if ((isWsl && waylandDisplay) || (isWsl && display)) {
    sessionType = 'wslg'
  } else if (waylandDisplay || xdgSessionType === 'wayland') {
    sessionType = 'wayland'
  } else if (forwarded || xdgSessionType === 'x11-forwarded') {
    sessionType = 'x11-forwarded'
  } else if (display || xdgSessionType === 'x11') {
    sessionType = 'x11'
  } else {
    sessionType = 'headless'
  }

  let remoteReason = null
  if (sshSession) remoteReason = 'ssh-session'
  else if (forwarded) remoteReason = 'x11-forwarding'

  return { applicable: true, sessionType, remoteReason }
}

// Capability matrix by session type. Values are honest as of this commit;
// upgrade a cell only WITH executable evidence (see docs/AETHEROS_LINUX_RELEASE.md).
const CAPABILITY_MATRIX = {
  x11: {
    notifications: 'native',
    tray: 'native',
    screen_capture: 'native',
    input_synthesis: 'native',
    window_management: 'native',
    clipboard: 'native'
  },
  'x11-forwarded': {
    notifications: 'limited',
    tray: 'unsupported',
    screen_capture: 'limited',
    input_synthesis: 'limited',
    window_management: 'limited',
    clipboard: 'native'
  },
  wayland: {
    notifications: 'native',
    tray: 'limited',
    screen_capture: 'unsupported',
    input_synthesis: 'unsupported',
    window_management: 'unsupported',
    clipboard: 'limited'
  },
  wslg: {
    notifications: 'native',
    tray: 'limited',
    screen_capture: 'limited',
    input_synthesis: 'limited',
    window_management: 'limited',
    clipboard: 'limited'
  },
  headless: {
    notifications: 'unsupported',
    tray: 'unsupported',
    screen_capture: 'unsupported',
    input_synthesis: 'unsupported',
    window_management: 'unsupported',
    clipboard: 'unsupported'
  }
}

const CAPABILITY_REASONS = {
  wayland: {
    screen_capture: 'wayland requires a desktop-portal capture path that is not implemented/validated',
    input_synthesis: 'wayland compositors do not allow global input synthesis',
    window_management: 'wayland exposes no global window-management protocol',
    clipboard: 'clipboard under wayland depends on compositor data-control support',
    tray: 'tray under wayland depends on the StatusNotifier/AppIndicator extension'
  },
  headless: {
    notifications: 'no display server available',
    tray: 'no display server available',
    screen_capture: 'no display server available',
    input_synthesis: 'no display server available',
    window_management: 'no display server available',
    clipboard: 'no display server available'
  },
  'x11-forwarded': {
    tray: 'system trays do not survive X11 forwarding',
    screen_capture: 'capture quality/timing degrades across forwarded X11',
    input_synthesis: 'input synthesis timing degrades across forwarded X11',
    window_management: 'window management degrades across forwarded X11',
    notifications: 'notification daemons are usually unreachable over forwarded X11'
  },
  wslg: {
    screen_capture: 'WSLg routes capture through RDP-derived surfaces; treat as degraded until validated',
    input_synthesis: 'WSLg input path is RDP-mediated; treat as degraded until validated',
    window_management: 'WSLg windows are managed by the Windows compositor',
    clipboard: 'WSLg clipboard is mediated and may drop rich formats',
    tray: 'WSLg tray integration depends on Windows-side support'
  }
}

function capabilityStatus(capability, sessionInfo) {
  if (!sessionInfo || !sessionInfo.applicable) return { level: 'native', reason: null }
  const row = CAPABILITY_MATRIX[sessionInfo.sessionType] || {}
  const level = row[capability]
  if (!level) return { level: null, reason: `unknown capability: ${capability}` }
  const reason =
    level === 'native'
      ? null
      : (CAPABILITY_REASONS[sessionInfo.sessionType] || {})[capability] || `${capability} degraded on ${sessionInfo.sessionType}`
  return { level, reason }
}

function linuxCapabilities(sessionInfo) {
  const caps = {}
  for (const capability of Object.keys(CAPABILITY_MATRIX.x11)) {
    caps[capability] = capabilityStatus(capability, sessionInfo)
  }
  return caps
}

// Structured error ONLY for genuinely unavailable capabilities ('unsupported').
// 'limited' surfaces degrade gracefully through capabilityStatus instead.
function capabilityError(capability, sessionInfo) {
  const status = capabilityStatus(capability, sessionInfo)
  if (!status.level) {
    return {
      code: 'unknown_capability',
      message: status.reason,
      details: { capability }
    }
  }
  if (status.level !== 'unsupported') return null
  return {
    code: 'capability_unavailable',
    message: `${capability} is unavailable on this Linux session`,
    details: {
      capability,
      sessionType: sessionInfo?.sessionType ?? null,
      reason: status.reason
    }
  }
}

module.exports = {
  SUPPORT_LEVELS,
  capabilityError,
  capabilityStatus,
  detectLinuxSession,
  linuxCapabilities
}
