// Product-identity regression guard (node:test — run via `npm run test:desktop:platforms`
// or `node --test electron/branding.test.cjs`).
//
// Locks the user-facing installer/application identity to AetherOS while
// pinning the stability invariants: appId, updater-relevant flags, and the
// legally-required MIT attribution MUST NOT drift with cosmetic changes.
const { test } = require('node:test')
const assert = require('node:assert/strict')
const { existsSync, readFileSync } = require('node:fs')
const { join } = require('node:path')

const ROOT = join(__dirname, '..')
const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'))
const build = pkg.build ?? {}

test('product identity is AetherOS everywhere user-facing', () => {
  assert.equal(build.productName, 'AetherOS')
  assert.equal(build.executableName, 'AetherOS')
  assert.equal(pkg.author, 'AetherOS')
  assert.match(build.artifactName, /^AetherOS-/)
  assert.equal(build.nsis?.shortcutName, 'AetherOS')
  assert.match(build.nsis?.uninstallDisplayName ?? '', /^AetherOS /)
  assert.equal(build.win?.legalTrademarks, 'AetherOS')
})

test('copyright metadata names the AetherOS owner (embedded in exe + installer)', () => {
  assert.equal(build.copyright, 'Copyright (c) 2026 AetherOS')
})

test('appId and update identity are stable (never change for cosmetics)', () => {
  assert.equal(build.appId, 'com.aetheros.aetheros')
  assert.equal(build.nsis?.guid, '{1A2B3C4D-5E6F-7A8B-9C0D-1E2F3A4B5C6D}')
  assert.equal(build.msi?.upgradeCode, '{5A6B7C8D-9E0F-1A2B-3C4D-5E6F7A8B9C0D}')
})

test('unsigned builds do not fabricate a publisher', () => {
  assert.equal(build.win?.signAndEditExecutable, false)
  assert.equal(build.win?.verifyUpdateCodeSignature, false)
  assert.equal(build.win?.publisherName, undefined)
})

test('canonical icons exist for every packaging target', () => {
  assert.ok(existsSync(join(ROOT, 'assets', 'icon.ico')), 'windows icon')
  assert.ok(existsSync(join(ROOT, 'assets', 'icon.icns')), 'macOS icon')
  assert.ok(existsSync(join(ROOT, 'assets', 'icon.png')), 'linux icon')
})

test('installer license presents AetherOS only (no upstream line)', () => {
  const license = readFileSync(join(ROOT, 'build', 'installer', 'license.txt'), 'utf8')
  assert.match(license, /MIT License/)
  assert.match(license, /AetherOS/)
  assert.match(license, /Copyright \(c\) 2026 AetherOS/)
  // The upstream copyright line MUST NOT appear in the installer-facing
  // License Agreement presentation.
  assert.doesNotMatch(license, /Copyright \(c\) 2025 Nous Research/)
  assert.doesNotMatch(license, /Nous Research/)
})

test('repo-canonical LICENSE retains upstream MIT attribution', () => {
  const canonical = readFileSync(join(ROOT, '..', '..', 'LICENSE'), 'utf8')
  assert.match(canonical, /MIT License/)
  assert.match(canonical, /Copyright \(c\) 2025 Nous Research/)
})

test('installer license matches the tracked installer presentation source', () => {
  const staged = readFileSync(join(ROOT, 'build', 'installer', 'license.txt'), 'utf8')
  const source = readFileSync(join(ROOT, 'assets', 'installer-license.txt'), 'utf8')
  assert.equal(staged, source)
})
