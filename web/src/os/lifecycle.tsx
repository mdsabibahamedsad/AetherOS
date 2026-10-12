import { useOsStore } from "../os/store";
import { WolfMark } from "../os/WolfMark";

/** Boot — premium, fast, wolf-signed startup state. */
export function BootScreen({ onDone }: { onDone: () => void }) {
  const setBooted = useOsStore((s) => s.setBooted);
  return (
    <div
      role="status"
      aria-label="AetherOS starting"
      style={{
        position: "fixed", inset: 0, zIndex: "var(--os-z-critical)", background: "var(--background-base, #060816)",
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14,
      }}
    >
      <WolfMark size={72} />
      <div style={{ letterSpacing: "0.28em", fontSize: 13, opacity: 0.85 }}>AETHEROS</div>
      <div style={{ fontSize: 12, opacity: 0.55 }}>AI Operating System · starting…</div>
      <button
        type="button"
        autoFocus
        onClick={() => { setBooted(true); onDone(); }}
        style={{
          marginTop: 8, border: "1px solid rgba(255,255,255,0.2)", background: "rgba(255,255,255,0.06)",
          color: "inherit", borderRadius: 9, padding: "9px 22px", cursor: "pointer", fontSize: 13,
        }}
      >
        Enter
      </button>
    </div>
  );
}

/** First-run onboarding — progressive disclosure, no config overwhelm. */
export function OnboardingFlow() {
  const setOnboarded = useOsStore((s) => s.setOnboarded);
  const steps = [
    { t: "AetherOS is an operating environment", b: "Home, workspaces, tasks, agents, applications, files, and system — one coherent place, not a chatbot in a dashboard." },
    { t: "Intelligence is built in", b: "Ask in Chat, turn answers into Tasks, watch Agents execute, collect Artifacts. Every step shows real state — never fake progress." },
    { t: "You stay in control", b: "Approvals, permissions, and audit live in Security. Sync, backup, and devices live in System. Nothing syncs or executes silently." },
  ];
  return (
    <div role="dialog" aria-modal="true" aria-label="Welcome to AetherOS"
      style={{ position: "fixed", inset: 0, zIndex: "var(--os-z-critical)", background: "rgba(0,0,0,0.75)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div style={{ width: "min(560px, 100%)", background: "var(--os-surface)", border: "1px solid var(--os-border)", borderRadius: 16, padding: 28, textAlign: "center" }}>
        <WolfMark size={52} />
        <h1 style={{ fontSize: 22, margin: "12px 0 4px" }}>AetherOS</h1>
        <div style={{ fontSize: 12, letterSpacing: "0.2em", opacity: 0.6, marginBottom: 18 }}>AI OPERATING SYSTEM</div>
        {steps.map((s, i) => (
          <div key={s.t} style={{ textAlign: "left", border: "1px solid rgba(255,255,255,0.09)", borderRadius: 10, padding: "12px 14px", marginBottom: 10 }}>
            <div style={{ fontSize: 13.5, fontWeight: 700 }}>{i + 1}. {s.t}</div>
            <div style={{ fontSize: 12.5, opacity: 0.7, marginTop: 4, lineHeight: 1.55 }}>{s.b}</div>
          </div>
        ))}
        <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 16 }}>
          <a href="/home" onClick={() => setOnboarded(true)} style={cta}>Open Home</a>
          <a href="/workspaces" onClick={() => setOnboarded(true)} style={ghost}>Choose workspace</a>
        </div>
        <button type="button" onClick={() => setOnboarded(true)} style={{ background: "none", border: "none", color: "inherit", opacity: 0.55, fontSize: 12, marginTop: 12, cursor: "pointer" }}>
          Skip for now
        </button>
      </div>
    </div>
  );
}

/** Lock — privacy-safe session state; never fakes authentication. */
export function LockScreen() {
  const setLocked = useOsStore((s) => s.setLocked);
  return (
    <div role="dialog" aria-modal="true" aria-label="Session locked"
      style={{ position: "fixed", inset: 0, zIndex: 200, background: "rgba(3,5,12,0.92)", backdropFilter: "blur(10px)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12 }}>
      <WolfMark size={56} />
      <div style={{ fontSize: 15, fontWeight: 700 }}>Session locked</div>
      <div style={{ fontSize: 12.5, opacity: 0.65 }}>Authentication is enforced by the backend. Unlock resumes your session.</div>
      <div style={{ fontSize: 12, opacity: 0.55 }}>{new Date().toLocaleString()}</div>
      <button type="button" autoFocus onClick={() => setLocked(false)} style={cta}>Unlock</button>
    </div>
  );
}

const cta: React.CSSProperties = {
  border: "1px solid rgba(53,224,255,0.5)", background: "rgba(53,224,255,0.12)",
  color: "inherit", borderRadius: 9, padding: "9px 20px", fontSize: 13, cursor: "pointer", textDecoration: "none", display: "inline-block",
};
const ghost: React.CSSProperties = {
  border: "1px solid rgba(255,255,255,0.18)", background: "transparent",
  color: "inherit", borderRadius: 9, padding: "9px 20px", fontSize: 13, cursor: "pointer", textDecoration: "none", display: "inline-block",
};
