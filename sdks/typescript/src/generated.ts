// GENERATED from aetheros_platform/schemas.py — do not hand-edit.
// Schema version: 1.0.0

export type AgentState = "REGISTERED" | "CREATED" | "READY" | "RUNNING" | "WAITING" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED" | "QUARANTINED" | "TERMINATED";
export type TaskState = "PENDING" | "RUNNING" | "WAITING_APPROVAL" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Stability = "PUBLIC" | "INTERNAL" | "EXPERIMENTAL" | "DEPRECATED" | "PRIVATE" | "UNSTABLE";


export interface Agent {
  name: string;
  version: string;
  description?: string;
  capabilities?: string[];
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
  tools?: string[];
  skills?: string[];
  models?: Record<string, unknown>;
  memoryPolicy?: Record<string, unknown>;
  artifactPolicy?: Record<string, unknown>;
  networkPolicy?: Record<string, unknown>;
  filesystemPolicy?: Record<string, unknown>;
  dataPolicy?: Record<string, unknown>;
  approvalPolicy?: Record<string, unknown>;
  resourceLimits?: Record<string, unknown>;
  tenant?: Record<string, unknown>;
}

export interface AgentTask {
  agent: string;
  input: Record<string, unknown>;
  idempotencyKey?: string;
  model?: Record<string, unknown>;
  tenant?: Record<string, unknown>;
}

export interface AgentResult {
  taskId: string;
  state: "PENDING" | "RUNNING" | "WAITING_APPROVAL" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED";
  output?: Record<string, unknown>;
  artifacts?: string[];
  usage?: Record<string, unknown>;
}

export interface Tool {
  name: string;
  version: string;
  description?: string;
  inputSchema: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  capabilities?: string[];
  riskLevel?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  sideEffects?: string[];
  idempotent?: boolean;
  safety?: {
  readsData?: boolean;
  writesData?: boolean;
  deletesData?: boolean;
  sendsMessages?: boolean;
  executesCode?: boolean;
  accessesNetwork?: boolean;
  accessesCredentials?: boolean;
  modifiesExternal?: boolean;
  financialLegalPhysical?: boolean;
  reversible?: boolean;
  idempotent?: boolean;
};
  timeoutSeconds?: number;
}

export interface Skill {
  name: string;
  version: string;
  description?: string;
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
  capabilities?: string[];
  dependencies?: Record<string, unknown>;
  tools?: string[];
  policies?: Record<string, unknown>;
}

export interface AgentCard {
  name: string;
  version: string;
  protocolVersion: string;
  description?: string;
  capabilities: string[];
  endpoint?: string;
  authentication?: Record<string, unknown>;
  trust?: "untrusted" | "known" | "trusted";
}

export interface MCPServer {
  name: string;
  version: string;
  transport: "stdio" | "sse" | "streamable-http";
  command?: string;
  tools?: string[];
}

export interface Automation {
  name: string;
  trigger: Record<string, unknown>;
  actions?: unknown[];
  enabled?: boolean;
}

export interface MemoryRecord {
  content: string;
  scope?: string;
  sensitivity?: string;
}

export interface Artifact {
  artifactId: string;
  hash: string;
  type?: string;
  size?: number;
  creator?: string;
  taskId?: string;
  provenance?: Record<string, unknown>;
  securityClassification?: string;
  parentArtifacts?: string[];
}

export interface APIKey {
  name: string;
  scopes?: string[];
  expiresInDays?: number;
}

export interface Webhook {
  url: string;
  events: string[];
}

export interface Package {
  name: string;
  version: string;
  kind: "agent" | "skill" | "tool" | "extension" | "mcp";
  aetherosVersion?: string;
}

export interface AgentEvent {
  type: "AgentStarted" | "AgentCompleted" | "TaskCreated" | "TaskUpdated" | "ToolInvoked" | "ToolCompleted" | "ApprovalRequested" | "ApprovalResolved" | "MemoryWritten" | "ResearchEvidenceAdded" | "ArtifactCreated" | "AutomationTriggered" | "PolicyDenied" | "SecurityAlert" | "ModelInvocation" | "MCPRequest" | "A2ARequest";
  eventId?: string;
  timestamp?: number;
  source?: string;
  task?: string;
  agent?: string;
  correlationId?: string;
  causationId?: string;
  schemaVersion?: string;
  payload?: Record<string, unknown>;
  securityClassification?: "public" | "internal" | "confidential";
}

export interface Approval {
  requestId: string;
  intent: Record<string, unknown>;
  status?: "pending" | "approved" | "denied" | "cancelled" | "expired";
  requestedBy?: string;
  resolvedBy?: string;
  resolvedAt?: number;
}

export interface Capability {
  name: string;
  risk?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  description?: string;
}

export interface CredentialReference {
  reference: string;
  scope?: string;
}

export interface Device {
  deviceId: string;
  kind?: string;
  owner?: string;
}

export interface Error {
  category: string;
  message: string;
  code?: string;
  retryable?: boolean;
  requestId?: string;
  remediation?: string;
}

export interface Extension {
  name: string;
  version: string;
  entrypoint: string;
  permissions?: string[];
  dependencies?: Record<string, unknown>;
}

export interface Intent {
  capability: string;
  actor?: string;
  args?: Record<string, unknown>;
  grants?: string[];
  idempotencyKey?: string;
  prompt_context?: string;
  side_effects_irreversible?: boolean;
}

export interface MCPTool {
  name: string;
  description?: string;
  inputSchema: Record<string, unknown>;
  server?: string;
  trust?: "untrusted" | "known" | "trusted";
}

export interface Model {
  name: string;
  provider?: string;
  contextLength?: number;
  supportsStreaming?: boolean;
  supportsTools?: boolean;
  supportsVision?: boolean;
  supportsStructuredOutput?: boolean;
}

export interface Policy {
  effect: "allow" | "deny" | "require_approval" | "require_sandbox" | "require_credential";
  capabilities?: string[];
  principals?: string[];
  conditions?: Record<string, unknown>;
}

export interface Project {
  name: string;
  workspace?: string;
  description?: string;
}

export interface Quota {
  scope: string;
  resource?: string;
  limit: number;
  used?: number;
  window_s?: number;
}

export interface ResearchEvidence {
  url: string;
  title?: string;
  excerpt: string;
  retrievedAt?: number;
  sourceRank?: number;
}

export interface ResearchTask {
  query: string;
  depth?: "quick" | "standard" | "deep";
  maxSources?: number;
}

export interface Session {
  sessionId: string;
  agent?: string;
  state?: string;
  createdAt?: number;
}

export interface Trace {
  traceId: string;
  spans: unknown[];
  taskId?: string;
  agent?: string;
}

export interface Usage {
  actor: string;
  workspace?: string;
  model?: string;
  tokens?: number;
  toolCalls?: number;
  runtime_s?: number;
  timestamp: number;
}

export interface User {
  userId: string;
  displayName?: string;
  organization?: string;
  workspace?: string;
}

export interface Workspace {
  organization?: string;
  workspace: string;
}


export interface AetherError {
  code: string; message: string; category: string; retryable: boolean;
  severity: string; requestId: string; traceId: string; taskId: string;
  capability: string; policyDecision: string; remediation: string;
  metadata: Record<string, unknown>;
}
export interface Page<T> { items: T[]; nextCursor: string; limit: number }

