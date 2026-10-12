'use strict'

/**
 * Update manifest validation + rollback recorder (Master 64.1 A7) — PURE.
 *
 * No network, no installer execution. Validates update metadata objects
 * (HTTPS, hash format, version ordering, channel, publisher, schema) and
 * records pre-update snapshots for rollback decisions. Live apply/rollback
 * is UNVERIFIED here (no packaged builds, no VM).
 */

const CHANNELS = new Set(['stable', 'beta', 'nightly'])
const SHA256_RE = /^[0-9a-f]{64}$/i
const VERSION_RE = /^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/

function compareVersions(a, b) {
  const pa = String(a).split('-')[0].split('.').map(Number)
  const pb = String(b).split('-')[0].split('.').map(Number)
  for (let i = 0; i < 3; i++) {
    if (pa[i] !== pb[i]) return pa[i] < pb[i] ? -1 : 1
  }
  return 0
}

/**
 * @param {object} manifest {updateId,currentVersion,targetVersion,channel,
 *   artifactUrl,size,sha256,signature,publisher,minimumVersion,schemaVersion}
 * @param {object} opts {currentVersion, channel, expectedPublisher,
 *   supportedSchemaVersions}
 */
function validateManifest(manifest = {}, opts = {}) {
  const errors = []
  const m = manifest

  for (const f of ['updateId', 'targetVersion', 'channel', 'artifactUrl', 'sha256', 'publisher']) {
    if (!m[f]) errors.push(`missing field: ${f}`)
  }
  if (m.artifactUrl && !String(m.artifactUrl).startsWith('https://')) {
    errors.push('artifactUrl must be https')
  }
  if (m.sha256 && !SHA256_RE.test(String(m.sha256))) {
    errors.push('sha256 must be 64 hex chars')
  }
  if (m.targetVersion && !VERSION_RE.test(String(m.targetVersion))) {
    errors.push('targetVersion must be semver')
  }
  if (m.channel && !CHANNELS.has(m.channel)) {
    errors.push(`unknown channel: ${m.channel}`)
  }
  if (opts.channel && m.channel && m.channel !== opts.channel) {
    errors.push(`channel mismatch: manifest=${m.channel} expected=${opts.channel}`)
  }
  if (opts.expectedPublisher && m.publisher && m.publisher !== opts.expectedPublisher) {
    errors.push(`unknown publisher: ${m.publisher}`)
  }
  if (opts.supportedSchemaVersions && m.schemaVersion != null &&
      !opts.supportedSchemaVersions.includes(m.schemaVersion)) {
    errors.push(`unsupported schemaVersion: ${m.schemaVersion}`)
  }
  if (opts.currentVersion && m.targetVersion && VERSION_RE.test(String(m.targetVersion))) {
    const cmp = compareVersions(opts.currentVersion, m.targetVersion)
    if (cmp >= 0) errors.push('downgrade-or-equal rejected: target must exceed current')
  }
  if (m.minimumVersion && opts.currentVersion &&
      compareVersions(opts.currentVersion, m.minimumVersion) < 0) {
    errors.push('current version below manifest minimumVersion')
  }
  if (m.signature != null && String(m.signature).trim() === '') {
    errors.push('empty signature')
  }
  return { valid: errors.length === 0, errors }
}

function recordPreUpdateSnapshot({ currentVersion, stateGeneration, schemaGeneration, updateId, artifactHash }) {
  if (!currentVersion || !updateId || !artifactHash) {
    throw new Error('snapshot requires currentVersion, updateId, artifactHash')
  }
  return {
    currentVersion,
    stateGeneration: stateGeneration ?? null,
    schemaGeneration: schemaGeneration ?? null,
    updateId,
    artifactHash,
    recordedAt: new Date().toISOString(),
  }
}

function rollbackDecision({ snapshot, healthCheckPassed, userDataChangedSince }) {
  if (!snapshot) return { action: 'abort', reason: 'no snapshot' }
  if (healthCheckPassed) return { action: 'keep', reason: 'health check passed' }
  // Never blindly restore stale user data: flag for operator decision.
  return {
    action: userDataChangedSince ? 'rollback-app-only' : 'rollback',
    reason: userDataChangedSince
      ? 'reinstall previous app build; preserve newer user data for manual merge'
      : 'reinstall previous app build and restore snapshot state',
    restoreVersion: snapshot.currentVersion,
  }
}

module.exports = { validateManifest, recordPreUpdateSnapshot, rollbackDecision, compareVersions }
