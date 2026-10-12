import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useOsStore } from "./store";
import { useOverlayBehavior } from "./overlay";
import { WolfMark } from "./WolfMark";

function bar(label: string, to: string, detail?: string) {
  return { label, to, detail };
}

/**
 * Canonical OS top bar: wolf identity, workspace context, global search entry,
 * launcher, live task/agent indicators, notifications, account.
 */
export function OsTopBar({ activeTasks, activeAgents }: { activeTasks: number; activeAgents: number }) {
  const openOverlay = useOsStore((s) => s.openOverlay);
  const workspace = useOsStore((s) => s.activeWorkspace);
  const offline = useOsStore((s) => s.offline);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        openOverlay("search");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openOverlay]);

  return (
    <div role="banner" aria-label="AetherOS system bar" className="os-topbar">
      <Link to="/home" aria-label="AetherOS Home" style={{ display: "inline-flex", alignItems: "center", gap: 8, color: "inherit", textDecoration: "none" }}>
        <WolfMark size={22} />
        <span style={{ fontWeight: 800, letterSpacing: "0.14em", fontSize: 12 }}>AETHEROS</span>
      </Link>

      <span
        role="status"
        title="Workspace context"
        style={{ fontSize: 12, opacity: 0.75, border: "1px solid var(--os-border)", borderRadius: 99, padding: "3px 10px" }}
      >
        {workspace ? `Workspace: ${workspace}` : "No workspace selected"}
      </span>

      <button type="button" className="os-btn" style={{ flex: "1 1 160px" }} onClick={() => openOverlay("search")} aria-label="Open universal search (Control K)">
        <span aria-hidden="true">⌘</span> Search AetherOS… <kbd style={{ opacity: 0.6 }}>Ctrl+K</kbd>
      </button>

      <button type="button" className="os-btn" onClick={() => openOverlay("launcher")}>Launcher</button>

      <Link to="/tasks" className="os-btn" aria-label={`${activeTasks} active tasks`}>
        <span aria-hidden="true">●</span> {activeTasks} tasks
      </Link>
      <Link to="/agent-hub" className="os-btn" aria-label={`${activeAgents} active agents`}>
        <span aria-hidden="true">●</span> {activeAgents} agents
      </Link>

      {offline && (
        <span role="status" style={{ fontSize: 12, color: "var(--os-warn)" }}>Offline</span>
      )}

      <button type="button" className="os-btn" onClick={() => openOverlay("notifications")} aria-label="Open notifications">
        Notifications
      </button>
      <button type="button" className="os-btn" onClick={() => openOverlay("quick-settings")} aria-label="Open quick settings">
        Settings
      </button>
      <button type="button" className="os-btn" onClick={() => openOverlay("system")} aria-label="Open system center">
        System
      </button>
    </div>
  );
}

interface Notice {
  id: string;
  title: string;
  detail: string;
  severity: "info" | "approval" | "security" | "error";
  link: string;
}

export function OsDrawers() {
  const overlay = useOsStore((s) => s.overlay);
  const close = useOsStore((s) => s.closeOverlay);
  const open = overlay === "notifications" || overlay === "system" || overlay === "quick-settings";
  const panelRef = useOverlayBehavior(open, close);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    (async () => {
      try {
        const found: Notice[] = [];
        try {
          const tasks = await api.listTasks?.();
          const list = Array.isArray(tasks) ? tasks : (tasks as { tasks?: unknown[] })?.tasks ?? [];
          for (const t of (list as Record<string, unknown>[]).slice(0, 5)) {
            const st = String(t.status ?? "unknown");
            if (["failed", "blocked", "waiting_for_approval", "WAITING_FOR_APPROVAL"].includes(st)) {
              found.push({
                id: `task-${String(t.id ?? st)}`,
                title: `Task ${st}: ${String(t.goal ?? t.id ?? "untitled")}`.slice(0, 90),
                detail: "Open the task to review approvals, errors, or retry.",
                severity: st.includes("approval") ? "approval" : "error",
                link: "/tasks",
              });
            }
          }
        } catch { /* tasks endpoint optional — empty state below covers it */ }
        try {
          const sync = await api.getSyncStatus?.();
          const s = sync as Record<string, unknown> | undefined;
          if (s && (s.conflicts || s.pending || s.failed)) {
            found.push({
              id: "sync-state",
              title: "Sync needs attention",
              detail: String(s.summary ?? "Conflicts or pending changes exist. Open Sync to resolve."),
              severity: "info",
              link: "/sync",
            });
          }
        } catch { /* optional */ }
        if (!cancelled) {
          setNotices(found);
          setStatus("");
        }
      } catch (e) {
        if (!cancelled) setStatus(e instanceof Error ? e.message : "Failed to load live status.");
      }
    })();
    return () => { cancelled = true; };
  }, [open, overlay]);

  if (!open) return null;

  const title = overlay === "notifications" ? "Notifications" : overlay === "quick-settings" ? "Quick settings" : "System center";
  const items = overlay === "quick-settings"
    ? [bar("Appearance", "/config?section=appearance", "Theme, density, contrast"), bar("Notifications", "/config?section=notifications", "What interrupts you"), bar("Privacy", "/config?section=privacy", "Memory and telemetry"), bar("Sync", "/sync", "Sync state and conflicts"), bar("Devices", "/sync/devices", "Registered devices")]
    : overlay === "system"
      ? [bar("Security", "/security", "Approvals, policies, audit"), bar("Sync & Backup", "/sync", "Health, conflicts, history"), bar("Models", "/models", "Availability and routing"), bar("System", "/system", "Telemetry and services"), bar("Settings", "/config", "All settings")]
      : [];

  return (
    <div className="os-veil os-veil--right" role="presentation" onClick={close}>
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        className="os-panel os-panel--drawer"
        style={{ padding: 18 }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ fontSize: 15, margin: 0 }}>{title}</h2>
          <button type="button" onClick={close} aria-label={`Close ${title}`} className="os-btn">Close</button>
        </div>

        {overlay === "notifications" && (
          <>
            {status && <p role="alert" style={{ fontSize: 12.5, color: "var(--os-danger)" }}>{status}</p>}
            {notices.length === 0 && !status && (
              <p style={{ fontSize: 13, opacity: 0.7, lineHeight: 1.6 }}>
                You’re caught up. Approvals, task completions, security alerts, and sync conflicts will appear here with deep links — never fabricated.
              </p>
            )}
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {notices.map((n) => (
                <li key={n.id} style={{ border: "1px solid var(--os-border)", borderRadius: 10, padding: "10px 12px", borderLeft: `3px solid ${n.severity === "security" ? "var(--os-danger)" : n.severity === "approval" ? "var(--os-warn)" : n.severity === "error" ? "var(--os-danger)" : "var(--os-accent)"}` }}>
                  <div style={{ fontSize: 11, opacity: 0.6, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                    <span aria-hidden="true">{n.severity === "info" ? "ℹ " : n.severity === "approval" ? "✋ " : "⚠ "}</span>{n.severity}
                  </div>
                  <div style={{ fontSize: 13.5, fontWeight: 650, margin: "3px 0" }}>{n.title}</div>
                  <div style={{ fontSize: 12.5, opacity: 0.7 }}>{n.detail}</div>
                  <Link to={n.link} onClick={close} style={{ fontSize: 12.5, color: "var(--os-accent)" }}>Open →</Link>
                </li>
              ))}
            </ul>
          </>
        )}

        {overlay !== "notifications" && (
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            {items.map((i) => (
              <li key={i.label} style={{ border: "1px solid var(--os-border)", borderRadius: 10, padding: "10px 12px" }}>
                <Link to={i.to} onClick={close} style={{ color: "inherit", textDecoration: "none" }}>
                  <div style={{ fontSize: 13.5, fontWeight: 650 }}>{i.label} →</div>
                  {i.detail && <div style={{ fontSize: 12.5, opacity: 0.65 }}>{i.detail}</div>}
                </Link>
              </li>
            ))}
          </ul>
        )}

        <p style={{ fontSize: 11.5, opacity: 0.55, marginTop: 16 }}>
          Only controls supported by the backend are shown. No decorative toggles.
        </p>
      </div>
    </div>
  );
}
