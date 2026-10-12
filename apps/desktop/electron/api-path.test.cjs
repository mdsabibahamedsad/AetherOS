/**
 * Tests for validateApiRequestPath (hardening.cjs).
 *
 * The generic `aetheros:api` bridge concatenates request.path onto the
 * backend base URL, so renderer-supplied paths must be same-host
 * references. Run with: node --test electron/api-path.test.cjs
 */

const test = require('node:test')
const assert = require('node:assert/strict')

const { validateApiRequestPath } = require('./hardening.cjs')

test('accepts ordinary backend routes', () => {
  assert.equal(validateApiRequestPath('/api/status'), '/api/status')
  assert.equal(
    validateApiRequestPath('/api/sessions/abc123/messages?profile=default'),
    '/api/sessions/abc123/messages?profile=default'
  )
})

test('accepts known action shorthands for backward compatibility', () => {
  for (const token of ['screen.analyze', 'screen.explain', 'screen.ocr', 'ocr.perform', 'ocr.languages']) {
    assert.equal(validateApiRequestPath(token), token)
  }
})

test('rejects absolute and protocol-relative URLs', () => {
  for (const bad of ['http://evil.example/x', 'https://127.0.0.1:9/api/status', '//evil.example/api', 'ftp://x/y']) {
    assert.throws(() => validateApiRequestPath(bad), /Invalid request\.path/)
  }
})

test('rejects traversal, backslashes, and control characters', () => {
  for (const bad of ['/api/../secret', '/api/sessions/..', '/api\\sessions', '/api/x\x00y', '/api/x\x1fy']) {
    assert.throws(() => validateApiRequestPath(bad), /Invalid request\.path/)
  }
})

test('rejects non-strings and relative paths', () => {
  for (const bad of [undefined, null, 42, {}, '', 'api/status', 'screen..analyze']) {
    assert.throws(() => validateApiRequestPath(bad), /Invalid request\.path/)
  }
})
