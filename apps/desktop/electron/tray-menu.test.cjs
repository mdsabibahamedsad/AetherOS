'use strict'

const assert = require('node:assert/strict')
const test = require('node:test')

const { ACTIONS, buildTrayMenu } = require('./tray-menu.cjs')

test('menu exposes the nine required actions on typed channels', () => {
  const ids = ACTIONS.map(a => a.id)
  for (const id of ['open', 'pause', 'resume', 'stop-agents', 'approvals', 'agents', 'security', 'update', 'quit']) {
    assert.ok(ids.includes(id), id)
  }
  for (const a of ACTIONS) {
    assert.match(a.channel, /^aetheros:[a-z-]+$/, a.id)
  }
})

test('backend-down disables backend actions but keeps open/quit', () => {
  const { items } = buildTrayMenu({ backendUp: false })
  const byId = Object.fromEntries(items.map(i => [i.id, i]))
  assert.equal(byId.open.enabled, true)
  assert.equal(byId.quit.enabled, true)
  assert.equal(byId.pause.enabled, false)
  assert.equal(byId['stop-agents'].enabled, false)
})

test('tooltip and badges reflect live counts, never fabricated', () => {
  const { tooltip, items } = buildTrayMenu({ backendUp: true, agentsActive: 2, approvalsPending: 3 })
  assert.match(tooltip, /2 agents active/)
  assert.match(tooltip, /3 approvals pending/)
  const byId = Object.fromEntries(items.map(i => [i.id, i]))
  assert.match(byId.approvals.label, /\(3\)/)
  assert.match(byId.agents.label, /\(2 active\)/)
})

test('pause/resume are mutually exclusive per automationsPaused', () => {
  const paused = buildTrayMenu({ backendUp: true, automationsPaused: true })
  const running = buildTrayMenu({ backendUp: true, automationsPaused: false })
  const p = Object.fromEntries(paused.items.map(i => [i.id, i]))
  const r = Object.fromEntries(running.items.map(i => [i.id, i]))
  assert.equal(p.pause.enabled, false)
  assert.equal(p.resume.enabled, true)
  assert.equal(r.pause.enabled, true)
  assert.equal(r.resume.enabled, false)
})

test('stop-all is confirm-gated; update surfaces availability', () => {
  const { tooltip, items } = buildTrayMenu({ backendUp: true, updateAvailable: true, securityOk: false })
  const byId = Object.fromEntries(items.map(i => [i.id, i]))
  assert.equal(byId['stop-agents'].confirm, true)
  assert.match(tooltip, /update available/)
  assert.match(tooltip, /security attention needed/)
})

test('empty state is honest, not zero-filled noise', () => {
  const { tooltip } = buildTrayMenu({ backendUp: true })
  assert.equal(tooltip, 'AetherOS')
})
