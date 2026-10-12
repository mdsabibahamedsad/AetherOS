import { HERMES_BASE_PATH } from "./api";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const base = HERMES_BASE_PATH;
  const res = await fetch(`${base}${url}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const orchestratorApi = {
  submitGoal: (goal: string, options: Record<string, unknown> = {}) =>
    fetchJSON<{ plan_id?: string; success: boolean; status: string; error?: string }>("/api/orchestrator/submit", {
      method: "POST",
      body: JSON.stringify({ goal, ...options }),
    }),

  submitNL: (text: string) =>
    fetchJSON<{ plan_id?: string; success: boolean; status: string; error?: string }>("/api/orchestrator/submit-nl", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  getPlan: (planId: string) =>
    fetchJSON<any>(`/api/orchestrator/plans/${planId}`),

  listPlans: (params: string = "") =>
    fetchJSON<{ plans: any[] }>(`/api/orchestrator/plans${params}`),

  pausePlan: (planId: string) =>
    fetchJSON<{ success: boolean }>(`/api/orchestrator/plans/${planId}/pause`, { method: "POST" }),

  resumePlan: (planId: string) =>
    fetchJSON<{ success: boolean }>(`/api/orchestrator/plans/${planId}/resume`, { method: "POST" }),

  cancelPlan: (planId: string) =>
    fetchJSON<{ success: boolean }>(`/api/orchestrator/plans/${planId}/cancel`, { method: "POST" }),

  retryTask: (planId: string, taskId: string) =>
    fetchJSON<{ success: boolean }>(`/api/orchestrator/plans/${planId}/tasks/${taskId}/retry`, { method: "POST" }),

  getGraph: (planId: string) =>
    fetchJSON<any>(`/api/orchestrator/plans/${planId}/graph`),

  getEvents: (eventFilter: string = "") =>
    fetchJSON<any[]>(`/api/orchestrator/events${eventFilter ? `?event=${eventFilter}` : ""}`),

  listAgents: () =>
    fetchJSON<any[]>("/api/orchestrator/agents"),

  listActiveAgents: () =>
    fetchJSON<any[]>("/api/orchestrator/agents/active"),

  listTemplates: (category: string = "") =>
    fetchJSON<any[]>(`/api/orchestrator/templates${category ? `?category=${category}` : ""}`),

  getTemplate: (templateId: string) =>
    fetchJSON<any>(`/api/orchestrator/templates/${templateId}`),

  createFromTemplate: (templateId: string, variables: Record<string, string> = {}) =>
    fetchJSON<{ plan_id?: string; success: boolean }>("/api/orchestrator/templates/execute", {
      method: "POST",
      body: JSON.stringify({ template_id: templateId, variables }),
    }),

  getPendingApprovals: (planId: string = "") =>
    fetchJSON<any[]>(`/api/orchestrator/approvals/pending${planId ? `?plan_id=${planId}` : ""}`),

  approveRequest: (requestId: string, approved: boolean, userId: string, duration: string) =>
    fetchJSON<{ success: boolean }>("/api/orchestrator/approvals/respond", {
      method: "POST",
      body: JSON.stringify({ request_id: requestId, approved, user_id: userId, duration }),
    }),

  parseNL: (text: string) =>
    fetchJSON<any>("/api/orchestrator/parse-nl", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  getStats: () =>
    fetchJSON<any>("/api/orchestrator/stats"),

  getStatus: () =>
    fetchJSON<any>("/api/orchestrator/status"),
};
