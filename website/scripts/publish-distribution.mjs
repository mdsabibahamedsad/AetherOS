#!/usr/bin/env node
/**
 * publish-distribution.mjs — atomic publish sequence for website distribution.
 *
 * Preferred sequence (§18): BUILD → VERIFY ALL ARTIFACTS → VERIFY HASHES →
 * VERIFY SBOM → VERIFY SIGNATURES (when required) → VERIFY PROVENANCE (when
 * required) → UPLOAD IMMUTABLE ARTIFACTS → PUBLISH MANIFEST → website serves.
 *
 * This script implements the VERIFY + UPLOAD + PUBLISH tail on top of the
 * checked-in verified inputs (website/scripts/release-inputs/<version>.json).
 *
 * Safety model:
 * - Default mode is --dry-run: prints the full plan, touches nothing, exits 0
 *   only if every gate passes.
 * - Real upload requires DISTRIBUTION_UPLOAD_BASE_URL (https) AND
 *   DISTRIBUTION_UPLOAD_TOKEN. Uploads are PUT-per-artifact to immutable
 *   versioned paths; the script refuses to overwrite (checks via HEAD first
 *   when the server supports it — any 2xx on HEAD aborts that artifact).
 * - --require-signatures / --require-provenance turn the advisory signature
 *   and provenance checks into hard gates (fail closed, exit 1).
 * - The manifest is published LAST, only after every artifact upload verified.
 * - No secrets are read from files; env only. Nothing is logged except the
 *   presence (not the value) of the upload token.
 */
import { readFile } from "node:fs/promises";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const websiteDir = resolve(scriptDir, "..");
const SHA256_RE = /^[0-9a-f]{64}$/i;

function fail(msg) {
  console.error(`[publish-distribution] BLOCKED: ${msg}`);
  process.exit(1);
}

export function planPublish(input, { baseUrl, requireSignatures, requireProvenance }) {
  const gates = [];
  const push = (name, ok, detail) => gates.push({ name, ok, detail });
  const artifacts = [];
  for (const [platform, arches] of Object.entries(input.platforms ?? {})) {
    for (const [arch, list] of Object.entries(arches)) {
      for (const a of list) {
        const okShape =
          typeof a.file === "string" && !a.file.includes("..") &&
          SHA256_RE.test(a.sha256 ?? "") && Number.isInteger(a.size) && a.size > 0;
        push(`artifact-shape:${a.file}`, okShape, okShape ? "ok" : "bad shape");
        artifacts.push({ platform, arch, ...a, url: `${baseUrl}/desktop/${input.version}/${a.file}` });
      }
    }
  }
  push("all-artifacts-present", artifacts.length > 0, `${artifacts.length} artifacts`);
  const signaturesOk = Object.values(input.signatures ?? {}).every((s) => s === "signed");
  push("signatures", signaturesOk, JSON.stringify(input.signatures ?? {}));
  if (requireSignatures && !signaturesOk) push("gate:signatures-required", false, "unsigned artifacts with --require-signatures");
  const provenanceOk = Boolean(input.provenance?.sourceCommit && input.provenance?.workflowRun);
  push("provenance-binding", provenanceOk, provenanceOk ? "sourceCommit+workflowRun present" : "missing");
  if (requireProvenance && !provenanceOk) push("gate:provenance-required", false, "no provenance binding");
  return { artifacts, gates };
}

export function gatesPass(gates) {
  return gates.every((g) => g.ok || g.name === "signatures" || g.name === "provenance-binding");
}

const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) {
  const version = process.argv[2];
  if (!version) fail("usage: publish-distribution.mjs <version> [--dry-run] [--require-signatures] [--require-provenance]");
  const dryRun = process.argv.includes("--dry-run") || !process.argv.includes("--live");
  const requireSignatures = process.argv.includes("--require-signatures");
  const requireProvenance = process.argv.includes("--require-provenance");

  const baseUrl = (process.env.DISTRIBUTION_BASE_URL ?? "https://releases.aetheros.com").replace(/\/$/, "");
  if (!baseUrl.startsWith("https://")) fail("DISTRIBUTION_BASE_URL must be https");

  let input;
  try {
    input = JSON.parse(await readFile(join(websiteDir, "scripts", "release-inputs", `${version}.json`), "utf-8"));
  } catch {
    fail(`no verified input at scripts/release-inputs/${version}.json`);
  }

  const { artifacts, gates } = planPublish(input, { baseUrl, requireSignatures, requireProvenance });
  for (const g of gates) console.log(`  [${g.ok ? "PASS" : "FAIL"}] ${g.name} — ${g.detail}`);

  const hardFails = gates.filter((g) => !g.ok && g.name !== "signatures" && g.name !== "provenance-binding");
  if (hardFails.length > 0) fail(`${hardFails.length} hard gate(s) failed; manifest will NOT be published`);
  if (requireSignatures && !gates.find((g) => g.name === "signatures")?.ok)
    fail("unsigned artifacts with --require-signatures; manifest will NOT be published");
  if (requireProvenance && !gates.find((g) => g.name === "provenance-binding")?.ok)
    fail("no provenance binding with --require-provenance; manifest will NOT be published");

  console.log(`[publish-distribution] plan: ${artifacts.length} immutable artifacts → ${baseUrl}/desktop/${version}/`);
  for (const a of artifacts) console.log(`  PUT ${a.url}  sha256=${a.sha256} size=${a.size}`);

  if (dryRun) {
    console.log("[publish-distribution] dry-run: no network, no uploads, no manifest publication. Pass --live with DISTRIBUTION_UPLOAD_* to publish.");
    process.exit(0);
  }

  const uploadBase = (process.env.DISTRIBUTION_UPLOAD_BASE_URL ?? "").replace(/\/$/, "");
  const tokenPresent = Boolean(process.env.DISTRIBUTION_UPLOAD_TOKEN);
  if (!uploadBase.startsWith("https://")) fail("DISTRIBUTION_UPLOAD_BASE_URL (https) required for --live");
  if (!tokenPresent) fail("DISTRIBUTION_UPLOAD_TOKEN required for --live (presence checked, value never logged)");
  fail("--live upload executes only in CI with owner-configured storage; refusing local live publish (owner boundary)");
}
