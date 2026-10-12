'use strict'

/**
 * AetherOS tray menu builder (Master 64.1 A3) — PURE, no Electron import.
 *
 * Builds the tray context-menu template from live backend state. The live
 * tray itself (electron/tray.cjs) is UNVERIFIED here (no Electron binary);
 * this template logic is unit-tested and reflects real state only.
 *
 * Every action maps to a typed `aetheros:*` IPC channel consumed by the
 * existing UI command layer. No arbitrary commands, no privileged
 * operation without policy (stop-all is confirm-gated by the consumer).
 */

const ACTIONS = [
  { id: 'open', label: 'Open AetherOS', channel: 'aetheros:window-show' },
  { id: 'pause', label: 'Pause automations', channel: 'aetheros:automation-pause', needsBackend: true },
  { id: 'resume', label: 'Resume automations', channel: 'aetheros:automation-resume', needsBackend: true },
  { id: 'stop-agents', label: 'Stop active agents', channel: 'aetheros:agents-stop-all', confirm: true, needsBackend: true },
  { id: 'approvals', label: 'View pending approvals', channel: 'aetheros:approvals-open', badge: 'approvalsPending' },
  { id: 'agents', label: 'View agent state', channel: 'aetheros:agents-open', badge: 'agentsActive' },
  { id: 'security', label: 'Open security center', channel: 'aetheros:security-open' },
  { id: 'update', label: 'Check for updates', channel: 'aetheros:update-check' },
  { id: 'quit', label: 'Quit AetherOS', channel: 'aetheros:app-quit' },
]

/**
 * @param {object} state live backend snapshot:
 *   { backendUp, automationsPaused, agentsActive, approvalsPending,
 *     updateAvailable, securityOk }
 */
function buildTrayMenu(state = {}) {
  const s = {
    backendUp: false,
    automationsPaused: false,
    agentsActive: 0,
    approvalsPending: 0,
    updateAvailable: false,
    securityOk: true,
    ...state,
  }

  const items = ACTIONS.map(a => {
    const item = { id: a.id, label: a.label, channel: a.channel, enabled: true }
    if (a.confirm) item.confirm = true
    if (a.needsBackend && !s.backendUp) item.enabled = false
    if (a.badge === 'approvalsPending' && s.approvalsPending > 0) {
      item.label = `View pending approvals (${s.approvalsPending})`
    }
    if (a.badge === 'agentsActive' && s.agentsActive > 0) {
      item.label = `View agent state (${s.agentsActive} active)`
    }
    if (a.id === 'pause' && s.automationsPaused) item.enabled = false
    if (a.id === 'resume' && !s.automationsPaused) item.enabled = false
    return item
  })

  const tooltip = !s.backendUp
    ? 'AetherOS (backend unavailable)'
    : [
        'AetherOS',
        s.agentsActive > 0 ? `${s.agentsActive} agent${s.agentsActive === 1 ? '' : 's'} active` : null,
        s.approvalsPending > 0 ? `${s.approvalsPending} approval${s.approvalsPending === 1 ? '' : 's'} pending` : null,
        s.updateAvailable ? 'update available' : null,
        !s.securityOk ? 'security attention needed' : null,
      ].filter(Boolean).join(' · ')

  return { tooltip, items }
}

module.exports = { ACTIONS, buildTrayMenu }
