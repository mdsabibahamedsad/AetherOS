import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { OS_NAV } from "./ia";
import { fuzzyRank } from "@/lib/fuzzy";
import { useOsStore } from "./store";
import { useOverlayBehavior } from "./overlay";
import { WolfMark } from "./WolfMark";

/** Application launcher overlay — OS capability surface, not a phone grid. */
export function LauncherOverlay() {
  const overlay = useOsStore((s) => s.overlay);
  const close = useOsStore((s) => s.closeOverlay);
  const open = overlay === "launcher";
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const panelRef = useOverlayBehavior(open, close);

  const items = useMemo(() => {
    const ranked = fuzzyRank(OS_NAV, query, (e) => `${e.label} ${e.description} ${e.keywords.join(" ")}`);
    return ranked;
  }, [query]);

  if (!open) return null;

  const launch = (path: string) => {
    close();
    navigate(path);
  };

  return (
    <div className="os-veil" role="presentation" onClick={close}>
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label="Application launcher"
        onClick={(e) => e.stopPropagation()}
        className="os-panel"
        style={{ width: "min(680px, calc(100vw - 32px))", padding: 20 }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <WolfMark size={26} />
          <div>
            <div style={{ fontWeight: 800, letterSpacing: "0.12em", fontSize: 13 }}>AETHEROS LAUNCHER</div>
            <div style={{ fontSize: 12, opacity: 0.6 }}>Every surface, one identity</div>
          </div>
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type to filter applications…"
          aria-label="Filter applications"
          className="os-input"
          style={{ border: "1px solid var(--os-border)", borderRadius: 10, marginBottom: 12 }}
        />
        <div
          role="list"
          aria-label="Applications"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
            gap: 8, maxHeight: 380, overflowY: "auto",
          }}
        >
          {items.map(({ item }) => (
            <button
              key={item.id}
              type="button"
              role="listitem"
              onClick={() => launch(item.path)}
              className="os-btn"
              style={{ textAlign: "left", padding: 12, minHeight: 44, alignItems: "flex-start", flexDirection: "column", gap: 3, whiteSpace: "normal" }}
            >
              <span style={{ fontSize: 13.5, fontWeight: 650 }}>{item.label}</span>
              <span style={{ fontSize: 11.5, opacity: 0.62, lineHeight: 1.4 }}>{item.description}</span>
              <span style={{ fontSize: 10.5, opacity: 0.45, fontFamily: "monospace" }}>{item.path}</span>
            </button>
          ))}
        </div>
        {items.length === 0 && (
          <div style={{ padding: 16, fontSize: 13, opacity: 0.7 }} role="status">No applications match “{query}”.</div>
        )}
      </div>
    </div>
  );
}
