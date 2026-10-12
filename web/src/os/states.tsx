import type { ReactNode } from "react";
import { WolfMark } from "./WolfMark";

export function OsEmpty({
  title: t,
  body: b,
  action,
  icon,
}: {
  title: string;
  body: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="os-state" role="status" aria-label={t}>
      {icon ?? <WolfMark size={36} />}
      <div className="os-state__title">{t}</div>
      <div className="os-state__body">{b}</div>
      {action}
    </div>
  );
}

export function OsLoading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="os-state" aria-busy="true" aria-live="polite">
      <WolfMark size={32} />
      <div className="os-state__title">{label}</div>
      <div className="os-state__body">Fetching live state from the AetherOS backend.</div>
      <div className="os-loading-bar" aria-hidden="true">
        <div />
      </div>
    </div>
  );
}

export function OsError({
  title: t = "Something went wrong",
  body: b = "The request failed. Check the backend connection and try again.",
  onRetry,
  detail,
}: {
  title?: string;
  body?: string;
  onRetry?: () => void;
  detail?: string;
}) {
  return (
    <div className="os-state" role="alert">
      <div style={{ fontSize: 22 }} aria-hidden="true">⚠</div>
      <div className="os-state__title">{t}</div>
      <div className="os-state__body">{b}</div>
      {detail && (
        <details style={{ fontSize: 12, opacity: 0.7, marginBottom: 12, textAlign: "left" }}>
          <summary>Technical detail</summary>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{detail}</pre>
        </details>
      )}
      {onRetry && (
        <button type="button" onClick={onRetry} className="os-btn os-btn--primary">
          Retry
        </button>
      )}
    </div>
  );
}

export function OsOfflineBanner({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <div
      role="status"
      style={{
        background: "color-mix(in srgb, var(--os-warn) 12%, transparent)",
        border: "1px solid color-mix(in srgb, var(--os-warn) 40%, transparent)",
        color: "var(--os-text)",
        fontSize: 12.5,
        padding: "8px 14px",
        borderRadius: 10,
        marginBottom: 12,
      }}
    >
      <span aria-hidden="true">⚠ </span>
      <strong>Offline</strong> — showing local state. Changes will sync when the connection returns.
    </div>
  );
}

export function OsPermissionNote({ what, why }: { what: string; why: string }) {
  return (
    <div
      role="note"
      style={{
        border: "1px solid color-mix(in srgb, var(--os-accent) 40%, transparent)",
        background: "color-mix(in srgb, var(--os-accent) 8%, transparent)",
        borderRadius: 10,
        padding: "10px 14px",
        fontSize: 12.5,
        lineHeight: 1.5,
      }}
    >
      <strong>Permission required — {what}.</strong> {why}
    </div>
  );
}
