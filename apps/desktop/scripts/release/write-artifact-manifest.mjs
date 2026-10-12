#!/usr/bin/env node
// Master 78 §30/§72 — deterministic artifact manifest + checksum writer.
//
// Enumerates distributables in dist-packaged/, recomputes size + SHA-256,
// binds each artifact to the source commit (via build/install-stamp.json,
// cross-checked against `git rev-parse HEAD`), and writes:
//   docs/AETHEROS_<TAG>_ARTIFACT_CHECKSUMS.txt
//   docs/AETHEROS_<TAG>_RELEASE_ARTIFACT_MANIFEST.json
// where <TAG> defaults to MASTER_78 (historical name; override per release
// phase with --tag, e.g. `--tag MASTER_79`). Master 79.1 §19: each release
// phase records its OWN manifest so validation compares current outputs
// against the current manifest instead of failing against a previous phase.
// Historical manifests are never overwritten: a new --tag creates new files.
//
// No artifact is listed as HEAD_BOUND unless the install stamp commit
// equals the current git HEAD. A dirty working tree is recorded honestly
// (LOCAL_SOURCE_BINDING, never ATTESTED). Exit 0 on success, 1 on failure.
// No network, no installer execution, no mutation of dist-packaged/.
import { createHash } from 'node:crypto'
import { execSync } from 'node:child_process'
import { readdirSync, readFileSync, statSync, existsSync, writeFileSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const REPO = join(ROOT, '..', '..')
const DIST = join(ROOT, 'dist-packaged')
const DOCS = join(REPO, 'docs')
const STAMP = join(ROOT, 'build', 'install-stamp.json')
const PKG = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'))

const NAME_RE =
  /^AetherOS-(?<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)-(?<os>win|linux|macOS|mac)-(x64|arm64|universal)(?<portable>-portable)?\.(?<ext>exe|msi|dmg|pkg|zip|AppImage|deb|rpm|yml|yaml|7z)(?<blockmap>\.blockmap)?$/

const IGNORED = new Set(['builder-debug.yml', 'builder-effective-config.yaml', 'latest.yml', 'latest-mac.yml', 'latest-linux.yml'])

function sha256Of(path) {
  const h = createHash('sha256')
  h.update(readFileSync(path))
  return h.digest('hex')
}

function gitHead() {
  try {
    return execSync('git rev-parse HEAD', { cwd: REPO, encoding: 'utf8' }).trim()
  } catch {
    return null
  }
}

function artifactType(os, ext, portable, blockmap) {
  if (blockmap) return 'blockmap'
  if (portable) return 'portable'
  if (ext === 'exe') return 'nsis'
  return ext.toLowerCase()
}

const failures = []
if (!existsSync(DIST)) {
  console.error(`FAIL: dist-packaged/ missing: ${DIST}`)
  process.exit(1)
}

const stamp = existsSync(STAMP) ? JSON.parse(readFileSync(STAMP, 'utf8')) : null
const head = gitHead()
const stampCommit = stamp?.commit ?? null
const headBound = Boolean(stampCommit && head && stampCommit === head)

console.log('AetherOS artifact manifest writer (Master 78 §30/§72)')
console.log(`  version    : ${PKG.version}`)
console.log(`  git HEAD   : ${head ?? 'UNKNOWN (no git)'}`)
console.log(`  stamp commit: ${stampCommit ?? 'ABSENT'}${stamp ? ` (dirty=${stamp.dirty}, builtAt=${stamp.builtAt})` : ''}`)
console.log(`  head-bound : ${headBound ? 'YES (LOCAL_SOURCE_BINDING)' : 'NO'}`)

const entries = readdirSync(DIST)
  .filter((f) => { try { return statSync(join(DIST, f)).isFile() } catch { return false } })
  .filter((f) => !IGNORED.has(f))
  .sort()

const artifacts = []
for (const file of entries) {
  const m = file.match(NAME_RE)
  if (!m) {
    failures.push(`unexpected filename (not AetherOS-{version}-{os}-{arch}.{ext}): ${file}`)
    continue
  }
  const { version, os, portable, ext, blockmap } = m.groups
  const full = join(DIST, file)
  const st = statSync(full)
  if (version !== PKG.version) failures.push(`stale version ${version} != ${PKG.version}: ${file}`)
  if (st.size === 0) failures.push(`zero-byte artifact: ${file}`)
  const platform = os === 'macOS' ? 'mac' : os
  const arch = m[0].match(/-(x64|arm64|universal)(?:-portable)?\./)[1]
  artifacts.push({
    platform,
    architecture: arch,
    type: artifactType(os, ext, portable, blockmap),
    filename: file,
    size: st.size,
    sha256: sha256Of(full),
    sourceCommit: stampCommit,
    status: headBound ? 'HEAD_BOUND' : 'NON_HEAD_BOUND',
  })
  console.log(`  ok: ${file} (${st.size} bytes)`)
}

if (failures.length > 0) {
  for (const f of failures) console.error(`  FAIL: ${f}`)
  process.exit(1)
}
if (artifacts.length === 0) {
  console.error('FAIL: no distributable artifacts found in dist-packaged/')
  process.exit(1)
}

const manifest = {
  product: 'AetherOS',
  version: PKG.version,
  sourceCommit: stampCommit,
  gitHead: head,
  headBound,
  workingTreeDirty: stamp?.dirty ?? null,
  stampBuiltAt: stamp?.builtAt ?? null,
  generatedAt: new Date().toISOString(),
  binding: headBound ? 'LOCAL_SOURCE_BINDING_VERIFIED' : 'UNVERIFIED',
  artifacts,
}

mkdirSync(DOCS, { recursive: true })
// Master 79.1 §19: --tag selects the manifest generation (validated shape
// MASTER_##); default preserves the historical Master 78 filenames.
const tagArg = process.argv.findIndex((a) => a === '--tag')
const tag = tagArg !== -1 && process.argv[tagArg + 1] ? process.argv[tagArg + 1] : 'MASTER_78'
if (!/^MASTER_[0-9]+[A-Z0-9.]*$/.test(tag)) {
  console.error(`FAIL: --tag must look like MASTER_79 (got: ${tag})`)
  process.exit(1)
}
const manifestPath = join(DOCS, `AETHEROS_${tag}_RELEASE_ARTIFACT_MANIFEST.json`)
const checksumsPath = join(DOCS, `AETHEROS_${tag}_ARTIFACT_CHECKSUMS.txt`)
writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n')
writeFileSync(
  checksumsPath,
  artifacts.map((a) => `${a.sha256}  ${a.filename}`).join('\n') + '\n',
)
console.log(`\nwrote ${manifestPath} (${artifacts.length} artifacts)`)
console.log(`wrote ${checksumsPath}`)
