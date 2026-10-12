'use strict'

/**
 * stage-bundled-backend.cjs
 *
 * Stages the AetherOS Python backend source into build/bundled-python/backend/
 * for electron-builder's extraResources packaging.
 *
 * The backend source (hermes_cli module + required packages) is copied from
 * the repository root.  The bundled Python runtime itself (python.exe + stdlib)
 * must be prepared separately — see build/bundled-python/py/.
 *
 * Runs as part of `npm run build`.  Idempotent — always re-stages on each
 * build to pick up source changes.
 */

const fs = require('node:fs')
const path = require('node:path')

const APP_ROOT = path.resolve(__dirname, '..')
const REPO_ROOT = path.resolve(APP_ROOT, '..', '..')
const BUNDLE_ROOT = path.join(APP_ROOT, 'build', 'bundled-python')
const BACKEND_STAGE = path.join(BUNDLE_ROOT, 'backend')

const BACKEND_SOURCE = {
  files: [
    // Python source packages (renamed from hermes_* to aetheros_*)
    'aetheros_cli/',
    'aetheros_actions/',
    'aetheros_automation/',
    'aetheros_cloud/',
    'aetheros_developer_platform/',
    'aetheros_intelligence/',
    'aetheros_knowledge/',
    'aetheros_ocr/',
    'aetheros_orchestrator/',
    'aetheros_platform/',
    'aetheros_production/',
    'aetheros_security/',
    'aetheros_voice/',
    'agent/',
    'agents/',
    'cluster/',
    'connect/',
    'extensions/',
    'hub/',
    'kernel/',
    'marketplace/',
    'sdk/',
    // Master 78: aetheros_cli.main imports memory_intelligence_cli at top
    // level (backend boot dependency — packaged backend crash-looped
    // without it: "No module named 'aetheros_memory_intelligence'").
    'aetheros_memory_intelligence/',
    // Master 78: agent.quality.metrics imports aetheros_observability at
    // top level (dashboard startup closure — same crash-loop class).
    'aetheros_observability/',
    // Master 78: main() builds ALL subcommand parsers at startup, including
    // benchmark (same crash-loop class — proven by dashboard --help probe).
    'benchmark/',
    'memory/',
    'providers/',
    'workflows/',
    'tools/',
    'tui_gateway/',
    'gateway/',
    'cron/',
    'plugins/',
    'skills/',
    'optional-skills/',
    'acp_adapter/',
    // Top-level Python modules (runtime-critical)
    'aetheros_constants.py',
    'aetheros_state.py',
    'aetheros_logging.py',
    'aetheros_bootstrap.py',
    'aetheros_time.py',
    'toolsets.py',
    'toolset_distributions.py',
    'trajectory_compressor.py',
    'model_tools.py',
    'utils.py',
    'run_agent.py',
    'batch_runner.py',
    // Project config
    'pyproject.toml',
  ]
}

function rmrf(target) {
  fs.rmSync(target, { recursive: true, force: true })
}

function ensureDir(target) {
  fs.mkdirSync(target, { recursive: true })
}

function walk(root) {
  const results = []
  const stack = [root]
  while (stack.length) {
    const current = stack.pop()
    let entries
    try {
      entries = fs.readdirSync(current, { withFileTypes: true })
    } catch {
      continue
    }
    for (const entry of entries) {
      if (entry.name === 'node_modules' || entry.name === '__pycache__' || entry.name === '.git') continue
      const full = path.join(current, entry.name)
      if (entry.isDirectory()) {
        stack.push(full)
      } else if (entry.isFile()) {
        results.push(full)
      }
    }
  }
  return results
}

function stageBackend() {
  rmrf(BACKEND_STAGE)
  ensureDir(BACKEND_STAGE)

  let total = 0
  for (const source of BACKEND_SOURCE.files) {
    const srcPath = path.join(REPO_ROOT, source)
    if (!fs.existsSync(srcPath)) {
      console.warn(`[stage-bundled-backend] WARNING: source not found: ${srcPath}`)
      continue
    }

    const stat = fs.statSync(srcPath)
    if (stat.isDirectory()) {
      const files = walk(srcPath)
      for (const abs of files) {
        const rel = path.relative(REPO_ROOT, abs)
        const dest = path.join(BACKEND_STAGE, rel)
        ensureDir(path.dirname(dest))
        fs.copyFileSync(abs, dest)
        total++
      }
    } else {
      const dest = path.join(BACKEND_STAGE, source)
      ensureDir(path.dirname(dest))
      fs.copyFileSync(srcPath, dest)
      total++
    }
  }

  console.log(`[stage-bundled-backend] staged ${total} files to ${path.relative(APP_ROOT, BACKEND_STAGE)}`)
}

function main() {
  stageBackend()
  console.log('[stage-bundled-backend] done')
}

main()
