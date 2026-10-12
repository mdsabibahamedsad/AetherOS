import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { orchestratorApi } from "@/lib/orchestrator-api";
import { useOsStore } from "../os/store";
import { OsEmpty, OsError, OsLoading, OsOfflineBanner } from "../os/states";
import { WolfMark } from "../os/WolfMark";

type Phase = "loading" | "ready" | "error";

const card: React.CSSProperties = {
  border: "1px solid rgba(255,255,255,0.09)",
  borderRadius: 12,
  background: "rgba(255,255,255,0.025)",
  padding: "14px 16px",
  minWidth: 0,
};

const h3: React.CSSProperties = { fontSize: 12, textTransform: "uppercase", letterSpacing: "0.1em", opacity: 0.6, margin: "0 0 8px" };

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return "Good night";
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

interface HomeData {
  sessions: number;
  plans: { id: string; goal: string; status: string }[];
  agents: number;
  files: number;
  profiles: number;
}

/**
 * Home — intelligent starting environment. Real backend data only;
 * every section degrades to an honest empty state, never fabricated activity.
 */
export default function HomePage() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState("");
  const [data, setData] = useState<HomeData>({ sessions: 0, plans: [], agents: 0, files: 0, profiles: 0 });
  const offline = useOsStore((s) => s.offline);
  const workspace = useOsStore((s) => s.activeWorkspace);
  const openOverlay = useOsStore((s) => s.openOverlay);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [sessions, plans, agents, files, profiles] = await Promise.allSettled([
          api.getSessions(5, 0),
          orchestratorApi.listPlans("?limit=5"),
          orchestratorApi.listActiveAgents(),
          api.listFiles(),
          api.getProfiles(),
        ]);
        if (cancelled) return;
        setData({
          sessions: sessions.status === "fulfilled" ? (sessions.value?.sessions?.length ?? sessions.value?.total ?? 0) : 0,
          plans: plans.status === "fulfilled"
            ? (plans.value?.plans ?? []).slice(0, 5).map((p: Record<string, unknown>) => ({
              id: String(p.plan_id ?? p.id ?? ""),
              goal: String(p.goal ?? p.title ?? "Untitled plan"),
              status: String(p.status ?? "unknown"),
            }))
            : [],
          agents: agents.status === "fulfilled" ? (Array.isArray(agents.value) ? agents.value.length : 0) : 0,
          files: files.status === "fulfilled" ? (files.value?.files?.length ?? files.value?.total ?? 0) : 0,
          profiles: profiles.status === "fulfilled" ? (Array.isArray(profiles.value) ? profiles.value.length : 0) : 0,
        });
        setPhase("ready");
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load Home.");
          setPhase("error");
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (phase === "loading") return <OsLoading label="Preparing your workspace…" />;
  if (phase === "error") return <OsError body={error} onRetry={() => window.location.reload()} />;

  const hasWork = data.sessions > 0 || data.plans.length > 0 || data.files > 0;

  return (
    <div style={{ maxWidth: 1060, margin: "0 auto", padding: "8px 4px 40px" }}>
      <OsOfflineBanner visible={offline} />
      <header style={{ display: "flex", alignItems: "center", gap: 14, margin: "10px 0 18px" }}>
        <WolfMark size={44} />
        <div>
          <div style={{ fontSize: 11, letterSpacing: "0.16em", opacity: 0.6 }}>AETHEROS · AI OPERATING SYSTEM</div>
          <h1 style={{ fontSize: 24, margin: "2px 0" }}>{greeting()}{workspace ? ` — ${workspace}` : ""}.</h1>
          <div style={{ fontSize: 13, opacity: 0.7 }}>
            {hasWork
              ? `${data.sessions} recent sessions · ${data.plans.length} tracked plans · ${data.agents} active agents`
              : "A quiet system. Start something and it will show up here."}
          </div>
        </div>
      </header>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <button type="button" onClick={() => openOverlay("search")} className="os-btn">Search anything ⌘K</button>
        <Link to="/chat" className="os-btn">Ask AetherOS</Link>
        <Link to="/tasks" className="os-btn">New task</Link>
        <Link to="/launcher" className="os-btn">Launcher</Link>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
        <section style={card} aria-label="Active tasks">
          <h3 style={h3}>Active tasks</h3>
          {data.plans.length === 0 ? (
            <OsEmpty title="No active tasks" body="Tasks you create will appear here with live status, approvals, and artifacts." action={<Link to="/tasks">Open Tasks →</Link>} />
          ) : (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {data.plans.map((p) => (
                <li key={p.id} style={{ fontSize: 13 }}>
                  <Link to={`/tasks?plan=${encodeURIComponent(p.id)}`} style={{ color: "inherit" }}>
                    <strong>{p.goal.slice(0, 80)}</strong>
                  </Link>
                  <div style={{ fontSize: 12, opacity: 0.65 }}>Status: {p.status}</div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section style={card} aria-label="Agents">
          <h3 style={h3}>Agents</h3>
          {data.agents === 0 ? (
            <OsEmpty title="No agents running" body="Spawn agents from a task or the Agent Hub. Their status, tools, and outputs surface here." action={<Link to="/agent-hub">Open Agent Hub →</Link>} />
          ) : (
            <p style={{ fontSize: 13 }}>{data.agents} active agent(s). <Link to="/agent-hub">Inspect →</Link></p>
          )}
        </section>

        <section style={card} aria-label="Recent work">
          <h3 style={h3}>Recent work</h3>
          {data.sessions === 0 && data.files === 0 ? (
            <OsEmpty title="Nothing yet" body="Conversations and files you create will be resumable from here." action={<Link to="/sessions">Open Sessions →</Link>} />
          ) : (
            <p style={{ fontSize: 13 }}>
              {data.sessions} session(s) · {data.files} file(s) · {data.profiles} profile(s).{" "}
              <Link to="/sessions">Sessions →</Link> · <Link to="/files">Files →</Link>
            </p>
          )}
        </section>

        <section style={card} aria-label="System">
          <h3 style={h3}>System</h3>
          <p style={{ fontSize: 13, lineHeight: 1.7, margin: 0 }}>
            <Link to="/system">System center →</Link><br />
            <Link to="/sync">Sync & backup →</Link><br />
            <Link to="/security">Security →</Link>
          </p>
        </section>
      </div>
    </div>
  );
}
