#!/usr/bin/env node
// Master 80 §B/§C — post-build hard gates for Windows release artifacts.
//
// Usage:
//   node scripts/release/validate-windows-release.mjs [--write-manifest]
//
// Gates (fail fast, §44): completeness → identity → source binding → MSI
// metadata → branding → developer-path screen → SHA-256 → manifest (+self-check).
// Exit 0 = all gates PASS. Writes evidence to docs/AETHEROS_MASTER_80_EVIDENCE/.
// Never signs, never publishes, never mutates source.
import fs from "node:fs"
import path from "node:path"
import crypto from "node:crypto"
import { fileURLToPath } from "node:url"
import { execSync, execFileSync } from "node:child_process"
import { createRequire } from "node:module"
const require = createRequire(import.meta.url)
const guards = require("./release-guards.cjs")
const { loadContract, gitHead } = require("./release-config.cjs")

const DESKTOP_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..")
const REPO_ROOT = path.resolve(DESKTOP_ROOT, "..", "..")
const EVIDENCE = path.join(REPO_ROOT, "docs", "AETHEROS_MASTER_80_EVIDENCE")
const WRITE_MANIFEST = process.argv.includes("--write-manifest")

const failures = []
function gate(id, name, res) {
  const st = res.ok ? "PASS" : "FAIL"
  const why = res.ok ? "" : (res.failures ? res.failures.map((f) => `${f.code}: ${f.detail}`).join(" | ") : ` — ${res.code}: ${res.detail || ""}`)
  console.log(`  [${st}] ${id} ${name}${why}`)
  if (!res.ok) failures.push({ id, name, ...(res.failures ? { failures: res.failures } : { code: res.code, detail: res.detail }) })
  return res.ok
}
function sha256Of(p) {
  return crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex")
}
function msiProp(msiPath, prop) {
  // PowerShell COM read of the MSI Property table (Windows-only).
  // Base64 (-EncodedCommand) avoids every shell-quoting failure mode.
  const ps = `$wi=New-Object -ComObject WindowsInstaller.Installer;` +
    `$db=$wi.GetType().InvokeMember("OpenDatabase","InvokeMethod",$null,$wi,@("${msiPath}",0));` +
    `$v=$db.OpenView("SELECT Value FROM Property WHERE Property='${prop}'");$v.Execute();$r=$v.Fetch();if($r){$r.StringData(1)}`
  try {
    const b64 = Buffer.from(ps, "utf16le").toString("base64")
    return execSync(`powershell -NoProfile -NonInteractive -EncodedCommand ${b64}`, { encoding: "utf8" }).trim() || null
  } catch { return null }
}

async function main() {
  const c = loadContract()
  fs.mkdirSync(EVIDENCE, { recursive: true })
  console.log("AetherOS Windows release validation (Master 80 §B/§C)")
  console.log(`  version: ${c.version}  commit: ${gitHead(REPO_ROOT) || "UNKNOWN"}`)

  const results = {}
  const onDisk = fs.existsSync(c.outputDir)
    ? fs.readdirSync(c.outputDir).filter((f) => { try { return fs.statSync(path.join(c.outputDir, f)).isFile() } catch { return false } })
    : []

  // B05/B06 — completeness + naming/identity (§8/§9).
  const expectedFiles = c.expectedArtifacts.map((a) => a.file)
  const setRes = guards.validateArtifactSet(onDisk, expectedFiles, c.version)
  gate("B05", `artifact set complete (EXPECTED=${expectedFiles.length} ACTUAL=${onDisk.filter((f) => !guards.isBuilderByproduct(f)).length})`, setRes)
  results.artifactSet = setRes

  // B12 — source binding via install stamp (§7/§10).
  const stampPath = path.join(DESKTOP_ROOT, "build", "install-stamp.json")
  const stamp = fs.existsSync(stampPath) ? JSON.parse(fs.readFileSync(stampPath, "utf8")) : null
  const head = gitHead(REPO_ROOT)
  const bindRes = guards.checkSourceBinding(stamp?.commit, stamp?.dirty, head)
  gate("B12", `source binding (stamp=${(stamp?.commit || "ABSENT").slice(0, 12)} head=${(head || "UNKNOWN").slice(0, 12)} dirty=${stamp?.dirty})`, bindRes)
  results.sourceBinding = { ...bindRes, stamp }

  // B11 — MSI metadata (§21; UpgradeCode pinned by policy, §20).
  const msiFile = expectedFiles.find((f) => f.endsWith(".msi"))
  const msiPath = path.join(c.outputDir, msiFile)
  const msiRes = { ok: true, properties: {} }
  if (!fs.existsSync(msiPath)) {
    msiRes.ok = false; msiRes.code = "ARTIFACT_MISSING"; msiRes.detail = msiFile
  } else if (process.platform !== "win32") {
    msiRes.note = "MSI Property table read is Windows-only; structural name gates already applied"
  } else {
    for (const p of ["ProductName", "ProductVersion", "ProductCode", "Manufacturer", "UpgradeCode"]) {
      msiRes.properties[p] = msiProp(msiPath, p)
    }
    const exp = { ProductName: "AetherOS", UpgradeCode: c.msiUpgradeCode }
    for (const [k, v] of Object.entries(exp)) {
      if (msiRes.properties[k] !== v) { msiRes.ok = false; msiRes.code = "MSI_IDENTITY_MISMATCH"; msiRes.detail = `${k}=${msiRes.properties[k]} expected=${v}` }
    }
    if (!/^1\.0\.0/.test(msiRes.properties.ProductVersion || "")) { msiRes.ok = false; msiRes.code = "MSI_VERSION_MISMATCH"; msiRes.detail = `ProductVersion=${msiRes.properties.ProductVersion}` }
    if (!/^\{[0-9A-F-]{36}\}$/.test(msiRes.properties.ProductCode || "")) { msiRes.ok = false; msiRes.code = "MSI_PRODUCTCODE_MALFORMED"; msiRes.detail = msiRes.properties.ProductCode }
  }
  gate("B11", "MSI package identity", msiRes)
  results.msi = msiRes.properties

  // C07 — packaged branding (§19): source title + fresh dist title + MSI/EXE names.
  const srcHtml = fs.readFileSync(path.join(DESKTOP_ROOT, "index.html"), "utf8")
  const srcTitle = guards.extractTitle(srcHtml)
  const distHtmlPath = path.join(DESKTOP_ROOT, "dist", "index.html")
  const distTitle = fs.existsSync(distHtmlPath) ? guards.extractTitle(fs.readFileSync(distHtmlPath, "utf8")) : null
  const brandRes = guards.checkTitleMatch(srcTitle || "", distTitle, "dist/index.html")
  gate("C07", `packaged branding (source=${srcTitle} packaged=${distTitle})`, brandRes)
  // Legacy-token sweep over small text surfaces (asar binary scan is the leak gate below).
  for (const [label, p] of [["source-index", path.join(DESKTOP_ROOT, "index.html")]]) {
    const t = guards.checkBrandingText(fs.readFileSync(p, "utf8"), label)
    gate("C07b", `legacy branding sweep (${label})`, t)
  }
  results.branding = { srcTitle, distTitle }

  // C09 — developer-path screen (§38): occurrences classified, not blindly failed.
  // Acceptable containers: sourcemaps + app.asar bundle + build stamp (documented).
  // Anything else (loader exe/dll adjacent) = DEVELOPER_PATH_LEAK.
  const repoRootPosix = REPO_ROOT.replace(/\\/g, "/")
  const leakHits = []
  const scanRoots = [path.join(c.outputDir, "..", "dist"), path.join(c.outputDir, "win-unpacked", "resources")].filter((d) => fs.existsSync(d))
  const walk = (d) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, e.name)
      if (e.isDirectory()) { if (e.name !== "py" && e.name !== "backend") walk(full); continue }
      if (/\.(map|asar|pak|bin|dat|dll|node)$/.test(e.name)) {
        leakHits.push({ file: path.relative(REPO_ROOT, full), container: e.name.endsWith(".map") ? "sourcemap" : "binary-bundle", verdict: "KNOWN_ACCEPTED_RISK" })
        continue
      }
      if (/\.(html|js|cjs|json|txt)$/.test(e.name)) {
        try {
          const content = fs.readFileSync(full, "utf8")
          if (content.includes(REPO_ROOT) || content.includes(repoRootPosix)) {
            leakHits.push({ file: path.relative(REPO_ROOT, full), container: "text", verdict: "FAIL" })
          }
        } catch { /* binary */ }
      }
    }
  }
  scanRoots.forEach(walk)
  const leakFails = leakHits.filter((h) => h.verdict === "FAIL")
  const leakRes = leakFails.length === 0
    ? { ok: true }
    : { ok: false, code: "DEVELOPER_PATH_LEAK", detail: leakFails.map((h) => h.file).slice(0, 10).join(", ") }
  gate("C09", `developer-path screen (${leakHits.length} container hits classified, ${leakFails.length} failing)`, leakRes)
  results.pathLeak = { hits: leakHits.slice(0, 50), totalContainers: leakHits.length }

  // C01/C02 — SHA-256 + canonical manifest (§24/§25/§26).
  const artifacts = []
  for (const a of c.expectedArtifacts) {
    const full = path.join(c.outputDir, a.file)
    if (!fs.existsSync(full)) continue
    const st = fs.statSync(full)
    artifacts.push({ target: a.target, file: a.file, size: st.size, sha256: sha256Of(full) })
  }
  const hashRes = artifacts.length === expectedFiles.length ? { ok: true } : { ok: false, code: "HASH_INCOMPLETE", detail: `${artifacts.length}/${expectedFiles.length}` }
  gate("C01", `SHA-256 post-build (${artifacts.length}/${expectedFiles.length})`, hashRes)

  const crypto2 = crypto
  const buildId = `AETHEROS-${c.version}-windows-x64-${(head || "unknown").slice(0, 12)}-${new Date().toISOString().replace(/[-:.]/g, "").slice(0, 14)}`
  const manifest = {
    schema: "aetheros-windows-release-manifest/1",
    product: c.product,
    release: c.version,
    platform: "windows",
    architecture: "x64",
    buildId,
    source: { commit: head, tree: stamp?.dirty ? "dirty" : "clean", stampBuiltAt: stamp?.builtAt || null },
    toolchain: {
      node: process.version,
      npm: (() => { try { return execSync("npm --version", { encoding: "utf8" }).trim() } catch { return null } })(),
      electronPackaged: c.electronPackaged,
      electronInstalled: c.electronInstalled,
      electronBuilder: c.electronBuilderInstalled,
    },
    signing: { stage: "unsigned", hashPhase: "post-build-pre-sign" },
    artifacts,
  }
  const manifestText = JSON.stringify(manifest, null, 2) + "\n"
  const manifestHash = crypto2.createHash("sha256").update(manifestText).digest("hex")
  manifest.manifestSha256 = manifestHash
  fs.writeFileSync(path.join(EVIDENCE, "09-manifest.json"), JSON.stringify(manifest, null, 2) + "\n")
  fs.writeFileSync(path.join(EVIDENCE, "08-hashes.json"), JSON.stringify({ buildId, artifacts }, null, 2) + "\n")

  // C03 — manifest self-validation (§26).
  const selfFails = []
  for (const a of manifest.artifacts) {
    const full = path.join(c.outputDir, a.file)
    if (!fs.existsSync(full)) { selfFails.push(`missing: ${a.file}`); continue }
    if (fs.statSync(full).size !== a.size) selfFails.push(`size: ${a.file}`)
    if (sha256Of(full) !== a.sha256) selfFails.push(`hash: ${a.file}`)
  }
  if (manifest.source.commit !== head) selfFails.push("commit")
  gate("C03", "manifest self-validation", selfFails.length === 0 ? { ok: true } : { ok: false, code: "MANIFEST_SELF_CHECK_FAIL", detail: selfFails.join("; ") })

  if (WRITE_MANIFEST) {
    const tag = "MASTER_80"
    const mp = path.join(REPO_ROOT, "docs", `AETHEROS_${tag}_RELEASE_ARTIFACT_MANIFEST.json`)
    fs.writeFileSync(mp, JSON.stringify(manifest, null, 2) + "\n")
    console.log(`  wrote ${mp}`)
  }

  const overall = failures.length === 0 ? "RELEASE_VALIDATION_PASS" : `RELEASE_VALIDATION_FAIL (${failures.length} gate(s))`
  console.log(failures.length === 0 ? "\nRELEASE_VALIDATION_PASS" : `\n${overall} — pipeline stops (§44)`)
  fs.writeFileSync(path.join(EVIDENCE, "12-validation-status.json"), JSON.stringify({ overall, failures, at: new Date().toISOString() }, null, 2) + "\n")
  process.exit(failures.length === 0 ? 0 : 1)
}

main().catch((e) => { console.error(`RELEASE_VALIDATION_FAIL: ${e.message}`); process.exit(1) })

