import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useOsStore } from "../os/store";
import { OsEmpty, OsError, OsLoading } from "../os/states";

interface Profile {
  name: string;
  [k: string]: unknown;
}

/** Workspaces — profile-anchored environments. Real data from /api/profiles. */
export default function WorkspacesPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [phase, setPhase] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const active = useOsStore((s) => s.activeWorkspace);
  const setWorkspace = useOsStore((s) => s.setWorkspace);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.getProfiles();
        const list: Profile[] = Array.isArray(res) ? res : (res as { profiles?: Profile[] })?.profiles ?? [];
        if (!cancelled) {
          setProfiles(list);
          setPhase("ready");
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load workspaces.");
          setPhase("error");
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (phase === "loading") return <OsLoading label="Loading workspaces…" />;
  if (phase === "error") return <OsError body={error} onRetry={() => window.location.reload()} />;

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "8px 4px 40px" }}>
      <h1 style={{ fontSize: 22 }}>Workspaces</h1>
      <p style={{ fontSize: 13, opacity: 0.7, maxWidth: 640, lineHeight: 1.6 }}>
        A workspace is the environment your work happens in — its files, tasks, agents,
        conversations, and permissions. Switching is instant; state persists per profile on the backend.
      </p>
      {profiles.length === 0 ? (
        <OsEmpty
          title="No workspaces yet"
          body="Create a profile to get an isolated environment with its own config, memory, sessions, and skills."
          action={<a href="/profiles/new">Create workspace →</a>}
        />
      ) : (
        <ul style={{ listStyle: "none", margin: "16px 0", padding: 0, display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
          {profiles.map((p) => {
            const isActive = active === p.name;
            return (
              <li key={p.name} style={{
                border: `1px solid ${isActive ? "color-mix(in srgb, var(--os-accent) 55%, transparent)" : "var(--os-border)"}`,
                borderRadius: 12, padding: "14px 16px",
                background: isActive ? "color-mix(in srgb, var(--os-accent) 7%, transparent)" : "color-mix(in srgb, var(--os-text) 3%, transparent)",
              }}>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{p.name} {isActive && <span style={{ fontSize: 11, opacity: 0.7 }}>· active</span>}</div>
                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                  {!isActive && (
                    <button type="button" onClick={() => setWorkspace(p.name)} className="os-btn">Switch</button>
                  )}
                  <a href={`/profiles?profile=${encodeURIComponent(p.name)}`} className="os-btn">Details →</a>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {active && (
        <button type="button" onClick={() => setWorkspace(null)} className="os-btn" style={{ marginTop: 4 }}>Clear workspace context</button>
      )}
    </div>
  );
}
