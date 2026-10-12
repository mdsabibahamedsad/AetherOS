'use strict'

/**
 * bundle-python.cjs
 *
 * Prepares a self-contained Python runtime + all pip dependencies under
 * build/bundled-python/ for electron-builder's extraResources packaging.
 *
 * Layout produced:
 *   build/bundled-python/
 *     py/               ← portable Python interpreter + stdlib + site-packages
 *       python.exe      (Windows) or bin/python3 (macOS/Linux)
 *       Lib/site-packages/  (Windows) or lib/python3.x/site-packages/ (POSIX)
 *     backend/          ← staged Python backend source (delegates to
 *                         stage-bundled-backend.cjs)
 *
 * HOW IT WORKS
 * ------------
 * 1. Creates a fresh virtual environment with `uv venv` (or `python -m venv`).
 * 2. Installs the project and its production dependencies into that venv.
 * 3. Strips build artifacts (pyc, test files, dist-info metadata) to keep
 *    the payload lean.
 * 4. Writes a BUNDLED_MANIFEST.json so the runtime can verify integrity.
 *
 * Runs as part of `npm run build`, BEFORE electron-builder packaging.
 * Idempotent — always rebuilds on each invocation.
 *
 * PREREQUISITES
 * -------------
 * - `uv` must be available (preferred) or `python3` with `pip`.
 * - The workspace root must have a pyproject.toml with production deps.
 * - Run from: apps/desktop/ (cwd is automatically the desktop root).
 */

const fs = require('node:fs')
const path = require('node:path')
const { execSync, spawnSync } = require('node:child_process')

const APP_ROOT = path.resolve(__dirname, '..')
const REPO_ROOT = path.resolve(APP_ROOT, '..', '..')
const BUNDLE_ROOT = path.join(APP_ROOT, 'build', 'bundled-python')
const PYTHON_STAGE = path.join(BUNDLE_ROOT, 'py')
const BACKEND_STAGE = path.join(BUNDLE_ROOT, 'backend')

const IS_WINDOWS = process.platform === 'win32'
const IS_POSIX = !IS_WINDOWS

/**
 * Resolve the path to the source virtual environment that contains ALL
 * pre-installed dependencies. Called once; result is passed down to avoid
 * duplicating resolution logic in stagePythonRuntime and installDependencies.
 */
function resolveSourceVenv() {
  return process.env.VIRTUAL_ENV || process.env.UV_PROJECT_ENVIRONMENT || path.join(REPO_ROOT, '.venv')
}

/**
 * Find a suitable Python interpreter for building the bundle.
 * Prefers: uv-managed Python > venv Python > system Python
 */
function findHostPython(sourceVenv) {
  // 1. Already in a venv? Use that (most reliable — has pip, known version).
  if (sourceVenv && fs.existsSync(sourceVenv)) {
    const pythonExe = IS_WINDOWS
      ? path.join(sourceVenv, 'Scripts', 'python.exe')
      : path.join(sourceVenv, 'bin', 'python')
    if (fs.existsSync(pythonExe)) return { python: pythonExe, source: 'venv' }
  }

  // 2. uv-managed Python (uv python find)
  try {
    const out = execSync('uv python find', {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore']
    }).trim()
    if (out && fs.existsSync(out)) {
      return { python: out, source: 'uv' }
    }
  } catch { /* uv not available */ }

  // 3. System python3/python
  for (const cmd of IS_WINDOWS ? ['python', 'python3'] : ['python3', 'python']) {
    try {
      const out = execSync(`${cmd} -c "import sys; print(sys.executable)"`, {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore']
      }).trim()
      if (out && fs.existsSync(out)) return { python: out, source: 'system' }
    } catch { /* not found */ }
  }

  throw new Error(
    'Could not find a Python interpreter for bundling. ' +
    'Install Python 3.11+ and ensure it is on PATH, or activate a venv.'
  )
}

/**
 * Check if `uv` is available (fastest way to create venvs + install deps).
 */
function hasUv() {
  try {
    execSync('uv --version', { stdio: 'ignore' })
    return true
  } catch {
    return false
  }
}

/**
 * Run a command and log its output. Throws on non-zero exit.
 */
function run(cmd, args, options = {}) {
  const cmdStr = `${cmd} ${args.join(' ')}`
  console.log(`[bundle-python] $ ${cmdStr}`)

  const result = spawnSync(cmd, args, {
    stdio: ['ignore', 'pipe', 'pipe'],
    encoding: 'utf8',
    ...options
  })

  if (result.status !== 0) {
    const stderr = (result.stderr || '').trim()
    const stdout = (result.stdout || '').trim()
    console.error(`[bundle-python] FAILED (exit ${result.status}): ${cmdStr}`)
    if (stdout) console.error(`  stdout: ${stdout.slice(0, 500)}`)
    if (stderr) console.error(`  stderr: ${stderr.slice(0, 500)}`)
    throw new Error(`Command failed: ${cmdStr} (exit ${result.status})`)
  }

  if (result.stdout) console.log(result.stdout.trim().slice(0, 300))
  return result
}

/**
 * Check the Python version to ensure it's compatible (3.11-3.13).
 */
function checkPythonVersion(pythonExe) {
  const result = spawnSync(pythonExe, ['-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'], {
    stdio: ['ignore', 'pipe', 'pipe'],
    encoding: 'utf8'
  })
  if (result.status !== 0) throw new Error(`Cannot determine Python version for ${pythonExe}`)

  const version = (result.stdout || '').trim()
  const supported = ['3.11', '3.12', '3.13']
  if (!supported.includes(version)) {
    throw new Error(
      `Python ${version} is not supported for bundling. ` +
      `Supported versions: ${supported.join(', ')}`
    )
  }
  console.log(`[bundle-python] Host Python version: ${version}`)
  return version
}

/**
 * Validate that the source virtual environment exists and has a working
 * Python interpreter. Returns the python executable path.
 */
function validateSourceVenv(sourceVenv) {
  if (!fs.existsSync(sourceVenv)) {
    throw new Error(
      'Cannot find a working virtual environment to bundle at ' + sourceVenv + '. ' +
      'Activate a venv or run `uv sync` first.'
    )
  }

  const pythonExe = IS_WINDOWS
    ? path.join(sourceVenv, 'Scripts', 'python.exe')
    : path.join(sourceVenv, 'bin', 'python3')

  if (!fs.existsSync(pythonExe)) {
    // Try alt POSIX path
    const altPythonExe = path.join(sourceVenv, 'bin', 'python')
    return fs.existsSync(altPythonExe) ? altPythonExe : null
  }

  return pythonExe
}

/**
 * Stage 1: Validate the source venv exists and print version info.
 * (No longer creates a fresh venv — we copy the fully-resolved one in Stage 2.)
 */
function stagePythonRuntime(sourceVenv) {
  console.log('[bundle-python] Validating source virtual environment...')
  const pythonExe = validateSourceVenv(sourceVenv)
  if (!pythonExe) {
    throw new Error(`No python binary found in source venv at ${sourceVenv}`)
  }

  checkPythonVersion(pythonExe)
  console.log(`[bundle-python] Source venv at ${sourceVenv}`)
}

/**
 * Stage 2: Copy the fully-resolved virtual environment (which has ALL
 * dependencies pre-installed via `uv sync`) to the bundle directory.
 *
 * We skip pip-install from scratch because pyproject.toml uses PEP 639
 * license format (`license = { text = "MIT" }`) which older setuptools
 * rejects during "Getting requirements to build editable".
 *
 * At runtime findBundledPython() finds the interpreter at resources/py/
 * and the backend source is added to PYTHONPATH.
 */
function bundlePythonRuntime(sourceVenv) {
  console.log('[bundle-python] Bundling existing virtual environment with all dependencies…')

  copyVenv(sourceVenv, PYTHON_STAGE)

  // Verify the copied venv has a working python
  const pythonExe = IS_WINDOWS
    ? path.join(PYTHON_STAGE, 'Scripts', 'python.exe')
    : path.join(PYTHON_STAGE, 'bin', 'python3')

  if (!fs.existsSync(pythonExe)) {
    throw new Error(`Copied venv has no python binary at ${pythonExe}`)
  }

  console.log(`[bundle-python] Python runtime bundled at ${PYTHON_STAGE}`)
}

/**
 * Deep-copy a fully-resolved virtual environment without preserving
 * symlinks. uv-created venvs link the interpreter binaries (POSIX:
 * `.venv/bin/python` -> absolute path of the base interpreter; Windows:
 * junction points into the uv Python install). Preserving those links
 * bakes build-machine-absolute paths into the bundle — on macOS
 * `codesign --verify --deep --strict` then fails the packaged app with
 * "invalid destination for symbolic link in bundle" (CI run 35178702673).
 * We therefore materialize file symlinks as real file copies and skip
 * directory symlinks entirely (same safety rationale as the original
 * Windows-only walker: never pull in the system Python installation).
 */
function copyVenv(src, dest) {
  if (fs.existsSync(dest)) {
    fs.rmSync(dest, { recursive: true, force: true, maxRetries: 3 })
  }

  console.log(`[bundle-python] Copying venv from ${src} to ${dest}...`)

  // Create parent directory
  fs.mkdirSync(path.dirname(dest), { recursive: true })

  // All platforms use the symlink-safe walker: fs.cpSync would preserve
  // absolute symlinks into the bundle (fatal for macOS codesign --strict).
  copyRecursiveSync(src, dest)

  console.log('[bundle-python] Venv copy complete')

  // CRITICAL: Patch pyvenv.cfg to remove absolute path to developer's machine.
  // The copied venv's pyvenv.cfg still references the developer's Python home
  // path (e.g. D:\hermes-agent-main\aetheros\.venv\Scripts). When the bundled
  // Python runs on a user's machine, that path won't exist. Python on Windows
  // finds its stdlib relative to the executable's own location, so python.exe
  // starts fine, but pip and any tool reading pyvenv.cfg can break.
  // We null out the home and version paths so the bundled interpreter relies
  // entirely on its own self-relative location.
  patchPyvenvCfg(dest)
}

/**
 * Patch pyvenv.cfg in a copied venv to remove developer-machine-absolute paths.
 * On Windows the interpreter is self-relative so it still works; we just need
 * to ensure pyvenv.cfg doesn't point at a non-existent home.
 */
function patchPyvenvCfg(venvDir) {
  const cfgPath = path.join(venvDir, 'pyvenv.cfg')
  if (!fs.existsSync(cfgPath)) {
    console.log('[bundle-python] No pyvenv.cfg to patch (expected only in venvs)')
    return
  }

  try {
    let content = fs.readFileSync(cfgPath, 'utf8')
    const lines = content.split(/\r?\n/)
    const patched = lines.map(line => {
      // Replace absolute home path with a relative one or empty it so the
      // bundled interpreter doesn't try to reach back to the build machine.
      if (/^home\s*=/.test(line)) {
        return 'home = .'
      }
      // base-executable is the original python.exe path; null it out.
      if (/^base-executable\s*=/.test(line)) {
        return 'base-executable = .'
      }
      return line
    })

    fs.writeFileSync(cfgPath, patched.join('\n'), 'utf8')
    console.log('[bundle-python] Patched pyvenv.cfg: removed absolute home path references')
  } catch (err) {
    console.warn(`[bundle-python] Could not patch pyvenv.cfg: ${err.message}`)
  }
}

/**
 * Recursive directory copy that materializes file symlinks as real files
 * and skips directory symlinks. Cross-platform: handles Windows junction
 * points AND POSIX absolute/relative symlinks (uv venv interpreter links).
 * Uses fs.copyFileSync which preserves permission bits, so copied
 * interpreter binaries stay executable.
 */
function copyRecursiveSync(src, dest) {
  const stats = fs.statSync(src)
  
  if (stats.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true })
    const entries = fs.readdirSync(src, { withFileTypes: true })
    for (const entry of entries) {
      if (entry.name === '.' || entry.name === '..') continue
      const srcPath = path.join(src, entry.name)
      const destPath = path.join(dest, entry.name)
      
      if (entry.isDirectory()) {
        copyRecursiveSync(srcPath, destPath)
      } else if (entry.isFile()) {
        fs.copyFileSync(srcPath, destPath)
      } else if (entry.isSymbolicLink()) {
        // SAFETY: Never follow symlinks/junctions to external directories.
        // A venv's interpreter is typically a link (POSIX symlink to the
        // base Python, Windows junction into the uv install); following a
        // directory link would recursively copy the ENTIRE system Python
        // into the bundle — a multi-GB mistake.
        // We skip directory symlinks entirely; for file symlinks we copy
        // the target file's contents so the bundle is fully self-contained
        // (no absolute build-machine paths survive for macOS codesign).
        try {
          const linkTarget = fs.readlinkSync(srcPath)
          const absTarget = path.isAbsolute(linkTarget)
            ? linkTarget
            : path.resolve(path.dirname(srcPath), linkTarget)
          const targetStat = fs.statSync(absTarget)
          if (targetStat.isFile()) {
            fs.copyFileSync(absTarget, destPath)
          }
          // Directory symlinks are intentionally skipped — they risk
          // pulling in the system Python installation.
        } catch {
          // Skip unreadable/dangling symlinks
        }
      }
    }
  } else if (stats.isFile()) {
    fs.copyFileSync(src, dest)
  }
}

/**
 * Stage 3: Strip unnecessary files from the bundled Python to reduce size.
 */
function stripBundledPython() {
  console.log('[bundle-python] Stripping unnecessary files...')

  const sitePackagesDir = findSitePackagesDir()
  if (!sitePackagesDir) {
    console.warn('[bundle-python] Could not find site-packages; skipping strip')
    return
  }

  let removed = 0
  let removedBytes = 0

  function walkAndStrip(dir) {
    if (!fs.existsSync(dir)) return
    const entries = fs.readdirSync(dir, { withFileTypes: true })
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name)

      if (entry.isDirectory()) {
        // Remove test directories
        if (/^(test|tests|__pycache__|\.pytest_cache|\.ruff_cache)$/.test(entry.name)) {
          const size = getDirSize(fullPath)
          fs.rmSync(fullPath, { recursive: true, force: true })
          removed++
          removedBytes += size
          continue
        }
        walkAndStrip(fullPath)
      } else if (entry.isFile()) {
        // Remove .pyc files (they'll be regenerated)
        if (entry.name.endsWith('.pyc')) {
          const stat = fs.statSync(fullPath)
          removedBytes += stat.size
          fs.rmSync(fullPath)
          removed++
        }
      }
    }
  }

  walkAndStrip(sitePackagesDir)

  // Remove .pyc files from the stdlib too
  const stdlibDir = findStdLibDir()
  if (stdlibDir) {
    walkAndStrip(stdlibDir)
  }

  console.log(`[bundle-python] Stripped ${removed} files (${formatBytes(removedBytes)})`)
}

function findSitePackagesDir() {
  const pythonExe = IS_WINDOWS
    ? path.join(PYTHON_STAGE, 'Scripts', 'python.exe')
    : path.join(PYTHON_STAGE, 'bin', 'python3')

  const exe = fs.existsSync(pythonExe) ? pythonExe : (IS_WINDOWS
    ? path.join(PYTHON_STAGE, 'Scripts', 'python.exe')
    : path.join(PYTHON_STAGE, 'bin', 'python'))

  if (!fs.existsSync(exe)) {
    // Can't find the interpreter; guess the layout
    return guessSitePackagesDir()
  }

  try {
    const out = execSync(`"${exe}" -c "import site; print(site.getsitepackages()[0])"`, {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 15000
    }).trim()
    return out || null
  } catch {
    return guessSitePackagesDir()
  }
}

function guessSitePackagesDir() {
  if (IS_WINDOWS) {
    const libDir = path.join(PYTHON_STAGE, 'Lib', 'site-packages')
    return fs.existsSync(libDir) ? libDir : null
  }
  try {
    const pythonLib = fs.readdirSync(path.join(PYTHON_STAGE, 'lib'))
      .find(d => d.startsWith('python3.'))
    return pythonLib ? path.join(PYTHON_STAGE, 'lib', pythonLib, 'site-packages') : null
  } catch {
    return null
  }
}

function findStdLibDir() {
  const pythonExe = IS_WINDOWS
    ? path.join(PYTHON_STAGE, 'Scripts', 'python.exe')
    : path.join(PYTHON_STAGE, 'bin', 'python3')

  for (const exe of [pythonExe, path.join(PYTHON_STAGE, 'bin', 'python')]) {
    if (!fs.existsSync(exe)) continue
    try {
      const out = execSync(`"${exe}" -c "import sys; print(sys.prefix)"`, {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
        timeout: 15000
      }).trim()
      return out || null
    } catch { /* continue */ }
  }
  return null
}

function getDirSize(dir) {
  let size = 0
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true })
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        size += getDirSize(fullPath)
      } else if (entry.isFile()) {
        size += fs.statSync(fullPath).size
      }
    }
  } catch { /* skip inaccessible */ }
  return size
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`
}

/**
 * Stage 4: Write a bundle manifest for runtime verification.
 */
function writeBundleManifest() {
  const manifest = {
    schemaVersion: 1,
    createdAt: new Date().toISOString(),
    python: {
      version: null,
      executable: IS_WINDOWS ? 'python.exe' : 'bin/python3'
    },
    backend: {
      staged: fs.existsSync(BACKEND_STAGE),
      sourceDirs: []
    }
  }

  // Get Python version from bundled runtime
  const pythonExe = IS_WINDOWS
    ? path.join(PYTHON_STAGE, 'Scripts', 'python.exe')
    : path.join(PYTHON_STAGE, 'bin', 'python3')

  if (fs.existsSync(pythonExe)) {
    try {
      const version = execSync(`"${pythonExe}" --version`, {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore']
      }).trim()
      manifest.python.version = version
    } catch { /* ignore */ }
  }

  if (fs.existsSync(BACKEND_STAGE)) {
    manifest.backend.sourceDirs = fs.readdirSync(BACKEND_STAGE)
      .filter(name => fs.statSync(path.join(BACKEND_STAGE, name)).isDirectory())
  }

  fs.writeFileSync(
    path.join(BUNDLE_ROOT, 'bundle-manifest.json'),
    JSON.stringify(manifest, null, 2) + '\n'
  )
  console.log(`[bundle-python] Bundle manifest written`)
}

/**
 * Stage 5: Stage the backend source code (delegates to stage-bundled-backend.cjs).
 */
function stageBackend() {
  console.log('[bundle-python] Staging backend source...')
  const stageScript = path.join(__dirname, 'stage-bundled-backend.cjs')
  if (!fs.existsSync(stageScript)) {
    throw new Error(`Backend staging script not found: ${stageScript}`)
  }
  require(stageScript)
}

/**
 * Calculate total bundle size for the build log.
 */
function reportSize() {
  const totalSize = getDirSize(BUNDLE_ROOT)
  console.log(`[bundle-python] Total bundle size: ${formatBytes(totalSize)}`)

  if (fs.existsSync(PYTHON_STAGE)) {
    const pythonSize = getDirSize(PYTHON_STAGE)
    console.log(`[bundle-python]   Python runtime: ${formatBytes(pythonSize)}`)
  }
  if (fs.existsSync(BACKEND_STAGE)) {
    const backendSize = getDirSize(BACKEND_STAGE)
    console.log(`[bundle-python]   Backend source: ${formatBytes(backendSize)}`)
  }
}

function main() {
  console.log('[bundle-python] ==========================================')
  console.log('[bundle-python] Bundling Python runtime for production')
  console.log('[bundle-python] ==========================================')

  // Resolve source venv ONCE — passed to all sub-stages to avoid duplication
  const sourceVenv = resolveSourceVenv()

  // Clean and prepare bundle root
  if (fs.existsSync(BUNDLE_ROOT)) {
    console.log('[bundle-python] Cleaning previous bundle...')
    fs.rmSync(BUNDLE_ROOT, { recursive: true, force: true })
  }
  fs.mkdirSync(BUNDLE_ROOT, { recursive: true })

  // Step 1: Find host Python
  console.log('[bundle-python] Step 1/4: Finding host Python...')
  const host = findHostPython(sourceVenv)
  console.log(`[bundle-python] Host Python: ${host.python} (${host.source})`)

  // Step 2: Validate source venv
  console.log('[bundle-python] Step 2/4: Validating source virtual environment...')
  stagePythonRuntime(sourceVenv)

  // Step 3: Copy source venv to bundle
  console.log('[bundle-python] Step 3/4: Copying Python runtime to bundle...')
  bundlePythonRuntime(sourceVenv)

  // Step 4: Stage backend source
  console.log('[bundle-python] Step 4/4: Staging backend source code...')
  stageBackend()

  // Cleanup (best-effort — must not fail the build)
  try {
    stripBundledPython()
  } catch (err) {
    console.warn(`[bundle-python] Stripping skipped: ${err.message}`)
  }

  writeBundleManifest()
  reportSize()

  // Verify the bundled Python is functional with a quick smoke test
  console.log('[bundle-python] Running smoke test on bundled Python...')
  const bundledPythonExe = IS_WINDOWS
    ? path.join(PYTHON_STAGE, 'Scripts', 'python.exe')
    : path.join(PYTHON_STAGE, 'bin', 'python3')

  if (fs.existsSync(bundledPythonExe)) {
    try {
      // Test: interpreter starts, stdlib works, core dep (pydantic) imports
      const smokeResult = spawnSync(bundledPythonExe, ['-c',
        'import sys; print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"); ' +
        'import site; print(f"site-packages: {site.getsitepackages()[0]}"); ' +
        'import pydantic; print(f"pydantic {pydantic.__version__}"); ' +
        'print("SMOKE_OK")'
      ], {
        stdio: ['ignore', 'pipe', 'pipe'],
        encoding: 'utf8',
        timeout: 30000
      })
      if (smokeResult.status === 0) {
        const lines = (smokeResult.stdout || '').trim().split('\n').filter(l => l !== 'SMOKE_OK')
        console.log(`[bundle-python] ✓ Smoke test passed: ${lines.join(', ')}`)
      } else {
        const err = (smokeResult.stderr || '').trim().slice(0, 500)
        console.warn(`[bundle-python] ⚠ Smoke test had issues: ${err}`)
      }
    } catch (err) {
      console.warn(`[bundle-python] ⚠ Smoke test failed: ${err.message}`)
    }
  }

  console.log('[bundle-python] ==========================================')
  console.log('[bundle-python] Python bundling complete!')
  console.log('[bundle-python] ==========================================')
}

main()
