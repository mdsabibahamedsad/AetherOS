#!/usr/bin/env node
// Master 77 §54 — deterministic release-artifact self-check.
//
// Discovers distributables in dist-packaged/, validates naming / size /
// staleness, recomputes SHA-256, and (when present) cross-checks
// docs/AETHEROS_MASTER_77_RELEASE_ARTIFACT_MANIFEST.json.
// Exit 0 = all checks pass; exit 1 = any failure. No network, no installer
// execution, no mutation.
import { createHash } from 'node:crypto'
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const DIST = join(ROOT, 'dist-packaged')
const REPO_DOCS = join(ROOT, '..', '..', 'docs')
// Master 78 §62 + Master 79.1 §19: prefer the current-phase manifest when
// present, so a fresh rebuild does not fail against a previous phase's hashes.
// Preference order: MASTER_79 → MASTER_78 → MASTER_77. Explicit
// --manifest <path> overrides. Older manifests are historical records of the
// artifacts THEY were generated against, not contracts for current outputs.
const M79_MANIFEST = join(REPO_DOCS, 'AETHEROS_MASTER_79_RELEASE_ARTIFACT_MANIFEST.json')
const M78_MANIFEST = join(REPO_DOCS, 'AETHEROS_MASTER_78_RELEASE_ARTIFACT_MANIFEST.json')
const M77_MANIFEST = join(REPO_DOCS, 'AETHEROS_MASTER_77_RELEASE_ARTIFACT_MANIFEST.json')
const manifestArg = process.argv.findIndex((a) => a === '--manifest')
const MANIFEST =
  manifestArg !== -1 && process.argv[manifestArg + 1]
    ? resolve(process.argv[manifestArg + 1])
    : existsSync(M79_MANIFEST) ? M79_MANIFEST : existsSync(M78_MANIFEST) ? M78_MANIFEST : M77_MANIFEST

const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'))
const expectedVersion = pkg.version

// AetherOS-{version}-{os}-{arch}.{ext} plus the portable + blockmap variants.
const NAME_RE =
  /^AetherOS-(?<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)-(?<os>win|linux|macOS|mac)-(x64|arm64|universal)(?<portable>-portable)?\.(?<ext>exe|msi|dmg|pkg|zip|AppImage|deb|rpm|yml|yaml|7z)(?<blockmap>\.blockmap)?$/

const failures = []
const records = []

function fail(msg) {
  failures.push(msg)
  console.error(`  FAIL: ${msg}`)
}

function sha256Of(path) {
  const h = createHash('sha256')
  h.update(readFileSync(path))
  return h.digest('hex')
}

console.log('AetherOS artifact self-check (Master 77 §54)')
console.log(`  root     : ${ROOT}`)
console.log(`  dist     : ${DIST}`)
console.log(`  version  : ${expectedVersion}`)
console.log(`  manifest : ${MANIFEST}`)

if (!existsSync(DIST)) {
  fail(`dist-packaged/ directory missing: ${DIST}`)
  process.exit(1)
}

const entries = readdirSync(DIST).filter((f) => {
  try {
    return statSync(join(DIST, f)).isFile()
  } catch {
    return false
  }
})

if (entries.length === 0) fail('dist-packaged/ contains no files')

// Internal builder byproducts that are not distributables.
const IGNORED = new Set(['builder-debug.yml', 'builder-effective-config.yaml', 'latest.yml', 'latest-mac.yml', 'latest-linux.yml'])

for (const file of entries.sort()) {
  const full = join(DIST, file)
  const st = statSync(full)
  if (IGNORED.has(file)) {
    console.log(`  skip (builder byproduct): ${file}`)
    continue
  }
  const m = file.match(NAME_RE)
  if (!m) {
    // win-unpacked/ etc. are directories; stray files get flagged.
    fail(`unexpected filename (not AetherOS-{version}-{os}-{arch}.{ext}): ${file}`)
    continue
  }
  const { version, os, portable, ext } = m.groups
  if (st.size === 0) fail(`zero-byte artifact: ${file}`)
  if (version !== expectedVersion) {
    fail(`stale artifact version ${version} != package.json ${expectedVersion}: ${file}`)
  }
  if (os === 'win' && !['exe', 'msi', 'blockmap'].includes(ext) && !portable) {
    fail(`unexpected Windows extension: ${file}`)
  }
  if (os === 'linux' && !['AppImage', 'deb', 'rpm', 'blockmap', 'yml', 'yaml'].includes(ext)) {
    fail(`unexpected Linux extension: ${file}`)
  }
  const record = { filename: file, size: st.size, sha256: sha256Of(full), mtime: st.mtime.toISOString() }
  records.push(record)
  console.log(`  ok: ${file} (${st.size} bytes, sha256 ${record.sha256.slice(0, 16)}…)`)
}

// Manifest cross-check (only when the manifest exists).
if (existsSync(MANIFEST)) {
  let manifest
  try {
    manifest = JSON.parse(readFileSync(MANIFEST, 'utf8'))
  } catch (e) {
    fail(`manifest is not valid JSON: ${e.message}`)
    manifest = null
  }
  if (manifest) {
    const listed = new Map((manifest.artifacts || []).map((a) => [a.filename, a]))
    for (const r of records) {
      const entry = listed.get(r.filename)
      if (!entry) {
        fail(`artifact missing from manifest: ${r.filename}`)
        continue
      }
      if (entry.sha256 && entry.sha256 !== r.sha256) fail(`hash mismatch for ${r.filename}`)
      if (entry.size && entry.size !== r.size) fail(`size mismatch for ${r.filename}`)
    }
    for (const name of listed.keys()) {
      if (!records.some((r) => r.filename === name) && !IGNORED.has(name)) {
        fail(`manifest lists artifact not present on disk: ${name}`)
      }
    }
    console.log(`  manifest: cross-checked ${listed.size} entries`)
  }
} else {
  console.log('  manifest: absent (skipped cross-check)')
}

// Duplicate detection: same bytes under two names.
const byHash = new Map()
for (const r of records) {
  if (!byHash.has(r.sha256)) byHash.set(r.sha256, [])
  byHash.get(r.sha256).push(r.filename)
}
for (const [h, names] of byHash) {
  if (names.length > 1) console.log(`  note: identical content shared by ${names.join(', ')} (${h.slice(0, 16)}…)`)
}

console.log(failures.length === 0 ? '\nVALID — all artifact checks passed' : `\nINVALID — ${failures.length} failure(s)`)
process.exit(failures.length === 0 ? 0 : 1)
