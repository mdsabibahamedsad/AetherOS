import { create } from "zustand";
import { orchestratorApi } from "@/lib/orchestrator-api";

export interface PlanStep {
  description: string;
  agent_role: string;
  tools: string[];
  estimated_duration: number;
  estimated_cost: number;
  risk_level: string;
  requires_approval: boolean;
  parallelizable: boolean;
}

export interface TaskItem {
  id: string;
  name: string;
  description: string;
  task_type: string;
  status: string;
  agent_role: string;
  dependencies: string[];
  progress: number;
  error: string;
  retry_count: number;
  estimated_duration: number;
  estimated_cost: number;
  requires_approval: boolean;
  approval_status: string;
}

export interface PlanData {
  id: string;
  goal: string;
  status: string;
  steps: PlanStep[];
  tasks: TaskItem[];
  estimated_time: number;
  estimated_cost: number;
  risk_level: string;
  created_at: number;
  started_at: number;
  completed_at: number;
  error: string;
  metadata: Record<string, unknown>;
}

export interface GraphNode {
  id: string;
  task_id: string;
  node_type: string;
  label: string;
  status: string;
  level: number;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  edge_type: string;
  condition: string;
  label: string;
}

export interface ExecutionGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  levels: string[][];
}

export interface AgentDef {
  role: string;
  name: string;
  description: string;
  tools: string[];
  permissions: string[];
  max_sub_agents: number;
  memory_enabled: boolean;
}

export interface AgentInstance {
  id: string;
  role: string;
  name: string;
  status: string;
  current_task_id: string;
  parent_id: string;
}

export interface TemplateInfo {
  id: string;
  name: string;
  description: string;
  category: string;
  estimated_duration: number;
  estimated_cost: number;
  risk_level: string;
  tags: string[];
  is_builtin: boolean;
  usage_count: number;
}

export interface ApprovalReq {
  id: string;
  plan_id: string;
  task_id: string;
  action: string;
  description: string;
  reason: string;
  risk_level: string;
  status: string;
  created_at: number;
}

export interface OrchestrationEvent {
  event: string;
  data: Record<string, unknown>;
  timestamp: number;
}

export interface NLParseResult {
  intent: string;
  goal: string;
  schedule: string;
  agents: string[];
  tools: string[];
  permissions: string[];
  output_format: string;
  constraints: string[];
}

export interface OrchestrationStats {
  total_plans: number;
  completed_plans: number;
  failed_plans: number;
  running_plans: number;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  avg_duration: number;
  agent_stats: { total: number; active: number; by_role: Record<string, number> };
  approval_stats: { total_requests: number; pending: number; approved: number; denied: number };
  template_stats: { total_templates: number; builtin: number; custom: number };
  memory_stats: { conversation_entries: number; task_results: number; long_term_entries: number };
}

interface TaskStore {
  plans: PlanData[];
  currentPlan: PlanData | null;
  graph: ExecutionGraph | null;
  events: OrchestrationEvent[];
  agents: AgentDef[];
  activeAgents: AgentInstance[];
  templates: TemplateInfo[];
  pendingApprovals: ApprovalReq[];
  stats: OrchestrationStats | null;
  loading: boolean;
  error: string | null;

  fetchPlans: (status?: string) => Promise<void>;
  fetchPlan: (planId: string) => Promise<void>;
  submitGoal: (goal: string, options?: Record<string, unknown>) => Promise<PlanData | null>;
  parseNL: (text: string) => Promise<NLParseResult | null>;
  executeNL: (text: string) => Promise<PlanData | null>;
  pausePlan: (planId: string) => Promise<boolean>;
  resumePlan: (planId: string) => Promise<boolean>;
  cancelPlan: (planId: string) => Promise<boolean>;
  retryTask: (planId: string, taskId: string) => Promise<boolean>;
  fetchGraph: (planId: string) => Promise<void>;
  fetchEvents: (eventFilter?: string) => Promise<void>;
  fetchAgents: () => Promise<void>;
  fetchActiveAgents: () => Promise<void>;
  fetchTemplates: (category?: string) => Promise<void>;
  fetchPendingApprovals: (planId?: string) => Promise<void>;
  approveRequest: (requestId: string, approved: boolean, userId?: string, duration?: string) => Promise<boolean>;
  fetchStats: () => Promise<void>;
  submitTemplate: (templateId: string, variables?: Record<string, string>) => Promise<PlanData | null>;
  clearCurrentPlan: () => void;
  clearError: () => void;
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  plans: [],
  currentPlan: null,
  graph: null,
  events: [],
  agents: [],
  activeAgents: [],
  templates: [],
  pendingApprovals: [],
  stats: null,
  loading: false,
  error: null,

  fetchPlans: async (status?: string) => {
    set({ loading: true, error: null });
    try {
      const params = status ? `?status=${status}` : "";
      const res = await orchestratorApi.listPlans(params);
      set({ plans: res.plans ?? [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchPlan: async (planId: string) => {
    set({ loading: true, error: null });
    try {
      const plan = await orchestratorApi.getPlan(planId);
      set({ currentPlan: plan, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  submitGoal: async (goal: string, options?: Record<string, unknown>) => {
    set({ loading: true, error: null });
    try {
      const result = await orchestratorApi.submitGoal(goal, options ?? {});
      if (result.plan_id) {
        await get().fetchPlan(result.plan_id);
      }
      set({ loading: false });
      return get().currentPlan;
    } catch (err) {
      set({ error: String(err), loading: false });
      return null;
    }
  },

  parseNL: async (text: string) => {
    try {
      return await orchestratorApi.parseNL(text);
    } catch {
      return null;
    }
  },

  executeNL: async (text: string) => {
    set({ loading: true, error: null });
    try {
      const result = await orchestratorApi.submitNL(text);
      if (result.plan_id) {
        await get().fetchPlan(result.plan_id);
      }
      set({ loading: false });
      return get().currentPlan;
    } catch (err) {
      set({ error: String(err), loading: false });
      return null;
    }
  },

  pausePlan: async (planId: string) => {
    try {
      const res = await orchestratorApi.pausePlan(planId);
      if (res.success) await get().fetchPlan(planId);
      return res.success;
    } catch {
      return false;
    }
  },

  resumePlan: async (planId: string) => {
    try {
      const res = await orchestratorApi.resumePlan(planId);
      if (res.success) await get().fetchPlan(planId);
      return res.success;
    } catch {
      return false;
    }
  },

  cancelPlan: async (planId: string) => {
    try {
      const res = await orchestratorApi.cancelPlan(planId);
      if (res.success) await get().fetchPlan(planId);
      return res.success;
    } catch {
      return false;
    }
  },

  retryTask: async (planId: string, taskId: string) => {
    try {
      const res = await orchestratorApi.retryTask(planId, taskId);
      if (res.success) await get().fetchPlan(planId);
      return res.success;
    } catch {
      return false;
    }
  },

  fetchGraph: async (planId: string) => {
    try {
      const graph = await orchestratorApi.getGraph(planId);
      set({ graph });
    } catch {
      // ignore
    }
  },

  fetchEvents: async (eventFilter?: string) => {
    try {
      const events = await orchestratorApi.getEvents(eventFilter ?? "");
      set({ events });
    } catch {
      // ignore
    }
  },

  fetchAgents: async () => {
    try {
      const agents = await orchestratorApi.listAgents();
      set({ agents });
    } catch {
      // ignore
    }
  },

  fetchActiveAgents: async () => {
    try {
      const activeAgents = await orchestratorApi.listActiveAgents();
      set({ activeAgents });
    } catch {
      // ignore
    }
  },

  fetchTemplates: async (category?: string) => {
    try {
      const templates = await orchestratorApi.listTemplates(category ?? "");
      set({ templates });
    } catch {
      // ignore
    }
  },

  fetchPendingApprovals: async (planId?: string) => {
    try {
      const pendingApprovals = await orchestratorApi.getPendingApprovals(planId ?? "");
      set({ pendingApprovals });
    } catch {
      // ignore
    }
  },

  approveRequest: async (requestId: string, approved: boolean, userId?: string, duration?: string) => {
    try {
      const res = await orchestratorApi.approveRequest(requestId, approved, userId ?? "", duration ?? "once");
      if (res.success) {
        await get().fetchPendingApprovals();
      }
      return res.success;
    } catch {
      return false;
    }
  },

  fetchStats: async () => {
    try {
      const stats = await orchestratorApi.getStats();
      set({ stats });
    } catch {
      // ignore
    }
  },

  submitTemplate: async (templateId: string, variables?: Record<string, string>) => {
    set({ loading: true, error: null });
    try {
      const result = await orchestratorApi.createFromTemplate(templateId, variables ?? {});
      if (result.plan_id) {
        await get().fetchPlan(result.plan_id);
      }
      set({ loading: false });
      return get().currentPlan;
    } catch (err) {
      set({ error: String(err), loading: false });
      return null;
    }
  },

  clearCurrentPlan: () => set({ currentPlan: null, graph: null }),
  clearError: () => set({ error: null }),
}));
