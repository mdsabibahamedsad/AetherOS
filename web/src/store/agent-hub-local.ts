import { create } from "zustand";
import { persist } from "zustand/middleware";

export type KnowledgeSourceType =
  | "pdf" | "markdown" | "word" | "text"
  | "website" | "git" | "folder" | "images";

export const KNOWLEDGE_SOURCE_TYPES: Array<{ type: KnowledgeSourceType; label: string }> = [
  { type: "pdf", label: "PDF" },
  { type: "markdown", label: "Markdown" },
  { type: "word", label: "Word" },
  { type: "text", label: "Text" },
  { type: "website", label: "Website" },
  { type: "git", label: "Git Repo" },
  { type: "folder", label: "Folder" },
  { type: "images", label: "Images" },
];

export interface KnowledgeAttachment {
  id: string;
  agentId: string;
  type: KnowledgeSourceType;
  name: string;
  path: string;
  size: number;
  status: "indexing" | "ready" | "error";
  error?: string;
  chunkCount: number;
  createdAt: string;
  metadata: Record<string, string>;
}

export interface AgentSecuritySettings {
  agentId: string;
  sandboxEnabled: boolean;
  sandboxMode: "isolated" | "restricted" | "standard";
  networkAccess: boolean;
  filesystemAccess: boolean;
  allowedDomains: string[];
  blockedDomains: string[];
  maxMemoryMb: number;
  maxCpuPercent: number;
  executionTimeout: number;
  requireApprovalFor: string[];
  auditLogging: boolean;
  secretsScope: "agent" | "profile" | "global";
}

export interface AgentAnalyticsData {
  agentId: string;
  dailyStats: Array<{
    date: string;
    messages: number;
    tokenInput: number;
    tokenOutput: number;
    cost: number;
    toolCalls: number;
  }>;
  topTools: Array<{ name: string; count: number }>;
  topModels: Array<{ name: string; count: number }>;
  avgResponseTime: number;
  totalSessions: number;
  totalCost: number;
}

export interface FavoriteAgent {
  agentId: string;
  addedAt: string;
  label?: string;
}

export interface ExportImportPayload {
  version: string;
  exportedAt: string;
  agent: Record<string, unknown>;
  config?: Record<string, unknown>;
  knowledge?: KnowledgeAttachment[];
  permissions?: Array<Record<string, unknown>>;
  security?: AgentSecuritySettings;
}

export interface BuiltInTemplate {
  id: string;
  name: string;
  description: string;
  role: string;
  category: string;
  recommendedToolsets: string[];
  tags: string[];
  defaultConfig: Partial<{
    model: string;
    provider: string;
    temperature: number;
    maxIterations: number;
    systemPrompt: string;
    toolsets: string[];
    memoryEnabled: boolean;
    timeoutSeconds: number;
  }>;
}

export const BUILT_IN_TEMPLATES: BuiltInTemplate[] = [
  {
    id: "general-assistant",
    name: "General Assistant",
    description: "A versatile assistant capable of handling a wide range of tasks including research, writing, analysis, and problem-solving.",
    role: "assistant",
    category: "productivity",
    recommendedToolsets: ["terminal", "file", "web", "search"],
    tags: ["general", "versatile", "starter"],
    defaultConfig: { model: "gpt-4o", provider: "openai", temperature: 0.7, maxIterations: 30, memoryEnabled: true, timeoutSeconds: 300 },
  },
  {
    id: "researcher",
    name: "Research Analyst",
    description: "Deep-dive research agent that gathers, synthesizes, and reports on complex topics using web search and document analysis.",
    role: "researcher",
    category: "research",
    recommendedToolsets: ["web", "search", "file", "terminal", "vision"],
    tags: ["research", "analysis", "deep-dive"],
    defaultConfig: { model: "claude-3-opus", provider: "anthropic", temperature: 0.3, maxIterations: 50, memoryEnabled: true, timeoutSeconds: 600 },
  },
  {
    id: "coder",
    name: "Software Engineer",
    description: "Full-stack development agent proficient in coding, debugging, code review, and software architecture across multiple languages.",
    role: "coder",
    category: "development",
    recommendedToolsets: ["terminal", "file", "code_execution", "debugging", "search"],
    tags: ["coding", "development", "engineering"],
    defaultConfig: { model: "claude-3-5-sonnet", provider: "anthropic", temperature: 0.2, maxIterations: 50, memoryEnabled: true, timeoutSeconds: 600 },
  },
  {
    id: "writer",
    name: "Content Writer",
    description: "Creative writing agent specialized in articles, documentation, marketing copy, and long-form content creation.",
    role: "writer",
    category: "writing",
    recommendedToolsets: ["file", "web", "search", "terminal"],
    tags: ["writing", "content", "creative"],
    defaultConfig: { model: "gpt-4o", provider: "openai", temperature: 0.8, maxIterations: 20, memoryEnabled: true, timeoutSeconds: 300 },
  },
  {
    id: "data-analyst",
    name: "Data Analyst",
    description: "Data analysis expert for querying databases, generating reports, creating visualizations, and extracting insights.",
    role: "analyst",
    category: "analysis",
    recommendedToolsets: ["terminal", "code_execution", "file", "search"],
    tags: ["data", "analytics", "visualization"],
    defaultConfig: { model: "gpt-4o", provider: "openai", temperature: 0.3, maxIterations: 40, memoryEnabled: true, timeoutSeconds: 600 },
  },
  {
    id: "devops-engineer",
    name: "DevOps Engineer",
    description: "Infrastructure and operations agent for managing deployments, monitoring, CI/CD pipelines, and cloud resources.",
    role: "coordinator",
    category: "devops",
    recommendedToolsets: ["terminal", "file", "search", "delegation"],
    tags: ["devops", "infrastructure", "automation"],
    defaultConfig: { model: "claude-3-5-sonnet", provider: "anthropic", temperature: 0.2, maxIterations: 40, memoryEnabled: true, timeoutSeconds: 600 },
  },
  {
    id: "security-analyst",
    name: "Security Analyst",
    description: "Security-focused agent for vulnerability assessment, threat analysis, audit review, and security best practices.",
    role: "analyst",
    category: "security",
    recommendedToolsets: ["terminal", "search", "file"],
    tags: ["security", "audit", "compliance"],
    defaultConfig: { model: "claude-3-opus", provider: "anthropic", temperature: 0.2, maxIterations: 40, memoryEnabled: true, timeoutSeconds: 600 },
  },
  {
    id: "automation-engineer",
    name: "Automation Engineer",
    description: "Automation specialist for building workflows, scheduling tasks, integrating APIs, and orchestrating multi-step processes.",
    role: "coordinator",
    category: "automation",
    recommendedToolsets: ["terminal", "file", "web", "delegation", "cronjob"],
    tags: ["automation", "workflows", "scheduling"],
    defaultConfig: { model: "gpt-4o", provider: "openai", temperature: 0.4, maxIterations: 40, memoryEnabled: true, timeoutSeconds: 600 },
  },
  {
    id: "communicator",
    name: "Communications Agent",
    description: "Multi-platform communications agent for drafting, sending, and managing messages across channels and platforms.",
    role: "assistant",
    category: "communication",
    recommendedToolsets: ["messaging", "file", "search"],
    tags: ["communication", "messaging", "social"],
    defaultConfig: { model: "gpt-4o", provider: "openai", temperature: 0.7, maxIterations: 20, memoryEnabled: true, timeoutSeconds: 300 },
  },
  {
    id: "browser-agent",
    name: "Web Browser Agent",
    description: "Web automation agent capable of browsing, filling forms, scraping data, and interacting with web applications.",
    role: "assistant",
    category: "productivity",
    recommendedToolsets: ["browser", "web", "search", "file"],
    tags: ["browser", "web", "automation"],
    defaultConfig: { model: "claude-3-5-sonnet", provider: "anthropic", temperature: 0.3, maxIterations: 50, memoryEnabled: true, timeoutSeconds: 600 },
  },
  {
    id: "project-manager",
    name: "Project Manager",
    description: "Project coordination agent for task tracking, milestone management, status reporting, and team coordination.",
    role: "coordinator",
    category: "productivity",
    recommendedToolsets: ["terminal", "file", "delegation", "kanban"],
    tags: ["project-management", "coordination", "agile"],
    defaultConfig: { model: "gpt-4o", provider: "openai", temperature: 0.5, maxIterations: 30, memoryEnabled: true, timeoutSeconds: 300 },
  },
  {
    id: "creative-writer",
    name: "Creative Writer",
    description: "Imaginative writing agent for stories, poetry, scripts, and creative content with strong narrative capabilities.",
    role: "writer",
    category: "creative",
    recommendedToolsets: ["file", "search"],
    tags: ["creative", "writing", "storytelling"],
    defaultConfig: { model: "claude-3-5-sonnet", provider: "anthropic", temperature: 0.9, maxIterations: 20, memoryEnabled: true, timeoutSeconds: 300 },
  },
  {
    id: "ml-engineer",
    name: "ML/AI Engineer",
    description: "Machine learning agent for model training, data preprocessing, experiment tracking, and ML pipeline management.",
    role: "coder",
    category: "development",
    recommendedToolsets: ["terminal", "code_execution", "file", "search"],
    tags: ["machine-learning", "ai", "data-science"],
    defaultConfig: { model: "claude-3-5-sonnet", provider: "anthropic", temperature: 0.3, maxIterations: 60, memoryEnabled: true, timeoutSeconds: 900 },
  },
  {
    id: "support-agent",
    name: "Customer Support Agent",
    description: "Customer-facing support agent for handling inquiries, troubleshooting issues, and providing guided assistance.",
    role: "assistant",
    category: "communication",
    recommendedToolsets: ["search", "file", "web"],
    tags: ["support", "customer-service", "helpdesk"],
    defaultConfig: { model: "gpt-4o", provider: "openai", temperature: 0.5, maxIterations: 20, memoryEnabled: true, timeoutSeconds: 300 },
  },
];

interface AgentHubLocalState {
  favorites: Record<string, FavoriteAgent>;
  knowledge: Record<string, KnowledgeAttachment[]>;
  securitySettings: Record<string, AgentSecuritySettings>;
  analytics: Record<string, AgentAnalyticsData>;
  exportQueue: ExportImportPayload[];
  selectedKnowledgeAgentId: string | null;

  toggleFavorite: (agentId: string, label?: string) => void;
  isFavorite: (agentId: string) => boolean;
  getFavorites: () => FavoriteAgent[];
  removeFavorite: (agentId: string) => void;

  addKnowledgeAttachment: (attachment: KnowledgeAttachment) => void;
  removeKnowledgeAttachment: (agentId: string, attachmentId: string) => void;
  getKnowledgeForAgent: (agentId: string) => KnowledgeAttachment[];
  updateKnowledgeStatus: (agentId: string, attachmentId: string, status: KnowledgeAttachment["status"], error?: string) => void;

  getSecuritySettings: (agentId: string) => AgentSecuritySettings;
  updateSecuritySettings: (agentId: string, settings: Partial<AgentSecuritySettings>) => void;

  getAnalytics: (agentId: string) => AgentAnalyticsData;
  updateAnalytics: (agentId: string, data: Partial<AgentAnalyticsData>) => void;

  addExportToQueue: (payload: ExportImportPayload) => void;
  clearExportQueue: () => void;
  setSelectedKnowledgeAgentId: (id: string | null) => void;
}

function defaultSecuritySettings(agentId: string): AgentSecuritySettings {
  return {
    agentId,
    sandboxEnabled: false,
    sandboxMode: "standard",
    networkAccess: true,
    filesystemAccess: true,
    allowedDomains: [],
    blockedDomains: [],
    maxMemoryMb: 512,
    maxCpuPercent: 50,
    executionTimeout: 300,
    requireApprovalFor: [],
    auditLogging: false,
    secretsScope: "profile",
  };
}

function defaultAnalytics(agentId: string): AgentAnalyticsData {
  return {
    agentId,
    dailyStats: [],
    topTools: [],
    topModels: [],
    avgResponseTime: 0,
    totalSessions: 0,
    totalCost: 0,
  };
}

export const useAgentHubLocal = create<AgentHubLocalState>()(
  persist(
    (set, get) => ({
      favorites: {},
      knowledge: {},
      securitySettings: {},
      analytics: {},
      exportQueue: [],
      selectedKnowledgeAgentId: null,

      toggleFavorite: (agentId: string, label?: string) => {
        set((state) => {
          const exists = !!state.favorites[agentId];
          if (exists) {
            const { [agentId]: _, ...rest } = state.favorites;
            return { favorites: rest };
          }
          return {
            favorites: {
              ...state.favorites,
              [agentId]: { agentId, addedAt: new Date().toISOString(), label },
            },
          };
        });
      },

      isFavorite: (agentId: string) => !!get().favorites[agentId],

      getFavorites: () => Object.values(get().favorites),

      removeFavorite: (agentId: string) => {
        set((state) => {
          const { [agentId]: _, ...rest } = state.favorites;
          return { favorites: rest };
        });
      },

      addKnowledgeAttachment: (attachment: KnowledgeAttachment) => {
        set((state) => {
          const existing = state.knowledge[attachment.agentId] || [];
          return {
            knowledge: {
              ...state.knowledge,
              [attachment.agentId]: [...existing, attachment],
            },
          };
        });
      },

      removeKnowledgeAttachment: (agentId: string, attachmentId: string) => {
        set((state) => {
          const existing = state.knowledge[agentId] || [];
          return {
            knowledge: {
              ...state.knowledge,
              [agentId]: existing.filter((a) => a.id !== attachmentId),
            },
          };
        });
      },

      getKnowledgeForAgent: (agentId: string) => get().knowledge[agentId] || [],

      updateKnowledgeStatus: (agentId: string, attachmentId: string, status: KnowledgeAttachment["status"], error?: string) => {
        set((state) => {
          const existing = state.knowledge[agentId] || [];
          return {
            knowledge: {
              ...state.knowledge,
              [agentId]: existing.map((a) =>
                a.id === attachmentId ? { ...a, status, error } : a
              ),
            },
          };
        });
      },

      getSecuritySettings: (agentId: string) => {
        return get().securitySettings[agentId] || defaultSecuritySettings(agentId);
      },

      updateSecuritySettings: (agentId: string, settings: Partial<AgentSecuritySettings>) => {
        set((state) => ({
          securitySettings: {
            ...state.securitySettings,
            [agentId]: { ...defaultSecuritySettings(agentId), ...state.securitySettings[agentId], ...settings },
          },
        }));
      },

      getAnalytics: (agentId: string) => {
        return get().analytics[agentId] || defaultAnalytics(agentId);
      },

      updateAnalytics: (agentId: string, data: Partial<AgentAnalyticsData>) => {
        set((state) => ({
          analytics: {
            ...state.analytics,
            [agentId]: { ...defaultAnalytics(agentId), ...state.analytics[agentId], ...data },
          },
        }));
      },

      addExportToQueue: (payload: ExportImportPayload) => {
        set((state) => ({ exportQueue: [...state.exportQueue, payload] }));
      },

      clearExportQueue: () => set({ exportQueue: [] }),

      setSelectedKnowledgeAgentId: (id: string | null) => set({ selectedKnowledgeAgentId: id }),
    }),
    { name: "aetheros-agent-hub-local" },
  ),
);
