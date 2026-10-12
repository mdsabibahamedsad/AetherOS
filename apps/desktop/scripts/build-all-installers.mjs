#!/usr/bin/env node

/**
 * RETIRED (Master 80 §67) — this legacy multi-platform builder is superseded by
 * the ONE canonical Windows release path:
 *   npm run desktop:release:windows   (from apps/desktop)
 * It wrote to release/ (a second competing output dir), used `npx` instead of
 * repo-local tooling, and had no preflight/identity/manifest gates, which caused
 * the stale-artifact loops of Masters 77–79. Kept in history; refuses to run.
 */
console.error(
  "RETIRED: build-all-installers.mjs is superseded by the canonical contract.\n" +
  "  Use: npm run desktop:release:windows   (release, gated)\n" +
  "  Use: npm run dist:win                  (developer build, ungated)\n" +
  "  See: docs/AETHEROS_MASTER_80_BUILD_CONTRACT.md"
)
process.exit(1)
void main

import { execSync } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DESKTOP_ROOT = resolve(__dirname, '..')
const RELEASE_DIR = resolve(DESKTOP_ROOT, 'release')

const args = process.argv.slice(2)
const ONLY_PLATFORM = args.includes('--platform') ? args[args.indexOf('--platform') + 1] : null
const SHOULD_SIGN = args.includes('--sign')

function run(cmd, label) {
  console.log(`\n━━━ ${label} ━━━\n`)
  execSync(cmd, { cwd: DESKTOP_ROOT, stdio: 'inherit', shell: true })
}

function ensureDir(dir) {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true })
  }
}

function createOutputStructure() {
  ensureDir(resolve(DESKTOP_ROOT, 'release'))
  const subdirs = ['windows', 'linux', 'macos']
  for (const dir of subdirs) {
    ensureDir(resolve(DESKTOP_ROOT, 'release', dir))
  }
}

function buildStep(step, cmd) {
  console.log(`\n[${step}]`)
  try {
    execSync(cmd, { cwd: DESKTOP_ROOT, stdio: 'inherit', shell: true, timeout: 600000 })
    console.log(`[${step}] OK`)
  } catch (err) {
    console.error(`[${step}] FAILED: ${err.message}`)
    process.exit(1)
  }
}

function main() {
  console.log('═══════════════════════════════════════════════')
  console.log('  AetherOS — Production Installer Builder')
  console.log('═══════════════════════════════════════════════\n')

  // Step 1: Pre-build validation
  buildStep('pre-build', 'node scripts/assert-root-install.cjs')

  // Step 2: Build the renderer + main process
  buildStep('build renderer', 'node scripts/write-build-stamp.cjs && node scripts/stage-native-deps.cjs && node scripts/bundle-python.cjs && npx tsc -b && npx vite build && node scripts/assert-dist-built.cjs')

  // Step 3: Create output directory structure
  createOutputStructure()
  console.log('✓ Output directories created')

  // Step 4: Build platform-specific installers
  const builderCmd = `cross-env NODE_OPTIONS=--max-old-space-size=16384 npx electron-builder`

  if (ONLY_PLATFORM === 'win' || !ONLY_PLATFORM) {
    buildStep('Windows NSIS Setup', `${builderCmd} --win --config.win.target=nsis --x64`)
    console.log('✓ Windows NSIS installer built')

    buildStep('Windows MSI', `${builderCmd} --win --config.win.target=msi --x64`)
    console.log('✓ Windows MSI installer built')

    buildStep('Windows Portable', `${builderCmd} --win --config.win.target=portable --x64`)
    console.log('✓ Windows Portable ZIP built')

    // Organize Windows artifacts
    try {
      execSync(`if exist "${RELEASE_DIR}\\*.exe" move /Y "${RELEASE_DIR}\\*.exe" "${RELEASE_DIR}\\windows\\" 2>nul`, { shell: true })
      execSync(`if exist "${RELEASE_DIR}\\*.msi" move /Y "${RELEASE_DIR}\\*.msi" "${RELEASE_DIR}\\windows\\" 2>nul`, { shell: true })
      execSync(`if exist "${RELEASE_DIR}\\*.zip" move /Y "${RELEASE_DIR}\\*.zip" "${RELEASE_DIR}\\windows\\" 2>nul`, { shell: true })
    } catch { /* best-effort */ }
  }

  if (ONLY_PLATFORM === 'linux' || !ONLY_PLATFORM) {
    buildStep('Linux AppImage + deb + rpm', `${builderCmd} --linux --x64`)
    console.log('✓ Linux installers built')

    try {
      execSync(`if exist "${RELEASE_DIR}\\*.AppImage" move /Y "${RELEASE_DIR}\\*.AppImage" "${RELEASE_DIR}\\linux\\" 2>nul`, { shell: true })
      execSync(`if exist "${RELEASE_DIR}\\*.deb" move /Y "${RELEASE_DIR}\\*.deb" "${RELEASE_DIR}\\linux\\" 2>nul`, { shell: true })
      execSync(`if exist "${RELEASE_DIR}\\*.rpm" move /Y "${RELEASE_DIR}\\*.rpm" "${RELEASE_DIR}\\linux\\" 2>nul`, { shell: true })
    } catch { /* best-effort */ }
  }

  if (ONLY_PLATFORM === 'mac' || !ONLY_PLATFORM) {
    if (SHOULD_SIGN) {
      buildStep('macOS DMG (signed)', `${builderCmd} --mac --config.mac.target=dmg --universal`)
    } else {
      buildStep('macOS DMG', `${builderCmd} --mac --config.mac.target=dmg --x64`)
      buildStep('macOS ARM DMG', `${builderCmd} --mac --config.mac.target=dmg --arm64`)
    }

    buildStep('macOS PKG', `${builderCmd} --mac --config.mac.target=pkg --universal`)
    buildStep('macOS ZIP', `${builderCmd} --mac --config.mac.target=zip --universal`)

    try {
      execSync(`if exist "${RELEASE_DIR}\\*.dmg" move /Y "${RELEASE_DIR}\\*.dmg" "${RELEASE_DIR}\\macos\\" 2>nul`, { shell: true })
      execSync(`if exist "${RELEASE_DIR}\\*.pkg" move /Y "${RELEASE_DIR}\\*.pkg" "${RELEASE_DIR}\\macos\\" 2>nul`, { shell: true })
      execSync(`if exist "${RELEASE_DIR}\\*.zip" move /Y "${RELEASE_DIR}\\*.zip" "${RELEASE_DIR}\\macos\\" 2>nul`, { shell: true })
    } catch { /* best-effort */ }
  }

  // Step 5: Generate build manifest
  const manifest = generateBuildManifest()
  writeFileSync(
    resolve(RELEASE_DIR, 'BUILD_MANIFEST.json'),
    JSON.stringify(manifest, null, 2) + '\n'
  )
  console.log('✓ Build manifest written')

  // Step 6: Summary
  console.log('\n═══════════════════════════════════════════════')
  console.log('  Build Complete')
  console.log('═══════════════════════════════════════════════\n')
  console.log(`  Output: ${RELEASE_DIR}`)
  console.log(`  Version: ${manifest.version}`)
  console.log(`  Electron: ${manifest.electronVersion}`)
  console.log(`  Built: ${manifest.builtAt}\n`)

  if (manifest.artifacts.length > 0) {
    console.log('  Artifacts:')
    for (const art of manifest.artifacts) {
      console.log(`    ✓ ${art.file} (${art.size})`)
    }
  }
  console.log('')
}

function generateBuildManifest() {
  const { version, build } = JSON.parse(
    execSync('node -e "console.log(JSON.stringify({version: require(\'./package.json\').version, build: {electronVersion: require(\'./package.json\').build.electronVersion}}))"', { cwd: DESKTOP_ROOT, encoding: 'utf8' })
  )

  const artifacts = []
  const releaseDir = RELEASE_DIR

  const patterns = {
    'windows': ['*.exe', '*.msi', '*.zip'],
    'linux': ['*.AppImage', '*.deb', '*.rpm'],
    'macos': ['*.dmg', '*.pkg', '*.zip']
  }

  for (const [platform, exts] of Object.entries(patterns)) {
    const platformDir = resolve(releaseDir, platform)
    if (!existsSync(platformDir)) continue
    const fs = require('node:fs')
    const path = require('node:path')
    try {
      const files = fs.readdirSync(platformDir)
      for (const file of files) {
        if (exts.some(ext => file.endsWith(ext.replace('*', '')))) {
          const stat = fs.statSync(path.join(platformDir, file))
          artifacts.push({ platform, file, size: formatSize(stat.size) })
        }
      }
    } catch { /* skip */ }
  }

  return {
    appName: 'Aetheros',
    version,
    electronVersion: build.electronVersion,
    builtAt: new Date().toISOString(),
    buildSystem: 'electron-builder',
    nodeVersion: process.version,
    platform: process.platform,
    arch: process.arch,
    artifacts
  }
}

function formatSize(bytes) {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`
}

main()
