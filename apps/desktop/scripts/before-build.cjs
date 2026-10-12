/**
 * before-build.cjs — electron-builder beforeBuild hook.
 *
 * Returns false to tell electron-builder to skip the node_modules
 * collector/install step. This avoids workspace dependency graph
 * explosions (the monorepo root hoists all node_modules) and keeps
 * packaging deterministic across environments.
 *
 * NATIVE DEPENDENCIES (node-pty):
 * The workspace dedup hoists node-pty into the root node_modules/,
 * which electron-builder cannot reach when `files:` is explicitly set.
 * We ship a minimal copy under resources/native-deps/ via extraResources
 * + scripts/stage-native-deps.cjs. The main process (main.cjs) falls
 * back to require()-ing from process.resourcesPath when the hoisted-root
 * require fails. See scripts/stage-native-deps.cjs for details.
 *
 * BUNDLED PYTHON BACKEND:
 * The Python interpreter + all pip dependencies are bundled into the
 * installer via scripts/bundle-python.cjs during `npm run build`.
 * At runtime, findBundledPython() resolves from
 * process.resourcesPath/py/ (the bundled Python) and
 * process.resourcesPath/backend/ (the backend source).
 * See electron/main.cjs resolveAetherosBackend() for the full
 * resolution ladder.
 */
module.exports = async function beforeBuild() {
  // Installer license presentation: stage the installer-specific EULA text.
  // package.json references build/installer/license.txt (nsis/linux license
  // prompts + extraResources). That staged file is the INSTALLER-FACING
  // presentation: AetherOS copyright + MIT terms, without the upstream
  // attribution line. The canonical repo LICENSE (which retains the upstream
  // MIT attribution) is intentionally NOT staged here — see
  // assets/installer-license.txt.
  try {
    const fs = require('node:fs')
    const path = require('node:path')
    const appRoot = path.resolve(__dirname, '..')
    const repoRoot = path.resolve(appRoot, '..', '..')
    const src = path.join(appRoot, 'assets', 'installer-license.txt')
    const dest = path.join(appRoot, 'build', 'installer', 'license.txt')
    if (fs.existsSync(src)) {
      fs.mkdirSync(path.dirname(dest), { recursive: true })
      fs.copyFileSync(src, dest)
      console.log('[before-build] staged installer license.txt from ' + path.relative(repoRoot, src))
    } else {
      console.warn('[before-build] WARNING: installer license source missing at ' + src)
    }
  } catch (err) {
    console.warn('[before-build] WARNING: license staging failed: ' + (err && err.message))
  }
  return false
}
