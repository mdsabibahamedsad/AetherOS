#!/usr/bin/env node
// Master 80 §57/§58 — regression tests for historical Windows packaging failures.
// Each test injects a KNOWN-BAD fixture into the SHARED guard functions
// (release-guards.cjs — the same code the live pipeline uses) and expects FAIL.
// A test that does not fail on a bad fixture is itself a failure.
// Run: node scripts/release/windows-release-guards.test.mjs
"use strict"
const { test } = require("node:test")
const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const guards = require("./release-guards.cjs")

const VERSION = "1.0.0"
const EXPECTED = [
  "AetherOS-1.0.0-win-x64.exe",
  "AetherOS-1.0.0-win-x64.msi",
  "AetherOS-1.0.0-win-x64-portable.exe",
]
const HEAD = "a".repeat(40)
const OTHER = "b".repeat(40)

// Test 1 — stale output: artifact bound to an older commit must FAIL.
test("T1 stale artifact (wrong source commit) → ARTIFACT_STALE", () => {
  const r = guards.checkSourceBinding(OTHER, false, HEAD)
  assert.equal(r.ok, false)
  assert.equal(r.code, "ARTIFACT_STALE")
})

// Test 2 — dirty-tree artifact must FAIL even when the commit matches.
test("T2 dirty-tree artifact → ARTIFACT_DIRTY_TREE", () => {
  const r = guards.checkSourceBinding(HEAD, true, HEAD)
  assert.equal(r.ok, false)
  assert.equal(r.code, "ARTIFACT_DIRTY_TREE")
})

// Test 3 — dirty working tree blocks release preflight.
test("T3 dirty tree (untracked file) → RELEASE_BUILD_BLOCKED_DIRTY_TREE", () => {
  const r = guards.checkTreeClean("?? apps/desktop/dist-packaged/AetherOS-1.0.0-win-x64.exe\n M src/x.ts\n")
  assert.equal(r.ok, false)
  assert.equal(r.code, "RELEASE_BUILD_BLOCKED_DIRTY_TREE")
  assert.ok(r.offenders.length === 2)
})
test("T3b clean tree passes", () => {
  assert.equal(guards.checkTreeClean("").ok, true)
})

// Test 4 — wrong version artifact must FAIL.
test("T4 wrong-version artifact → ARTIFACT_WRONG_VERSION", () => {
  const files = ["AetherOS-0.9.9-win-x64.exe", ...EXPECTED.slice(1)]
  const r = guards.validateArtifactSet(files, EXPECTED, VERSION)
  assert.equal(r.ok, false)
  assert.ok(r.failures.some((f) => f.code === "ARTIFACT_WRONG_VERSION"))
})

// Test 5 — wrong architecture artifact must FAIL.
test("T5 wrong-arch artifact → ARTIFACT_WRONG_ARCH", () => {
  const files = [EXPECTED[0], EXPECTED[1], "AetherOS-1.0.0-win-arm64-portable.exe"]
  const r = guards.validateArtifactSet(files, EXPECTED, VERSION)
  assert.equal(r.ok, false)
  assert.ok(r.failures.some((f) => f.code === "ARTIFACT_WRONG_ARCH" || f.code === "ARTIFACT_MISSING" || f.code === "ARTIFACT_UNEXPECTED"))
})

// Test 6 — old branding must FAIL.
test("T6 legacy branding → PACKAGED_BRANDING_MISMATCH", () => {
  const r = guards.checkBrandingText("<title>Hermes Agent</title>", "test-surface")
  assert.equal(r.ok, false)
  assert.equal(r.failures[0].code, "PACKAGED_BRANDING_MISMATCH")
})
test("T6b packaged title mismatch → PACKAGED_BRANDING_MISMATCH", () => {
  const r = guards.checkTitleMatch("AetherOS", "Aetheros", "dist/index.html")
  assert.equal(r.ok, false)
  assert.equal(r.code, "PACKAGED_BRANDING_MISMATCH")
})
test("T6c matching AetherOS titles pass", () => {
  assert.equal(guards.checkTitleMatch("AetherOS", "AetherOS", "x").ok, true)
})

// Test 7 — unexpected output file must FAIL.
test("T7 stray exe in output → ARTIFACT_UNEXPECTED/FOREIGN", () => {
  const r = guards.validateArtifactSet([...EXPECTED, "random-tool.exe"], EXPECTED, VERSION)
  assert.equal(r.ok, false)
  assert.ok(r.failures.some((f) => f.code === "ARTIFACT_UNEXPECTED" || f.code === "ARTIFACT_FOREIGN_FILE"))
})
test("T7b missing artifact → ARTIFACT_MISSING", () => {
  const r = guards.validateArtifactSet(EXPECTED.slice(0, 2), EXPECTED, VERSION)
  assert.equal(r.ok, false)
  assert.ok(r.failures.some((f) => f.code === "ARTIFACT_MISSING"))
})

// Test 8 — lockfile mutation must FAIL.
test("T8 lockfile diff non-empty → LOCKFILE_MUTATED", () => {
  const r = guards.checkLockfileClean("M package-lock.json\n")
  assert.equal(r.ok, false)
  assert.equal(r.code, "LOCKFILE_MUTATED")
})
test("T8b empty diff passes", () => {
  assert.equal(guards.checkLockfileClean("").ok, true)
})

// Test 9 — wrong Node major must FAIL.
test("T9 Node 25 vs canonical 22 → NODE_MAJOR_MISMATCH", () => {
  const r = guards.checkNodeVersion("v25.5.0", 22)
  assert.equal(r.ok, false)
  assert.equal(r.code, "NODE_MAJOR_MISMATCH")
})
test("T9b Node 22 passes", () => {
  assert.equal(guards.checkNodeVersion("v22.12.0", 22).ok, true)
})

// Test 10 — output-directory guard rejects dangerous paths.
test("T10 repo root / home / foreign path rejected", () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "m80-repo-"))
  for (const bad of [repo, os.homedir(), path.parse(repo).root, path.join(repo, "src")]) {
    const r = guards.assertOutputDirSafe(bad, repo)
    assert.equal(r.ok, false, bad)
  }
})
test("T10b canonical output accepted", () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "m80-repo-"))
  const out = path.join(repo, "apps", "desktop", "dist-packaged")
  assert.equal(guards.assertOutputDirSafe(out, repo).ok, true)
})

// Policy lock: other-platform artifacts share dist-packaged/ and must be
// noted (foreignPlatform) without failing the Windows gate; blockmaps are
// electron sidecars, not distributables.
test("T11 linux artifacts noted, windows gate passes", () => {
  const files = [...EXPECTED, "AetherOS-1.0.0-linux-x64.AppImage", "AetherOS-1.0.0-linux-x64.deb"]
  const r = guards.validateArtifactSet(files, EXPECTED, VERSION)
  assert.equal(r.ok, true)
  assert.deepEqual(r.foreignPlatform.sort(), ["AetherOS-1.0.0-linux-x64.AppImage", "AetherOS-1.0.0-linux-x64.deb"])
})
test("T12 blockmap sidecar ignored", () => {
  const r = guards.validateArtifactSet([...EXPECTED, "AetherOS-1.0.0-win-x64.exe.blockmap"], EXPECTED, VERSION)
  assert.equal(r.ok, true)
})

// §13 lockfile contract: root authoritative; standalone desktop lockfile optional.
test("T13 root lockfile + workspace coverage passes without desktop lockfile", () => {
  assert.equal(guards.checkLockfilesPresent(true, false, true).ok, true)
})
test("T13b missing root lockfile fails", () => {
  const r = guards.checkLockfilesPresent(false, true, true)
  assert.equal(r.ok, false)
  assert.equal(r.code, "LOCKFILE_ABSENT")
})
test("T13c uncovered workspace without desktop lockfile fails", () => {
  assert.equal(guards.checkLockfilesPresent(true, false, false).ok, false)
})
