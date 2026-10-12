#!/usr/bin/env node
// Master 78 §46 — packaging path-length early-fail guard.
//
// WiX light (v3 toolchain used by electron-builder for the MSI target) fails with an
// obscure LGHT0103 error when any staged file path reaches Windows MAX_PATH (260).
// The bundled Python tree (build/bundled-python/py) contains auto-generated SDK stubs
// (elevenlabs, mistralai) whose filenames alone exceed 130 chars, so a long checkout
// prefix pushes absolute staged paths over the limit.
//
// This script fails EARLY with an actionable error (offending path, length, budget,
// owning package, remediation) instead of letting WiX die obscurely minutes later.
// It changes NOTHING about the runtime: no files are renamed, moved, or deleted.
//
// Usage:
//   node scripts/release/check-packaging-path-lengths.mjs [--root <dir>] [--max <n>]
//   [--dirs <d1,d2>] [--install-prefix <prefix>] [--warn-only] [--strict]
//
// Exit 0 = every scanned path is within budget. Exit 1 = over budget (or scan root
// missing and --warn-only not set).
import { readdirSync, statSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve, relative, sep } from 'node:path'

const DEFAULT_MAX_SAFE_LENGTH = 240
// Default production install prefix for projection. NSIS is perMachine, so the
// real on-disk target is %PROGRAMFILES%\AetherOS\... (see build.nsis in
// package.json). Override with --install-prefix when the contract changes.
const DEFAULT_INSTALL_PREFIX = 'C:\\Program Files\\AetherOS\\'
// Absolute-path headroom rationale: WiX v3 light.exe fails at MAX_PATH 260 on the
// harvested absolute source paths. Master 79.1 §17 verdict: the absolute length
// conflates TWO things — (A) the genuine production path and (B) the
// development checkout prefix. Evidence: the 2026-09-15 MSI built SUCCESSFULLY
// from a checkout where absolute staged paths reached 262 chars, so
// absolute > 240 is NOT a reliable failure predictor for the current
// electron-builder staging. The guard therefore evaluates the PROJECTED
// production path (install prefix + package-relative path) as the blocking
// check, and reports absolute-only excess as a non-blocking build-environment
// warning. The one exception is dist-packaged/__msi-x64: that directory IS the
// WiX staging input, so its absolute paths are evaluated as-is.

// Maps a scan dir (absolute) to the path segment its content occupies on the
// TARGET machine, relative to the install prefix. Returns null when the scan
// dir is itself a tool-staging path (WiX __msi-x64) whose absolute length is
// the production-relevant one.
export function targetBaseFor(scanDir) {
  const norm = resolve(scanDir).split(sep).join('/')
  if (norm.endsWith('dist-packaged/__msi-x64')) return null
  // build/bundled-python/{py,backend}/... is packed as resources/{py,backend}/
  // (see build.extraResources in package.json).
  if (norm.endsWith('build/bundled-python')) return 'resources/'
  return ''
}

export function scanLongPaths(scanDirs, maxSafeLength, opts = {}) {
  const installPrefix = opts.installPrefix || DEFAULT_INSTALL_PREFIX
  const offenders = []
  const absoluteWarnings = []
  let files = 0
  const normPrefix = installPrefix.endsWith('\\') || installPrefix.endsWith('/')
    ? installPrefix
    : `${installPrefix}\\`
  for (const scanDir of scanDirs) {
    const base = targetBaseFor(scanDir)
    const walk = (dir) => {
      let entries
      try {
        entries = readdirSync(dir, { withFileTypes: true })
      } catch {
        return
      }
      for (const entry of entries) {
        const full = join(dir, entry.name)
        if (entry.isDirectory()) {
          walk(full)
        } else if (entry.isFile()) {
          files += 1
          const abs = resolve(full)
          const rel = relative(resolve(scanDir), abs)
          // Staging inputs are evaluated by projected production path; WiX
          // staging itself is evaluated by absolute path.
          const projected = base === null ? abs : `${normPrefix}${base}${rel.split(sep).join('\\')}`
          const record = {
            path: abs,
            length: abs.length,
            rel,
            projected,
            projectedLength: projected.length,
          }
          if (record.projectedLength > maxSafeLength) {
            offenders.push(record)
          } else if (abs.length > maxSafeLength) {
            absoluteWarnings.push(record)
          }
        }
      }
    }
    walk(scanDir)
  }
  offenders.sort((a, b) => b.projectedLength - a.projectedLength)
  absoluteWarnings.sort((a, b) => b.length - a.length)
  return { files, offenders, absoluteWarnings }
}

export function owningPackage(absPath) {
  const m = absPath.match(/[\\/]site-packages[\\/]([^\\/]+)/)
  // NOTE: keep the regex simple and dependency-free on purpose.
  if (!m) return 'unknown'
  return m[1]
}

function parseArgs(argv) {
  const out = {}
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--root' && argv[i + 1]) out.root = argv[i + 1]
    if (argv[i] === '--max' && argv[i + 1]) out.max = Number.parseInt(argv[i + 1], 10)
    if (argv[i] === '--dirs' && argv[i + 1]) out.dirs = argv[i + 1].split(',')
    if (argv[i] === '--install-prefix' && argv[i + 1]) out.installPrefix = argv[i + 1]
    if (argv[i] === '--warn-only') out.warnOnly = true
    if (argv[i] === '--strict') out.strict = true
  }
  return out
}

export function runCheck({ root, maxSafeLength, dirs, warnOnly, strict, installPrefix } = {}) {
  const scanDirs = dirs.map((d) => join(root, d)).filter((d) => existsSync(d))
  const missing = dirs.filter((d) => !existsSync(join(root, d)))
  if (scanDirs.length === 0) {
    const msg = `no scan directories exist under ${root} (expected: ${dirs.join(', ')}). Run 'npm run build' first.`
    return { ok: Boolean(warnOnly), files: 0, offenders: [], absoluteWarnings: [], error: msg }
  }
  const { files, offenders, absoluteWarnings } = scanLongPaths(scanDirs, maxSafeLength, { installPrefix })
  const blocking = strict ? offenders.concat(absoluteWarnings.map((w) => ({ ...w, strict: true }))) : offenders
  return { ok: blocking.length === 0, files, offenders: blocking, absoluteWarnings, missing }
}

function main() {
  const here = dirname(fileURLToPath(import.meta.url))
  const desktopRoot = join(here, '..', '..')
  const args = parseArgs(process.argv.slice(2))
  const root = args.root ? resolve(args.root) : desktopRoot
  const maxSafeLength = args.max || DEFAULT_MAX_SAFE_LENGTH
  const dirs = args.dirs || ['build/bundled-python', 'dist-packaged/win-unpacked', 'dist-packaged/__msi-x64']
  const warnOnly = Boolean(args.warnOnly)

  console.log('AetherOS packaging path-length guard (Master 78 §46, Master 79.1 §17)')
  console.log(`  root           : ${root}`)
  console.log(`  maxSafeLength  : ${maxSafeLength}`)
  console.log(`  installPrefix  : ${args.installPrefix || DEFAULT_INSTALL_PREFIX}`)
  console.log(`  strict         : ${Boolean(args.strict)} (strict also fails on absolute-only excess)`)

  const result = runCheck({ root, maxSafeLength, dirs, warnOnly, strict: args.strict, installPrefix: args.installPrefix })
  if (result.missing && result.missing.length > 0) {
    console.log(`  note: absent scan dirs (skipped): ${result.missing.join(', ')}`)
  }
  if (result.error && result.files === 0 && result.offenders.length === 0) {
    console.log(`  ${result.ok ? 'WARN' : 'FAIL'}: ${result.error}`)
    process.exit(result.ok ? 0 : 1)
  }
  console.log(`  files scanned  : ${result.files}`)
  if (result.absoluteWarnings && result.absoluteWarnings.length > 0) {
    console.log(`  note: ${result.absoluteWarnings.length} absolute-only path(s) exceed ${maxSafeLength} chars but fit the projected production path (checkout-prefix effect; non-blocking):`)
    for (const o of result.absoluteWarnings.slice(0, 10)) {
      console.log(`    ABS=${o.length} PROJ=${o.projectedLength} PACKAGE=${owningPackage(o.path)}`)
      console.log(`      ${o.path}`)
    }
  }
  if (result.ok) {
    console.log(`\nVALID — all ${result.files} projected production paths are within ${maxSafeLength} chars`)
    process.exit(0)
  }
  console.error(`\nFAIL — ${result.offenders.length} projected production path(s) exceed MAX_SAFE_LENGTH=${maxSafeLength}:`)
  for (const o of result.offenders.slice(0, 25)) {
    console.error(`  OFFENDING_PATH=${o.path}`)
    console.error(`    LENGTH=${o.length} PROJECTED=${o.projected}`)
    console.error(`    PROJECTED_LENGTH=${o.projectedLength} MAX_SAFE_LENGTH=${maxSafeLength} PACKAGE=${owningPackage(o.path)}`)
  }
  if (result.offenders.length > 25) {
    console.error(`  ... and ${result.offenders.length - 25} more`)
  }
  console.error('  REMEDIATION: rebuild from a shorter checkout path, e.g.')
  console.error('    subst X: <desktop-root>  (then run the MSI build from X:\\)')
  console.error('  Do NOT delete or rename vendored site-packages files: they are imported at runtime')
  console.error('  (elevenlabs eagerly imports its types/ tree; renaming breaks package integrity).')
  process.exit(warnOnly ? 0 : 1)
}

const invokedDirectly = process.argv[1] === fileURLToPath(import.meta.url)
if (invokedDirectly) main()
