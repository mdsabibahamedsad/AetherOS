#!/usr/bin/env node
// Master 80 §3 — ONE canonical Windows release path.
//   node scripts/release/release-windows.mjs [--preflight-only] [--skip-build] [--write-manifest]
// Stages: preflight → clean output → npm ci (root) → lockfile check → tests →
// build → electron-builder(__win) → validate → manifest. Fails fast (§44).
// Developer builds must use `npm run dist:win`; RELEASE builds use this.
import { execSync, execFileSync } from "node:child_process"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { createRequire } from "node:module"
const require = createRequire(import.meta.url)
const guards = require("./release-guards.cjs")
const { loadContract, gitHead, gitPorcelain } = require("./release-config.cjs")

const DESKTOP_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..")
const REPO_ROOT = path.resolve(DESKTOP_ROOT, "..", "..")
const ARGS = new Set(process.argv.slice(2))

function run(cmd, cwd, label) {
  console.log(`\n━━━ ${label}: ${cmd} ━━━`)
  execSync(cmd, { cwd, stdio: "inherit", shell: true })
}
function fail(code, detail) {
  console.error(`\n${code}${detail ? `: ${detail}` : ""} — pipeline stops (§44)`)
  process.exit(1)
}

function main() {
  const c = loadContract()
  const nodeMajor = parseInt(process.version.slice(1).split(".")[0], 10)
  if (nodeMajor !== c.canonicalNodeMajor) {
    fail("NODE_MAJOR_MISMATCH", `actual ${process.version}, canonical major ${c.canonicalNodeMajor} (.nvmrc ${c.nvmrc}) — use the canonical toolchain, no silent fallback`)
  }
  const tree = guards.checkTreeClean(gitPorcelain(REPO_ROOT))
  if (!tree.ok) fail(tree.code, `${tree.detail}: ${tree.offenders.join(" | ")}`)
  console.log("preflight: tree CLEAN, Node canonical — delegating to preflight-windows.mjs for full A01–A12");
  run("node scripts/release/preflight-windows.mjs", DESKTOP_ROOT, "preflight")
  if (ARGS.has("--preflight-only")) { console.log("\nPREFLIGHT_ONLY — no artifacts produced (§47)"); return }

  const safe = guards.assertOutputDirSafe(c.outputDir, REPO_ROOT)
  if (!safe.ok) fail(safe.code, safe.detail)
  fs.rmSync(c.outputDir, { recursive: true, force: true })
  fs.mkdirSync(c.outputDir, { recursive: true })
  if (fs.readdirSync(c.outputDir).length !== 0) fail("OUTPUT_DIRECTORY_NOT_CLEAN", c.outputDir)
  console.log(`clean output: ${c.outputDir} (build-owned, verified empty)`)

  if (!ARGS.has("--skip-build")) {
    run("npm ci", REPO_ROOT, "deps (npm ci, lockfile-based)")
    const diff = execSync("git diff -- package-lock.json apps/desktop/package-lock.json", { cwd: REPO_ROOT, encoding: "utf8" })
    const lock = guards.checkLockfileClean(diff)
    if (!lock.ok) fail(lock.code, "dependency installation rewrote the lockfile")
    run("npm run build", DESKTOP_ROOT, "renderer+main build")
    run("node scripts/release/check-packaging-path-lengths.mjs", DESKTOP_ROOT, "path guard (post-build, pre-package)")
    run("npx --no-install electron-builder --win", DESKTOP_ROOT, "electron-builder (repo-local, NSIS+MSI+portable)")
    try {
      execFileSync(process.execPath, ["scripts/release/write-build-stamp.cjs"], { cwd: DESKTOP_ROOT, stdio: "inherit" })
    } catch { /* stamp best-effort refresh; binding gate validates */ }
  } else {
    console.log("--skip-build: reusing existing output (validation still fully applies)");
  }

  run(`node scripts/release/validate-windows-release.mjs${ARGS.has("--write-manifest") ? " --write-manifest" : ""}`, DESKTOP_ROOT, "post-build validation + manifest")
  console.log(`\nCANONICAL_RELEASE_PASS — buildId manifest in docs/AETHEROS_MASTER_80_EVIDENCE/09-manifest.json`)
  console.log(`source: ${gitHead(REPO_ROOT)} (clean) | node ${process.version} | electron ${c.electronPackaged} | builder ${c.electronBuilderInstalled}`)
}

main()

