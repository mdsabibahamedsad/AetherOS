"use strict"
// Master 80 §43/§44/§57/§71 — pure, dependency-free guard functions.
//
// Every function here is exercised by windows-release-guards.test.mjs AND
// used by the live pipeline (preflight-windows.mjs, validate-windows-release.mjs).
// A historical failure mode must fail HERE, deterministically, forever.
const path = require("node:path")

// §71 — build-owned output directory safety. Never delete outside these.
function assertOutputDirSafe(outputDir, repoRoot) {
  const resolved = path.resolve(outputDir)
  const root = path.resolve(repoRoot)
  const rel = path.relative(root, resolved)
  const fail = (code, detail) => ({ ok: false, code, detail })
  if (resolved === root) return fail("OUTPUT_IS_REPO_ROOT", resolved)
  if (rel === "" || rel.startsWith("..") || path.isAbsolute(rel)) {
    return fail("OUTPUT_OUTSIDE_REPO", `${resolved} not inside ${root}`)
  }
  const home = path.resolve(process.env.USERPROFILE || process.env.HOME || "~")
  if (resolved === home) return fail("OUTPUT_IS_HOME", resolved)
  const winRoot = path.parse(resolved).root
  if (resolved === winRoot) return fail("OUTPUT_IS_DRIVE_ROOT", resolved)
  const lower = resolved.toLowerCase()
  for (const seg of ["\\windows\\", "\\program files", "system32"]) {
    if (lower.includes(seg)) return fail("OUTPUT_IS_SYSTEM_PATH", resolved)
  }
  // Must be the canonical build-owned directory, nothing else.
  const expected = path.join(root, "apps", "desktop", "dist-packaged")
  if (path.normalize(resolved) !== path.normalize(expected)) {
    return fail("OUTPUT_NOT_BUILD_OWNED", `expected ${expected}, got ${resolved}`)
  }
  return { ok: true }
}

// §4 — release clean-tree gate. ANY porcelain output blocks release.
function checkTreeClean(porcelain) {
  if (porcelain === null) return { ok: false, code: "GIT_STATE_UNKNOWN", detail: "git status failed" }
  const lines = porcelain.split("\n").filter((l) => l.trim() !== "")
  if (lines.length === 0) return { ok: true }
  return {
    ok: false,
    code: "RELEASE_BUILD_BLOCKED_DIRTY_TREE",
    detail: `${lines.length} changed path(s)`,
    offenders: lines.slice(0, 25),
  }
}

// §12 — canonical toolchain gate (major must match .nvmrc/CI).
function checkNodeVersion(actualVersion, canonicalMajor) {
  const m = /^v(\d+)\./.exec(actualVersion || "")
  if (!m) return { ok: false, code: "NODE_VERSION_UNPARSEABLE", detail: String(actualVersion) }
  const major = parseInt(m[1], 10)
  if (major !== canonicalMajor) {
    return { ok: false, code: "NODE_MAJOR_MISMATCH", detail: `actual ${actualVersion}, canonical major ${canonicalMajor}` }
  }
  return { ok: true, major }
}

// §13 — lockfile contract: the ROOT workspace lockfile is authoritative (it
// covers apps/desktop; every CI workflow installs via root `npm ci`). A
// standalone desktop lockfile is accepted when present but NOT required —
// requiring it would enshrine a redundant file as a release gate.
function checkLockfilesPresent(rootLock, deskLock, rootCoversDesktop) {
  if (!rootLock) return { ok: false, code: "LOCKFILE_ABSENT", detail: "root package-lock.json missing" }
  if (!deskLock && !rootCoversDesktop) {
    return { ok: false, code: "LOCKFILE_ABSENT", detail: "desktop workspace not covered by any lockfile" }
  }
  return { ok: true }
}
function checkLockfileClean(diff) {
  if (diff === null) return { ok: false, code: "LOCKFILE_STATE_UNKNOWN", detail: "git diff failed" }
  if (diff.trim() !== "") return { ok: false, code: "LOCKFILE_MUTATED", detail: diff.slice(0, 500) }
  return { ok: true }
}

// §8 — artifact set completeness: exactly the expected set, no more, no less.
function validateArtifactSet(filesOnDisk, expectedFiles, version) {
  const expected = new Set(expectedFiles)
  const actual = filesOnDisk.filter((f) => !isBuilderByproduct(f))
  const missing = expectedFiles.filter((f) => !actual.includes(f))
  const unexpected = actual.filter((f) => !expected.has(f))
  const foreignPlatform = []
  const failures = []
  if (missing.length > 0) failures.push({ code: "ARTIFACT_MISSING", detail: missing.join(", ") })
  for (const u of unexpected) {
    const m = /^AetherOS-(.+?)-(win|linux|macOS|mac)-(.+?)\.(.+)$/.exec(u)
    if (m && m[2] !== "win") {
      // Other-platform artifacts share the output dir (linux/macOS builds).
      // They are NOT Windows release identity: noted, owned by their own
      // platform gates — never silently counted as Windows artifacts.
      foreignPlatform.push(u)
      continue
    }
    failures.push({ code: /AetherOS-/i.test(u) ? "ARTIFACT_UNEXPECTED" : "ARTIFACT_FOREIGN_FILE", detail: u })
  }
  // Wrong-version / wrong-arch / wrong-product detection on anything present.
  // Foreign-platform files are owned by their own platform gates (see above).
  const foreign = new Set(foreignPlatform)
  for (const f of actual) {
    if (foreign.has(f)) continue
    const m = /^AetherOS-(.+?)-(win|linux|macOS|mac)-(.+?)\.(.+)$/.exec(f)
    if (!m) {
      if (!unexpected.includes(f)) failures.push({ code: "ARTIFACT_BAD_NAME", detail: f })
      continue
    }
    const [, fver, fos, farch] = m
    if (fver !== version) failures.push({ code: "ARTIFACT_WRONG_VERSION", detail: `${f}: ${fver} != ${version}` })
    if (fos !== "win") failures.push({ code: "ARTIFACT_WRONG_PLATFORM", detail: f })
    if (!farch.startsWith("x64")) failures.push({ code: "ARTIFACT_WRONG_ARCH", detail: f })
  }
  // Duplicate semantic identity (same bytes under two names is handled by
  // hash stage; here: same target twice).
  const seen = new Set()
  for (const f of actual) {
    const key = f.toLowerCase()
    if (seen.has(key)) failures.push({ code: "ARTIFACT_DUPLICATE", detail: f })
    seen.add(key)
  }
  return { ok: failures.length === 0, failures, foreignPlatform }
}

function isBuilderByproduct(f) {
  if (f.endsWith(".blockmap")) return true // electron differential-update sidecar of an expected exe
  return new Set(["builder-debug.yml", "builder-effective-config.yaml", "latest.yml", "latest-mac.yml", "latest-linux.yml"]).has(f)
}

// §7 — stale artifact: manifest source identity must equal current source.
function checkSourceBinding(manifestCommit, manifestDirty, headCommit) {
  if (!manifestCommit || !headCommit) return { ok: false, code: "SOURCE_IDENTITY_UNKNOWN", detail: "missing commit" }
  if (manifestCommit !== headCommit) {
    return { ok: false, code: "ARTIFACT_STALE", detail: `artifact from ${manifestCommit.slice(0, 12)}, source is ${headCommit.slice(0, 12)}` }
  }
  if (manifestDirty) return { ok: false, code: "ARTIFACT_DIRTY_TREE", detail: "release artifact built from dirty tree" }
  return { ok: true }
}

// §19 — packaged branding: old tokens fail, hard.
const OLD_BRANDING = ["Hermes Agent", "HERMES AGENT"]
function checkBrandingText(haystack, where) {
  const failures = []
  for (const token of OLD_BRANDING) {
    if (haystack.includes(token)) failures.push({ code: "PACKAGED_BRANDING_MISMATCH", detail: `${where} contains legacy branding ${JSON.stringify(token)}` })
  }
  return { ok: failures.length === 0, failures }
}

// Title check: source title must be AetherOS; packaged title must match source.
function checkTitleMatch(sourceTitle, packagedTitle, where) {
  if (!/AetherOS/.test(sourceTitle)) return { ok: false, code: "SOURCE_TITLE_WRONG", detail: `source: ${sourceTitle}` }
  if (packagedTitle === null) return { ok: false, code: "PACKAGED_TITLE_ABSENT", detail: where }
  if (!/AetherOS/.test(packagedTitle)) {
    return { ok: false, code: "PACKAGED_BRANDING_MISMATCH", detail: `${where}: source=AetherOS, packaged=${packagedTitle}` }
  }
  return { ok: true }
}

function extractTitle(html) {
  const m = /<title>(.*?)<\/title>/s.exec(html || "")
  return m ? m[1] : null
}

module.exports = {
  assertOutputDirSafe,
  checkTreeClean,
  checkNodeVersion,
  checkLockfileClean,
  checkLockfilesPresent,
  validateArtifactSet,
  isBuilderByproduct,
  checkSourceBinding,
  checkBrandingText,
  checkTitleMatch,
  extractTitle,
}
