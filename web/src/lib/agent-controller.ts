import { api } from "./api";
import { useAgentStore } from "@/store/agent-store";

export const agentController = {
  async initialize() {
    await Promise.all([
      useAgentStore.getState().fetchAgents(),
      useAgentStore.getState().fetchTemplates(),
      useAgentStore.getState().fetchOrchestrations(),
      useAgentStore.getState().fetchAutomations(),
      useAgentStore.getState().fetchTasks(),
      useAgentStore.getState().fetchMarketplace(),
      useAgentStore.getState().fetchWorkflows(),
      useAgentStore.getState().fetchSchedulers(),
      useAgentStore.getState().fetchBackgrounds(),
      useAgentStore.getState().fetchNotifications(),
      useAgentStore.getState().fetchTags(),
    ]);
  },

  async getMonitoringData() {
    return api.getMonitoringData();
  },

  async refreshAgent(id: string) {
    await useAgentStore.getState().fetchAgent(id);
  },

  async refreshAll() {
    await useAgentStore.getState().fetchAgents();
  },

  async createAgentFromTemplate(templateId: string, overrides?: Record<string, unknown>) {
    const templates = useAgentStore.getState().templates;
    const template = templates.find((t) => t.id === templateId);
    if (!template) throw new Error(`Template not found: ${templateId}`);
    return useAgentStore.getState().createAgent({
      name: template.name,
      description: template.description,
      role: template.role,
      tags: template.tags,
      toolsets: template.recommended_toolsets,
      config: template.default_config,
      ...overrides,
    });
  },

  async bulkDeleteAgent(ids: string[]) {
    for (const id of ids) {
      await useAgentStore.getState().deleteAgent(id);
    }
  },

  async bulkPauseAgent(ids: string[]) {
    for (const id of ids) {
      await useAgentStore.getState().pauseAgent(id);
    }
  },

  async bulkResumeAgent(ids: string[]) {
    for (const id of ids) {
      await useAgentStore.getState().resumeAgent(id);
    }
  },

  async exportAgents(ids: string[]) {
    const results: Record<string, string> = {};
    for (const id of ids) {
      results[id] = await useAgentStore.getState().exportAgent(id);
    }
    return results;
  },

  search: {
    async agents(query: string) {
      useAgentStore.getState().setSearchQuery(query);
      await useAgentStore.getState().fetchAgents();
    },
    async memories(query: string) {
      await useAgentStore.getState().searchMemories(query);
    },
  },
};
