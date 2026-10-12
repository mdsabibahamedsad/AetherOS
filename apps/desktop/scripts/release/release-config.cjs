"use strict"
// Master 80 — single source of truth for the Windows release build contract.
// Pure functions live in release-guards.cjs (shared with regression tests).
// This module binds the contract to the live repository (package.json, .nvmrc,
// installed node_modules) and exposes it to preflight/validator/manifest code.
const fs = require("node:fs")
const path = require("node:path")
const { execSync } = require("node:child_process")

const DESKTOP_ROOT = path.resolve(__dirname, "..", "..")
const REPO_ROOT = path.resolve(DESKTOP_ROOT, "..", "..")

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"))
}

function loadContract() {
  const pkg = readJson(path.join(DESKTOP_ROOT, "package.json"))
  const nvmrc = fs.existsSync(path.join(REPO_ROOT, ".nvmrc"))
    ? fs.readFileSync(path.join(REPO_ROOT, ".nvmrc"), "utf8").trim()
    : null
  const nodeMajor = nvmrc ? parseInt(nvmrc.split(".")[0], 10) : 22
  let electronBuilder = null
  try {
    electronBuilder = readJson(
      path.join(REPO_ROOT, "node_modules", "electron-builder", "package.json")
    ).version
  } catch { /* not installed */ }
  let electronInstalled = null
  try {
    electronInstalled = readJson(
      path.join(REPO_ROOT, "node_modules", "electron", "package.json")
    ).version
  } catch { /* not installed */ }
  const version = pkg.version
  return {
    product: "AetherOS",
    appId: pkg.build.appId,
    version,
    platform: "windows",
    arch: "x64",
    // Canonical toolchain (Master 80 §12/§14/§15): Node 22 = .nvmrc + CI +
    // desktop engines (>=22.12.0 branch) + electron-builder 26 support matrix.
    canonicalNodeMajor: Number.isFinite(nodeMajor) ? nodeMajor : 22,
    nvmrc,
    electronPackaged: pkg.build.electronVersion, // intentional pin, §14
    electronDevRange: pkg.devDependencies.electron,
    electronInstalled,
    electronBuilderRange: pkg.devDependencies["electron-builder"],
    electronBuilderInstalled: electronBuilder,
    msiUpgradeCode: pkg.build.msi.upgradeCode,
    nsisGuid: pkg.build.nsis.guid,
    outputDir: path.join(DESKTOP_ROOT, "dist-packaged"),
    repoRoot: REPO_ROOT,
    desktopRoot: DESKTOP_ROOT,
    // Canonical artifact set (§8/§9): exactly these three, nothing else.
    expectedArtifacts: [
      { target: "nsis", file: `AetherOS-${version}-win-x64.exe` },
      { target: "msi", file: `AetherOS-${version}-win-x64.msi` },
      { target: "portable", file: `AetherOS-${version}-win-x64-portable.exe` },
    ],
  }
}

function gitHead(cwd) {
  try {
    return execSync("git rev-parse HEAD", { cwd, encoding: "utf8" }).trim()
  } catch { return null }
}

function gitPorcelain(cwd) {
  try {
    return execSync("git status --porcelain", { cwd, encoding: "utf8" })
  } catch { return null }
}

module.exports = { loadContract, gitHead, gitPorcelain, DESKTOP_ROOT, REPO_ROOT }
