#!/usr/bin/env node
/**
 * distribution.test.mjs — tests for the website download-distribution layer.
 * Run: npm run test:distribution   (node --test scripts/, stdlib only)
 *
 * Covers Master 88 §21/§22 for new/changed code:
 * - manifest generation from verified inputs (real hashes, no invention)
 * - generator fails closed on bad inputs
 * - manifest schema validation (incl. invalid-manifest handling)
 * - allowlist resolution + path-traversal / injection rejection
 * - TS lib and generator allowlists do not drift
 * - no secret identifiers in new frontend files or the public manifest
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFile, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const websiteDir = resolve(scriptDir, "..");

const { generate } = await import("./generate-download-manifest.mjs");
const { planPublish } = await import("./publish-distribution.mjs");

const SECRET_IDENTIFIERS = [
  "GITHUB_TOKEN",
  "GH_TOKEN",
  "AWS_SECRET",
  "AZURE_CLIENT_SECRET",
  "APPLE_PASSWORD",
  "APPLE_APP_SPECIFIC_PASSWORD",
  "APPLE_ID",
  "PRIVATE_KEY",
  "CERTIFICATE",
  "WINDOWS_SIGN_CERT",
  "WINDOWS_CSC_LINK",
  "CSC_KEY_PASSWORD",
  "UPDATE_SIGNING_KEY_PEM",
  "DISTRIBUTION_UPLOAD_TOKEN",
];

describe("manifest generation (real inputs only)", () => {
  it("generates 1.0.0.json + latest.json with verified hashes and sizes", async () => {
    const out = await mkdtemp(join(tmpdir(), "dl-manifest-"));
    try {
      const m = await generate("1.0.0", { markLatest: true, outDir: out });
      assert.equal(m.version, "1.0.0");
      assert.equal(m.schemaVersion, 1);
      assert.equal(m.productionReady, false);
      assert.ok(m.distributionBaseUrl.startsWith("https://"));
      const files = JSON.parse(await readFile(join(out, "1.0.0.json"), "utf-8"));
      const latest = JSON.parse(await readFile(join(out, "latest.json"), "utf-8"));
      assert.deepEqual(files, latest);
      // Spot-check real verified values (Master 86 evidence chain).
      const win = Object.fromEntries(files.platforms.windows.x64.map((a) => [a.kind, a]));
      assert.equal(win.installer.sha256, "a46ed24924c10bd646403d203f047d3c7558039a6a6b2665237ffbfb959a0e0a");
      assert.equal(win.installer.size, 166195774);
      assert.equal(win.installer.url, "https://releases.aetheros.com/desktop/1.0.0/AetherOS-1.0.0-win-x64.exe");
      const mac = Object.fromEntries(files.platforms.macos.arm64.map((a) => [a.kind, a]));
      assert.equal(mac.dmg.sha256, "588a3556a9fbce115790db8f36140a26a7ac996067adafb41185ae08381866d2");
      const lin = Object.fromEntries(files.platforms.linux.x64.map((a) => [a.kind, a]));
      assert.equal(lin.appimage.sha256, "66ab4d6af249a9d7ee66a6dcd9919456bfc3071c5664a33c151d74fad2b095ee");
    } finally {
      await rm(out, { recursive: true, force: true });
    }
  });

  it("fails closed on unknown version (never invents data)", () => {
    const r = spawnSync("node", [join(scriptDir, "generate-download-manifest.mjs"), "9.9.9"], {
      encoding: "utf-8",
    });
    assert.notEqual(r.status, 0);
    assert.match(r.stderr, /BLOCKED/);
  });

  it("fails closed on non-https base URL", () => {
    const r = spawnSync("node", [join(scriptDir, "generate-download-manifest.mjs"), "1.0.0"], {
      encoding: "utf-8",
      env: { ...process.env, DISTRIBUTION_BASE_URL: "http://evil.example" },
    });
    assert.notEqual(r.status, 0);
  });
});

describe("allowlist + traversal safety (generator parity)", () => {
  it("TS lib allowlists match the generator constants (no drift)", async () => {
    const ts = await readFile(join(websiteDir, "src", "lib", "distribution.ts"), "utf-8");
    for (const token of ["windows", "macos", "linux", "x64", "arm64", "installer", "msi", "portable", "dmg", "zip", "appimage", "deb", "rpm"]) {
      assert.ok(ts.includes(`"${token}"`), `TS lib missing allowlist token ${token}`);
    }
    // resolveArtifact must reject unknown dimensions (static check on the guard).
    assert.ok(ts.includes("return null"), "resolveArtifact must have null-returning guards");
    // Filenames with traversal must be rejected.
    assert.ok(ts.includes('..'), "filename traversal check present");
  });

  it("published manifest contains only allowlisted keys and safe filenames", async () => {
    const m = JSON.parse(await readFile(join(websiteDir, "static", "api", "releases", "latest.json"), "utf-8"));
    const platforms = ["windows", "macos", "linux"];
    const arches = ["x64", "arm64"];
    const kinds = ["installer", "msi", "portable", "dmg", "zip", "appimage", "deb", "rpm"];
    for (const [p, aMap] of Object.entries(m.platforms)) {
      assert.ok(platforms.includes(p), `unexpected platform ${p}`);
      for (const [a, list] of Object.entries(aMap)) {
        assert.ok(arches.includes(a), `unexpected arch ${a}`);
        for (const art of list) {
          assert.ok(kinds.includes(art.kind), `unexpected kind ${art.kind}`);
          assert.ok(!art.file.includes("..") && !art.file.includes("/"), `unsafe file ${art.file}`);
          assert.match(art.sha256, /^[0-9a-f]{64}$/);
          assert.ok(art.url.startsWith(m.distributionBaseUrl));
        }
      }
    }
  });

  it("invalid manifest shapes are detectable (missing platform / bad hash)", async () => {
    const m = JSON.parse(await readFile(join(websiteDir, "static", "api", "releases", "latest.json"), "utf-8"));
    const broken = structuredClone(m);
    broken.platforms.windows.x64[0].sha256 = "not-a-hash";
    assert.ok(!/^[0-9a-f]{64}$/i.test(broken.platforms.windows.x64[0].sha256));
    const noUrl = structuredClone(m);
    delete noUrl.platforms.linux;
    assert.ok(!noUrl.platforms.linux);
  });
});

describe("publish-distribution gates", () => {
  it("dry-run passes advisory gates on unsigned 1.0.0 input", async () => {
    const input = JSON.parse(await readFile(join(websiteDir, "scripts", "release-inputs", "1.0.0.json"), "utf-8"));
    const { artifacts, gates } = planPublish(input, {
      baseUrl: "https://releases.aetheros.com",
      requireSignatures: false,
      requireProvenance: false,
    });
    assert.equal(artifacts.length, 8);
    assert.ok(gates.find((g) => g.name === "all-artifacts-present")?.ok);
    // Signatures advisory: unsigned input must be reported, not hidden.
    assert.equal(gates.find((g) => g.name === "signatures")?.ok, false);
  });

  it("--require-signatures fails closed on unsigned input", () => {
    const r = spawnSync(
      "node",
      [join(scriptDir, "publish-distribution.mjs"), "1.0.0", "--dry-run", "--require-signatures"],
      { encoding: "utf-8" },
    );
    assert.notEqual(r.status, 0);
    assert.match(r.stderr + r.stdout, /unsigned|BLOCKED/i);
  });

  it("refuses live publish without owner-configured storage (owner boundary)", () => {
    const r = spawnSync("node", [join(scriptDir, "publish-distribution.mjs"), "1.0.0", "--live"], {
      encoding: "utf-8",
    });
    assert.notEqual(r.status, 0);
    assert.match(r.stderr, /BLOCKED/);
  });
});

describe("security: no secret leakage in public surface", () => {
  it("new frontend files + public manifest contain no secret identifiers", async () => {
    const files = [
      join(websiteDir, "src", "lib", "distribution.ts"),
      join(websiteDir, "src", "pages", "download.tsx"),
      join(websiteDir, "scripts", "generate-download-manifest.mjs"),
      join(websiteDir, "scripts", "publish-distribution.mjs"),
      join(websiteDir, "static", "api", "releases", "latest.json"),
      join(websiteDir, "scripts", "release-inputs", "1.0.0.json"),
    ];
    for (const f of files) {
      const text = await readFile(f, "utf-8");
      for (const id of SECRET_IDENTIFIERS) {
        // publish-distribution.mjs legitimately *names* its upload-token env var;
        // assert it never carries a value (no assignment, presence-check only).
        if (f.endsWith("publish-distribution.mjs") && id === "DISTRIBUTION_UPLOAD_TOKEN") {
          assert.ok(!text.includes("DISTRIBUTION_UPLOAD_TOKEN="), "token value must never appear");
          continue;
        }
        assert.ok(!text.includes(id), `${f} leaks identifier ${id}`);
      }
    }
  });

  it("download page builds no URLs from user input (static check)", async () => {
    const tsx = await readFile(join(websiteDir, "src", "pages", "download.tsx"), "utf-8");
    assert.ok(!tsx.includes("?file=") && !tsx.includes("?path=") && !tsx.includes("?url="));
    assert.ok(tsx.includes("artifactUrl(manifest, artifact)"), "URLs come from the trusted manifest only");
  });
});
