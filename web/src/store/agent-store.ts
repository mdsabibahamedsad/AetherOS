import { create } from "zustand";
import { api } from "@/lib/api";
import type { Agent, AgentTemplate, AgentConfig, AgentOrchestration, AutomationBlueprint2, TaskDefinition, MarketplaceListing, WorkflowDefinition, SchedulerJob, BackgroundService, AgentLogEntry, AgentNotification, AgentPermission, AgentMemoryEntry, TagDefinition } from "@/lib/api";

interface AgentStore {
  agents: Agent[];
  agent: Agent | null;
  templates: AgentTemplate[];
  configs: Record<string, AgentConfig>;
  orchestrations: AgentOrchestration[];
  automations: AutomationBlueprint2[];
  tasks: TaskDefinition[];
  marketplaces: MarketplaceListing[];
  workflows: WorkflowDefinition[];
  schedulers: SchedulerJob[];
  backgrounds: BackgroundService[];
  logs: AgentLogEntry[];
  notifications: AgentNotification[];
  permissions: AgentPermission[];
  memories: AgentMemoryEntry[];
  tags: TagDefinition[];
  searchQuery: string;
  loading: boolean;
  error: string | null;

  fetchAgents: () => Promise<void>;
  fetchAgent: (id: string) => Promise<void>;
  createAgent: (data: Partial<Agent>) => Promise<Agent>;
  updateAgent: (id: string, data: Partial<Agent>) => Promise<void>;
  deleteAgent: (id: string) => Promise<void>;
  duplicateAgent: (id: string) => Promise<void>;
  cloneAgent: (id: string) => Promise<void>;
  pauseAgent: (id: string) => Promise<void>;
  resumeAgent: (id: string) => Promise<void>;
  restartAgent: (id: string) => Promise<void>;
  fetchTemplates: () => Promise<void>;
  fetchConfig: (agentId: string) => Promise<void>;
  saveConfig: (agentId: string, config: AgentConfig) => Promise<void>;
  fetchOrchestrations: () => Promise<void>;
  createOrchestration: (data: Partial<AgentOrchestration>) => Promise<void>;
  fetchAutomations: () => Promise<void>;
  createAutomation: (data: Partial<AutomationBlueprint2>) => Promise<void>;
  fetchTasks: () => Promise<void>;
  createTask: (data: Partial<TaskDefinition>) => Promise<void>;
  updateTask: (id: string, data: Partial<TaskDefinition>) => Promise<void>;
  fetchMarketplace: () => Promise<void>;
  installMarketplace: (id: string) => Promise<void>;
  fetchWorkflows: () => Promise<void>;
  createWorkflow: (data: Partial<WorkflowDefinition>) => Promise<void>;
  runWorkflow: (id: string) => Promise<void>;
  fetchSchedulers: () => Promise<void>;
  createScheduler: (data: Partial<SchedulerJob>) => Promise<void>;
  fetchBackgrounds: () => Promise<void>;
  startBackground: (id: string) => Promise<void>;
  stopBackground: (id: string) => Promise<void>;
  fetchLogs: (agentId?: string) => Promise<void>;
  fetchNotifications: () => Promise<void>;
  markNotificationRead: (id: string) => Promise<void>;
  fetchPermissions: (agentId?: string) => Promise<void>;
  grantPermission: (permission: AgentPermission) => Promise<void>;
  revokePermission: (id: string) => Promise<void>;
  fetchMemories: (agentId: string) => Promise<void>;
  searchMemories: (query: string) => Promise<void>;
  fetchTags: () => Promise<void>;
  createTag: (data: Partial<TagDefinition>) => Promise<void>;
  importAgent: (data: FormData) => Promise<void>;
  exportAgent: (id: string) => Promise<string>;
  setSearchQuery: (query: string) => void;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: [],
  agent: null,
  templates: [],
  configs: {},
  orchestrations: [],
  automations: [],
  tasks: [],
  marketplaces: [],
  workflows: [],
  schedulers: [],
  backgrounds: [],
  logs: [],
  notifications: [],
  permissions: [],
  memories: [],
  tags: [],
  searchQuery: "",
  loading: false,
  error: null,

  setSearchQuery: (query: string) => set({ searchQuery: query }),

  fetchAgents: async () => {
    set({ loading: true, error: null });
    try {
      const res = await api.getAgents();
      set({ agents: res.agents ?? [], loading: false });
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  fetchAgent: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const res = await api.getAgent(id);
      set({ agent: res, loading: false });
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  createAgent: async (data: Partial<Agent>) => {
    set({ loading: true, error: null });
    try {
      const res = await api.createAgent(data);
      const agents = [...get().agents, res];
      set({ agents, loading: false });
      return res;
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
      throw err;
    }
  },

  updateAgent: async (id: string, data: Partial<Agent>) => {
    set({ loading: true, error: null });
    try {
      const res = await api.updateAgent(id, data);
      set((state) => ({
        agents: state.agents.map((a) => (a.id === id ? res : a)),
        agent: state.agent?.id === id ? res : state.agent,
        loading: false,
      }));
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  deleteAgent: async (id: string) => {
    set({ loading: true, error: null });
    try {
      await api.deleteAgent(id);
      set((state) => ({
        agents: state.agents.filter((a) => a.id !== id),
        agent: state.agent?.id === id ? null : state.agent,
        loading: false,
      }));
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  duplicateAgent: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const res = await api.duplicateAgent(id);
      set((state) => ({ agents: [...state.agents, res], loading: false }));
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  cloneAgent: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const res = await api.cloneAgent(id);
      set((state) => ({ agents: [...state.agents, res], loading: false }));
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  pauseAgent: async (id: string) => {
    try {
      await api.pauseAgent(id);
      set((state) => ({
        agents: state.agents.map((a) =>
          a.id === id ? { ...a, status: "paused" } : a
        ),
        agent: state.agent?.id === id ? { ...state.agent, status: "paused" } : state.agent,
      }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  resumeAgent: async (id: string) => {
    try {
      await api.resumeAgent(id);
      set((state) => ({
        agents: state.agents.map((a) =>
          a.id === id ? { ...a, status: "running" } : a
        ),
        agent: state.agent?.id === id ? { ...state.agent, status: "running" } : state.agent,
      }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  restartAgent: async (id: string) => {
    try {
      await api.restartAgent(id);
      set((state) => ({
        agents: state.agents.map((a) =>
          a.id === id ? { ...a, status: "restarting" } : a
        ),
        agent: state.agent?.id === id ? { ...state.agent, status: "restarting" } : state.agent,
      }));
      setTimeout(() => get().fetchAgents(), 2000);
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchTemplates: async () => {
    try {
      const res = await api.getAgentTemplates();
      set({ templates: res.templates ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchConfig: async (agentId: string) => {
    try {
      const res = await api.getAgentConfig(agentId);
      set((state) => ({ configs: { ...state.configs, [agentId]: res } }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  saveConfig: async (agentId: string, config: AgentConfig) => {
    try {
      await api.saveAgentConfig(agentId, config);
      set((state) => ({ configs: { ...state.configs, [agentId]: config } }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchOrchestrations: async () => {
    try {
      const res = await api.getOrchestrations();
      set({ orchestrations: res.orchestrations ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  createOrchestration: async (data: Partial<AgentOrchestration>) => {
    try {
      const res = await api.createOrchestration(data);
      set((state) => ({ orchestrations: [...state.orchestrations, res] }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchAutomations: async () => {
    try {
      const res = await api.getAutomations();
      set({ automations: res.automations ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  createAutomation: async (data: Partial<AutomationBlueprint2>) => {
    try {
      const res = await api.createAutomation(data);
      set((state) => ({ automations: [...state.automations, res] }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchTasks: async () => {
    try {
      const res = await api.getTasks();
      set({ tasks: res.tasks ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  createTask: async (data: Partial<TaskDefinition>) => {
    try {
      const res = await api.createTask(data);
      set((state) => ({ tasks: [...state.tasks, res] }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  updateTask: async (id: string, data: Partial<TaskDefinition>) => {
    try {
      const res = await api.updateTask(id, data);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? res : t)),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchMarketplace: async () => {
    try {
      const res = await api.getMarketplace();
      set({ marketplaces: res.listings ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  installMarketplace: async (id: string) => {
    try {
      await api.installMarketplace(id);
      await get().fetchMarketplace();
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchWorkflows: async () => {
    try {
      const res = await api.getWorkflows();
      set({ workflows: res.workflows ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  createWorkflow: async (data: Partial<WorkflowDefinition>) => {
    try {
      const res = await api.createWorkflow(data);
      set((state) => ({ workflows: [...state.workflows, res] }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  runWorkflow: async (id: string) => {
    try {
      await api.runWorkflow(id);
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchSchedulers: async () => {
    try {
      const res = await api.getSchedulerJobs();
      set({ schedulers: res.jobs ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  createScheduler: async (data: Partial<SchedulerJob>) => {
    try {
      const res = await api.createSchedulerJob(data);
      set((state) => ({ schedulers: [...state.schedulers, res] }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchBackgrounds: async () => {
    try {
      const res = await api.getBackgroundServices();
      set({ backgrounds: res.services ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  startBackground: async (id: string) => {
    try {
      await api.startBackgroundService(id);
      await get().fetchBackgrounds();
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  stopBackground: async (id: string) => {
    try {
      await api.stopBackgroundService(id);
      await get().fetchBackgrounds();
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchLogs: async (agentId?: string) => {
    try {
      const res = await api.getAgentLogs(agentId);
      set({ logs: res.logs ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchNotifications: async () => {
    try {
      const res = await api.getAgentNotifications();
      set({ notifications: res.notifications ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  markNotificationRead: async (id: string) => {
    try {
      await api.markAgentNotificationRead(id);
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, read: true } : n
        ),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchPermissions: async (agentId?: string) => {
    try {
      const res = await api.getAgentPermissions(agentId);
      set({ permissions: res.permissions ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  grantPermission: async (permission: AgentPermission) => {
    try {
      await api.grantAgentPermission(permission);
      await get().fetchPermissions();
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  revokePermission: async (id: string) => {
    try {
      await api.revokeAgentPermission(id);
      set((state) => ({
        permissions: state.permissions.filter((p) => p.id !== id),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchMemories: async (agentId: string) => {
    try {
      const res = await api.getAgentMemories(agentId);
      set({ memories: res.memories ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  searchMemories: async (query: string) => {
    try {
      const res = await api.searchAgentMemories(query);
      set({ memories: res.memories ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  fetchTags: async () => {
    try {
      const res = await api.getTags();
      set({ tags: res.tags ?? [] });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  createTag: async (data: Partial<TagDefinition>) => {
    try {
      const res = await api.createTag(data);
      set((state) => ({ tags: [...state.tags, res] }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  importAgent: async (data: FormData) => {
    set({ loading: true, error: null });
    try {
      const res = await api.importAgent(data);
      set((state) => ({
        agents: [...state.agents, res],
        loading: false,
      }));
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  exportAgent: async (id: string) => {
    try {
      return await api.exportAgent(id);
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },
}));
