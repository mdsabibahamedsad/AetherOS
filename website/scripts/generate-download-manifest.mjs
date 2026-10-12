#!/usr/bin/env node
/**
 * generate-download-manifest.mjs — build the public website download manifest
 * from VERIFIED pipeline inputs. Never invents hashes, sizes, or URLs.
 *
 * Input:  website/scripts/release-inputs/<version>.json (checked-in pipeline
 *         facts: filenames + sha256 + sizes + provenance, as certified by
 *         the release evidence chain; kept beside this script because the
 *         repo gitignores website/data/ as generated scratch).
 * Output: website/static/api/releases/<version>.json
 *         website/static/api/releases/latest.json (only when --mark-latest)
 *
 * URL scheme: ${DISTRIBUTION_BASE_URL}/desktop/<version>/<file>
 * Default base: https://releases.aetheros.com (the project's established
 * distribution domain — see services/update/update-server.ts and
 * services/update/scripts/publish-manifest.mjs). Override via
 * DISTRIBUTION_BASE_URL (must be https).
 *
 * Fails closed (exit 1) on: missing input, bad sha256/size/filename,
 * unknown platform/arch/kind, non-https base URL.
 */
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const websiteDir = resolve(scriptDir, "..");

const KNOWN_PLATFORMS = ["windows", "macos", "linux"];
const KNOWN_ARCHES = ["x64", "arm64"];
const KNOWN_KINDS = ["installer", "msi", "portable", "dmg", "zip", "appimage", "deb", "rpm"];
const SHA256_RE = /^[0-9a-f]{64}$/i;

function fail(msg) {
  console.error(`[generate-download-manifest] BLOCKED: ${msg}`);
  process.exit(1);
}

export async function generate(version, { markLatest = false, outDir = null } = {}) {
  const baseUrl = (process.env.DISTRIBUTION_BASE_URL ?? "https://releases.aetheros.com").replace(/\/$/, "");
  if (!baseUrl.startsWith("https://")) fail("DISTRIBUTION_BASE_URL must be https");

  let input;
  try {
    input = JSON.parse(
      await readFile(join(websiteDir, "scripts", "release-inputs", `${version}.json`), "utf-8"),
    );
  } catch {
    fail(`no verified input at scripts/release-inputs/${version}.json (refusing to invent manifest data)`);
  }
  if (input.version !== version) fail(`input version mismatch: ${input.version} != ${version}`);

  // Strict validation of every artifact field.
  for (const [platform, arches] of Object.entries(input.platforms ?? {})) {
    if (!KNOWN_PLATFORMS.includes(platform)) fail(`unknown platform ${platform}`);
    for (const [arch, list] of Object.entries(arches)) {
      if (!KNOWN_ARCHES.includes(arch)) fail(`unknown arch ${arch}`);
      if (!Array.isArray(list) || list.length === 0) fail(`empty artifact list for ${platform}/${arch}`);
      for (const a of list) {
        if (!KNOWN_KINDS.includes(a.kind)) fail(`unknown kind ${a.kind}`);
        if (typeof a.file !== "string" || a.file.includes("..") || a.file.includes("/") || a.file.includes("\\"))
          fail(`unsafe filename ${a.file}`);
        if (!SHA256_RE.test(a.sha256 ?? "")) fail(`bad sha256 for ${a.file}`);
        if (!Number.isInteger(a.size) || a.size <= 0) fail(`bad size for ${a.file}`);
      }
    }
  }

  const platforms = {};
  for (const [platform, arches] of Object.entries(input.platforms)) {
    platforms[platform] = {};
    for (const [arch, list] of Object.entries(arches)) {
      platforms[platform][arch] = list.map((a) => ({
        kind: a.kind,
        file: a.file,
        url: `${baseUrl}/desktop/${version}/${a.file}`,
        sha256: a.sha256.toLowerCase(),
        size: a.size,
      }));
    }
  }

  const manifest = {
    schemaVersion: 1,
    product: "AetherOS",
    version,
    channel: input.channel ?? "stable",
    releaseDate: input.releaseDate,
    distributionBaseUrl: baseUrl,
    sourceCommit: input.provenance?.sourceCommit ?? "unknown",
    workflowRun: input.provenance?.workflowRun ?? "unknown",
    signed: false,
    productionReady: false,
    signatures: input.signatures ?? {},
    platforms,
    generatedBy: "website/scripts/generate-download-manifest.mjs",
    generatedAt: new Date().toISOString(),
  };

  const dest = outDir ?? join(websiteDir, "static", "api", "releases");
  await mkdir(dest, { recursive: true });
  await writeFile(join(dest, `${version}.json`), JSON.stringify(manifest, null, 2) + "\n");
  if (markLatest) {
    await writeFile(join(dest, "latest.json"), JSON.stringify(manifest, null, 2) + "\n");
  }
  return manifest;
}

// CLI: node scripts/generate-download-manifest.mjs <version> [--mark-latest] [--out-dir <dir>]
const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) {
  const version = process.argv[2];
  if (!version) fail("usage: generate-download-manifest.mjs <version> [--mark-latest] [--out-dir <dir>]");
  const markLatest = process.argv.includes("--mark-latest");
  const outIdx = process.argv.indexOf("--out-dir");
  const outDir = outIdx >= 0 ? process.argv[outIdx + 1] : null;
  if (outIdx >= 0 && !outDir) fail("--out-dir requires a directory");
  const manifest = await generate(version, { markLatest, outDir });
  const count = Object.values(manifest.platforms).flatMap((a) => Object.values(a)).flat().length;
  console.log(`[generate-download-manifest] wrote ${version}.json${markLatest ? " + latest.json" : ""} (${count} artifacts, signed=false, productionReady=false)`);
}
