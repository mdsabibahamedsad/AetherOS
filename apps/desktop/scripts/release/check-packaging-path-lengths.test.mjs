#!/usr/bin/env node
// Master 78 §46/§61 — tests for check-packaging-path-lengths.mjs.
// Run: node --test scripts/release/check-packaging-path-lengths.test.mjs
// stdlib only (node:test, node:fs, node:os, node:path). No network.
import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { scanLongPaths, owningPackage, runCheck, targetBaseFor } from './check-packaging-path-lengths.mjs'

function makeTree(files) {
  const root = mkdtempSync(join(tmpdir(), 'aetheros-pathguard-'))
  for (const rel of files) {
    const full = join(root, rel)
    mkdirSync(join(full, '..'), { recursive: true })
    writeFileSync(full, 'x')
  }
  return root
}

describe('scanLongPaths', () => {
  it('passes a tree of short paths', () => {
    const root = makeTree(['a/b.py', 'c/d/e.py'])
    try {
      const { files, offenders } = scanLongPaths([root], 200)
      assert.equal(files, 2)
      assert.equal(offenders.length, 0)
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })

  it('flags paths over budget, longest first', () => {
    const long1 = join('pkg', `${'f'.repeat(120)}.py`)
    const long2 = join('pkg', `${'g'.repeat(150)}.py`)
    const root = makeTree(['short.py', long1, long2])
    try {
      // A bare tmp scan dir has no known target mapping: rel == projected tail,
      // so with a short install prefix the projected length still exceeds 100.
      const { offenders } = scanLongPaths([root], 100)
      assert.equal(offenders.length, 2)
      assert.ok(offenders[0].projectedLength >= offenders[1].projectedLength)
      assert.ok(offenders[0].path.endsWith(long2))
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })

  it('treats checkout-prefix-only excess as a non-blocking warning (Master 79.1 §17)', () => {
    // Deep checkout root inflates the absolute path, but the projected
    // production path (install prefix + package-relative path) fits.
    const deep = join('very', 'deep', 'checkout', 'prefix', 'apps', 'desktop')
    const root = makeTree([join(deep, 'dist-packaged', 'win-unpacked', 'resources', 'ok.py')])
    try {
      const scanDir = join(root, deep, 'dist-packaged', 'win-unpacked')
      const abs = join(scanDir, 'resources', 'ok.py')
      const { offenders, absoluteWarnings } = scanLongPaths(
        [scanDir],
        abs.length - 1, // absolute is over budget by construction...
        { installPrefix: 'C:\\P\\' }, // ...but the projection fits
      )
      assert.equal(offenders.length, 0)
      assert.equal(absoluteWarnings.length, 1)
      assert.equal(absoluteWarnings[0].rel, join('resources', 'ok.py'))
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })

  it('still fails when the projected production path is over budget', () => {
    const root = makeTree([
      join('dist-packaged', 'win-unpacked', 'resources', 'py', `${'h'.repeat(220)}.py`),
    ])
    try {
      const scanDir = join(root, 'dist-packaged', 'win-unpacked')
      const { offenders } = scanLongPaths([scanDir], 200)
      assert.equal(offenders.length, 1)
      assert.ok(offenders[0].projected.startsWith('C:\\Program Files\\AetherOS\\'))
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })

  it('maps bundled-python content under resources/ (Master 79.1 §17)', () => {
    assert.equal(targetBaseFor(join('x', 'build', 'bundled-python')), 'resources/')
    assert.equal(targetBaseFor(join('x', 'dist-packaged', 'win-unpacked')), '')
    assert.equal(targetBaseFor(join('x', 'dist-packaged', '__msi-x64')), null)
  })

  it('tolerates a missing directory', () => {
    const { files, offenders } = scanLongPaths([join(tmpdir(), 'aetheros-pathguard-absent-xyz')], 10)
    assert.equal(files, 0)
    assert.equal(offenders.length, 0)
  })
})

describe('owningPackage', () => {
  it('extracts the site-packages owner', () => {
    assert.equal(
      owningPackage('D:\\x\\Lib\\site-packages\\elevenlabs\\types\\foo.py'),
      'elevenlabs',
    )
    assert.equal(owningPackage('/no/site/here.py'), 'unknown')
  })
})

describe('runCheck', () => {
  it('fails closed when no scan dirs exist', () => {
    const root = mkdtempSync(join(tmpdir(), 'aetheros-pathguard-'))
    try {
      const r = runCheck({ root, maxSafeLength: 200, dirs: ['nope'], warnOnly: false })
      assert.equal(r.ok, false)
      assert.match(r.error, /Run 'npm run build' first/)
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })

  it('reports offenders against a real staged-looking tree', () => {
    const root = mkdtempSync(join(tmpdir(), 'aetheros-pathguard-'))
    try {
      const staged = join(root, 'build', 'bundled-python')
      mkdirSync(join(staged, 'Lib', 'site-packages', 'elevenlabs'), { recursive: true })
      writeFileSync(join(staged, 'ok.py'), 'x')
      writeFileSync(join(staged, 'Lib', 'site-packages', 'elevenlabs', `${'h'.repeat(220)}.py`), 'x')
      const r = runCheck({ root, maxSafeLength: 200, dirs: ['build/bundled-python'], warnOnly: false })
      assert.equal(r.ok, false)
      assert.equal(r.offenders.length, 1)
      assert.equal(owningPackage(r.offenders[0].path), 'elevenlabs')
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })
})
