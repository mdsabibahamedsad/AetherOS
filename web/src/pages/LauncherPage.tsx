import { useEffect } from "react";
import { Navigate } from "react-router-dom";
import { useOsStore } from "../os/store";

/** /launcher deep-link: the launcher is an overlay; land on Home with it open. */
export default function LauncherPage() {
  const openOverlay = useOsStore((s) => s.openOverlay);
  useEffect(() => {
    openOverlay("launcher");
  }, [openOverlay]);
  return <Navigate to="/home" replace />;
}
