import { create } from "zustand";

export type OsOverlay = "none" | "search" | "launcher" | "notifications" | "quick-settings" | "system";

interface OsState {
  overlay: OsOverlay;
  booted: boolean;
  onboarded: boolean;
  locked: boolean;
  offline: boolean;
  activeWorkspace: string | null;
  openOverlay: (o: Exclude<OsOverlay, "none">) => void;
  closeOverlay: () => void;
  setBooted: (v: boolean) => void;
  setOnboarded: (v: boolean) => void;
  setLocked: (v: boolean) => void;
  setOffline: (v: boolean) => void;
  setWorkspace: (w: string | null) => void;
}

const BOOT_KEY = "aetheros-os-booted";
const ONBOARD_KEY = "aetheros-os-onboarded";
const WS_KEY = "aetheros-os-workspace";

function readLS(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export const useOsStore = create<OsState>((set) => ({
  overlay: "none",
  booted: readLS(BOOT_KEY) === "1",
  onboarded: readLS(ONBOARD_KEY) === "1",
  locked: false,
  offline: typeof navigator !== "undefined" ? !navigator.onLine : false,
  activeWorkspace: readLS(WS_KEY),
  openOverlay: (o) => set({ overlay: o }),
  closeOverlay: () => set({ overlay: "none" }),
  setBooted: (v) => {
    try {
      localStorage.setItem(BOOT_KEY, v ? "1" : "0");
    } catch { /* ignore */ }
    set({ booted: v });
  },
  setOnboarded: (v) => {
    try {
      localStorage.setItem(ONBOARD_KEY, v ? "1" : "0");
    } catch { /* ignore */ }
    set({ onboarded: v });
  },
  setLocked: (locked) => set({ locked }),
  setOffline: (offline) => set({ offline }),
  setWorkspace: (w) => {
    try {
      if (w) localStorage.setItem(WS_KEY, w);
      else localStorage.removeItem(WS_KEY);
    } catch { /* ignore */ }
    set({ activeWorkspace: w });
  },
}));
