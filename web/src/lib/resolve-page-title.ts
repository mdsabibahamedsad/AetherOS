import type { Translations } from "@/i18n/types";

const BUILTIN: Record<string, keyof Translations["app"]["nav"]> = {
  "/chat": "chat",
  "/launcher": "sessions",
  "/sessions": "sessions",
  "/analytics": "analytics",
  "/models": "models",
  "/logs": "logs",
  "/cron": "cron",
  "/skills": "skills",
  "/plugins": "plugins",
  "/profiles": "profiles",
  "/security": "security",
  "/permissions": "permissions",
  "/secrets": "secrets",
  "/audit-log": "auditLog",
  "/threat-monitor": "threatMonitor",
  "/sandbox-manager": "sandboxManager",
  "/intelligence": "intelligence",
  "/agent-monitor": "agentMonitor",
  "/agent-hub": "agentHub",
  "/agent-hub/agents": "agentList",
  "/agent-hub/templates": "agentTemplates",
  "/agent-hub/orchestration": "agentOrchestration",
  "/agent-hub/automation": "agentAutomation",
  "/agent-hub/tasks": "agentTasks",
  "/agent-hub/monitoring": "agentMonitoring",
  "/agent-hub/marketplace": "agentMarketplace",
  "/agent-hub/workflows": "agentWorkflows",
  "/agent-hub/scheduler": "agentScheduler",
  "/agent-hub/background": "agentBackground",
  "/agent-hub/logs": "agentLogs",
  "/agent-hub/notifications": "agentNotifications",
  "/agent-hub/permissions": "agentPermissions",
  "/agent-hub/memory": "agentMemory",
  "/agent-hub/search": "agentSearch",
  "/agent-hub/tags": "agentTags",
  "/memory-viewer": "memoryViewer",
  "/knowledge-graph": "knowledgeGraph",
  "/planning": "planning",
  "/config": "config",
  "/env": "keys",
  "/docs": "documentation",
};

export function resolvePageTitle(
  pathname: string,
  t: Translations,
  pluginTabs: { path: string; label: string }[],
): string {
  const normalized = pathname.replace(/\/$/, "") || "/";
  if (normalized === "/") {
    return "Home";
  }
  if (normalized === "/home") {
    return "Home";
  }
  if (normalized === "/workspaces") {
    return "Workspaces";
  }
  if (normalized === "/launcher") {
    return "Launcher";
  }
  const plugin = pluginTabs.find((p) => p.path === normalized);
  if (plugin) {
    return plugin.label;
  }
  const key = BUILTIN[normalized];
  if (key) {
    return t.app.nav[key];
  }
  // Derive title from pathname: "/profiles" → "Profiles"
  const segment = normalized.slice(1);
  if (segment) {
    return segment.charAt(0).toUpperCase() + segment.slice(1);
  }
  return t.app.webUi;
}
