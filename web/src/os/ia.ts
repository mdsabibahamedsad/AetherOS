/**
 * AetherOS Canonical Information Architecture (web dashboard binding).
 *
 * Maps every built-in dashboard route to one OS domain so navigation,
 * search, launcher, and system surfaces share a single source of truth.
 * Existing routes are preserved — this file only classifies them.
 */

export type OsDomain =
  | "home"
  | "search"
  | "launcher"
  | "workspaces"
  | "agi"
  | "applications"
  | "system"
  | "developer"
  | "account";

export interface OsNavEntry {
  id: string;
  label: string;
  description: string;
  path: string;
  domain: OsDomain;
  keywords: string[];
}

export const OS_DOMAINS: { id: OsDomain; label: string; description: string }[] = [
  { id: "home", label: "Home", description: "Intelligent starting environment" },
  { id: "search", label: "Search", description: "Universal search across the OS" },
  { id: "launcher", label: "Launcher", description: "Installed applications and actions" },
  { id: "workspaces", label: "Workspaces", description: "Projects, files, tasks, agents, artifacts" },
  { id: "agi", label: "AGI", description: "Conversations, tasks, agents, memory, activity" },
  { id: "applications", label: "Applications", description: "Files, chat, tools, installed apps" },
  { id: "system", label: "System", description: "Notifications, security, storage, sync, backup, settings" },
  { id: "developer", label: "Developer", description: "Projects, tools, APIs, automation" },
  { id: "account", label: "Account", description: "Identity, devices, sessions" },
];

/** Canonical OS destinations. `path` values MUST be real routes in App.tsx. */
export const OS_NAV: OsNavEntry[] = [
  { id: "home", label: "Home", description: "Greeting, active work, next actions", path: "/home", domain: "home", keywords: ["home", "start", "overview", "dashboard"] },
  { id: "search", label: "Search", description: "Search apps, files, tasks, agents, settings", path: "/home", domain: "search", keywords: ["search", "find", "command", "palette"] },
  { id: "launcher", label: "Launcher", description: "Open any application", path: "/launcher", domain: "launcher", keywords: ["launcher", "apps", "open", "launch"] },
  { id: "workspaces", label: "Workspaces", description: "Profiles and project context", path: "/workspaces", domain: "workspaces", keywords: ["workspace", "profile", "project", "context"] },
  // AGI
  { id: "chat", label: "Agent Chat", description: "Natural-language command surface", path: "/chat", domain: "agi", keywords: ["chat", "agent", "conversation", "agi"] },
  { id: "sessions", label: "Sessions", description: "Conversations and runs", path: "/sessions", domain: "agi", keywords: ["sessions", "conversations", "history"] },
  { id: "tasks", label: "Tasks", description: "First-class task objects", path: "/tasks", domain: "agi", keywords: ["tasks", "jobs", "execution", "plan"] },
  { id: "agent-hub", label: "Agents", description: "Agent identity, status, outputs", path: "/agent-hub", domain: "agi", keywords: ["agents", "hub", "orchestration", "swarm"] },
  { id: "memory", label: "Memory", description: "Inspectable memory with provenance", path: "/memory-viewer", domain: "agi", keywords: ["memory", "knowledge", "graph", "recall"] },
  { id: "intelligence", label: "Intelligence", description: "Reasoning and research state", path: "/intelligence", domain: "agi", keywords: ["intelligence", "reasoning", "research", "planning"] },
  // Applications
  { id: "files", label: "Files", description: "Folders, preview, sync and backup state", path: "/files", domain: "applications", keywords: ["files", "folders", "documents", "browse"] },
  { id: "live", label: "Live", description: "Live agent session", path: "/live", domain: "applications", keywords: ["live", "realtime", "session"] },
  { id: "cron", label: "Schedules", description: "Cron jobs and triggers", path: "/cron", domain: "applications", keywords: ["cron", "schedule", "automation", "trigger"] },
  { id: "skills", label: "Skills", description: "Installed skills", path: "/skills", domain: "applications", keywords: ["skills", "capabilities"] },
  // System
  { id: "system-center", label: "System", description: "Status, notifications, quick settings", path: "/system", domain: "system", keywords: ["system", "status", "notifications", "quick settings"] },
  { id: "notifications", label: "Notifications", description: "Approvals, completions, alerts", path: "/agent-hub/notifications", domain: "system", keywords: ["notifications", "alerts", "approvals", "unread"] },
  { id: "security", label: "Security", description: "Auth, permissions, audit, threats", path: "/security", domain: "system", keywords: ["security", "permissions", "audit", "threat", "secrets"] },
  { id: "sync", label: "Sync & Backup", description: "Sync state, conflicts, history", path: "/sync", domain: "system", keywords: ["sync", "backup", "devices", "conflicts", "offline"] },
  { id: "models", label: "Models", description: "Model resources and routing", path: "/models", domain: "system", keywords: ["models", "providers", "routing"] },
  { id: "config", label: "Settings", description: "Goal-oriented settings with search", path: "/config", domain: "system", keywords: ["settings", "config", "preferences", "keys"] },
  // Developer
  { id: "developer", label: "Developer", description: "SDK, MCP, logs, traces", path: "/marketplace/devtools", domain: "developer", keywords: ["developer", "sdk", "mcp", "logs", "api"] },
  { id: "marketplace", label: "Marketplace", description: "Extensions and plugins", path: "/marketplace", domain: "developer", keywords: ["marketplace", "plugins", "extensions", "install"] },
  // Account
  { id: "profiles", label: "Profiles", description: "Identity and workspace profiles", path: "/profiles", domain: "account", keywords: ["profiles", "account", "identity", "devices"] },
  { id: "pairing", label: "Devices", description: "Pairing and device trust", path: "/pairing", domain: "account", keywords: ["pairing", "devices", "channels"] },
];

export function osEntriesForDomain(domain: OsDomain): OsNavEntry[] {
  return OS_NAV.filter((e) => e.domain === domain);
}

/** Deep-link helpers — canonical entity routes used across the OS. */
export const osLink = {
  task: (id: string) => `/tasks/${encodeURIComponent(id)}`,
  agent: (id: string) => `/agent-hub/agents/${encodeURIComponent(id)}`,
  file: (path: string) => `/files?path=${encodeURIComponent(path)}`,
  session: (id: string) => `/sessions?session=${encodeURIComponent(id)}`,
  setting: (section: string) => `/config?section=${encodeURIComponent(section)}`,
  workspace: (id: string) => `/workspaces?profile=${encodeURIComponent(id)}`,
};
