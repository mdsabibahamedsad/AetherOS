// The dashboard can be served either at the root of its host (e.g.
// https://kanban.tilos.com/) or under a URL prefix when reverse-proxied
// (e.g. https://mission-control.tilos.com/aetheros/). The Python backend
// injects ``window.__HERMES_BASE_PATH__`` into index.html based on the
// incoming ``X-Forwarded-Prefix`` header so the SPA can address its own
// ``/api/...`` and ``/dashboard-plugins/...`` URLs correctly without a
// rebuild. Empty string means "served at root".
function readBasePath(): string {
  if (typeof window === "undefined") return "";
  const raw = window.__HERMES_BASE_PATH__ ?? "";
  if (!raw) return "";
  // Normalise: ensure leading slash, strip trailing slash.
  const withLead = raw.startsWith("/") ? raw : `/${raw}`;
  return withLead.replace(/\/+$/, "");
}

export const HERMES_BASE_PATH = readBasePath();
const BASE = HERMES_BASE_PATH;

import type { DashboardTheme } from "@/themes/types";

// ── Intelligence types ─────────────────────────────────────────────────

export interface IntelligenceStatusResponse {
  version: string;
  initialized: boolean;
  reasoning?: string;
  research?: string;
  project_understanding?: string;
  explainability?: string;
  subsystems?: Record<string, boolean>;
}

export interface IntelligenceAgentsResponse {
  agents: Array<{
    role: string;
    class: string;
    description: string;
    enabled: boolean;
    status: string;
  }>;
  total: number;
  active: number;
}

export interface IntelligenceAgentDetailResponse {
  name: string;
  status: string;
  enabled: boolean;
  stats: {
    tasks_completed: number;
    tasks_failed: number;
    avg_duration: string;
    last_active: string | null;
  };
}

export interface IntelligencePlansResponse {
  plans: Array<{
    plan_id: string;
    goal: string;
    status: string;
    progress: number;
  }>;
  total: number;
}

export interface IntelligencePlanCreateResponse {
  plan_id: string;
  goal: string;
  result?: {
    answer: string;
    confidence: number;
    steps: Array<{ strategy: string; output: string; confidence: number; verified: boolean; duration: number }>;
    alternatives: Array<{ title: string; description: string; tradeoffs: string }>;
    total_duration: number;
  };
  created_at: number;
}

export interface IntelligenceThinkResponse {
  answer: string;
  confidence: number;
  steps: Array<{ strategy: string; output: string; confidence: number; verified: boolean; duration: number }>;
  alternatives: Array<{ title: string; description: string; tradeoffs: string }>;
  total_duration: number;
}

export interface IntelligenceResearchResponse {
  id: string;
  query: string;
  summary: string;
  sections: Array<{ title: string; findings: Array<{ source: string; title: string; content: string }> }>;
  findings: Array<{ source: string; title: string; content: string; url: string; relevance: number }>;
  depth: number;
  total_sources: number;
  duration: number;
}

export interface IntelligenceMemoryResponse {
  short_term: { entries: number; capacity: number };
  long_term: { entries: number; capacity: number };
  semantic: { entries: number };
  episodic: { entries: number };
  working: { current: number; max: number };
  enabled: boolean;
  learning_enabled: boolean;
}

export interface IntelligenceKnowledgeStatsResponse {
  total_entities: number;
  total_relationships: number;
  last_indexed: string | null;
  sources: string[];
}

export interface IntelligenceKnowledgeSearchResponse {
  results: Array<{ source: string; title: string; content: string; url: string; relevance: number }>;
  total: number;
  summary: string;
}

// ── End Intelligence types ─────────────────────────────────────────────

// Ephemeral session token for protected endpoints.
// Injected into index.html by the server — never fetched via API.
declare global {
  interface Window {
    __AETHEROS_SESSION_TOKEN__?: string;
    __HERMES_BASE_PATH__?: string;
    /** Server-injected flag: ``true`` when the dashboard's OAuth gate is
     * engaged (public bind, no ``--insecure``). Toggles the SPA's
     * WS-upgrade path from legacy ``?token=`` to single-use ``?ticket=``
     * fetched via :func:`getWsTicket`. */
    __HERMES_AUTH_REQUIRED__?: boolean;
  }
}
let _sessionToken: string | null = null;
const SESSION_HEADER = "X-Aetheros-Session-Token";

function setSessionHeader(headers: Headers, token: string): void {
  if (!headers.has(SESSION_HEADER)) {
    headers.set(SESSION_HEADER, token);
  }
}

// ── Global management-profile scope ──────────────────────────────────
// The dashboard is a machine-level management surface: one header switcher
// (ProfileProvider in App.tsx) decides which profile the management pages
// read/write, and fetchJSON transparently appends ?profile=<name> to the
// profile-scoped endpoint families below. "" = the dashboard process's own
// profile (legacy behavior). Calls that already carry an explicit profile
// (e.g. ProfileBuilder writes) are left untouched — explicit beats global.
let _managementProfile = "";

export function setManagementProfile(name: string): void {
  _managementProfile = (name || "").trim();
}

export function getManagementProfile(): string {
  return _managementProfile;
}

// Endpoint families that honor ?profile= on the backend (web_server.py
// _profile_scope). Anything else — sessions, analytics, ops, pairing,
// channels, cron (which has its own per-job profile params), profiles
// themselves — is machine-global or self-scoped and must NOT be rewritten.
const PROFILE_SCOPED_PREFIXES = [
  "/api/skills",
  "/api/tools/toolsets",
  "/api/config",
  "/api/env",
  "/api/mcp",
  "/api/model/info",
  "/api/model/set",
  "/api/model/auxiliary",
  "/api/model/options",
];

function withManagementProfile(url: string): string {
  if (!_managementProfile) return url;
  if (url.includes("profile=")) return url; // explicit param wins
  const path = url.split("?")[0];
  if (!PROFILE_SCOPED_PREFIXES.some((p) => path.startsWith(p))) return url;
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}profile=${encodeURIComponent(_managementProfile)}`;
}

export async function fetchJSON<T>(
  url: string,
  init?: RequestInit,
  options?: FetchJSONOptions,
): Promise<T> {
  url = withManagementProfile(url);
  // Inject the session token into all /api/ requests.
  const headers = new Headers(init?.headers);
  const token = window.__AETHEROS_SESSION_TOKEN__;
  if (token) {
    setSessionHeader(headers, token);
  }
  const res = await fetch(`${BASE}${url}`, {
    ...init,
    headers,
    // ``credentials: 'include'`` so the cookie-auth path (gated mode) works
    // for any fetch routed through here. Loopback mode is unaffected — the
    // server doesn't read cookies and the legacy session-token header is
    // already attached above.
    credentials: init?.credentials ?? "include",
  });
  if (res.status === 401) {
    // Phase 6: the gated middleware emits a structured envelope so the
    // SPA can full-page-navigate to /login on session expiry. Parse it,
    // and only redirect on the known error codes — domain-level 401s
    // (e.g. "you don't have permission to read this monitor") bubble
    // up as regular errors so callers can handle them.
    let body: { error?: string; login_url?: string } = {};
    try {
      body = await res.clone().json();
    } catch {
      /* non-JSON 401 — let it fall through */
    }
    if (
      (body.error === "unauthenticated" || body.error === "session_expired") &&
      body.login_url
    ) {
      // Preserve where the user was so /auth/callback can land them back
      // after re-auth. The gate's login_url already carries a ``next=``
      // built from the request path, but the SPA may be deep inside a
      // SPA route the gate never saw — e.g. a hash route or a client-side
      // /sessions/<id> deep link. Save the current location as a
      // fallback the post-login handler can read.
      try {
        sessionStorage.setItem(
          "aetheros.lastLocation",
          window.location.pathname + window.location.search,
        );
      } catch {
        /* SSR / privacy mode — ignore */
      }
      window.location.assign(body.login_url);
      // Never resolve — the page is about to unload.
      return new Promise<T>(() => {});
    }
    // Loopback mode: ``_SESSION_TOKEN`` rotates on every server restart
    // (``aetheros update``, ``aetheros gateway restart``, etc.). A tab kept
    // open across the restart holds the OLD token in
    // ``window.__AETHEROS_SESSION_TOKEN__`` from the previous HTML render,
    // so every fetch returns 401. The HTML is served ``Cache-Control:
    // no-store`` so a reload picks up the freshly-injected token. Trigger
    // that reload once on the first stale-token 401 — gated mode is
    // handled above, so reaching here in gated mode means a real
    // middleware failure that should not reload-loop.
    if (!window.__HERMES_AUTH_REQUIRED__ && !options?.allowUnauthorized) {
      let alreadyReloaded = false;
      try {
        alreadyReloaded =
          sessionStorage.getItem("aetheros.tokenReloadAttempted") === "1";
      } catch {
        /* SSR / privacy mode — fall through to throw */
      }
      if (!alreadyReloaded) {
        try {
          sessionStorage.setItem("aetheros.tokenReloadAttempted", "1");
        } catch {
          /* SSR / privacy mode — best effort */
        }
        window.location.reload();
        return new Promise<T>(() => {});
      }
    }
  }
  if (res.ok) {
    // Clear the stale-token reload guard: a successful 2xx proves the
    // current ``window.__AETHEROS_SESSION_TOKEN__`` is valid, so the next
    // 401 — if any — should be allowed to trigger its own reload cycle.
    try {
      sessionStorage.removeItem("aetheros.tokenReloadAttempted");
    } catch {
      /* SSR / privacy mode — ignore */
    }
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

/** Encode a plugin registry key for URL paths (preserves `/` segment separators). */
function pluginPath(name: string): string {
  return name.split("/").map(encodeURIComponent).join("/");
}

async function getSessionToken(): Promise<string> {
  if (_sessionToken) return _sessionToken;
  const injected = window.__AETHEROS_SESSION_TOKEN__;
  if (injected) {
    _sessionToken = injected;
    return _sessionToken;
  }
  throw new Error("Session token not available — page must be served by the Aetheros dashboard server");
}

/**
 * Fetch a single-use ticket for a WebSocket upgrade in gated mode.
 *
 * The dashboard's gated-mode WS auth (``aetheros_cli.web_server._ws_auth_ok``)
 * rejects the legacy ``?token=<_SESSION_TOKEN>`` path and only accepts
 * ``?ticket=<minted>`` consumed against the in-memory ticket store. Browsers
 * can't set ``Authorization`` on a WS upgrade, so this round-trip via the
 * authenticated REST endpoint is the bridge from cookie auth to WS auth.
 *
 * Tickets are single-use and TTL=30s — every WS connect attempt must
 * fetch a fresh ticket.
 */
export async function getWsTicket(): Promise<{ ticket: string; ttl_seconds: number }> {
  const res = await fetch(`${BASE}/api/auth/ws-ticket`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(`/api/auth/ws-ticket: HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Resolve the auth query-param pair (``[name, value]``) for a WebSocket
 * connect. In gated mode mints a fresh single-use ticket; in loopback
 * mode returns the injected session token.
 */
export async function buildWsAuthParam(): Promise<[string, string]> {
  if (window.__HERMES_AUTH_REQUIRED__) {
    const { ticket } = await getWsTicket();
    return ["ticket", ticket];
  }
  const token = window.__AETHEROS_SESSION_TOKEN__ ?? "";
  return ["token", token];
}

/**
 * Authenticated ``fetch`` for dashboard ``/api/...`` requests that aren't
 * plain JSON — file uploads (``FormData``), binary downloads (blobs), etc.
 * Mirrors ``fetchJSON``'s auth handling but returns the raw ``Response`` so
 * the caller can read ``.blob()`` / ``.formData()`` / stream it.
 *
 * Auth, in both modes, exactly as ``fetchJSON`` does it:
 *  - loopback / ``--insecure``: attach the ``X-Aetheros-Session-Token`` header.
 *  - gated OAuth: no token header (it's absent by design); the
 *    ``aetheros_session_at`` cookie rides along via ``credentials: 'include'``.
 *
 * Unlike ``fetchJSON`` this does NOT parse the body, does NOT throw on
 * non-2xx (the caller decides — a 404 on a download is meaningful), and
 * does NOT run the global 401 → /login redirect (binary endpoints aren't
 * navigation targets). Callers that want the redirect behaviour should use
 * ``fetchJSON``.
 */
export async function authedFetch(
  url: string,
  init?: RequestInit,
): Promise<Response> {
  const headers = new Headers(init?.headers);
  const token = window.__AETHEROS_SESSION_TOKEN__;
  if (token) {
    setSessionHeader(headers, token);
  }
  return fetch(`${BASE}${url}`, {
    ...init,
    headers,
    credentials: init?.credentials ?? "include",
  });
}

/**
 * Build an absolute ``ws(s)://`` URL for a dashboard WebSocket endpoint,
 * with the correct auth query param appended for the active mode (fresh
 * single-use ``ticket`` in gated mode, ``token`` in loopback). Plugins and
 * the SPA should use this instead of hand-assembling a WS URL + reading
 * ``window.__AETHEROS_SESSION_TOKEN__`` directly, so the gated-mode ticket
 * path can never be forgotten.
 *
 * ``path`` is the dashboard-relative path (e.g.
 * ``"/api/plugins/kanban/events"``); the base-path prefix and host are
 * applied here. Extra query params can be supplied via ``params`` and are
 * merged before the auth param.
 */
export async function buildWsUrl(
  path: string,
  params?: Record<string, string>,
): Promise<string> {
  const [authName, authValue] = await buildWsAuthParam();
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const qs = new URLSearchParams(params ?? {});
  qs.set(authName, authValue);
  return `${proto}//${window.location.host}${BASE}${path}?${qs}`;
}

/** Build a ``?profile=<name>`` query suffix, or "" when unset.
 *
 * Used by the skills/toolsets endpoints so the dashboard can manage a
 * profile other than the one the server process runs under. */
function profileQuery(profile?: string): string {
  return profile ? `?profile=${encodeURIComponent(profile)}` : "";
}

export const api = {
  getStatus: () => fetchJSON<StatusResponse>("/api/status"),
  /**
   * Identity probe for the dashboard auth gate (Phase 7).
   *
   * Returns the verified Session as JSON when gated mode is active and a
   * valid cookie is attached. Loopback mode is unaffected — the endpoint
   * still exists but is never useful there (no Session, no cookie). The
   * AuthWidget component swallows 401s from this call: if the gate isn't
   * engaged, /api/auth/me returns 401 and the widget renders nothing.
   *
   * ``allowUnauthorized`` is load-bearing: in loopback mode this endpoint
   * 401s by design, and fetchJSON's default loopback behaviour treats a
   * 401 as a rotated session token and full-page-reloads to pick up a
   * fresh one. Because every *other* dashboard request succeeds (and so
   * clears the one-shot reload guard), that turns this expected 401 into
   * an infinite reload loop. Opting out keeps the 401 a plain throw the
   * widget can catch.
   */
  getAuthMe: () =>
    fetchJSON<AuthMeResponse>("/api/auth/me", undefined, {
      allowUnauthorized: true,
    }),
  logout: () =>
    fetch(`${BASE}/auth/logout`, {
      method: "POST",
      credentials: "include",
    }).then((r) => {
      // /auth/logout returns 302 → /login. Follow that with a full-page
      // navigation rather than letting fetch() opaquely consume the
      // redirect — the SPA needs to leave the protected area.
      window.location.assign("/login");
      return r;
    }),
  getSessions: (limit = 20, offset = 0) =>
    fetchJSON<PaginatedSessions>(`/api/sessions?limit=${limit}&offset=${offset}`),
  getSessionMessages: (id: string) =>
    fetchJSON<SessionMessagesResponse>(`/api/sessions/${encodeURIComponent(id)}/messages`),
  getSessionLatestDescendant: (id: string) =>
    fetchJSON<SessionLatestDescendantResponse>(
      `/api/sessions/${encodeURIComponent(id)}/latest-descendant`,
    ),
  deleteSession: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/sessions/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  getEmptySessionsCount: () =>
    fetchJSON<{ count: number }>("/api/sessions/empty/count"),
  deleteEmptySessions: () =>
    fetchJSON<{ ok: boolean; deleted: number }>("/api/sessions/empty", {
      method: "DELETE",
    }),
  bulkDeleteSessions: (ids: string[]) =>
    fetchJSON<{ ok: boolean; deleted: number }>("/api/sessions/bulk-delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    }),
  renameSession: (id: string, title: string) =>
    fetchJSON<{ ok: boolean; title: string }>(
      `/api/sessions/${encodeURIComponent(id)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      },
    ),
  getSessionStats: () => fetchJSON<SessionStoreStats>("/api/sessions/stats"),
  exportSessionUrl: (id: string) =>
    `/api/sessions/${encodeURIComponent(id)}/export`,
  pruneSessions: (older_than_days: number, source?: string) =>
    fetchJSON<{ ok: boolean; removed: number }>("/api/sessions/prune", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ older_than_days, source }),
    }),
  listFiles: (path?: string) => {
    const query = path ? `?path=${encodeURIComponent(path)}` : "";
    return fetchJSON<ManagedFilesResponse>(`/api/files${query}`);
  },
  readFile: (path: string) =>
    fetchJSON<ManagedFileReadResponse>(
      `/api/files/read?path=${encodeURIComponent(path)}`,
    ),
  uploadFile: (path: string, dataUrl: string, overwrite = true) =>
    fetchJSON<ManagedFileWriteResponse>("/api/files/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, data_url: dataUrl, overwrite }),
    }),
  createDirectory: (path: string) =>
    fetchJSON<ManagedFileWriteResponse>("/api/files/mkdir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    }),
  deleteFile: (path: string, recursive = false) =>
    fetchJSON<{ ok: boolean; path: string }>("/api/files", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, recursive }),
    }),
  getLogs: (params: { file?: string; lines?: number; level?: string; component?: string }) => {
    const qs = new URLSearchParams();
    if (params.file) qs.set("file", params.file);
    if (params.lines) qs.set("lines", String(params.lines));
    if (params.level && params.level !== "ALL") qs.set("level", params.level);
    if (params.component && params.component !== "all") qs.set("component", params.component);
    return fetchJSON<LogsResponse>(`/api/logs?${qs.toString()}`);
  },
  getAnalytics: (days: number) =>
    fetchJSON<AnalyticsResponse>(`/api/analytics/usage?days=${days}`),
  getModelsAnalytics: (days: number) =>
    fetchJSON<ModelsAnalyticsResponse>(`/api/analytics/models?days=${days}`),
  getConfig: () => fetchJSON<Record<string, unknown>>("/api/config"),
  getDefaults: () => fetchJSON<Record<string, unknown>>("/api/config/defaults"),
  getSchema: () => fetchJSON<{ fields: Record<string, unknown>; category_order: string[] }>("/api/config/schema"),
  getModelInfo: () => fetchJSON<ModelInfoResponse>("/api/model/info"),
  getModelOptions: () => fetchJSON<ModelOptionsResponse>("/api/model/options"),
  getAuxiliaryModels: () => fetchJSON<AuxiliaryModelsResponse>("/api/model/auxiliary"),
  setModelAssignment: (body: ModelAssignmentRequest) =>
    fetchJSON<ModelAssignmentResponse>("/api/model/set", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  saveConfig: (config: Record<string, unknown>) =>
    fetchJSON<{ ok: boolean }>("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config }),
    }),
  getConfigRaw: () => fetchJSON<{ yaml: string; path?: string }>("/api/config/raw"),
  saveConfigRaw: (yaml_text: string) =>
    fetchJSON<{ ok: boolean }>("/api/config/raw", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yaml_text }),
    }),
  getEnvVars: () => fetchJSON<Record<string, EnvVarInfo>>("/api/env"),
  setEnvVar: (key: string, value: string) =>
    fetchJSON<{ ok: boolean }>("/api/env", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value }),
    }),
  deleteEnvVar: (key: string) =>
    fetchJSON<{ ok: boolean }>("/api/env", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key }),
    }),
  revealEnvVar: async (key: string) => {
    const token = await getSessionToken();
    return fetchJSON<{ key: string; value: string }>("/api/env/reveal", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        [SESSION_HEADER]: token,
      },
      body: JSON.stringify({ key }),
    });
  },

  // Cron jobs
  getCronJobs: (profile = "all") =>
    fetchJSON<CronJob[]>(`/api/cron/jobs?profile=${encodeURIComponent(profile)}`),
  getCronDeliveryTargets: () =>
    fetchJSON<{ targets: CronDeliveryTarget[] }>("/api/cron/delivery-targets"),
  createCronJob: (job: { prompt: string; schedule: string; name?: string; deliver?: string; skills?: string[] }, profile = "default") =>
    fetchJSON<CronJob>(`/api/cron/jobs?profile=${encodeURIComponent(profile)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(job),
    }),
  pauseCronJob: (id: string, profile = "default") =>
    fetchJSON<CronJob>(`/api/cron/jobs/${encodeURIComponent(id)}/pause?profile=${encodeURIComponent(profile)}`, { method: "POST" }),
  updateCronJob: (
    id: string,
    updates: { prompt?: string; schedule?: string; name?: string; deliver?: string; skills?: string[] },
    profile = "default",
  ) =>
    fetchJSON<CronJob>(
      `/api/cron/jobs/${encodeURIComponent(id)}?profile=${encodeURIComponent(profile)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates }),
      },
    ),
  resumeCronJob: (id: string, profile = "default") =>
    fetchJSON<CronJob>(`/api/cron/jobs/${encodeURIComponent(id)}/resume?profile=${encodeURIComponent(profile)}`, { method: "POST" }),
  triggerCronJob: (id: string, profile = "default") =>
    fetchJSON<CronJob>(`/api/cron/jobs/${encodeURIComponent(id)}/trigger?profile=${encodeURIComponent(profile)}`, { method: "POST" }),
  deleteCronJob: (id: string, profile = "default") =>
    fetchJSON<{ ok: boolean }>(`/api/cron/jobs/${encodeURIComponent(id)}?profile=${encodeURIComponent(profile)}`, { method: "DELETE" }),

  // Automation Blueprints — parameterized automation blueprints
  getAutomationBlueprints: () =>
    fetchJSON<{ blueprints: AutomationBlueprint[] }>("/api/cron/blueprints"),
  instantiateAutomationBlueprint: (
    body: { blueprint: string; values: Record<string, string> },
    profile = "default",
  ) =>
    fetchJSON<CronJob>(`/api/cron/blueprints/instantiate?profile=${encodeURIComponent(profile)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  // Profiles
  getProfiles: () =>
    fetchJSON<{ profiles: ProfileInfo[] }>("/api/profiles"),
  getActiveProfile: () =>
    fetchJSON<ActiveProfileInfo>("/api/profiles/active"),
  setActiveProfile: (name: string) =>
    fetchJSON<{ ok: boolean; active: string }>("/api/profiles/active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),
  createProfile: (body: {
    name: string;
    clone_from_default: boolean;
    clone_all?: boolean;
    no_skills?: boolean;
    description?: string;
    provider?: string;
    model?: string;
    mcp_servers?: McpServerCreate[];
    keep_skills?: string[];
    hub_skills?: string[];
  }) =>
    fetchJSON<{
      ok: boolean;
      name: string;
      path: string;
      model_set?: boolean;
      mcp_written?: number;
      skills_disabled?: number;
      hub_installs?: Array<{ identifier: string; pid: number | null }>;
    }>("/api/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  updateProfileDescription: (name: string, description: string) =>
    fetchJSON<{ ok: boolean; description: string; description_auto: boolean }>(
      `/api/profiles/${encodeURIComponent(name)}/description`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description }),
      },
    ),
  describeProfileAuto: (name: string, overwrite = true) =>
    fetchJSON<ProfileDescribeAutoResult>(
      `/api/profiles/${encodeURIComponent(name)}/describe-auto`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ overwrite }),
      },
    ),
  setProfileModel: (name: string, provider: string, model: string) =>
    fetchJSON<{ ok: boolean; provider: string; model: string }>(
      `/api/profiles/${encodeURIComponent(name)}/model`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, model }),
      },
    ),
  renameProfile: (name: string, newName: string) =>
    fetchJSON<{ ok: boolean; name: string; path: string }>(
      `/api/profiles/${encodeURIComponent(name)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_name: newName }),
      },
    ),
  deleteProfile: (name: string) =>
    fetchJSON<{ ok: boolean }>(
      `/api/profiles/${encodeURIComponent(name)}`,
      { method: "DELETE" },
    ),
  getProfileSetupCommand: (name: string) =>
    fetchJSON<{ command: string }>(
      `/api/profiles/${encodeURIComponent(name)}/setup-command`,
    ),
  getProfileSoul: (name: string) =>
    fetchJSON<{ content: string; exists: boolean }>(
      `/api/profiles/${encodeURIComponent(name)}/soul`,
    ),
  updateProfileSoul: (name: string, content: string) =>
    fetchJSON<{ ok: boolean }>(
      `/api/profiles/${encodeURIComponent(name)}/soul`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      },
    ),

  // Skills & Toolsets
  //
  // All calls accept an optional ``profile`` so the Skills page can manage
  // any profile's skills/toolsets — not just the one the dashboard process
  // runs under. Omitted/empty profile = the dashboard's own profile.
  getSkills: (profile?: string) =>
    fetchJSON<SkillInfo[]>(`/api/skills${profileQuery(profile)}`),
  toggleSkill: (name: string, enabled: boolean, profile?: string) =>
    fetchJSON<{ ok: boolean }>("/api/skills/toggle", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, enabled, profile: profile || undefined }),
    }),
  getSkillContent: (name: string, profile?: string) =>
    fetchJSON<SkillContent>(
      `/api/skills/content?name=${encodeURIComponent(name)}${profile ? `&profile=${encodeURIComponent(profile)}` : ""}`,
    ),
  createSkill: (skill: { name: string; content: string; category?: string }, profile?: string) =>
    fetchJSON<SkillWriteResult>("/api/skills", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...skill, profile: profile || undefined }),
    }),
  updateSkillContent: (name: string, content: string, profile?: string) =>
    fetchJSON<SkillWriteResult>("/api/skills/content", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, content, profile: profile || undefined }),
    }),
  getToolsets: (profile?: string) =>
    fetchJSON<ToolsetInfo[]>(`/api/tools/toolsets${profileQuery(profile)}`),
  toggleToolset: (name: string, enabled: boolean, profile?: string) =>
    fetchJSON<{ ok: boolean; name: string; enabled: boolean }>(
      `/api/tools/toolsets/${encodeURIComponent(name)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled, profile: profile || undefined }),
      },
    ),
  getToolsetConfig: (name: string, profile?: string) =>
    fetchJSON<ToolsetConfig>(
      `/api/tools/toolsets/${encodeURIComponent(name)}/config${profileQuery(profile)}`,
    ),
  selectToolsetProvider: (name: string, provider: string, profile?: string) =>
    fetchJSON<{ ok: boolean; name: string; provider: string }>(
      `/api/tools/toolsets/${encodeURIComponent(name)}/provider`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, profile: profile || undefined }),
      },
    ),
  saveToolsetEnv: (name: string, env: Record<string, string>, profile?: string) =>
    fetchJSON<ToolsetEnvResult>(
      `/api/tools/toolsets/${encodeURIComponent(name)}/env`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ env, profile: profile || undefined }),
      },
    ),
  runToolsetPostSetup: (name: string, key: string, profile?: string) =>
    fetchJSON<ActionResponse & { key: string }>(
      `/api/tools/toolsets/${encodeURIComponent(name)}/post-setup`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, profile: profile || undefined }),
      },
    ),

  // Session search (FTS5)
  searchSessions: (q: string) =>
    fetchJSON<SessionSearchResponse>(`/api/sessions/search?q=${encodeURIComponent(q)}`),

  // OAuth provider management
  getOAuthProviders: () =>
    fetchJSON<OAuthProvidersResponse>("/api/providers/oauth"),
  disconnectOAuthProvider: async (providerId: string) => {
    const token = await getSessionToken();
    return fetchJSON<{ ok: boolean; provider: string }>(
      `/api/providers/oauth/${encodeURIComponent(providerId)}`,
      {
        method: "DELETE",
        headers: { [SESSION_HEADER]: token },
      },
    );
  },
  startOAuthLogin: async (providerId: string) => {
    const token = await getSessionToken();
    return fetchJSON<OAuthStartResponse>(
      `/api/providers/oauth/${encodeURIComponent(providerId)}/start`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          [SESSION_HEADER]: token,
        },
        body: "{}",
      },
    );
  },
  submitOAuthCode: async (providerId: string, sessionId: string, code: string) => {
    const token = await getSessionToken();
    return fetchJSON<OAuthSubmitResponse>(
      `/api/providers/oauth/${encodeURIComponent(providerId)}/submit`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          [SESSION_HEADER]: token,
        },
        body: JSON.stringify({ session_id: sessionId, code }),
      },
    );
  },
  pollOAuthSession: (providerId: string, sessionId: string) =>
    fetchJSON<OAuthPollResponse>(
      `/api/providers/oauth/${encodeURIComponent(providerId)}/poll/${encodeURIComponent(sessionId)}`,
    ),
  cancelOAuthSession: async (sessionId: string) => {
    const token = await getSessionToken();
    return fetchJSON<{ ok: boolean }>(
      `/api/providers/oauth/sessions/${encodeURIComponent(sessionId)}`,
      {
        method: "DELETE",
        headers: { [SESSION_HEADER]: token },
      },
    );
  },

  // Messaging platforms (gateway channels)
  getMessagingPlatforms: () =>
    fetchJSON<{ platforms: MessagingPlatform[] }>("/api/messaging/platforms"),
  updateMessagingPlatform: (id: string, body: MessagingPlatformUpdate) =>
    fetchJSON<{ ok: boolean; platform: string }>(
      `/api/messaging/platforms/${encodeURIComponent(id)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
  testMessagingPlatform: (id: string) =>
    fetchJSON<MessagingPlatformTestResult>(
      `/api/messaging/platforms/${encodeURIComponent(id)}/test`,
      { method: "POST" },
    ),
  startTelegramOnboarding: (body: { bot_name?: string }) =>
    fetchJSON<TelegramOnboardingStartResponse>(
      "/api/messaging/telegram/onboarding/start",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
  getTelegramOnboardingStatus: (pairingId: string) =>
    fetchJSON<TelegramOnboardingStatusResponse>(
      `/api/messaging/telegram/onboarding/${encodeURIComponent(pairingId)}`,
    ),
  applyTelegramOnboarding: (
    pairingId: string,
    body: { allowed_user_ids: string[] },
  ) =>
    fetchJSON<TelegramOnboardingApplyResponse>(
      `/api/messaging/telegram/onboarding/${encodeURIComponent(pairingId)}/apply`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
  cancelTelegramOnboarding: (pairingId: string) =>
    fetchJSON<{ ok: boolean }>(
      `/api/messaging/telegram/onboarding/${encodeURIComponent(pairingId)}`,
      { method: "DELETE" },
    ),

  // Gateway / update actions
  restartGateway: () =>
    fetchJSON<ActionResponse>("/api/gateway/restart", { method: "POST" }),
  updateAetheros: () =>
    fetchJSON<ActionResponse>("/api/aetheros/update", { method: "POST" }),
  checkAetherosUpdate: (force = false) =>
    fetchJSON<UpdateCheckResponse>(
      `/api/aetheros/update/check${force ? "?force=true" : ""}`,
    ),
  getActionStatus: (name: string, lines = 200) =>
    fetchJSON<ActionStatusResponse>(
      `/api/actions/${encodeURIComponent(name)}/status?lines=${lines}`,
    ),

  // Dashboard plugins
  getPlugins: () =>
    fetchJSON<PluginManifestResponse[]>("/api/dashboard/plugins"),
  rescanPlugins: () =>
    fetchJSON<{ ok: boolean; count: number }>("/api/dashboard/plugins/rescan"),

  getPluginsHub: () => fetchJSON<PluginsHubResponse>("/api/dashboard/plugins/hub"),

  installAgentPlugin: (body: AgentPluginInstallRequest) =>
    fetchJSON<AgentPluginInstallResponse>("/api/dashboard/agent-plugins/install", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body }),
    }),

  enableAgentPlugin: (name: string) =>
    fetchJSON<{ ok: boolean; name: string; unchanged?: boolean }>(
      `/api/dashboard/agent-plugins/${pluginPath(name)}/enable`,
      { method: "POST" },
    ),

  disableAgentPlugin: (name: string) =>
    fetchJSON<{ ok: boolean; name: string; unchanged?: boolean }>(
      `/api/dashboard/agent-plugins/${pluginPath(name)}/disable`,
      { method: "POST" },
    ),

  updateAgentPlugin: (name: string) =>
    fetchJSON<AgentPluginUpdateResponse>(
      `/api/dashboard/agent-plugins/${pluginPath(name)}/update`,
      { method: "POST" },
    ),

  removeAgentPlugin: (name: string) =>
    fetchJSON<{ ok: boolean; name: string }>(
      `/api/dashboard/agent-plugins/${pluginPath(name)}`,
      { method: "DELETE" },
    ),

  savePluginProviders: (body: PluginProvidersPutRequest) =>
    fetchJSON<{ ok: boolean }>("/api/dashboard/plugin-providers", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  setPluginVisibility: (name: string, hidden: boolean) =>
    fetchJSON<{ ok: boolean; name: string; hidden: boolean }>(
      `/api/dashboard/plugins/${pluginPath(name)}/visibility`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hidden }),
      },
    ),

  // Dashboard themes
  getThemes: () =>
    fetchJSON<DashboardThemesResponse>("/api/dashboard/themes"),
  setTheme: (name: string) =>
    fetchJSON<{ ok: boolean; theme: string }>("/api/dashboard/theme", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),
  getFontPref: () =>
    fetchJSON<DashboardFontResponse>("/api/dashboard/font"),
  setFontPref: (font: string) =>
    fetchJSON<{ ok: boolean; font: string }>("/api/dashboard/font", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ font }),
    }),

  // ── Admin: MCP servers ──────────────────────────────────────────────
  getMcpServers: () => fetchJSON<{ servers: McpServer[] }>("/api/mcp/servers"),
  addMcpServer: (body: McpServerCreate) =>
    fetchJSON<McpServer>("/api/mcp/servers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  removeMcpServer: (name: string) =>
    fetchJSON<{ ok: boolean }>(`/api/mcp/servers/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
  testMcpServer: (name: string) =>
    fetchJSON<McpTestResult>(
      `/api/mcp/servers/${encodeURIComponent(name)}/test`,
      { method: "POST" },
    ),
  setMcpServerEnabled: (name: string, enabled: boolean) =>
    fetchJSON<{ ok: boolean; name: string; enabled: boolean }>(
      `/api/mcp/servers/${encodeURIComponent(name)}/enabled`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      },
    ),
  getMcpCatalog: () =>
    fetchJSON<{ entries: McpCatalogEntry[]; diagnostics: McpCatalogDiagnostic[] }>(
      "/api/mcp/catalog",
    ),
  installMcpCatalogEntry: (
    name: string,
    env: Record<string, string> = {},
    enable = true,
  ) =>
    fetchJSON<{ ok: boolean; name: string; background: boolean; action?: string }>(
      "/api/mcp/catalog/install",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, env, enable }),
      },
    ),

  // ── Admin: Pairing ──────────────────────────────────────────────────
  getPairing: () => fetchJSON<PairingResponse>("/api/pairing"),
  approvePairing: (platform: string, code: string) =>
    fetchJSON<{ ok: boolean; user: PairingUser }>("/api/pairing/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, code }),
    }),
  revokePairing: (platform: string, user_id: string) =>
    fetchJSON<{ ok: boolean }>("/api/pairing/revoke", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, user_id }),
    }),
  clearPendingPairing: () =>
    fetchJSON<{ ok: boolean; cleared: number }>("/api/pairing/clear-pending", {
      method: "POST",
    }),

  // ── Admin: Webhooks ─────────────────────────────────────────────────
  getWebhooks: () => fetchJSON<WebhooksResponse>("/api/webhooks"),
  enableWebhooks: () =>
    fetchJSON<WebhookEnableResponse>("/api/webhooks/enable", { method: "POST" }),
  createWebhook: (body: WebhookCreate) =>
    fetchJSON<WebhookRoute & { secret: string }>("/api/webhooks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  deleteWebhook: (name: string) =>
    fetchJSON<{ ok: boolean }>(`/api/webhooks/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
  setWebhookEnabled: (name: string, enabled: boolean) =>
    fetchJSON<{ ok: boolean; name: string; enabled: boolean }>(
      `/api/webhooks/${encodeURIComponent(name)}/enabled`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      },
    ),

  // ── Admin: Credential pool ──────────────────────────────────────────
  getCredentialPool: () =>
    fetchJSON<{ providers: CredentialPoolProvider[] }>("/api/credentials/pool"),
  addCredentialPoolEntry: (
    provider: string,
    api_key: string,
    label?: string,
  ) =>
    fetchJSON<{ ok: boolean; provider: string; count: number }>(
      "/api/credentials/pool",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, api_key, label }),
      },
    ),
  removeCredentialPoolEntry: (provider: string, index: number) =>
    fetchJSON<{ ok: boolean; provider: string; count: number }>(
      `/api/credentials/pool/${encodeURIComponent(provider)}/${index}`,
      { method: "DELETE" },
    ),

  // ── Admin: Memory provider ──────────────────────────────────────────
  getMemory: () => fetchJSON<MemoryStatus>("/api/memory"),
  setMemoryProvider: (provider: string) =>
    fetchJSON<{ ok: boolean; active: string }>("/api/memory/provider", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider }),
    }),
  resetMemory: (target: "all" | "memory" | "user") =>
    fetchJSON<{ ok: boolean; deleted: string[] }>("/api/memory/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target }),
    }),

  // ── Admin: Gateway lifecycle ────────────────────────────────────────
  startGateway: () =>
    fetchJSON<ActionResponse>("/api/gateway/start", { method: "POST" }),
  stopGateway: () =>
    fetchJSON<ActionResponse>("/api/gateway/stop", { method: "POST" }),

  // ── Admin: Operations ───────────────────────────────────────────────
  runDoctor: () =>
    fetchJSON<ActionResponse>("/api/ops/doctor", { method: "POST" }),
  runSecurityAudit: () =>
    fetchJSON<ActionResponse>("/api/ops/security-audit", { method: "POST" }),
  runBackup: (output?: string) =>
    fetchJSON<ActionResponse>("/api/ops/backup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ output }),
    }),
  runImport: (archive: string, force = false) =>
    fetchJSON<ActionResponse>("/api/ops/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ archive, force }),
    }),
  getHooks: () => fetchJSON<HooksResponse>("/api/ops/hooks"),
  createHook: (body: HookCreate) =>
    fetchJSON<{ ok: boolean; event: string; command: string; approved: boolean }>(
      "/api/ops/hooks",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
  deleteHook: (event: string, command: string) =>
    fetchJSON<{ ok: boolean }>("/api/ops/hooks", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event, command }),
    }),
  getSystemStats: () => fetchJSON<SystemStats>("/api/system/stats"),

  // ── Admin: Curator ──────────────────────────────────────────────────
  getCurator: () => fetchJSON<CuratorStatus>("/api/curator"),
  setCuratorPaused: (paused: boolean) =>
    fetchJSON<{ ok: boolean; paused: boolean }>("/api/curator/paused", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paused }),
    }),
  runCurator: () =>
    fetchJSON<ActionResponse>("/api/curator/run", { method: "POST" }),

  // ── Admin: Portal ───────────────────────────────────────────────────
  getPortal: () => fetchJSON<PortalStatus>("/api/portal"),

  // ── Admin: Diagnostics (backgrounded) ───────────────────────────────
  runPromptSize: () =>
    fetchJSON<ActionResponse>("/api/ops/prompt-size", { method: "POST" }),
  runDump: () => fetchJSON<ActionResponse>("/api/ops/dump", { method: "POST" }),
  runConfigMigrate: () =>
    fetchJSON<ActionResponse>("/api/ops/config-migrate", { method: "POST" }),
  runDebugShare: (opts?: { redact?: boolean; lines?: number }) =>
    fetchJSON<DebugShareResponse>("/api/ops/debug-share", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        redact: opts?.redact ?? true,
        lines: opts?.lines ?? 200,
      }),
    }),


  getCheckpoints: () => fetchJSON<CheckpointsResponse>("/api/ops/checkpoints"),
  pruneCheckpoints: () =>
    fetchJSON<ActionResponse>("/api/ops/checkpoints/prune", { method: "POST" }),

  // ── Admin: Skills hub ───────────────────────────────────────────────
  // ``profile`` scopes install/uninstall/update and the installed-state
  // annotations to that profile (omitted = the dashboard's own profile).
  installSkillFromHub: (identifier: string, profile?: string) =>
    fetchJSON<ActionResponse>("/api/skills/hub/install", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, profile: profile || undefined }),
    }),
  uninstallSkillFromHub: (name: string, profile?: string) =>
    fetchJSON<ActionResponse>("/api/skills/hub/uninstall", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, profile: profile || undefined }),
    }),
  updateSkillsFromHub: (profile?: string) =>
    fetchJSON<ActionResponse>("/api/skills/hub/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile: profile || undefined }),
    }),
  searchSkillsHub: (q: string, source = "all", limit = 20, profile?: string) =>
    fetchJSON<SkillHubSearchResponse>(
      `/api/skills/hub/search?q=${encodeURIComponent(q)}&source=${encodeURIComponent(source)}&limit=${limit}${profile ? `&profile=${encodeURIComponent(profile)}` : ""}`,
    ),
  getSkillHubSources: (profile?: string) =>
    fetchJSON<SkillHubSourcesResponse>(
      `/api/skills/hub/sources${profileQuery(profile)}`,
    ),
  previewSkillFromHub: (identifier: string) =>
    fetchJSON<SkillHubPreview>(
      `/api/skills/hub/preview?identifier=${encodeURIComponent(identifier)}`,
    ),
  scanSkillFromHub: (identifier: string) =>
    fetchJSON<SkillHubScan>(
      `/api/skills/hub/scan?identifier=${encodeURIComponent(identifier)}`,
    ),

  // ── Security ─────────────────────────────────────────────────────────
  getSecurityStatus: () =>
    fetchJSON<SecurityStatusResponse>("/api/security/status"),

  // Permissions
  getPermissions: () =>
    fetchJSON<PermissionsResponse>("/api/security/permissions"),
  getPermissionCategories: () =>
    fetchJSON<PermissionCategoriesResponse>("/api/security/permissions/categories"),
  getPermissionStats: () =>
    fetchJSON<Record<string, unknown>>("/api/security/permissions/stats"),
  grantPermission: (permission: string, requester: string, duration: string, reason: string) =>
    fetchJSON<{ ok: boolean }>("/api/security/permissions/grant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ permission, requester, duration, reason }),
    }),
  revokePermission: (permission: string, requester: string) =>
    fetchJSON<{ ok: boolean }>("/api/security/permissions/revoke", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ permission, requester }),
    }),

  // Secrets
  listSecrets: () =>
    fetchJSON<SecretsResponse>("/api/security/secrets"),
  storeSecret: (name: string, value: string, category: string, description: string) =>
    fetchJSON<{ ok: boolean }>("/api/security/secrets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, value, category, description }),
    }),
  retrieveSecret: (name: string) =>
    fetchJSON<{ value: string }>(`/api/security/secrets/${encodeURIComponent(name)}/reveal`),
  deleteSecret: (name: string) =>
    fetchJSON<{ ok: boolean }>(`/api/security/secrets/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),

  // Audit
  getAuditLog: (params?: { limit?: number; severity?: string; event_type?: string; user?: string }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.severity) qs.set("severity", params.severity);
    if (params?.event_type) qs.set("event_type", params.event_type);
    if (params?.user) qs.set("user", params.user);
    return fetchJSON<{ entries: AuditEntryResponse[] }>(`/api/security/audit?${qs.toString()}`);
  },
  getAuditStats: () =>
    fetchJSON<AuditStatsResponse>("/api/security/audit/stats"),
  exportAuditLog: () =>
    fetchJSON<{ url: string }>("/api/security/audit/export"),

  // Threats
  getThreatAlerts: (params?: { limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    return fetchJSON<{ alerts: ThreatAlertResponse[] }>(`/api/security/threats?${qs.toString()}`);
  },
  getThreatSummary: () =>
    fetchJSON<ThreatSummaryResponse>("/api/security/threats/summary"),

  // Sandbox
  getSandboxes: () =>
    fetchJSON<SandboxesResponse>("/api/security/sandbox"),
  getSandboxStats: () =>
    fetchJSON<SandboxStatsResponse>("/api/security/sandbox/stats"),
  createSandbox: (name: string, backend: string, mode: string, network: boolean) =>
    fetchJSON<{ ok: boolean }>("/api/security/sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, backend, mode, network }),
    }),
  destroySandbox: (name: string) =>
    fetchJSON<{ ok: boolean }>(`/api/security/sandbox/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
  executeSandbox: (name: string, command: string) =>
    fetchJSON<{ output?: string; error?: string }>(`/api/security/sandbox/${encodeURIComponent(name)}/exec`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    }),

  // ── Intelligence Engine ────────────────────────────────────────────────
  getIntelligenceStatus: () =>
    fetchJSON<IntelligenceStatusResponse>("/api/intelligence/status"),
  getIntelligenceAgents: () =>
    fetchJSON<IntelligenceAgentsResponse>("/api/intelligence/agents"),
  getIntelligenceAgentDetail: (name: string) =>
    fetchJSON<IntelligenceAgentDetailResponse>(`/api/intelligence/agent/${encodeURIComponent(name)}`),
  getIntelligencePlans: () =>
    fetchJSON<IntelligencePlansResponse>("/api/intelligence/plans"),
  createIntelligencePlan: (goal: string) =>
    fetchJSON<IntelligencePlanCreateResponse>("/api/intelligence/plans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal }),
    }),
  thinkIntelligence: (question: string) =>
    fetchJSON<IntelligenceThinkResponse>("/api/intelligence/think", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
  researchIntelligence: (query: string, depth: number = 1) =>
    fetchJSON<IntelligenceResearchResponse>("/api/intelligence/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, depth }),
    }),
  getIntelligenceMemory: () =>
    fetchJSON<IntelligenceMemoryResponse>("/api/intelligence/memory"),
  getIntelligenceKnowledgeStats: () =>
    fetchJSON<IntelligenceKnowledgeStatsResponse>("/api/intelligence/knowledge/stats"),
  getIntelligenceKnowledgeSearch: (q: string, limit: number = 10) =>
    fetchJSON<IntelligenceKnowledgeSearchResponse>(`/api/intelligence/knowledge/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  // ── Agent Hub ────────────────────────────────────────────────────────
  getAgents: () => fetchJSON<AgentsResponse>("/api/agents"),
  getAgent: (id: string) => fetchJSON<Agent>(`/api/agents/${encodeURIComponent(id)}`),
  createAgent: (data: Partial<Agent>) =>
    fetchJSON<Agent>("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  updateAgent: (id: string, data: Partial<Agent>) =>
    fetchJSON<Agent>(`/api/agents/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  deleteAgent: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/${encodeURIComponent(id)}`, { method: "DELETE" }),
  duplicateAgent: (id: string) =>
    fetchJSON<Agent>(`/api/agents/${encodeURIComponent(id)}/duplicate`, { method: "POST" }),
  cloneAgent: (id: string) =>
    fetchJSON<Agent>(`/api/agents/${encodeURIComponent(id)}/clone`, { method: "POST" }),
  pauseAgent: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/${encodeURIComponent(id)}/pause`, { method: "POST" }),
  resumeAgent: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/${encodeURIComponent(id)}/resume`, { method: "POST" }),
  restartAgent: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/${encodeURIComponent(id)}/restart`, { method: "POST" }),
  getAgentTemplates: () =>
    fetchJSON<AgentTemplatesResponse>("/api/agents/templates"),
  getAgentConfig: (agentId: string) =>
    fetchJSON<AgentConfig>(`/api/agents/${encodeURIComponent(agentId)}/config`),
  saveAgentConfig: (agentId: string, config: AgentConfig) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/${encodeURIComponent(agentId)}/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }),
  getOrchestrations: () =>
    fetchJSON<OrchestrationsResponse>("/api/agents/orchestrations"),
  createOrchestration: (data: Partial<AgentOrchestration>) =>
    fetchJSON<AgentOrchestration>("/api/agents/orchestrations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getAutomations: () =>
    fetchJSON<AutomationsResponse>("/api/agents/automations"),
  createAutomation: (data: Partial<AutomationBlueprint2>) =>
    fetchJSON<AutomationBlueprint2>("/api/agents/automations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getTasks: () =>
    fetchJSON<TasksResponse>("/api/agents/tasks"),
  createTask: (data: Partial<TaskDefinition>) =>
    fetchJSON<TaskDefinition>("/api/agents/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  updateTask: (id: string, data: Partial<TaskDefinition>) =>
    fetchJSON<TaskDefinition>(`/api/agents/tasks/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getMarketplace: () =>
    fetchJSON<MarketplaceResponse>("/api/agents/marketplace"),
  installMarketplace: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/marketplace/${encodeURIComponent(id)}/install`, { method: "POST" }),
  getWorkflows: () =>
    fetchJSON<WorkflowsResponse>("/api/agents/workflows"),
  createWorkflow: (data: Partial<WorkflowDefinition>) =>
    fetchJSON<WorkflowDefinition>("/api/agents/workflows", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  runWorkflow: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/workflows/${encodeURIComponent(id)}/run`, { method: "POST" }),
  getSchedulerJobs: () =>
    fetchJSON<SchedulerJobsResponse>("/api/agents/scheduler"),
  createSchedulerJob: (data: Partial<SchedulerJob>) =>
    fetchJSON<SchedulerJob>("/api/agents/scheduler", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getBackgroundServices: () =>
    fetchJSON<BackgroundServicesResponse>("/api/agents/background"),
  startBackgroundService: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/background/${encodeURIComponent(id)}/start`, { method: "POST" }),
  stopBackgroundService: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/background/${encodeURIComponent(id)}/stop`, { method: "POST" }),
  getAgentLogs: (agentId?: string) => {
    const qs = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : "";
    return fetchJSON<AgentLogsResponse>(`/api/agents/logs${qs}`);
  },
  getAgentNotifications: () =>
    fetchJSON<AgentNotificationsResponse>("/api/agents/notifications"),
  markAgentNotificationRead: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/notifications/${encodeURIComponent(id)}/read`, { method: "POST" }),
  getAgentPermissions: (agentId?: string) => {
    const qs = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : "";
    return fetchJSON<AgentPermissionsResponse>(`/api/agents/permissions${qs}`);
  },
  grantAgentPermission: (permission: AgentPermission) =>
    fetchJSON<{ ok: boolean }>("/api/agents/permissions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(permission),
    }),
  revokeAgentPermission: (id: string) =>
    fetchJSON<{ ok: boolean }>(`/api/agents/permissions/${encodeURIComponent(id)}`, { method: "DELETE" }),
  getAgentMemories: (agentId: string) =>
    fetchJSON<AgentMemoriesResponse>(`/api/agents/memories?agent_id=${encodeURIComponent(agentId)}`),
  searchAgentMemories: (query: string) =>
    fetchJSON<AgentMemoriesResponse>(`/api/agents/memories/search?q=${encodeURIComponent(query)}`),
  getTags: () =>
    fetchJSON<TagsResponse>("/api/agents/tags"),
  createTag: (data: Partial<TagDefinition>) =>
    fetchJSON<TagDefinition>("/api/agents/tags", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  importAgent: (data: FormData) =>
    fetchJSON<Agent>("/api/agents/import", {
      method: "POST",
      body: data,
    }),
  exportAgent: (id: string) =>
    fetchJSON<string>(`/api/agents/${encodeURIComponent(id)}/export`),
  getMonitoringData: () =>
    fetchJSON<MonitoringData>("/api/agents/monitoring"),

  // ── Plugin Marketplace ──────────────────────────────────────────────
  searchPluginMarketplace: (params: {
    q?: string;
    category?: string;
    sort?: string;
    page?: number;
    page_size?: number;
    tag?: string;
    verified?: boolean;
    official?: boolean;
  }) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.category) qs.set("category", params.category);
    if (params.sort) qs.set("sort", params.sort);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    if (params.tag) qs.set("tag", params.tag);
    if (params.verified) qs.set("verified", "true");
    if (params.official) qs.set("official", "true");
    return fetchJSON<MarketplaceSearchResponse>(
      `/api/plugins/marketplace/search?${qs.toString()}`,
    );
  },
  getPluginDetail: (id: string) =>
    fetchJSON<PluginDetailResponse>(
      `/api/plugins/marketplace/${encodeURIComponent(id)}`,
    ),
  getPluginReviews: (id: string) =>
    fetchJSON<{ reviews: PluginReview[] }>(
      `/api/plugins/marketplace/${encodeURIComponent(id)}/reviews`,
    ),
  installMarketplacePlugin: (id: string) =>
    fetchJSON<{ ok: boolean; name?: string }>(
      `/api/plugins/marketplace/${encodeURIComponent(id)}/install`,
      { method: "POST" },
    ),
  updateMarketplacePlugin: (id: string) =>
    fetchJSON<{ ok: boolean; version?: string }>(
      `/api/plugins/marketplace/${encodeURIComponent(id)}/update`,
      { method: "POST" },
    ),
  removeMarketplacePlugin: (id: string) =>
    fetchJSON<{ ok: boolean }>(
      `/api/plugins/marketplace/${encodeURIComponent(id)}`,
      { method: "DELETE" },
    ),
  ratePlugin: (id: string, rating: number, title?: string, content?: string) =>
    fetchJSON<{ ok: boolean; review_id?: string }>(
      `/api/plugins/marketplace/${encodeURIComponent(id)}/rate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, title, content }),
      },
    ),
  getPluginVersions: (id: string) =>
    fetchJSON<{ versions: PluginVersion[] }>(
      `/api/plugins/marketplace/${encodeURIComponent(id)}/versions`,
    ),
  rollbackPlugin: (id: string, version: string) =>
    fetchJSON<{ ok: boolean }>(
      `/api/plugins/marketplace/${encodeURIComponent(id)}/rollback`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version }),
      },
    ),

  // ── Installed plugins management ────────────────────────────────────
  getInstalledPlugins: () =>
    fetchJSON<{ plugins: PluginMarketEntry[] }>("/api/plugins/installed"),
  setPluginEnabled: (id: string, enabled: boolean) =>
    fetchJSON<{ ok: boolean }>(
      `/api/plugins/${encodeURIComponent(id)}/enabled`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      },
    ),
  getPluginPermissions: (id: string) =>
    fetchJSON<PluginPermissions>(
      `/api/plugins/${encodeURIComponent(id)}/permissions`,
    ),
  setPluginPermission: (
    id: string,
    resource: string,
    action: string,
    effect: "allow" | "deny",
  ) =>
    fetchJSON<{ ok: boolean }>(
      `/api/plugins/${encodeURIComponent(id)}/permissions`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resource, action, effect }),
      },
    ),
  getPluginConfig: (id: string) =>
    fetchJSON<Record<string, unknown>>(
      `/api/plugins/${encodeURIComponent(id)}/config`,
    ),
  setPluginConfig: (id: string, config: Record<string, unknown>) =>
    fetchJSON<{ ok: boolean }>(
      `/api/plugins/${encodeURIComponent(id)}/config`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config }),
      },
    ),

  // ── Marketplace Updates ─────────────────────────────────────────────
  getPluginUpdates: () =>
    fetchJSON<{ updates: Array<PluginMarketEntry & { installed_version: string }> }>(
      "/api/plugins/updates",
    ),
  updateAllPlugins: () =>
    fetchJSON<{ ok: boolean; updated: number; failed: string[] }>(
      "/api/plugins/updates/all",
      { method: "POST" },
    ),
  setAutoUpdate: (enabled: boolean) =>
    fetchJSON<{ ok: boolean; auto_update: boolean }>(
      "/api/plugins/updates/auto",
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      },
    ),

  // ── Enhanced MCP management ─────────────────────────────────────────
  getMcpServersStatus: () =>
    fetchJSON<{ servers: McpServerStatus[] }>("/api/mcp/servers/status"),
  getMcpServerLogs: (name: string, lines?: number) =>
    fetchJSON<{ logs: McpServerLog[] }>(
      `/api/mcp/servers/${encodeURIComponent(name)}/logs${lines ? `?lines=${lines}` : ""}`,
    ),
  restartMcpServer: (name: string) =>
    fetchJSON<{ ok: boolean }>(
      `/api/mcp/servers/${encodeURIComponent(name)}/restart`,
      { method: "POST" },
    ),
  runMcpHealthCheck: (name: string) =>
    fetchJSON<McpHealthResult>(
      `/api/mcp/servers/${encodeURIComponent(name)}/health`,
      { method: "POST" },
    ),
  bulkMcpHealthCheck: () =>
    fetchJSON<{ results: McpHealthResult[] }>(
      "/api/mcp/servers/health",
      { method: "POST" },
    ),
  discoverLocalMcpServers: () =>
    fetchJSON<{ servers: McpAutoDiscovery[] }>(
      "/api/mcp/discover",
    ),
  importMcpConfig: (yaml: string) =>
    fetchJSON<{ ok: boolean; imported: number }>("/api/mcp/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yaml }),
    }),
  exportMcpConfig: () =>
    fetchJSON<{ yaml: string }>("/api/mcp/export"),

  // ── Extension SDK ────────────────────────────────────────────────────
  getExtensionTemplates: () =>
    fetchJSON<{ templates: ExtensionTemplate[] }>(
      "/api/extensions/templates",
    ),
  getExtensionTemplate: (id: string) =>
    fetchJSON<ExtensionTemplate>(
      `/api/extensions/templates/${encodeURIComponent(id)}`,
    ),
  createExtension: (template: string, name: string, config?: Record<string, unknown>) =>
    fetchJSON<{ ok: boolean; path: string; name: string }>(
      "/api/extensions/create",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template, name, config }),
      },
    ),
  buildExtension: (name: string) =>
    fetchJSON<BuildResult>(
      `/api/extensions/${encodeURIComponent(name)}/build`,
      { method: "POST" },
    ),
  validateExtension: (name: string) =>
    fetchJSON<ValidationResult>(
      `/api/extensions/${encodeURIComponent(name)}/validate`,
    ),
  getExtensionManifest: (name: string) =>
    fetchJSON<PluginPackage>(
      `/api/extensions/${encodeURIComponent(name)}/manifest`,
    ),
  saveExtensionManifest: (name: string, manifest: Record<string, unknown>) =>
    fetchJSON<{ ok: boolean }>(
      `/api/extensions/${encodeURIComponent(name)}/manifest`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(manifest),
      },
    ),
  setHotReload: (enabled: boolean) =>
    fetchJSON<{ ok: boolean; hot_reload: boolean }>(
      "/api/extensions/hot-reload",
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      },
    ),
  setDevMode: (enabled: boolean) =>
    fetchJSON<{ ok: boolean; dev_mode: boolean }>(
      "/api/extensions/dev-mode",
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      },
    ),
  runExtensionTests: (name: string) =>
    fetchJSON<{
      ok: boolean;
      passed: number;
      failed: number;
      skipped: number;
      duration_ms: number;
      output: string;
    }>(`/api/extensions/${encodeURIComponent(name)}/test`, { method: "POST" }),
  generateExtensionDocs: (name: string) =>
    fetchJSON<{ ok: boolean; path: string }>(
      `/api/extensions/${encodeURIComponent(name)}/docs`,
      { method: "POST" },
    ),

  // ── Developer Tools ─────────────────────────────────────────────────
  getPluginLogs: (params?: {
    plugin?: string;
    level?: string;
    lines?: number;
    since?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.plugin) qs.set("plugin", params.plugin);
    if (params?.level) qs.set("level", params.level);
    if (params?.lines) qs.set("lines", String(params.lines));
    if (params?.since) qs.set("since", params.since);
    return fetchJSON<{ logs: PluginLogEntry[] }>(
      `/api/developer/logs${qs.toString() ? `?${qs.toString()}` : ""}`,
    );
  },
  getPerformanceMetrics: () =>
    fetchJSON<PerformanceMetrics>("/api/developer/performance"),
  getDebugConsole: (lines?: number) =>
    fetchJSON<{ messages: DebugConsoleMessage[] }>(
      `/api/developer/console${lines ? `?lines=${lines}` : ""}`,
    ),
  sendDebugCommand: (command: string) =>
    fetchJSON<{ ok: boolean; output: string }>("/api/developer/console", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    }),
  inspectPlugin: (name: string) =>
    fetchJSON<InspectorPluginData>(
      `/api/developer/inspect/${encodeURIComponent(name)}`,
    ),
  getExtensionProjects: () =>
    fetchJSON<{ projects: Array<{ name: string; path: string; type: string; version: string }> }>(
      "/api/developer/projects",
    ),

  // ── Cloud Sync ─────────────────────────────────────────────────────────
  getSyncStatus: () =>
    fetchJSON<CloudSyncStatus>("/api/sync/status"),
  startSync: (scope?: string) =>
    fetchJSON<{ ok: boolean }>("/api/sync/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope }),
    }),
  stopSync: () =>
    fetchJSON<{ ok: boolean }>("/api/sync/stop", { method: "POST" }),
  getSyncHistory: (params?: { scope?: string; status?: string; device?: string; since?: string; until?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.scope) qs.set("scope", params.scope);
    if (params?.status) qs.set("status", params.status);
    if (params?.device) qs.set("device", params.device);
    if (params?.since) qs.set("since", params.since);
    if (params?.until) qs.set("until", params.until);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    return fetchJSON<{ events: SyncEvent[]; total: number }>(
      `/api/sync/history${qs.toString() ? `?${qs.toString()}` : ""}`,
    );
  },
  resolveConflict: (conflictId: string, resolution: string, mergedContent?: string) =>
    fetchJSON<{ ok: boolean }>(`/api/sync/conflicts/${encodeURIComponent(conflictId)}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolution, merged_content: mergedContent }),
    }),
  batchResolveConflicts: (conflictIds: string[], resolution: string) =>
    fetchJSON<{ ok: boolean; resolved: number; failed: string[] }>(
      "/api/sync/conflicts/batch-resolve",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conflict_ids: conflictIds, resolution }),
      },
    ),
  getConflicts: () =>
    fetchJSON<{ conflicts: SyncConflict[] }>("/api/sync/conflicts"),
  getResolvedConflicts: () =>
    fetchJSON<{ conflicts: SyncConflict[] }>("/api/sync/conflicts/resolved"),
  clearSyncHistory: () =>
    fetchJSON<{ ok: boolean }>("/api/sync/history", { method: "DELETE" }),
  exportSyncHistory: () =>
    fetchJSON<{ csv: string }>("/api/sync/history/export"),

  // ── Devices ───────────────────────────────────────────────────────────
  listDevices: () =>
    fetchJSON<{ devices: DeviceInfo[] }>("/api/devices"),
  getDevice: (deviceId: string) =>
    fetchJSON<DeviceInfo>(`/api/devices/${encodeURIComponent(deviceId)}`),
  registerDevice: (data: { name: string; device_type: string }) =>
    fetchJSON<DeviceInfo>("/api/devices/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  revokeDevice: (deviceId: string) =>
    fetchJSON<{ ok: boolean }>(`/api/devices/${encodeURIComponent(deviceId)}/revoke`, {
      method: "POST",
    }),
  renameDevice: (deviceId: string, name: string) =>
    fetchJSON<{ ok: boolean }>(`/api/devices/${encodeURIComponent(deviceId)}/rename`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),
  getDevicePermissions: (deviceId: string) =>
    fetchJSON<{ permissions: string[] }>(
      `/api/devices/${encodeURIComponent(deviceId)}/permissions`,
    ),
  getDeviceSessions: (deviceId: string) =>
    fetchJSON<{ sessions: DeviceSession[] }>(
      `/api/devices/${encodeURIComponent(deviceId)}/sessions`,
    ),

  // ── Remote Instances ──────────────────────────────────────────────────
  listRemoteInstances: () =>
    fetchJSON<{ instances: RemoteInstance[] }>("/api/remote/instances"),
  connectRemoteInstance: (instanceId: string) =>
    fetchJSON<{ ok: boolean }>(`/api/remote/instances/${encodeURIComponent(instanceId)}/connect`, {
      method: "POST",
    }),
  disconnectRemoteInstance: (instanceId: string) =>
    fetchJSON<{ ok: boolean }>(`/api/remote/instances/${encodeURIComponent(instanceId)}/disconnect`, {
      method: "POST",
    }),
  reconnectRemoteInstance: (instanceId: string) =>
    fetchJSON<{ ok: boolean }>(`/api/remote/instances/${encodeURIComponent(instanceId)}/reconnect`, {
      method: "POST",
    }),
  addRemoteInstance: (data: { name: string; url: string; auth_token?: string; credentials?: Record<string, string> }) =>
    fetchJSON<RemoteInstance>("/api/remote/instances", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  editRemoteInstance: (instanceId: string, data: Partial<{ name: string; url: string; auth_token: string; credentials: Record<string, string> }>) =>
    fetchJSON<RemoteInstance>(`/api/remote/instances/${encodeURIComponent(instanceId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  removeRemoteInstance: (instanceId: string) =>
    fetchJSON<{ ok: boolean }>(`/api/remote/instances/${encodeURIComponent(instanceId)}`, {
      method: "DELETE",
    }),
  testConnection: (url: string, authToken?: string) =>
    fetchJSON<{ ok: boolean; latency_ms: number; error?: string }>("/api/remote/test-connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, auth_token: authToken }),
    }),
  remoteAgentAction: (instanceId: string, action: string) =>
    fetchJSON<{ ok: boolean }>(`/api/remote/instances/${encodeURIComponent(instanceId)}/agent/${action}`, {
      method: "POST",
    }),
  getRemoteAgentStatus: (instanceId: string) =>
    fetchJSON<RemoteAgentStatus>(
      `/api/remote/instances/${encodeURIComponent(instanceId)}/agent/status`,
    ),
  getRemoteLogs: (instanceId: string, params?: { level?: string; lines?: number; since?: string }) => {
    const qs = new URLSearchParams();
    if (params?.level) qs.set("level", params.level);
    if (params?.lines) qs.set("lines", String(params.lines));
    if (params?.since) qs.set("since", params.since);
    return fetchJSON<{ logs: RemoteLogEntry[] }>(
      `/api/remote/instances/${encodeURIComponent(instanceId)}/logs${qs.toString() ? `?${qs.toString()}` : ""}`,
    );
  },
  getRemoteTasks: (instanceId: string) =>
    fetchJSON<{ tasks: RemoteTask[] }>(
      `/api/remote/instances/${encodeURIComponent(instanceId)}/tasks`,
    ),
  getRemoteMetrics: (instanceId: string) =>
    fetchJSON<RemoteMetrics>(
      `/api/remote/instances/${encodeURIComponent(instanceId)}/metrics`,
    ),
};

// ── Cloud Sync types ────────────────────────────────────────────────────

export type SyncStatus = "online" | "offline" | "syncing" | "error";
export type SyncScope = "settings" | "agents" | "workflows" | "knowledge" | "memory" | "tools" | "automations" | "files" | "skills";
export type SyncEventAction = "create" | "update" | "delete" | "rename" | "conflict" | "resolve" | "merge";

export interface CloudSyncStatus {
  status: SyncStatus;
  last_sync_at: string | null;
  progress: number;
  error_message: string | null;
  connected_devices: number;
  connection_type: "local" | "cloud" | "self_hosted" | "custom";
  offline_queue_count: number;
  conflict_count: number;
  scopes: SyncScopeStatus[];
}

export interface SyncScopeStatus {
  scope: SyncScope;
  enabled: boolean;
  status: SyncStatus;
  last_sync_at: string | null;
  pending_changes: number;
  error_message: string | null;
}

export interface SyncEvent {
  id: string;
  timestamp: string;
  scope: string;
  action: SyncEventAction;
  file_key: string;
  device: string;
  status: "success" | "failed" | "conflict";
  detail: string | null;
}

export interface SyncConflict {
  id: string;
  scope: string;
  file_key: string;
  timestamp: string;
  local_version: { hash: string; modified_at: string; device: string };
  remote_version: { hash: string; modified_at: string; device: string };
  local_content: string | null;
  remote_content: string | null;
  resolved: boolean;
  resolution: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
}

// ── Device types ────────────────────────────────────────────────────────

export interface DeviceInfo {
  id: string;
  name: string;
  os: string;
  version: string;
  last_active: string | null;
  online: boolean;
  sync_status: SyncStatus;
  device_type: string;
  device_id: string;
  public_key_fingerprint: string | null;
  created_at: string;
  current: boolean;
  permissions: string[];
}

export interface DeviceSession {
  id: string;
  device_id: string;
  ip_address: string;
  user_agent: string;
  started_at: string;
  last_active_at: string;
  active: boolean;
}

// ── Remote Instance types ───────────────────────────────────────────────

export type RemoteInstanceStatus = "online" | "offline" | "error" | "connecting";

export interface RemoteInstance {
  id: string;
  name: string;
  url: string;
  status: RemoteInstanceStatus;
  version: string | null;
  latency_ms: number | null;
  uptime_seconds: number | null;
  connected: boolean;
  auth_type: string | null;
  error_message: string | null;
  created_at: string;
  last_seen: string | null;
  health: RemoteHealthResult | null;
}

export interface RemoteHealthResult {
  ok: boolean;
  latency_ms: number;
  timestamp: string;
  error: string | null;
}

export type AgentStatus = "running" | "stopped" | "paused" | "error";

export interface RemoteAgentStatus {
  status: AgentStatus;
  version: string;
  uptime_seconds: number;
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  tasks_completed: number;
  tasks_failed: number;
  active_tasks: number;
  memory_breakdown: Record<string, number>;
  started_at: string;
  error_message: string | null;
}

export interface RemoteTask {
  id: string;
  name: string;
  status: "running" | "queued" | "completed" | "failed" | "cancelled";
  progress: number;
  created_at: string;
  updated_at: string;
  error_message: string | null;
}

export interface RemoteLogEntry {
  id: string;
  timestamp: string;
  level: "debug" | "info" | "warn" | "error";
  source: string;
  message: string;
}

export interface RemoteMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  uptime_seconds: number;
  tasks_completed: number;
  tasks_failed: number;
  active_tasks: number;
  memory_breakdown: Record<string, number>;
}

/** Identity payload returned by ``GET /api/auth/me`` (Phase 7).
 *
 * Returned by the dashboard's gated middleware when a valid session cookie
 * is attached. ``email`` and ``display_name`` are empty strings under the
 * AetherOS portal contract V1 (the access token has no email/name claims —
 * see Contract Anchor C4 in the plan). The AuthWidget surfaces a
 * truncated ``user_id`` instead.
 */
export interface AuthMeResponse {
  user_id: string;
  email: string;
  display_name: string;
  org_id: string;
  provider: string;
  expires_at: number;
}

export interface ActionResponse {
  name: string;
  ok: boolean;
  pid: number | null;
  error?: string;
  message?: string;
  update_command?: string;
}

export interface DebugShareResponse {
  ok: boolean;
  // label -> paste URL, e.g. { Report: "https://paste.rs/abc", "agent.log": "..." }
  urls: Record<string, string>;
  // "label: error" strings for optional full-log uploads that failed.
  failures: string[];
  redacted: boolean;
  auto_delete_seconds: number;
}

export interface SessionStoreStats {
  total: number;
  active_store: number;
  archived: number;
  messages: number;
  by_source: Record<string, number>;
}

export interface SkillHubResult {
  name: string;
  description: string;
  source: string;
  identifier: string;
  trust_level: string;
  repo: string | null;
  tags: string[];
}

/** Lock-entry summary for an already-installed hub skill (keyed by identifier). */
export interface SkillHubInstalledEntry {
  name: string | null;
  trust_level: string | null;
  scan_verdict: string | null;
}

export interface SkillHubSearchResponse {
  results: SkillHubResult[];
  /** source_id -> number of results returned by that source. */
  source_counts: Record<string, number>;
  /** source ids that didn't return within the parallel-search timeout. */
  timed_out: string[];
  /** identifier -> installed lock entry (for "already installed" badges). */
  installed: Record<string, SkillHubInstalledEntry>;
}

export interface SkillHubSource {
  id: string;
  label: string;
  /** GitHub only: whether the API is currently rate-limited. */
  rate_limited?: boolean;
  /** hermes-index only: whether the centralized index loaded. */
  available?: boolean;
}

export interface SkillHubSourcesResponse {
  sources: SkillHubSource[];
  index_available: boolean;
  /** Featured/popular skills from the centralized index (zero extra API calls). */
  featured: SkillHubResult[];
  installed: Record<string, SkillHubInstalledEntry>;
}

export interface SkillHubPreview {
  name: string;
  description: string;
  source: string;
  identifier: string;
  trust_level: string;
  repo: string | null;
  tags: string[];
  /** Rendered SKILL.md content (the actual skill text). */
  skill_md: string;
  /** Relative paths of every file in the bundle. */
  files: string[];
}

export interface SkillHubScanFinding {
  severity: string;
  category: string;
  file: string;
  line: number;
  description: string;
}

export interface SkillHubScan {
  name: string;
  identifier: string;
  source: string;
  trust_level: string;
  /** "safe" | "caution" | "dangerous". */
  verdict: string;
  summary: string;
  /** Install-policy decision for this trust+verdict combo. */
  policy: "allow" | "ask" | "block";
  policy_reason: string;
  findings: SkillHubScanFinding[];
  severity_counts: Record<string, number>;
}

// ── Admin types ───────────────────────────────────────────────────────

export interface McpServer {
  name: string;
  transport: "http" | "stdio" | "unknown";
  url: string | null;
  command: string | null;
  args: string[];
  env: Record<string, string>;
  auth: string | null;
  enabled: boolean;
  tools: string[] | null;
}

export interface McpCatalogEntry {
  name: string;
  description: string;
  source: string;
  transport: "http" | "stdio";
  auth_type: "api_key" | "oauth" | "none";
  required_env: Array<{ name: string; prompt: string; required: boolean }>;
  needs_install: boolean;
  installed: boolean;
  enabled: boolean;
}

export interface McpCatalogDiagnostic {
  name: string;
  kind: string;
  message: string;
}


export interface McpServerCreate {
  name: string;
  url?: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  auth?: string;
}

export interface McpTestResult {
  ok: boolean;
  error?: string;
  tools: Array<{ name: string; description: string }>;
}

export interface MessagingPlatformEnvVar {
  key: string;
  required: boolean;
  is_set: boolean;
  redacted_value: string | null;
  description: string;
  prompt: string;
  url: string | null;
  is_password: boolean;
  advanced: boolean;
}

export interface MessagingPlatform {
  id: string;
  name: string;
  description: string;
  docs_url: string;
  enabled: boolean;
  configured: boolean;
  gateway_running: boolean;
  /**
   * "connected" | "disabled" | "not_configured" | "pending_restart" |
   * "gateway_stopped" | "disconnected" | "fatal" | string
   */
  state: string;
  error_code: string | null;
  error_message: string | null;
  updated_at: string | null;
  home_channel: { platform: string; chat_id: string; name: string; thread_id?: string } | null;
  env_vars: MessagingPlatformEnvVar[];
}

export interface MessagingPlatformUpdate {
  enabled?: boolean;
  env?: Record<string, string>;
  clear_env?: string[];
}

export interface MessagingPlatformTestResult {
  ok: boolean;
  state: string;
  message: string;
}

export interface PairingUser {
  platform: string;
  user_id: string;
  user_name?: string;
  code?: string;
  age_minutes?: number;
}

export interface PairingResponse {
  pending: PairingUser[];
  approved: PairingUser[];
}

export interface WebhookRoute {
  name: string;
  description: string;
  events: string[];
  deliver: string;
  deliver_only: boolean;
  prompt: string;
  skills: string[];
  created_at: string | null;
  url: string;
  secret_set: boolean;
  enabled: boolean;
}

export interface WebhooksResponse {
  enabled: boolean;
  base_url: string;
  subscriptions: WebhookRoute[];
}

export interface WebhookEnableResponse {
  ok: boolean;
  platform: "webhook";
  enabled: true;
  needs_restart: boolean;
  restart_started?: boolean;
  restart_action?: string;
  restart_pid?: number | null;
  restart_error?: string;
}

export interface WebhookCreate {
  name: string;
  description?: string;
  events?: string[];
  prompt?: string;
  skills?: string[];
  deliver?: string;
  deliver_only?: boolean;
  deliver_chat_id?: string;
}

export interface CredentialPoolEntry {
  index: number;
  id: string | null;
  label: string | null;
  auth_type: string | null;
  source: string | null;
  priority: number;
  last_status: string | null;
  request_count: number;
  token_preview: string;
  has_refresh: boolean;
}

export interface CredentialPoolProvider {
  provider: string;
  entries: CredentialPoolEntry[];
}

export interface MemoryProviderInfo {
  name: string;
  description: string;
  configured: boolean;
}

export interface MemoryStatus {
  active: string;
  providers: MemoryProviderInfo[];
  builtin_files: { memory: number; user: number };
}

export interface HookEntry {
  event: string;
  matcher: string | null;
  command: string | null;
  timeout: number | null;
  allowed: boolean;
  approved_at?: string | null;
  executable?: boolean;
}

export interface HooksResponse {
  hooks: HookEntry[];
  valid_events: string[];
}

export interface HookCreate {
  event: string;
  command: string;
  matcher?: string;
  timeout?: number;
  approve?: boolean;
}

export interface UpdateCheckResponse {
  install_method: string;
  current_version: string;
  // commits behind: >=1 known count, 0 up to date, -1 behind by unknown
  // count (nix/pypi), or null when the check could not run.
  behind: number | null;
  update_available: boolean;
  can_apply: boolean;
  update_command: string;
  message: string | null;
}

export interface SystemStats {
  os: string;
  os_release: string;
  os_version: string;
  platform: string;
  arch: string;
  hostname: string;
  python_version: string;
  python_impl: string;
  aetheros_version: string;
  cpu_count: number | null;
  psutil: boolean;
  cpu_percent?: number;
  load_avg?: number[];
  uptime_seconds?: number;
  memory?: { total: number; available: number; used: number; percent: number };
  disk?: { total: number; used: number; free: number; percent: number };
  process?: { pid: number; rss: number; create_time: number; num_threads: number };
}

export interface CuratorStatus {
  enabled: boolean;
  paused: boolean;
  interval_hours: number | null;
  last_run_at: string | null;
  min_idle_hours: number | null;
  stale_after_days: number | null;
  archive_after_days: number | null;
}

export interface PortalFeature {
  label: string;
  state: string;
}

export interface PortalStatus {
  logged_in: boolean;
  portal_url: string | null;
  inference_url: string | null;
  provider: string;
  subscription_url: string;
  features: PortalFeature[];
}

export interface CheckpointSession {
  session: string;
  files: number;
  bytes: number;
}

export interface CheckpointsResponse {
  sessions: CheckpointSession[];
  total_bytes: number;
}

/** Per-call overrides for {@link fetchJSON}. */
interface FetchJSONOptions {
  /** When true, a 401 response is surfaced as a normal thrown error rather
   *  than triggering the loopback stale-token page reload. Use for probes
   *  whose 401 is an expected signal (e.g. /api/auth/me in non-gated mode)
   *  rather than evidence of a rotated session token. */
  allowUnauthorized?: boolean;
}

export interface ActionStatusResponse {
  exit_code: number | null;
  lines: string[];
  name: string;
  pid: number | null;
  running: boolean;
}

export interface PlatformStatus {
  error_code?: string;
  error_message?: string;
  state: string;
  updated_at: string;
}

export interface StatusResponse {
  active_sessions: number;
  /** Phase 7: ``true`` when the dashboard's OAuth gate is engaged
   * (public bind, no ``--insecure``). Read alongside ``auth_providers``
   * to render a "gated / loopback" badge. */
  auth_required?: boolean;
  /** Phase 7: registered ``DashboardAuthProvider`` names (e.g. ``["nous"]``).
   * Empty in loopback mode; empty + ``auth_required=true`` is a
   * fail-closed state (the dashboard will refuse to bind). */
  auth_providers?: string[];
  config_path: string;
  config_version: number;
  env_path: string;
  gateway_exit_reason: string | null;
  gateway_health_url: string | null;
  gateway_pid: number | null;
  gateway_platforms: Record<string, PlatformStatus>;
  gateway_running: boolean;
  gateway_state: string | null;
  gateway_updated_at: string | null;
  aetheros_home: string;
  latest_config_version: number;
  release_date: string;
  version: string;
}

export interface SessionInfo {
  id: string;
  source: string | null;
  model: string | null;
  title: string | null;
  started_at: number;
  ended_at: number | null;
  last_active: number;
  is_active: boolean;
  message_count: number;
  tool_call_count: number;
  input_tokens: number;
  output_tokens: number;
  preview: string | null;
  parent_session_id?: string | null;
}

export interface SessionLatestDescendantResponse {
  requested_session_id: string;
  session_id: string;
  path: string[];
  changed: boolean;
}

export interface PaginatedSessions {
  sessions: SessionInfo[];
  total: number;
  limit: number;
  offset: number;
}

export interface EnvVarInfo {
  is_set: boolean;
  redacted_value: string | null;
  description: string;
  url: string | null;
  category: string;
  is_password: boolean;
  tools: string[];
  advanced: boolean;
  /** True when this var is a messaging-platform credential owned by the Channels page. */
  channel_managed?: boolean;
}

export interface TelegramOnboardingStartResponse {
  pairing_id: string;
  suggested_username: string;
  deep_link: string;
  qr_payload: string;
  expires_at: string;
}

export type TelegramOnboardingStatusResponse =
  | { status: "waiting"; expires_at: string }
  | {
      status: "ready";
      bot_username: string;
      owner_user_id?: string;
      expires_at: string;
    };

export interface TelegramOnboardingApplyResponse {
  ok: boolean;
  platform: "telegram";
  bot_username?: string;
  needs_restart: boolean;
  restart_started?: boolean;
  restart_action?: string;
  restart_pid?: number | null;
  restart_error?: string;
}

export interface SessionMessage {
  role: "user" | "assistant" | "system" | "tool";
  content: string | null;
  tool_calls?: Array<{
    id: string;
    function: { name: string; arguments: string };
  }>;
  tool_name?: string;
  tool_call_id?: string;
  timestamp?: number;
}

export interface SessionMessagesResponse {
  session_id: string;
  messages: SessionMessage[];
}

export interface LogsResponse {
  file: string;
  lines: string[];
}

export interface ManagedFileEntry {
  name: string;
  path: string;
  is_directory: boolean;
  size: number | null;
  mtime: number;
  mime_type: string | null;
}

export interface ManagedFilesResponse {
  root: string | null;
  path: string;
  parent: string | null;
  locked_root: string | null;
  can_change_path: boolean;
  entries: ManagedFileEntry[];
}

export interface ManagedFileReadResponse {
  name: string;
  path: string;
  size: number;
  mime_type: string;
  data_url: string;
  root: string | null;
  locked_root: string | null;
  can_change_path: boolean;
}

export interface ManagedFileWriteResponse {
  ok: boolean;
  path: string;
  entry: ManagedFileEntry;
  root: string | null;
  locked_root: string | null;
  can_change_path: boolean;
}

export interface AnalyticsDailyEntry {
  day: string;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  reasoning_tokens: number;
  estimated_cost: number;
  actual_cost: number;
  sessions: number;
  api_calls: number;
}

export interface AnalyticsModelEntry {
  model: string;
  input_tokens: number;
  output_tokens: number;
  estimated_cost: number;
  sessions: number;
  api_calls: number;
}

export interface AnalyticsSkillEntry {
  skill: string;
  view_count: number;
  manage_count: number;
  total_count: number;
  percentage: number;
  last_used_at: number | null;
}

export interface AnalyticsSkillsSummary {
  total_skill_loads: number;
  total_skill_edits: number;
  total_skill_actions: number;
  distinct_skills_used: number;
}

export interface AnalyticsResponse {
  daily: AnalyticsDailyEntry[];
  by_model: AnalyticsModelEntry[];
  totals: {
    total_input: number;
    total_output: number;
    total_cache_read: number;
    total_reasoning: number;
    total_estimated_cost: number;
    total_actual_cost: number;
    total_sessions: number;
    total_api_calls: number;
  };
  skills: {
    summary: AnalyticsSkillsSummary;
    top_skills: AnalyticsSkillEntry[];
  };
}

export interface ActiveProfileInfo {
  active: string;
  current: string;
}

export interface ProfileDescribeAutoResult {
  ok: boolean;
  reason: string;
  description: string | null;
  description_auto: boolean;
}

export interface ProfileInfo {
  name: string;
  path: string;
  is_default: boolean;
  model: string | null;
  provider: string | null;
  has_env: boolean;
  skill_count: number;
  gateway_running: boolean;
  description: string;
  description_auto: boolean;
  distribution_name: string | null;
  distribution_version: string | null;
  distribution_source: string | null;
  has_alias: boolean;
}

export interface ModelsAnalyticsModelEntry {
  model: string;
  provider: string;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  reasoning_tokens: number;
  estimated_cost: number;
  actual_cost: number;
  sessions: number;
  api_calls: number;
  tool_calls: number;
  last_used_at: number;
  avg_tokens_per_session: number;
  capabilities: {
    supports_tools?: boolean;
    supports_vision?: boolean;
    supports_reasoning?: boolean;
    context_window?: number;
    max_output_tokens?: number;
    model_family?: string;
  };
}

export interface ModelsAnalyticsResponse {
  models: ModelsAnalyticsModelEntry[];
  totals: {
    distinct_models: number;
    total_input: number;
    total_output: number;
    total_cache_read: number;
    total_reasoning: number;
    total_estimated_cost: number;
    total_actual_cost: number;
    total_sessions: number;
    total_api_calls: number;
  };
  period_days: number;
}

export interface CronJob {
  id: string;
  profile?: string | null;
  profile_name?: string | null;
  aetheros_home?: string | null;
  is_default_profile?: boolean;
  name?: string | null;
  prompt?: string | null;
  script?: string | null;
  skills?: string[] | null;
  schedule?: { kind?: string; expr?: string; display?: string };
  schedule_display?: string | null;
  enabled: boolean;
  state?: string | null;
  deliver?: string | null;
  last_run_at?: string | null;
  next_run_at?: string | null;
  last_error?: string | null;
}

export interface CronDeliveryTarget {
  id: string;
  name: string;
  home_target_set: boolean;
  home_env_var: string | null;
}

export interface AutomationBlueprintField {
  name: string;
  type: "time" | "enum" | "text" | "weekdays";
  label: string;
  default: string | null;
  options: string[];
  optional: boolean;
  /** When false, options are suggestions — any value is accepted. */
  strict?: boolean;
  help: string;
}

export interface AutomationBlueprint {
  key: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  fields: AutomationBlueprintField[];
  command: string;
  appUrl: string;
}

export interface SkillInfo {
  name: string;
  description: string;
  category: string;
  enabled: boolean;
}

export interface SkillContent {
  name: string;
  content: string;
  path: string;
}

export interface SkillWriteResult {
  success: boolean;
  message?: string;
  path?: string;
  error?: string;
}

export interface ToolsetInfo {
  name: string;
  label: string;
  description: string;
  enabled: boolean;
  configured: boolean;
  tools: string[];
}

export interface ToolsetProviderEnvVar {
  key: string;
  prompt: string;
  url: string | null;
  default: string | null;
  is_set: boolean;
}

export interface ToolsetProvider {
  name: string;
  badge: string;
  tag: string;
  env_vars: ToolsetProviderEnvVar[];
  post_setup: string | null;
  requires_nous_auth: boolean;
  is_active: boolean;
}

export interface ToolsetConfig {
  name: string;
  has_category: boolean;
  providers: ToolsetProvider[];
  active_provider: string | null;
}

export interface ToolsetEnvResult {
  ok: boolean;
  name: string;
  saved: string[];
  skipped: string[];
  is_set: Record<string, boolean>;
}

export interface SessionSearchResult {
  session_id: string;
  snippet: string;
  role: string | null;
  source: string | null;
  model: string | null;
  session_started: number | null;
}

export interface SessionSearchResponse {
  results: SessionSearchResult[];
}

// ── Model info types ──────────────────────────────────────────────────

export interface ModelInfoResponse {
  model: string;
  provider: string;
  auto_context_length: number;
  config_context_length: number;
  effective_context_length: number;
  capabilities: {
    supports_tools?: boolean;
    supports_vision?: boolean;
    supports_reasoning?: boolean;
    context_window?: number;
    max_output_tokens?: number;
    model_family?: string;
  };
}

// ── Model options / assignment types ──────────────────────────────────

export interface ModelOptionProvider {
  name: string;
  slug: string;
  models?: string[];
  total_models?: number;
  is_current?: boolean;
  is_user_defined?: boolean;
  source?: string;
  warning?: string;
}

export interface ModelOptionsResponse {
  model?: string;
  provider?: string;
  providers?: ModelOptionProvider[];
}

export interface AuxiliaryTaskAssignment {
  task: string;
  provider: string;
  model: string;
  base_url: string;
}

export interface AuxiliaryModelsResponse {
  tasks: AuxiliaryTaskAssignment[];
  main: { provider: string; model: string };
}

export interface ModelAssignmentRequest {
  confirm_expensive_model?: boolean;
  scope: "main" | "auxiliary";
  provider: string;
  model: string;
  /** Optional OpenAI-compatible endpoint URL for custom/local main providers. */
  base_url?: string;
  /** For auxiliary: task slot name, "" for all, "__reset__" to reset all. */
  task?: string;
}

/** An auxiliary task still pinned to a provider that differs from the
 *  newly-selected main provider after a main-model switch. */
export interface StaleAuxAssignment {
  task: string;
  provider: string;
  model: string;
}

export interface ModelAssignmentResponse {
  confirm_message?: string;
  confirm_required?: boolean;
  ok: boolean;
  scope?: string;
  provider?: string;
  model?: string;
  tasks?: string[];
  reset?: boolean;
  /** Auxiliary slots still pinned to a different provider than the new main.
   *  Switching main never clears aux pins; this lets the UI warn the user
   *  their helper tasks aren't following the switch. Only set on scope:'main'. */
  stale_aux?: StaleAuxAssignment[];
}

// ── OAuth provider types ────────────────────────────────────────────────

export interface OAuthProviderStatus {
  logged_in: boolean;
  source?: string | null;
  source_label?: string | null;
  token_preview?: string | null;
  expires_at?: string | null;
  has_refresh_token?: boolean;
  last_refresh?: string | null;
  error?: string;
}

export interface OAuthProvider {
  id: string;
  name: string;
  /** "pkce" (browser redirect + paste code), "device_code" (show code + URL),
   *  or "external" (delegated to a separate CLI like Claude Code or Qwen). */
  flow: "pkce" | "device_code" | "external";
  cli_command: string;
  docs_url: string;
  status: OAuthProviderStatus;
}

export interface OAuthProvidersResponse {
  providers: OAuthProvider[];
}

/** Discriminated union — the shape of /start depends on the flow. */
export type OAuthStartResponse =
  | {
      session_id: string;
      flow: "pkce";
      auth_url: string;
      expires_in: number;
    }
  | {
      session_id: string;
      flow: "device_code";
      user_code: string;
      verification_url: string;
      expires_in: number;
      poll_interval: number;
    };

export interface OAuthSubmitResponse {
  ok: boolean;
  status: "approved" | "error";
  message?: string;
}

export interface OAuthPollResponse {
  session_id: string;
  status: "pending" | "approved" | "denied" | "expired" | "error";
  error_message?: string | null;
  expires_at?: number | null;
}

// ── Dashboard theme types ──────────────────────────────────────────────

export interface DashboardThemeSummary {
  description: string;
  label: string;
  name: string;
  /** Full theme definition for user themes; undefined for built-ins
   *  (which the frontend already has locally). */
  definition?: DashboardTheme;
}

export interface DashboardThemesResponse {
  active: string;
  themes: DashboardThemeSummary[];
}

export interface DashboardFontResponse {
  /** Active font-override id, or "theme" when no override is set. */
  font: string;
}

// ── Dashboard plugin types ─────────────────────────────────────────────

export interface PluginManifestResponse {
  name: string;
  label: string;
  description: string;
  icon: string;
  version: string;
  tab: {
    path: string;
    position?: string;
    override?: string;
    hidden?: boolean;
  };
  slots?: string[];
  entry: string;
  css?: string | null;
  has_api: boolean;
  source: string;
}

export interface HubAgentPluginRow {
  name: string;
  version: string;
  description: string;
  source: string;
  runtime_status: "disabled" | "enabled" | "inactive";
  has_dashboard_manifest: boolean;
  dashboard_manifest: PluginManifestResponse | null;
  path: string;
  can_remove: boolean;
  can_update_git: boolean;
  auth_required: boolean;
  auth_command: string;
  user_hidden: boolean;
}

export interface PluginsHubProviders {
  memory_provider: string;
  memory_options: Array<{ name: string; description: string }>;
  context_engine: string;
  context_options: Array<{ name: string; description: string }>;
}

export interface PluginsHubResponse {
  plugins: HubAgentPluginRow[];
  orphan_dashboard_plugins: PluginManifestResponse[];
  providers: PluginsHubProviders;
}

export interface AgentPluginInstallRequest {
  identifier: string;
  force?: boolean;
  enable?: boolean;
}

export interface AgentPluginInstallResponse {
  ok: boolean;
  plugin_name?: string;
  warnings?: string[];
  missing_env?: string[];
  after_install_path?: string | null;
  enabled?: boolean;
  error?: string;
}

// ── Security types ────────────────────────────────────────────────────

export interface SecurityStatusResponse {
  zero_trust: boolean;
  initialized: boolean;
  version: string;
  permission_count?: number;
  active_sandboxes?: number;
  audit_entry_count?: number;
  threat_alerts?: number;
  secrets_count?: number;
}

export interface PermissionsResponse {
  grants: Array<{
    permission: string;
    grantee: string;
    granted_at: number;
    expires_at: number;
    duration: string;
    reason: string;
  }>;
}

export interface PermissionCategoriesResponse {
  categories: Array<{ category: string; actions: string[] }>;
}

export interface SecretsResponse {
  secrets: Array<{
    name: string;
    category: string;
    description: string;
    created_at: number;
    updated_at: number;
    expires_at: number;
  }>;
}

export interface AuditEntryResponse {
  event_type: string;
  timestamp: number;
  severity: string;
  user: string;
  source: string;
  details: Record<string, unknown>;
  message: string;
}

export interface AuditStatsResponse {
  total_entries: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  by_user: Record<string, number>;
}

export interface ThreatAlertResponse {
  alert_id: string;
  category: string;
  level: string;
  title: string;
  description: string;
  timestamp: number;
  source: string;
  recommendations: string[];
}

export interface ThreatSummaryResponse {
  total_alerts: number;
  by_level: Record<string, number>;
  by_category: Record<string, number>;
  recent_count: number;
}

export interface SandboxesResponse {
  sandboxes: Array<{
    name: string;
    active: boolean;
    backend: string;
    mode: string;
  }>;
}

export interface SandboxStatsResponse {
  total_sandboxes: number;
  active_sandboxes: number;
  backend: string;
}

export interface AgentPluginUpdateResponse {
  ok: boolean;
  name?: string;
  output?: string;
  unchanged?: boolean;
  error?: string;
}

export interface PluginProvidersPutRequest {
  memory_provider?: string;
  context_engine?: string;
}

// ── Agent Hub types ────────────────────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  description: string;
  role: string;
  model: string;
  provider: string;
  status: "idle" | "running" | "paused" | "error" | "restarting" | "stopped";
  enabled: boolean;
  tags: string[];
  memory_enabled: boolean;
  toolsets: string[];
  config: Record<string, unknown>;
  stats: AgentStats;
  created_at: string;
  updated_at: string;
  last_active: string | null;
}

export interface AgentStats {
  tasks_completed: number;
  tasks_failed: number;
  avg_duration: string;
  total_tokens: number;
  total_cost: number;
  last_active: string | null;
}

export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  role: string;
  category: string;
  icon: string;
  default_config: Record<string, unknown>;
  recommended_toolsets: string[];
  tags: string[];
}

export interface AgentConfig {
  agent_id: string;
  model: string;
  provider: string;
  temperature: number;
  max_iterations: number;
  system_prompt: string;
  toolsets: string[];
  memory_enabled: boolean;
  memory_provider: string;
  timeout_seconds: number;
  max_concurrent_tasks: number;
  allowed_tools: string[];
  disabled_tools: string[];
  environment_vars: Record<string, string>;
  mcp_servers: string[];
  plugin_configs: Record<string, unknown>;
  automation_rules: AutomationRule[];
}

export interface AutomationRule {
  trigger: AutomationTrigger;
  conditions: AutomationCondition[];
  actions: AutomationAction[];
  retry_count: number;
  retry_delay: number;
  enabled: boolean;
}

export interface AutomationTrigger {
  type: "schedule" | "event" | "webhook" | "file_change" | "agent_status" | "metric_threshold";
  config: Record<string, unknown>;
}

export interface AutomationCondition {
  field: string;
  operator: "eq" | "neq" | "gt" | "gte" | "lt" | "lte" | "contains" | "matches" | "exists";
  value: unknown;
}

export interface AutomationAction {
  type: "run_agent" | "send_notification" | "execute_workflow" | "call_webhook" | "update_config" | "log_message";
  config: Record<string, unknown>;
  timeout: number;
}

export interface AgentOrchestration {
  id: string;
  name: string;
  description: string;
  strategy: "sequential" | "parallel" | "fan_out" | "debate" | "voting" | "hierarchical";
  agents: string[];
  max_concurrent: number;
  timeout: number;
  input_template: string;
  output_aggregator: string;
  enabled: boolean;
  status: "idle" | "running" | "completed" | "failed";
  last_run: string | null;
  created_at: string;
}

export interface AutomationBlueprint2 {
  id: string;
  name: string;
  description: string;
  category: string;
  trigger: AutomationTrigger;
  conditions: AutomationCondition[];
  actions: AutomationAction[];
  variables: Record<string, string>;
  tags: string[];
  enabled: boolean;
  background: boolean;
  retry_policy: { max_retries: number; delay_seconds: number };
  created_at: string;
  updated_at: string;
}

export interface TaskDefinition {
  id: string;
  name: string;
  description: string;
  agent_id: string;
  priority: "low" | "medium" | "high" | "critical";
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  progress: number;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  scheduled_at: string | null;
  tags: string[];
}

export interface MarketplaceListing {
  id: string;
  name: string;
  description: string;
  type: "agent_template" | "workflow_template" | "automation_blueprint" | "toolset";
  author: string;
  version: string;
  category: string;
  tags: string[];
  downloads: number;
  rating: number;
  installed: boolean;
  has_update: boolean;
  source: string;
  readme: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables: Record<string, string>;
  tags: string[];
  enabled: boolean;
  status: "draft" | "active" | "running" | "completed" | "failed";
  last_run: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowNode {
  id: string;
  type: "trigger" | "condition" | "action" | "loop" | "subworkflow" | "output";
  label: string;
  config: Record<string, unknown>;
  position: { x: number; y: number };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  condition: string;
}

export interface SchedulerJob {
  id: string;
  name: string;
  description: string;
  agent_id: string;
  schedule: string;
  schedule_type: "cron" | "interval" | "once";
  action: string;
  params: Record<string, unknown>;
  enabled: boolean;
  last_run: string | null;
  next_run: string | null;
  retry_count: number;
  max_retries: number;
  created_at: string;
}

export interface BackgroundService {
  id: string;
  name: string;
  description: string;
  type: "watcher" | "listener" | "monitor" | "sync" | "maintenance";
  status: "running" | "stopped" | "error" | "starting";
  agent_id: string | null;
  pid: number | null;
  uptime: number;
  memory_mb: number;
  cpu_percent: number;
  last_heartbeat: string | null;
  error: string | null;
  auto_restart: boolean;
  created_at: string;
}

export interface AgentLogEntry {
  id: string;
  timestamp: string;
  level: "debug" | "info" | "warn" | "error";
  agent_id: string | null;
  component: string;
  message: string;
  metadata: Record<string, unknown>;
}

export interface AgentNotification {
  id: string;
  type: "info" | "warning" | "error" | "success";
  title: string;
  message: string;
  agent_id: string | null;
  read: boolean;
  created_at: string;
  expires_at: string | null;
}

export interface AgentPermission {
  id: string;
  agent_id: string;
  resource: string;
  action: string;
  effect: "allow" | "deny";
  granted_by: string;
  created_at: string;
  expires_at: string | null;
}

export interface AgentMemoryEntry {
  id: string;
  agent_id: string;
  type: "episodic" | "semantic" | "working";
  content: string;
  metadata: Record<string, unknown>;
  importance: number;
  created_at: string;
  last_accessed: string | null;
  access_count: number;
}

export interface TagDefinition {
  id: string;
  name: string;
  color: string;
  description: string;
  agent_count: number;
  created_at: string;
}

export interface AgentsResponse {
  agents: Agent[];
}

export interface AgentTemplatesResponse {
  templates: AgentTemplate[];
}

export interface OrchestrationsResponse {
  orchestrations: AgentOrchestration[];
}

export interface AutomationsResponse {
  automations: AutomationBlueprint2[];
}

export interface TasksResponse {
  tasks: TaskDefinition[];
}

export interface MarketplaceResponse {
  listings: MarketplaceListing[];
}

export interface WorkflowsResponse {
  workflows: WorkflowDefinition[];
}

export interface SchedulerJobsResponse {
  jobs: SchedulerJob[];
}

export interface BackgroundServicesResponse {
  services: BackgroundService[];
}

export interface AgentLogsResponse {
  logs: AgentLogEntry[];
}

export interface AgentNotificationsResponse {
  notifications: AgentNotification[];
}

export interface AgentPermissionsResponse {
  permissions: AgentPermission[];
}

export interface AgentMemoriesResponse {
  memories: AgentMemoryEntry[];
}

export interface TagsResponse {
  tags: TagDefinition[];
}

// ── Plugin Marketplace types ────────────────────────────────────────────

export interface PluginMarketEntry {
  id: string;
  name: string;
  description: string;
  long_description?: string;
  icon: string;
  author: string;
  author_url?: string;
  version: string;
  latest_version?: string;
  license?: string;
  category: string;
  tags: string[];
  downloads: number;
  rating: number;
  review_count: number;
  homepage?: string;
  repository?: string;
  readme?: string;
  documentation?: string;
  screenshots: string[];
  permissions?: PluginPermissions;
  dependencies?: string[];
  installed: boolean;
  installed_version?: string;
  enabled: boolean;
  has_update: boolean;
  verified: boolean;
  official: boolean;
  created_at: string;
  updated_at: string;
}

export interface MarketplaceCategory {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  count: number;
  featured: boolean;
}

export interface PluginReview {
  id: string;
  plugin_id: string;
  user: string;
  rating: number;
  title: string;
  content: string;
  version: string;
  created_at: string;
  updated_at: string;
  helpful_count: number;
}

export interface PluginVersion {
  version: string;
  changelog: string;
  published_at: string;
  size?: number;
}

export interface PluginPermissions {
  filesystem?: { read?: string[]; write?: string[] };
  network?: { hosts?: string[]; ports?: number[] };
  environment?: string[];
  system?: { exec?: boolean; process?: boolean };
  browser?: { navigate?: boolean; extract?: boolean };
  clipboard?: { read?: boolean; write?: boolean };
  microphone?: boolean;
  camera?: boolean;
  notifications?: boolean;
}

export interface PermissionRule {
  resource: string;
  action: string;
  effect: "allow" | "deny";
  conditions?: Record<string, unknown>;
}

export interface MarketplaceSearchResponse {
  entries: PluginMarketEntry[];
  categories: MarketplaceCategory[];
  featured: PluginMarketEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface PluginDetailResponse {
  entry: PluginMarketEntry;
  reviews: PluginReview[];
  versions: PluginVersion[];
  rating_distribution: Record<number, number>;
}

// ── MCP Enhanced types ──────────────────────────────────────────────────

export interface McpServerStatus {
  name: string;
  transport: string;
  enabled: boolean;
  status: "healthy" | "warning" | "error" | "unknown";
  latency_ms?: number;
  last_health_check?: string;
  error_message?: string;
  tools_count: number;
  uptime_seconds?: number;
  memory_mb?: number;
  cpu_percent?: number;
}

export interface McpServerLog {
  timestamp: string;
  level: "debug" | "info" | "warn" | "error";
  message: string;
  server: string;
}

export interface McpHealthResult {
  server: string;
  ok: boolean;
  latency_ms: number;
  tools: string[];
  error?: string;
  timestamp: string;
}

export interface McpAutoDiscovery {
  name: string;
  command: string;
  args: string[];
  description?: string;
  source: string;
}

// ── Extension SDK types ─────────────────────────────────────────────────

export interface ExtensionTemplate {
  id: string;
  name: string;
  description: string;
  type: "plugin" | "tool" | "mcp_server" | "skill" | "provider" | "hook";
  icon: string;
  files: string[];
  dependencies: string[];
  readme: string;
}

export interface BuildResult {
  success: boolean;
  output_path?: string;
  errors: string[];
  warnings: string[];
  duration_ms: number;
  size_bytes?: number;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationMessage[];
  warnings: ValidationMessage[];
  info: ValidationMessage[];
}

export interface ValidationMessage {
  file: string;
  line: number;
  column: number;
  message: string;
  code: string;
}

export interface PluginPackage {
  name: string;
  version: string;
  description: string;
  entry: string;
  dependencies: string[];
  permissions: string[];
}

// ── Developer Tools types ───────────────────────────────────────────────

export interface PluginLogEntry {
  id: string;
  plugin: string;
  timestamp: string;
  level: "debug" | "info" | "warn" | "error";
  message: string;
  metadata?: Record<string, unknown>;
}

export interface PerformanceMetrics {
  cpu_percent: number;
  memory_mb: number;
  memory_percent: number;
  plugin_cpu: Record<string, number>;
  plugin_memory: Record<string, number>;
  uptime_seconds: number;
}

export interface DebugConsoleMessage {
  id: string;
  timestamp: string;
  level: "log" | "info" | "warn" | "error" | "debug";
  source: string;
  message: string;
  data?: unknown;
}

export interface InspectorPluginData {
  name: string;
  version: string;
  hooks: string[];
  tools: string[];
  permissions: string[];
  routes: string[];
  slots: string[];
  state: Record<string, unknown>;
}

export interface MonitoringData {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  gpu_percent: number | null;
  gpu_memory_mb: number | null;
  running_agents: number;
  total_agents: number;
  running_tasks: number;
  total_tasks: number;
  providers_online: number;
  providers_total: number;
  models_available: number;
  memory_usage_percent: number;
  token_usage: { input: number; output: number; total: number; cost: number };
  logs: AgentLogEntry[];
}

export interface DesktopControllerEvent {
  type: string;
  payload: unknown;
  timestamp: number;
}

// ── Agent Hub API ──────────────────────────────────────────────────────
export interface AgentHubApi {
  getAgents: () => Promise<AgentsResponse>;
  getAgent: (id: string) => Promise<Agent>;
  createAgent: (data: Partial<Agent>) => Promise<Agent>;
  updateAgent: (id: string, data: Partial<Agent>) => Promise<Agent>;
  deleteAgent: (id: string) => Promise<{ ok: boolean }>;
  duplicateAgent: (id: string) => Promise<Agent>;
  cloneAgent: (id: string) => Promise<Agent>;
  pauseAgent: (id: string) => Promise<{ ok: boolean }>;
  resumeAgent: (id: string) => Promise<{ ok: boolean }>;
  restartAgent: (id: string) => Promise<{ ok: boolean }>;
  getAgentTemplates: () => Promise<AgentTemplatesResponse>;
  getAgentConfig: (agentId: string) => Promise<AgentConfig>;
  saveAgentConfig: (agentId: string, config: AgentConfig) => Promise<{ ok: boolean }>;
  getOrchestrations: () => Promise<OrchestrationsResponse>;
  createOrchestration: (data: Partial<AgentOrchestration>) => Promise<AgentOrchestration>;
  getAutomations: () => Promise<AutomationsResponse>;
  createAutomation: (data: Partial<AutomationBlueprint2>) => Promise<AutomationBlueprint2>;
  getTasks: () => Promise<TasksResponse>;
  createTask: (data: Partial<TaskDefinition>) => Promise<TaskDefinition>;
  updateTask: (id: string, data: Partial<TaskDefinition>) => Promise<TaskDefinition>;
  getMarketplace: () => Promise<MarketplaceResponse>;
  installMarketplace: (id: string) => Promise<{ ok: boolean }>;
  getWorkflows: () => Promise<WorkflowsResponse>;
  createWorkflow: (data: Partial<WorkflowDefinition>) => Promise<WorkflowDefinition>;
  runWorkflow: (id: string) => Promise<{ ok: boolean }>;
  getSchedulerJobs: () => Promise<SchedulerJobsResponse>;
  createSchedulerJob: (data: Partial<SchedulerJob>) => Promise<SchedulerJob>;
  getBackgroundServices: () => Promise<BackgroundServicesResponse>;
  startBackgroundService: (id: string) => Promise<{ ok: boolean }>;
  stopBackgroundService: (id: string) => Promise<{ ok: boolean }>;
  getAgentLogs: (agentId?: string) => Promise<AgentLogsResponse>;
  getAgentNotifications: () => Promise<AgentNotificationsResponse>;
  markAgentNotificationRead: (id: string) => Promise<{ ok: boolean }>;
  getAgentPermissions: (agentId?: string) => Promise<AgentPermissionsResponse>;
  grantAgentPermission: (permission: AgentPermission) => Promise<{ ok: boolean }>;
  revokeAgentPermission: (id: string) => Promise<{ ok: boolean }>;
  getAgentMemories: (agentId: string) => Promise<AgentMemoriesResponse>;
  searchAgentMemories: (query: string) => Promise<AgentMemoriesResponse>;
  getTags: () => Promise<TagsResponse>;
  createTag: (data: Partial<TagDefinition>) => Promise<TagDefinition>;
  importAgent: (data: FormData) => Promise<Agent>;
  exportAgent: (id: string) => Promise<string>;
  getMonitoringData: () => Promise<MonitoringData>;
}
