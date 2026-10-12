import React, {useEffect, useState} from "react";
import Layout from "@theme/Layout";
import {
  artifactUrl,
  formatBytes,
  validateManifest,
  type ArtifactKind,
  type ReleaseArtifact,
  type ReleaseManifest,
} from "@site/src/lib/distribution";
import styles from "./download.module.css";

// Routes Docusaurus serves the static download manifest from. `baseUrl` is
// `/docs/`, `static/api/` ends up at `/docs/api/`. Same hardcoding convention
// as src/pages/skills/index.tsx.
const MANIFEST_URL = "/docs/api/releases/latest.json";

const KIND_LABELS: Record<ArtifactKind, string> = {
  installer: "EXE installer",
  msi: "MSI installer",
  portable: "Portable EXE",
  dmg: "DMG disk image",
  zip: "ZIP archive",
  appimage: "AppImage",
  deb: "DEB package",
  rpm: "RPM package",
};

const PLATFORM_ORDER = ["windows", "macos", "linux"] as const;
const PLATFORM_TITLES: Record<string, string> = {
  windows: "Windows",
  macos: "macOS",
  linux: "Linux",
};

function detectPlatform(): string | null {
  try {
    const p = (navigator as Navigator).platform || "";
    if (/win/i.test(p)) return "windows";
    if (/mac/i.test(p)) return "macos";
    if (/linux/i.test(p)) return "linux";
  } catch {
    // ignore — detection only highlights a card, never builds URLs
  }
  return null;
}

function ArtifactRow({manifest, artifact}: {manifest: ReleaseManifest; artifact: ReleaseArtifact}) {
  const [copied, setCopied] = useState(false);
  const url = artifactUrl(manifest, artifact);
  const copySha = async () => {
    try {
      await navigator.clipboard.writeText(artifact.sha256);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable — the hash is still fully visible below
    }
  };
  return (
    <div className={styles.artifact}>
      <div className={styles.artifactHead}>
        <strong>{KIND_LABELS[artifact.kind] ?? artifact.kind}</strong>
        {url ? (
          <a className={styles.button} href={url} download={artifact.file}>
            Download
          </a>
        ) : (
          <span className={styles.unavailable}>Unavailable</span>
        )}
      </div>
      <div className={styles.file}>{artifact.file}</div>
      <div className={styles.meta}>
        {formatBytes(artifact.size)} · SHA-256:
      </div>
      <code className={styles.sha}>{artifact.sha256}</code>
      <button type="button" className={styles.copy} onClick={() => void copySha()}>
        {copied ? "Copied" : "Copy hash"}
      </button>
    </div>
  );
}

export default function DownloadPage() {
  const [manifest, setManifest] = useState<ReleaseManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mine, setMine] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(MANIFEST_URL);
        if (!r.ok) throw new Error(`release manifest HTTP ${r.status}`);
        const m = (await r.json()) as unknown;
        const problem = validateManifest(m);
        if (problem) throw new Error(`invalid release manifest: ${problem}`);
        if (cancelled) return;
        setManifest(m as ReleaseManifest);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
    setMine(detectPlatform());
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Layout title="Download AetherOS" description="Download the AetherOS desktop app for Windows, macOS, and Linux.">
      <main className={styles.page}>
        <h1>Download AetherOS</h1>
        {error && (
          <div className={`${styles.notice} ${styles.noticeError}`} role="alert">
            Release metadata is currently unavailable ({error}). Public desktop
            distribution is pending — check back after the next signed release.
          </div>
        )}
        {!error && !manifest && <p>Loading release metadata…</p>}
        {manifest && (
          <>
            <p className={styles.version}>
              AetherOS {manifest.version} · {manifest.channel} · released{" "}
              {manifest.releaseDate}
            </p>
            {!manifest.productionReady && (
              <div className={`${styles.notice} ${styles.noticeWarn}`} role="note">
                Pre-production build: artifacts are currently{" "}
                {Object.entries(manifest.signatures)
                  .map(([k, v]) => `${k} ${v}`)
                  .join(", ")}
                . This page never advertises an artifact as production-ready
                unless its required signing and verification gates pass.
              </div>
            )}
            <div className={styles.grid}>
              {PLATFORM_ORDER.filter((p) => manifest.platforms[p]).map((platform) => (
                <section
                  key={platform}
                  className={mine === platform ? `${styles.card} ${styles.cardMine}` : styles.card}
                  aria-label={PLATFORM_TITLES[platform]}
                >
                  <h2>
                    {PLATFORM_TITLES[platform]}
                    {mine === platform && <span className={styles.badge}>Your OS</span>}
                  </h2>
                  {Object.entries(manifest.platforms[platform]).map(([arch, list]) => (
                    <div key={arch}>
                      <h3 className={styles.arch}>{arch}</h3>
                      {list.map((a) => (
                        <ArtifactRow key={a.file} manifest={manifest} artifact={a} />
                      ))}
                    </div>
                  ))}
                </section>
              ))}
            </div>
            <h2>Verify your download</h2>
            <p>
              Compare the SHA-256 of the file you downloaded against the hash
              shown above — the authoritative value comes from the release
              pipeline, not from your browser:
            </p>
            <ul>
              <li>
                Windows (PowerShell):{" "}
                <code>Get-FileHash ./{"{filename}"} -Algorithm SHA256</code>
              </li>
              <li>
                macOS / Linux: <code>shasum -a 256 {"{filename}"}</code>
              </li>
            </ul>
            <p className={styles.source}>
              Built from source commit {manifest.sourceCommit} (workflow run{" "}
              {manifest.workflowRun}). Source stays private; only these release
              bytes are distributed.
            </p>
          </>
        )}
      </main>
    </Layout>
  );
}
