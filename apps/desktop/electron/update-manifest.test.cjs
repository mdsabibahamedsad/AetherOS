'use strict'

const assert = require('node:assert/strict')
const test = require('node:test')

const { validateManifest, recordPreUpdateSnapshot, rollbackDecision } = require('./update-manifest.cjs')

const GOOD = {
  updateId: 'u-123',
  currentVersion: '1.0.0',
  targetVersion: '1.1.0',
  channel: 'stable',
  artifactUrl: 'https://releases.example.com/AetherOS-1.1.0-win-x64.exe',
  size: 123456,
  sha256: 'a'.repeat(64),
  signature: 'sig-blob',
  publisher: 'AetherOS',
  minimumVersion: '1.0.0',
  schemaVersion: 1,
}

const OPTS = { currentVersion: '1.0.0', channel: 'stable', expectedPublisher: 'AetherOS', supportedSchemaVersions: [1] }

test('valid manifest passes', () => {
  const r = validateManifest(GOOD, OPTS)
  assert.equal(r.valid, true)
  assert.deepEqual(r.errors, [])
})

test('rejects http, bad hash, unknown publisher, channel mismatch', () => {
  let r = validateManifest({ ...GOOD, artifactUrl: 'http://x/y.exe' }, OPTS)
  assert.ok(!r.valid && r.errors.some(e => e.includes('https')))
  r = validateManifest({ ...GOOD, sha256: 'zzz' }, OPTS)
  assert.ok(r.errors.some(e => e.includes('sha256')))
  r = validateManifest({ ...GOOD, publisher: 'EvilCorp' }, OPTS)
  assert.ok(r.errors.some(e => e.includes('publisher')))
  r = validateManifest({ ...GOOD, channel: 'beta' }, OPTS)
  assert.ok(r.errors.some(e => e.includes('channel mismatch')))
})

test('downgrade and equal versions rejected; minimum enforced', () => {
  assert.ok(!validateManifest({ ...GOOD, targetVersion: '0.9.0' }, OPTS).valid)
  assert.ok(!validateManifest({ ...GOOD, targetVersion: '1.0.0' }, OPTS).valid)
  assert.ok(!validateManifest({ ...GOOD, minimumVersion: '2.0.0' }, OPTS).valid)
})

test('missing fields and empty signature reported', () => {
  const r = validateManifest({ targetVersion: '1.1.0' }, OPTS)
  assert.ok(!r.valid && r.errors.length >= 4)
  const r2 = validateManifest({ ...GOOD, signature: '  ' }, OPTS)
  assert.ok(r2.errors.some(e => e.includes('signature')))
})

test('snapshot requires identity fields', () => {
  assert.throws(() => recordPreUpdateSnapshot({}), /requires/)
  const s = recordPreUpdateSnapshot({ currentVersion: '1.0.0', updateId: 'u-1', artifactHash: 'b'.repeat(64) })
  assert.equal(s.currentVersion, '1.0.0')
  assert.ok(s.recordedAt)
})

test('rollback never blindly restores newer user data', () => {
  const s = recordPreUpdateSnapshot({ currentVersion: '1.0.0', updateId: 'u-1', artifactHash: 'b'.repeat(64) })
  assert.deepEqual(rollbackDecision({ snapshot: null }).action, 'abort')
  assert.deepEqual(rollbackDecision({ snapshot: s, healthCheckPassed: true }).action, 'keep')
  const r = rollbackDecision({ snapshot: s, healthCheckPassed: false, userDataChangedSince: true })
  assert.equal(r.action, 'rollback-app-only')
  assert.match(r.reason, /preserve newer user data/)
  const r2 = rollbackDecision({ snapshot: s, healthCheckPassed: false, userDataChangedSince: false })
  assert.equal(r2.action, 'rollback')
})
