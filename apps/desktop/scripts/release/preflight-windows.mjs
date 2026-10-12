#!/usr/bin/env node
// Master 80 §A (preflight) + §47 (dry-run report).
// Usage:
//   node scripts/release/preflight-windows.mjs            # gate: exit 1 on any failure
//   node scripts/release/preflight-windows.mjs --report   # same checks, JSON report, still exits 1 on failure
// Never mutates source, never commits, never stashes, never deletes (§45).
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { execSync } from "node:child_process"
import { createRequire } from "node:module"
const require = createRequire(import.meta.url)
const guards = require("./release-guards.cjs")
const { loadContract, gitHead, gitPorcelain } = require("./release-config.cjs")

const DESKTOP_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..")
const REPO_ROOT = path.resolve(DESKTOP_ROOT, "..", "..")
const reportOnly = process.argv.includes("--report")

function sh(cmd, cwd) {
  try { return execSync(cmd, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim() }
  catch { return null }
}

async function main() {
  const c = loadContract()
  const checks = []
  const check = (id, name, res, extra) => {
    const entry = { id, name, status: res.ok ? "PASS" : "FAIL" }
    if (!res.ok) { entry.code = res.code; if (res.detail) entry.detail = res.detail; if (res.offenders) entry.offenders = res.offenders }
    checks.push({ ...entry, ...(extra || {}) })
  }

  // A01 — clean tree (full porcelain, untracked included; §4).
  const porcelain = gitPorcelain(REPO_ROOT)
  const tree = guards.checkTreeClean(porcelain)
  check("A01", "git clean (release policy)", tree)

  // A02/A03 — canonical Node + npm present.
  const nodeRes = guards.checkNodeVersion(process.version, c.canonicalNodeMajor)
  check("A02", `canonical Node ${c.canonicalNodeMajor} (nvmrc ${c.nvmrc})`, nodeRes, { actual: process.version })
  const npmV = sh("npm --version", DESKTOP_ROOT)
  check("A03", "npm available (bundled with canonical Node)", npmV ? { ok: true } : { ok: false, code: "NPM_ABSENT", detail: "npm not on PATH" }, { actual: npmV })

  // A04 — packaged Electron pin declared.
  check("A04", `packaged Electron pin ${c.electronPackaged}`, c.electronPackaged ? { ok: true } : { ok: false, code: "ELECTRON_PIN_ABSENT", detail: "build.electronVersion missing" }, { devRange: c.electronDevRange, installed: c.electronInstalled })

  // A05 — electron-builder repo-local.
  const ebOk = c.electronBuilderInstalled === "26.8.1"
  check("A05", "electron-builder 26.8.1 repo-local (./node_modules/.bin)", ebOk ? { ok: true } : { ok: false, code: "BUILDER_VERSION_MISMATCH", detail: `installed=${c.electronBuilderInstalled}` }, { range: c.electronBuilderRange })

  // A06 — lockfiles present (root workspace install contract, §13).
  // Root lockfile is authoritative; standalone desktop lockfile optional.
  const rootLock = fs.existsSync(path.join(REPO_ROOT, "package-lock.json"))
  const deskLock = fs.existsSync(path.join(DESKTOP_ROOT, "package-lock.json"))
  let rootCoversDesktop = false
  try {
    const rl = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, "package-lock.json"), "utf8"))
    rootCoversDesktop = Boolean((rl.packages || {})["apps/desktop"])
  } catch { /* treated as absent below */ }
  const lockPresent = guards.checkLockfilesPresent(rootLock, deskLock, rootCoversDesktop)
  check("A06", "lockfiles present (root authoritative, desktop optional)", lockPresent, { root: rootLock, desktop: deskLock, workspaceCovered: rootCoversDesktop })

  // A07/A08 — informational here (npm ci runs in the canonical build, not in preflight).
  check("A07", "npm ci succeeds", { ok: true }, { note: "INFORMATIONAL in preflight — enforced by canonical build; use desktop:release:windows for the real gate" })
  checks[checks.length - 1].status = "INFORMATIONAL"
  check("A08", "lockfile unchanged after install", { ok: true }, { note: "INFORMATIONAL in preflight — enforced post-install by canonical build (LOCKFILE_MUTATED)" })
  checks[checks.length - 1].status = "INFORMATIONAL"

  // A09/A10 — output path safety + initial cleanliness (§6/§71).
  const safe = guards.assertOutputDirSafe(c.outputDir, REPO_ROOT)
  check("A09", "output path safe + build-owned", safe)
  let initialClean = { ok: true }
  if (safe.ok) {
    if (!fs.existsSync(c.outputDir)) initialClean = { ok: true, note: "absent (will be created)" }
    else {
      const entries = fs.readdirSync(c.outputDir)
      if (entries.length > 0) initialClean = { ok: false, code: "OUTPUT_DIRECTORY_NOT_CLEAN", detail: `${entries.length} entries: ${entries.slice(0, 10).join(", ")}` }
    }
  } else initialClean = { ok: false, code: "OUTPUT_SAFETY_BLOCKS_CHECK", detail: "resolve A09 first" }
  check("A10", "output initially clean", initialClean.ok ? { ok: true } : initialClean, initialClean.note ? { note: initialClean.note } : {})

  // A11 — path guard config present (full scan runs post-build against staging).
  const guardPresent = fs.existsSync(path.join(DESKTOP_ROOT, "scripts", "release", "check-packaging-path-lengths.mjs"))
  check("A11", "projected-path guard wired", guardPresent ? { ok: true } : { ok: false, code: "PATH_GUARD_ABSENT", detail: "guard script missing" })

  // A12 — expected configuration (appId/product/targets/output).
  const cfgOk = c.appId === "com.aetheros.aetheros" && c.product === "AetherOS"
  check("A12", "packaging identity (appId/product/output)", cfgOk ? { ok: true } : { ok: false, code: "PACKAGING_IDENTITY_WRONG", detail: `appId=${c.appId} product=${c.product}` })

  const head = gitHead(REPO_ROOT)
  const report = {
    schema: "aetheros-windows-preflight/1",
    generatedAt: new Date().toISOString(),
    commit: head,
    node: process.version,
    canonicalNodeMajor: c.canonicalNodeMajor,
    version: c.version,
    checks,
    overall: checks.every((k) => k.status === "PASS" || k.status === "INFORMATIONAL") ? "PREFLIGHT_PASS" : "PREFLIGHT_FAIL",
  }
  if (reportOnly || true) {
    const dir = path.join(REPO_ROOT, "docs", "AETHEROS_MASTER_80_EVIDENCE")
    fs.mkdirSync(dir, { recursive: true })
    fs.writeFileSync(path.join(dir, "01-preflight.json"), JSON.stringify(report, null, 2) + "\n")
  }
  for (const k of checks) console.log(`  [${k.status}] ${k.id} ${k.name}${k.code ? ` — ${k.code}: ${k.detail || ""}` : ""}`)
  console.log(report.overall === "PREFLIGHT_PASS" ? "\nPREFLIGHT_PASS" : "\nPREFLIGHT_FAIL — release build blocked (§44)")
  process.exit(report.overall === "PREFLIGHT_PASS" ? 0 : 1)
}

main().catch((e) => { console.error(`PREFLIGHT_FAIL: ${e.message}`); process.exit(1) })

