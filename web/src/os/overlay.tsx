import { useEffect, useRef } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Shared overlay behavior: Escape closes, background scroll locks, focus is
 * trapped inside while open and returned to the invoker on close.
 * Every dialog/drawer/palette in the OS layer must use this.
 */
export function useOverlayBehavior(
  open: boolean,
  onClose: () => void,
  options: { initialFocusRef?: React.RefObject<HTMLElement | null> } = {},
) {
  const panelRef = useRef<HTMLDivElement>(null);
  const invokerRef = useRef<Element | null>(null);

  useEffect(() => {
    if (!open) return;
    invokerRef.current = document.activeElement;

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Focus the panel (or a designated initial element) on mount.
    const t = window.setTimeout(() => {
      const target =
        options.initialFocusRef?.current ??
        panelRef.current?.querySelector<HTMLElement>(FOCUSABLE) ??
        panelRef.current;
      target?.focus?.();
    }, 30);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panelRef.current) return;
      const items = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE),
      ).filter((el) => el.offsetParent !== null || el === document.activeElement);
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey, true);

    return () => {
      window.clearTimeout(t);
      document.removeEventListener("keydown", onKey, true);
      document.body.style.overflow = prevOverflow;
      // Return focus so keyboard users don't lose their place.
      (invokerRef.current as HTMLElement | null)?.focus?.();
    };
    // onClose is a stable zustand action; initialFocusRef is stable per caller.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return panelRef;
}
