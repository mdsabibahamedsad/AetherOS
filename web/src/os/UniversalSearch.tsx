import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { OS_NAV } from "./ia";
import { fuzzyRank } from "@/lib/fuzzy";
import { useOsStore } from "./store";
import { useOverlayBehavior } from "./overlay";

export interface SearchItem {
  id: string;
  label: string;
  hint: string;
  path: string;
  kind: string;
}

export function buildStaticIndex(): SearchItem[] {
  const apps: SearchItem[] = OS_NAV.map((e) => ({
    id: `app:${e.id}`,
    label: e.label,
    hint: e.description,
    path: e.path,
    kind: "App",
  }));
  const actions: SearchItem[] = [
    { id: "act:new-task", label: "Create task", hint: "Open Tasks and start a new task", path: "/tasks", kind: "Action" },
    { id: "act:open-chat", label: "Ask AetherOS", hint: "Open the agent command surface", path: "/chat", kind: "Action" },
    { id: "act:switch-ws", label: "Switch workspace", hint: "Change active profile context", path: "/workspaces", kind: "Action" },
    { id: "act:notif", label: "View notifications", hint: "Approvals and completions", path: "/agent-hub/notifications", kind: "Action" },
    { id: "act:backup", label: "Check backup status", hint: "Sync, backup and conflicts", path: "/sync", kind: "Action" },
    { id: "act:security", label: "Review security", hint: "Permissions, audit, threats", path: "/security", kind: "Action" },
  ];
  return [...actions, ...apps];
}

/** Universal search / command palette. Ctrl+K or Cmd+K opens it. */
export function UniversalSearch() {
  const overlay = useOsStore((s) => s.overlay);
  const close = useOsStore((s) => s.closeOverlay);
  const open = overlay === "search";
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const panelRef = useOverlayBehavior(open, close, { initialFocusRef: inputRef });
  const index = useMemo(buildStaticIndex, []);

  const results = useMemo(() => {
    const ranked = fuzzyRank(index, query, (i) => `${i.label} ${i.hint} ${i.kind}`);
    return ranked.slice(0, 14).map((r) => r.item);
  }, [index, query]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setCursor(0);
    }
  }, [open ]);

  useEffect(() => setCursor(0), [query]);

  // Keep the active option visible while arrow-keying.
  useEffect(() => {
    document.getElementById(`os-search-opt-${cursor}`)?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  if (!open) return null;

  const go = (item: SearchItem) => {
    close();
    navigate(item.path);
  };

  return (
    <div className="os-veil" role="presentation" onClick={close}>
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label="Universal search"
        onClick={(e) => e.stopPropagation()}
        className="os-panel"
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, results.length - 1)); }
            if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
            if (e.key === "Enter" && results[cursor]) go(results[cursor]);
          }}
          placeholder="Search apps, tasks, agents, files, settings, actions…"
          aria-label="Search AetherOS"
          role="combobox"
          aria-expanded="true"
          aria-controls="os-search-list"
          aria-activedescendant={results[cursor] ? `os-search-opt-${cursor}` : undefined}
          className="os-input"
        />
        <ul id="os-search-list" role="listbox" aria-label="Results" className="os-list" style={{ maxHeight: 380 }}>
          {results.length === 0 && (
            <li style={{ padding: 18, fontSize: 13, opacity: 0.7 }}>
              No matches. Try an app name, setting, or action like “backup”.
            </li>
          )}
          {results.map((r, i) => (
            <li key={r.id} role="option" id={`os-search-opt-${i}`} aria-selected={i === cursor}>
              <button
                type="button"
                onMouseEnter={() => setCursor(i)}
                onClick={() => go(r)}
                className="os-btn"
                style={{
                  width: "100%",
                  border: "none",
                  background: i === cursor ? "color-mix(in srgb, var(--os-accent) 12%, transparent)" : "transparent",
                  justifyContent: "flex-start",
                  minHeight: 44,
                }}
              >
                <span style={{ fontSize: 11, opacity: 0.6, minWidth: 52, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  {r.kind}
                </span>
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ display: "block", fontSize: 13.5, fontWeight: 600 }}>{r.label}</span>
                  <span style={{ display: "block", fontSize: 12, opacity: 0.65, overflow: "hidden", textOverflow: "ellipsis" }}>{r.hint}</span>
                </span>
                <span style={{ fontSize: 11, opacity: 0.5 }}>{r.path}</span>
              </button>
            </li>
          ))}
        </ul>
        <div style={{ padding: "8px 14px", fontSize: 11, opacity: 0.55, borderTop: "1px solid var(--os-border)" }}>
          ↑↓ navigate · Enter open · Esc close · Ctrl+K anywhere
        </div>
      </div>
    </div>
  );
}
