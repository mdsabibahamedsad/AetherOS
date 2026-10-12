#!/usr/bin/env node
// Static validation of the Linux packaging configuration.
//
// Runs on ANY host OS (including CI on Windows/macOS) and proves the
// electron-builder Linux config is coherent BEFORE a native Linux runner
// attempts packaging. It does NOT produce artifacts — AppImage/deb/rpm need a
// native Linux build environment (see .github/workflows/desktop-release.yml).
//
// Exit 0 = valid; exit 1 = invalid with reasons printed.
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const pkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'))
const build = pkg.build || {}
const linux = build.linux

const problems = []
const ok = (cond, msg) => {
  if (!cond) problems.push(msg)
}

ok(linux && typeof linux === 'object', 'build.linux section missing from package.json')

const targets = Array.isArray(linux?.target)
  ? linux.target.map((t) => (typeof t === 'string' ? t : t.target))
  : [linux?.target].filter(Boolean)
ok(targets.length > 0, 'no Linux targets configured')
for (const t of targets) {
  ok(['AppImage', 'deb', 'rpm', 'tar.gz', 'snap', 'flatpak', 'dir'].includes(t), `unknown Linux target: ${t}`)
}

// Arch declarations must be x64/arm64 only (electron-builder supported set).
const archsOk = (Array.isArray(linux?.target) ? linux.target : []).every(
  (t) => typeof t === 'string' || !Array.isArray(t.arch) || t.arch.every((a) => ['x64', 'arm64', 'armv7l', 'universal'].includes(a))
)
ok(archsOk, 'unsupported architecture in build.linux.target')

// Icons must exist on disk; Linux needs PNG (not .ico).
const icon = linux?.icon ? join(root, linux.icon) : null
if (icon) {
  const png = icon.endsWith('.png') ? icon : `${icon}.png`
  ok(existsSync(png), `Linux icon missing on disk: ${png}`)
} else {
  ok(build.icon && existsSync(join(root, `${build.icon}.png`)), 'no usable icon for Linux target')
}

// artifactName template may only use known electron-builder tokens.
const KNOWN_TOKENS = new Set(['${version}', '${os}', '${arch}', '${ext}', '${name}', '${productName}', '${shortVersion}'])
const template = linux?.artifactName || build.artifactName
if (template) {
  for (const token of template.match(/\$\{[^}]+\}/g) || []) {
    ok(KNOWN_TOKENS.has(token), `unknown placeholder ${token} in Linux artifactName`)
  }
} else {
  problems.push('no artifactName template for Linux artifacts')
}

// Executable name must be filesystem-safe lowercase for Linux conventions.
ok(/^[a-z0-9-_]+$/.test(linux.executableName || ''), 'linux.executableName must be lowercase kebab/snake')
ok(Boolean(linux?.maintainer), 'deb/rpm require build.linux.maintainer')
ok(Boolean(linux?.synopsis && linux?.description), 'deb/rpm require synopsis + description')
ok(Boolean(linux?.category), 'desktop entry requires a category')
// Master 78: FpmTarget (deb/rpm) hard-fails without a project homepage
// ("Please specify project homepage"). Caught here in seconds on any host
// instead of minutes into a Linux packaging run.
ok(Boolean(pkg.homepage && String(pkg.homepage).startsWith('http')),
  'deb/rpm require top-level "homepage" in apps/desktop/package.json')
// Master 78: CI existence globs (desktop-release.yml) and the artifact
// validator (validate-artifacts.mjs, x64|arm64|universal) both assume the
// Linux artifactName hardcodes the arch as -linux-x64- (electron-builder
// would otherwise emit -x86_64/-amd64 per target and CI would fail closed).
// ARM64 is NOT_IMPLEMENTED; adding it requires per-target artifactNames.
ok((linux?.artifactName || '').includes('-linux-x64.'),
  'Linux artifactName must hardcode -linux-x64- (CI globs + validator contract)')

console.log('AetherOS Linux packaging static validation')
console.log(`  targets      : ${targets.join(', ')}`)
console.log(`  artifactName : ${template}`)
console.log(`  executable   : ${linux?.executableName}`)
if (problems.length > 0) {
  console.error('\nFAIL:')
  for (const p of problems) console.error(`  - ${p}`)
  process.exit(1)
}
console.log('\nVALID — native artifact production still requires a Linux runner')
console.log('(.github/workflows/desktop-release.yml, ubuntu-latest job).')
