import { atom } from 'nanostores'

export type NodeType =
  | 'trigger'
  | 'action'
  | 'condition'
  | 'variable'
  | 'timer'
  | 'loop'
  | 'switch'
  | 'merge'
  | 'split'

export type TriggerKind =
  | 'application-started'
  | 'agent-finished'
  | 'timer'
  | 'cron'
  | 'folder-changed'
  | 'file-created'
  | 'git-push'
  | 'webhook'
  | 'http-request'
  | 'email-received'
  | 'telegram-message'
  | 'discord-message'
  | 'slack-message'
  | 'whatsapp-message'
  | 'github-issue'
  | 'github-pr'
  | 'rss-feed'
  | 'clipboard-changed'
  | 'voice-command'
  | 'screen-capture'
  | 'manual'

export type ActionKind =
  | 'run-agent'
  | 'run-prompt'
  | 'call-model'
  | 'send-email'
  | 'send-telegram'
  | 'send-discord'
  | 'send-slack'
  | 'send-whatsapp'
  | 'create-file'
  | 'delete-file'
  | 'move-file'
  | 'run-terminal'
  | 'run-python'
  | 'run-docker'
  | 'git-commit'
  | 'git-push'
  | 'ocr'
  | 'vision-analysis'
  | 'speech-to-text'
  | 'text-to-speech'
  | 'web-search'
  | 'open-browser'
  | 'close-browser'
  | 'open-url'
  | 'screenshot'
  | 'database-query'
  | 'http-request'
  | 'webhook'
  | 'delay'
  | 'loop'
  | 'merge'
  | 'split'
  | 'switch'
  | 'if-else'
  | 'for-each'
  | 'ai-decision'
  | 'memory-read'
  | 'memory-write'
  | 'knowledge-search'
  | 'plugin-action'
  | 'mcp-tool'

export type ConditionKind =
  | 'if'
  | 'else'
  | 'switch'
  | 'contains'
  | 'regex'
  | 'equals'
  | 'greater'
  | 'less'
  | 'date'
  | 'time'
  | 'schedule'
  | 'model-output'
  | 'llm-decision'

export type VariableScope = 'workflow' | 'global' | 'session' | 'environment' | 'secret' | 'output' | 'input'

export type ScheduleType = 'once' | 'daily' | 'hourly' | 'weekly' | 'monthly' | 'cron' | 'manual'

export type NodeExecutionStatus = 'idle' | 'running' | 'completed' | 'failed' | 'skipped' | 'waiting'

export interface Position {
  x: number
  y: number
}

export interface Size {
  width: number
  height: number
}

export interface Port {
  id: string
  nodeId: string
  type: 'input' | 'output'
  label: string
  dataType: string
}

export interface Connection {
  id: string
  sourceNodeId: string
  sourcePortId: string
  targetNodeId: string
  targetPortId: string
}

export interface CanvasNodeConfig {
  label: string
  description: string
  [key: string]: unknown
}

export interface WorkflowNode {
  id: string
  type: NodeType
  kind: TriggerKind | ActionKind | ConditionKind
  label: string
  description: string
  position: Position
  size: Size
  config: CanvasNodeConfig
  ports: Port[]
  status: NodeExecutionStatus
  error?: string
  metadata?: Record<string, unknown>
}

export interface WorkflowVariable {
  id: string
  name: string
  scope: VariableScope
  type: 'string' | 'number' | 'boolean' | 'object' | 'array' | 'any'
  value: unknown
  description: string
  encrypted: boolean
}

export interface SecretEntry {
  id: string
  name: string
  description: string
  createdAt: string
  updatedAt: string
  maskedValue: string
}

export interface TriggerConfig {
  kind: TriggerKind
  label: string
  description: string
  icon: string
  configFields: ConfigField[]
}

export interface ActionConfig {
  kind: ActionKind
  label: string
  description: string
  icon: string
  category: 'communication' | 'file' | 'code' | 'git' | 'ai' | 'web' | 'data' | 'flow' | 'integration'
  configFields: ConfigField[]
}

export interface ConditionConfig {
  kind: ConditionKind
  label: string
  description: string
  icon: string
  configFields: ConfigField[]
}

export interface ConfigField {
  name: string
  label: string
  type: 'text' | 'number' | 'boolean' | 'select' | 'multiselect' | 'textarea' | 'code' | 'json' | 'secret' | 'variable' | 'expression'
  required: boolean
  defaultValue?: unknown
  options?: { label: string; value: string }[]
  placeholder?: string
  description?: string
}

export interface WorkflowSchedule {
  type: ScheduleType
  cronExpression?: string
  timezone?: string
  startDate?: string
  endDate?: string
  interval?: number
  intervalUnit?: 'minutes' | 'hours' | 'days'
  dayOfWeek?: number[]
  dayOfMonth?: number[]
}

export interface WorkflowExecution {
  id: string
  workflowId: string
  workflowName: string
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  startedAt: string
  completedAt: string | null
  duration: number | null
  trigger: TriggerKind
  nodesExecuted: number
  nodesTotal: number
  cost: number | null
  modelUsed: string | null
  error: string | null
  retryCount: number
  logs: ExecutionLogEntry[]
  nodeStates: Record<string, NodeExecutionStatus>
}

export interface ExecutionLogEntry {
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  nodeId: string
  message: string
  data?: unknown
}

export interface WorkflowTemplate {
  id: string
  name: string
  description: string
  category: string
  icon: string
  tags: string[]
  nodes: WorkflowNode[]
  connections: Connection[]
  variables: WorkflowVariable[]
  schedule?: WorkflowSchedule
  retryPolicy?: RetryPolicy
}

export interface RetryPolicy {
  maxRetries: number
  retryDelay: number
  retryDelayUnit: 'seconds' | 'minutes' | 'hours'
  backoffMultiplier: number
  retryOnError: boolean
  maxDuration: number
}

export interface WorkflowDocument {
  id: string
  name: string
  description: string
  tags: string[]
  owner: string
  agentAssignment: string
  nodes: WorkflowNode[]
  connections: Connection[]
  variables: WorkflowVariable[]
  secrets: string[]
  schedule: WorkflowSchedule | null
  retryPolicy: RetryPolicy
  logging: boolean
  createdAt: string
  updatedAt: string
  version: number
  enabled: boolean
}

export interface ClipboardState {
  nodes: WorkflowNode[]
  connections: Connection[]
}

export interface AutomationState {
  workflows: WorkflowDocument[]
  executions: WorkflowExecution[]
  secrets: SecretEntry[]
  activeWorkflowId: string | null
  canvasScale: number
  canvasPan: Position
  selectedNodeIds: string[]
  selectedConnectionIds: string[]
  clipboard: ClipboardState | null
  history: AutomationHistoryEntry[]
  historyIndex: number
  showMiniMap: boolean
  snapToGrid: boolean
  gridSize: number
  nodeSearchQuery: string
  editingNodeId: string | null
  isDragging: boolean
  isPanning: boolean
  showNodePalette: boolean
  showVariablesPanel: boolean
  showSecretsPanel: boolean
  showScheduler: boolean
  showHistory: boolean
  showTemplates: boolean
  activeTab: 'editor' | 'scheduler' | 'history' | 'templates' | 'secrets' | 'marketplace'
}

export interface AutomationHistoryEntry {
  nodes: WorkflowNode[]
  connections: Connection[]
}

const TRIGGER_CONFIGS: TriggerConfig[] = [
  { kind: 'application-started', label: 'Application Started', description: 'Triggers when the application launches', icon: 'rocket', configFields: [] },
  { kind: 'agent-finished', label: 'Agent Finished', description: 'Triggers when an agent completes its task', icon: 'check-circle', configFields: [{ name: 'agentId', label: 'Agent', type: 'select', required: true, description: 'Select the agent to watch' }] },
  { kind: 'timer', label: 'Timer', description: 'Triggers after a specified duration', icon: 'timer', configFields: [{ name: 'duration', label: 'Duration', type: 'number', required: true, defaultValue: 60, placeholder: 'Duration in seconds' }, { name: 'unit', label: 'Unit', type: 'select', required: true, options: [{ label: 'Seconds', value: 'seconds' }, { label: 'Minutes', value: 'minutes' }, { label: 'Hours', value: 'hours' }], defaultValue: 'seconds' }] },
  { kind: 'cron', label: 'Cron', description: 'Triggers on a cron schedule', icon: 'calendar', configFields: [{ name: 'expression', label: 'Cron Expression', type: 'text', required: true, placeholder: '*/5 * * * *' }, { name: 'timezone', label: 'Timezone', type: 'text', required: false, placeholder: 'UTC' }] },
  { kind: 'folder-changed', label: 'Folder Changed', description: 'Triggers when a folder is modified', icon: 'folder', configFields: [{ name: 'path', label: 'Folder Path', type: 'text', required: true, placeholder: '/path/to/folder' }, { name: 'recursive', label: 'Recursive', type: 'boolean', required: false, defaultValue: false }] },
  { kind: 'file-created', label: 'File Created', description: 'Triggers when a file is created', icon: 'file-add', configFields: [{ name: 'pattern', label: 'File Pattern', type: 'text', required: false, placeholder: '*.txt' }, { name: 'path', label: 'Directory', type: 'text', required: true, placeholder: '/path/to/watch' }] },
  { kind: 'git-push', label: 'Git Push', description: 'Triggers on git push events', icon: 'git-commit', configFields: [{ name: 'repository', label: 'Repository', type: 'text', required: true, placeholder: 'owner/repo' }, { name: 'branch', label: 'Branch', type: 'text', required: false, placeholder: 'main' }] },
  { kind: 'webhook', label: 'Webhook', description: 'Triggers via incoming webhook', icon: 'webhook', configFields: [{ name: 'url', label: 'Webhook URL', type: 'text', required: true, placeholder: '/webhook/my-endpoint' }, { name: 'method', label: 'HTTP Method', type: 'select', required: false, options: [{ label: 'POST', value: 'POST' }, { label: 'GET', value: 'GET' }, { label: 'PUT', value: 'PUT' }], defaultValue: 'POST' }] },
  { kind: 'http-request', label: 'HTTP Request', description: 'Triggers on an HTTP request to a local endpoint', icon: 'globe', configFields: [{ name: 'port', label: 'Port', type: 'number', required: true, defaultValue: 8080 }, { name: 'path', label: 'Path', type: 'text', required: true, placeholder: '/webhook' }] },
  { kind: 'email-received', label: 'Email Received', description: 'Triggers when an email is received', icon: 'mail', configFields: [{ name: 'from', label: 'From Address', type: 'text', required: false, placeholder: 'sender@example.com' }, { name: 'subject', label: 'Subject Filter', type: 'text', required: false, placeholder: 'Subject contains...' }] },
  { kind: 'telegram-message', label: 'Telegram Message', description: 'Triggers on a Telegram message', icon: 'send', configFields: [{ name: 'chatId', label: 'Chat ID', type: 'text', required: false }, { name: 'command', label: 'Command Filter', type: 'text', required: false, placeholder: '/start' }] },
  { kind: 'discord-message', label: 'Discord Message', description: 'Triggers on a Discord message', icon: 'message-circle', configFields: [{ name: 'channelId', label: 'Channel ID', type: 'text', required: false }, { name: 'contains', label: 'Contains Text', type: 'text', required: false }] },
  { kind: 'slack-message', label: 'Slack Message', description: 'Triggers on a Slack message', icon: 'message-square', configFields: [{ name: 'channel', label: 'Channel', type: 'text', required: false, placeholder: '#general' }] },
  { kind: 'whatsapp-message', label: 'WhatsApp Message', description: 'Triggers on a WhatsApp message', icon: 'message-circle', configFields: [{ name: 'number', label: 'Phone Number', type: 'text', required: false }] },
  { kind: 'github-issue', label: 'GitHub Issue', description: 'Triggers on a GitHub issue event', icon: 'issue-opened', configFields: [{ name: 'repository', label: 'Repository', type: 'text', required: true, placeholder: 'owner/repo' }, { name: 'action', label: 'Action', type: 'select', required: false, options: [{ label: 'Opened', value: 'opened' }, { label: 'Closed', value: 'closed' }, { label: 'Reopened', value: 'reopened' }] }] },
  { kind: 'github-pr', label: 'GitHub PR', description: 'Triggers on a GitHub pull request event', icon: 'git-pull-request', configFields: [{ name: 'repository', label: 'Repository', type: 'text', required: true, placeholder: 'owner/repo' }, { name: 'action', label: 'Action', type: 'select', required: false, options: [{ label: 'Opened', value: 'opened' }, { label: 'Closed', value: 'closed' }, { label: 'Merged', value: 'merged' }, { label: 'Review Requested', value: 'review_requested' }] }] },
  { kind: 'rss-feed', label: 'RSS Feed', description: 'Triggers on new RSS feed items', icon: 'rss', configFields: [{ name: 'url', label: 'Feed URL', type: 'text', required: true, placeholder: 'https://example.com/feed.xml' }, { name: 'interval', label: 'Check Interval (min)', type: 'number', required: false, defaultValue: 15 }] },
  { kind: 'clipboard-changed', label: 'Clipboard Changed', description: 'Triggers when clipboard content changes', icon: 'clipboard', configFields: [{ name: 'contains', label: 'Contains Text', type: 'text', required: false }] },
  { kind: 'voice-command', label: 'Voice Command', description: 'Triggers on a voice command', icon: 'mic', configFields: [{ name: 'command', label: 'Command Phrase', type: 'text', required: true, placeholder: 'hey aetheros...' }] },
  { kind: 'screen-capture', label: 'Screen Capture', description: 'Triggers on screen content change', icon: 'screen', configFields: [{ name: 'region', label: 'Screen Region', type: 'text', required: false }, { name: 'interval', label: 'Check Interval (s)', type: 'number', required: false, defaultValue: 30 }] },
  { kind: 'manual', label: 'Manual Button', description: 'Triggered manually by clicking a button', icon: 'play', configFields: [{ name: 'buttonLabel', label: 'Button Label', type: 'text', required: false, defaultValue: 'Run Workflow' }] },
]

const ACTION_CONFIGS: ActionConfig[] = [
  { kind: 'run-agent', label: 'Run Agent', description: 'Execute an AI agent', icon: 'robot', category: 'ai', configFields: [{ name: 'agentId', label: 'Agent', type: 'select', required: true }, { name: 'task', label: 'Task Description', type: 'textarea', required: true }, { name: 'waitForCompletion', label: 'Wait For Completion', type: 'boolean', required: false, defaultValue: true }] },
  { kind: 'run-prompt', label: 'Run Prompt', description: 'Send a prompt to the AI model', icon: 'message', category: 'ai', configFields: [{ name: 'prompt', label: 'Prompt', type: 'textarea', required: true }, { name: 'model', label: 'Model Override', type: 'text', required: false }, { name: 'temperature', label: 'Temperature', type: 'number', required: false, defaultValue: 0.7 }] },
  { kind: 'call-model', label: 'Call Model', description: 'Call an AI model directly', icon: 'brain', category: 'ai', configFields: [{ name: 'provider', label: 'Provider', type: 'select', required: true }, { name: 'model', label: 'Model', type: 'select', required: true }, { name: 'systemPrompt', label: 'System Prompt', type: 'textarea', required: false }, { name: 'maxTokens', label: 'Max Tokens', type: 'number', required: false, defaultValue: 4096 }] },
  { kind: 'send-email', label: 'Send Email', description: 'Send an email message', icon: 'mail', category: 'communication', configFields: [{ name: 'to', label: 'To', type: 'text', required: true, placeholder: 'recipient@example.com' }, { name: 'subject', label: 'Subject', type: 'text', required: true }, { name: 'body', label: 'Body', type: 'textarea', required: true }] },
  { kind: 'send-telegram', label: 'Send Telegram', description: 'Send a Telegram message', icon: 'send', category: 'communication', configFields: [{ name: 'chatId', label: 'Chat ID', type: 'text', required: true }, { name: 'text', label: 'Message Text', type: 'textarea', required: true }] },
  { kind: 'send-discord', label: 'Send Discord', description: 'Send a Discord message', icon: 'message-circle', category: 'communication', configFields: [{ name: 'channelId', label: 'Channel ID', type: 'text', required: true }, { name: 'content', label: 'Message Content', type: 'textarea', required: true }] },
  { kind: 'send-slack', label: 'Send Slack', description: 'Send a Slack message', icon: 'message-square', category: 'communication', configFields: [{ name: 'channel', label: 'Channel', type: 'text', required: true, placeholder: '#general' }, { name: 'text', label: 'Message Text', type: 'textarea', required: true }] },
  { kind: 'send-whatsapp', label: 'Send WhatsApp', description: 'Send a WhatsApp message', icon: 'message-circle', category: 'communication', configFields: [{ name: 'to', label: 'Phone Number', type: 'text', required: true }, { name: 'text', label: 'Message', type: 'textarea', required: true }] },
  { kind: 'create-file', label: 'Create File', description: 'Create a new file', icon: 'file-add', category: 'file', configFields: [{ name: 'path', label: 'File Path', type: 'text', required: true }, { name: 'content', label: 'Content', type: 'code', required: true }, { name: 'overwrite', label: 'Overwrite If Exists', type: 'boolean', required: false, defaultValue: false }] },
  { kind: 'delete-file', label: 'Delete File', description: 'Delete a file', icon: 'trash', category: 'file', configFields: [{ name: 'path', label: 'File Path', type: 'text', required: true }, { name: 'permanent', label: 'Permanent Delete', type: 'boolean', required: false, defaultValue: false }] },
  { kind: 'move-file', label: 'Move File', description: 'Move or rename a file', icon: 'file-move', category: 'file', configFields: [{ name: 'source', label: 'Source Path', type: 'text', required: true }, { name: 'destination', label: 'Destination Path', type: 'text', required: true }] },
  { kind: 'run-terminal', label: 'Run Terminal', description: 'Execute a terminal command', icon: 'terminal', category: 'code', configFields: [{ name: 'command', label: 'Command', type: 'code', required: true }, { name: 'workdir', label: 'Working Directory', type: 'text', required: false }, { name: 'timeout', label: 'Timeout (s)', type: 'number', required: false, defaultValue: 30 }] },
  { kind: 'run-python', label: 'Run Python', description: 'Execute Python code', icon: 'code', category: 'code', configFields: [{ name: 'code', label: 'Python Code', type: 'code', required: true }, { name: 'requirements', label: 'Requirements', type: 'text', required: false }] },
  { kind: 'run-docker', label: 'Run Docker', description: 'Execute a Docker container', icon: 'container', category: 'code', configFields: [{ name: 'image', label: 'Image', type: 'text', required: true, placeholder: 'node:18' }, { name: 'command', label: 'Command', type: 'text', required: false }, { name: 'volumes', label: 'Volumes', type: 'text', required: false }] },
  { kind: 'git-commit', label: 'Git Commit', description: 'Create a git commit', icon: 'git-commit', category: 'git', configFields: [{ name: 'message', label: 'Commit Message', type: 'text', required: true }, { name: 'path', label: 'Repository Path', type: 'text', required: false }, { name: 'addAll', label: 'Add All Changes', type: 'boolean', required: false, defaultValue: true }] },
  { kind: 'git-push', label: 'Git Push', description: 'Push to git remote', icon: 'git-push', category: 'git', configFields: [{ name: 'remote', label: 'Remote Name', type: 'text', required: false, defaultValue: 'origin' }, { name: 'branch', label: 'Branch', type: 'text', required: false }] },
  { kind: 'ocr', label: 'OCR', description: 'Extract text from images', icon: 'scan', category: 'ai', configFields: [{ name: 'imagePath', label: 'Image Path', type: 'text', required: true }, { name: 'language', label: 'Language', type: 'text', required: false, defaultValue: 'eng' }] },
  { kind: 'vision-analysis', label: 'Vision Analysis', description: 'Analyze images with AI vision', icon: 'eye', category: 'ai', configFields: [{ name: 'imagePath', label: 'Image Path', type: 'text', required: true }, { name: 'prompt', label: 'Analysis Prompt', type: 'textarea', required: false, defaultValue: 'Describe this image in detail.' }] },
  { kind: 'speech-to-text', label: 'Speech To Text', description: 'Transcribe audio to text', icon: 'mic', category: 'ai', configFields: [{ name: 'audioPath', label: 'Audio File Path', type: 'text', required: true }, { name: 'language', label: 'Language', type: 'text', required: false }] },
  { kind: 'text-to-speech', label: 'Text To Speech', description: 'Convert text to speech', icon: 'volume-up', category: 'ai', configFields: [{ name: 'text', label: 'Text', type: 'textarea', required: true }, { name: 'voice', label: 'Voice', type: 'select', required: false }, { name: 'outputPath', label: 'Output Path', type: 'text', required: true }] },
  { kind: 'web-search', label: 'Web Search', description: 'Search the web', icon: 'search', category: 'web', configFields: [{ name: 'query', label: 'Search Query', type: 'textarea', required: true }, { name: 'numResults', label: 'Number of Results', type: 'number', required: false, defaultValue: 10 }] },
  { kind: 'open-browser', label: 'Open Browser', description: 'Open a browser window', icon: 'globe', category: 'web', configFields: [{ name: 'url', label: 'URL', type: 'text', required: true }, { name: 'headless', label: 'Headless Mode', type: 'boolean', required: false, defaultValue: false }] },
  { kind: 'close-browser', label: 'Close Browser', description: 'Close a browser window', icon: 'x-circle', category: 'web', configFields: [] },
  { kind: 'open-url', label: 'Open URL', description: 'Open a URL in the default browser', icon: 'link', category: 'web', configFields: [{ name: 'url', label: 'URL', type: 'text', required: true }] },
  { kind: 'screenshot', label: 'Screenshot', description: 'Take a screenshot', icon: 'camera', category: 'web', configFields: [{ name: 'outputPath', label: 'Output Path', type: 'text', required: true }, { name: 'fullPage', label: 'Full Page', type: 'boolean', required: false, defaultValue: false }] },
  { kind: 'database-query', label: 'Database Query', description: 'Execute a database query', icon: 'database', category: 'data', configFields: [{ name: 'connection', label: 'Connection String', type: 'secret', required: true }, { name: 'query', label: 'SQL Query', type: 'code', required: true }] },
  { kind: 'http-request', label: 'HTTP Request', description: 'Make an HTTP request', icon: 'globe', category: 'web', configFields: [{ name: 'url', label: 'URL', type: 'text', required: true }, { name: 'method', label: 'Method', type: 'select', required: true, options: [{ label: 'GET', value: 'GET' }, { label: 'POST', value: 'POST' }, { label: 'PUT', value: 'PUT' }, { label: 'DELETE', value: 'DELETE' }, { label: 'PATCH', value: 'PATCH' }] }, { name: 'headers', label: 'Headers', type: 'json', required: false }, { name: 'body', label: 'Body', type: 'textarea', required: false }] },
  { kind: 'webhook', label: 'Webhook', description: 'Send a webhook', icon: 'webhook', category: 'integration', configFields: [{ name: 'url', label: 'Webhook URL', type: 'text', required: true }, { name: 'payload', label: 'Payload', type: 'json', required: true }] },
  { kind: 'delay', label: 'Delay', description: 'Wait for a duration', icon: 'clock', category: 'flow', configFields: [{ name: 'duration', label: 'Duration', type: 'number', required: true, defaultValue: 5 }, { name: 'unit', label: 'Unit', type: 'select', required: false, options: [{ label: 'Seconds', value: 'seconds' }, { label: 'Minutes', value: 'minutes' }, { label: 'Hours', value: 'hours' }], defaultValue: 'seconds' }] },
  { kind: 'loop', label: 'Loop', description: 'Repeat actions multiple times', icon: 'repeat', category: 'flow', configFields: [{ name: 'count', label: 'Iterations', type: 'number', required: true, defaultValue: 3 }, { name: 'variable', label: 'Loop Variable Name', type: 'text', required: false, defaultValue: 'item' }] },
  { kind: 'merge', label: 'Merge', description: 'Merge multiple execution paths', icon: 'merge', category: 'flow', configFields: [{ name: 'strategy', label: 'Merge Strategy', type: 'select', required: true, options: [{ label: 'Wait All', value: 'wait-all' }, { label: 'First Complete', value: 'first-complete' }, { label: 'All Complete', value: 'all-complete' }] }] },
  { kind: 'split', label: 'Split', description: 'Split execution into parallel paths', icon: 'split', category: 'flow', configFields: [{ name: 'count', label: 'Number of Branches', type: 'number', required: true, defaultValue: 2 }, { name: 'mode', label: 'Split Mode', type: 'select', required: false, options: [{ label: 'Parallel', value: 'parallel' }, { label: 'Sequential', value: 'sequential' }] }] },
  { kind: 'switch', label: 'Switch', description: 'Conditional routing based on value', icon: 'git-branch', category: 'flow', configFields: [{ name: 'expression', label: 'Switch Expression', type: 'expression', required: true }, { name: 'cases', label: 'Cases', type: 'json', required: true, defaultValue: { default: [] } }] },
  { kind: 'if-else', label: 'If Else', description: 'Conditional branching', icon: 'git-branch', category: 'flow', configFields: [{ name: 'condition', label: 'Condition', type: 'expression', required: true }, { name: 'elseBranch', label: 'Else Branch Enabled', type: 'boolean', required: false, defaultValue: true }] },
  { kind: 'for-each', label: 'For Each', description: 'Iterate over a list', icon: 'list', category: 'flow', configFields: [{ name: 'items', label: 'Items Source', type: 'expression', required: true }, { name: 'variable', label: 'Item Variable', type: 'text', required: true, defaultValue: 'item' }] },
  { kind: 'ai-decision', label: 'AI Decision', description: 'Let AI make a routing decision', icon: 'brain', category: 'ai', configFields: [{ name: 'context', label: 'Decision Context', type: 'textarea', required: true }, { name: 'options', label: 'Decision Options', type: 'json', required: true, defaultValue: ['option_a', 'option_b'] }] },
  { kind: 'memory-read', label: 'Memory Read', description: 'Read from agent memory', icon: 'database', category: 'ai', configFields: [{ name: 'key', label: 'Memory Key', type: 'text', required: true }, { name: 'namespace', label: 'Namespace', type: 'text', required: false, defaultValue: 'default' }] },
  { kind: 'memory-write', label: 'Memory Write', description: 'Write to agent memory', icon: 'database-plus', category: 'ai', configFields: [{ name: 'key', label: 'Memory Key', type: 'text', required: true }, { name: 'value', label: 'Value', type: 'expression', required: true }, { name: 'namespace', label: 'Namespace', type: 'text', required: false, defaultValue: 'default' }] },
  { kind: 'knowledge-search', label: 'Knowledge Search', description: 'Search the knowledge base', icon: 'book', category: 'ai', configFields: [{ name: 'query', label: 'Search Query', type: 'textarea', required: true }, { name: 'maxResults', label: 'Max Results', type: 'number', required: false, defaultValue: 5 }] },
  { kind: 'plugin-action', label: 'Plugin Action', description: 'Execute a plugin action', icon: 'puzzle', category: 'integration', configFields: [{ name: 'plugin', label: 'Plugin', type: 'select', required: true }, { name: 'action', label: 'Action', type: 'select', required: true }, { name: 'params', label: 'Parameters', type: 'json', required: false }] },
  { kind: 'mcp-tool', label: 'MCP Tool', description: 'Call an MCP tool', icon: 'server', category: 'integration', configFields: [{ name: 'server', label: 'MCP Server', type: 'select', required: true }, { name: 'tool', label: 'Tool Name', type: 'select', required: true }, { name: 'arguments', label: 'Arguments', type: 'json', required: false }] },
]

const CONDITION_CONFIGS: ConditionConfig[] = [
  { kind: 'if', label: 'If', description: 'If condition is true', icon: 'git-branch', configFields: [{ name: 'condition', label: 'Condition Expression', type: 'expression', required: true }] },
  { kind: 'else', label: 'Else', description: 'Else branch', icon: 'git-branch', configFields: [] },
  { kind: 'switch', label: 'Switch', description: 'Multi-way branch', icon: 'list', configFields: [{ name: 'value', label: 'Switch Value', type: 'expression', required: true }] },
  { kind: 'contains', label: 'Contains', description: 'String contains check', icon: 'search', configFields: [{ name: 'value', label: 'Value', type: 'expression', required: true }, { name: 'substring', label: 'Substring', type: 'text', required: true }] },
  { kind: 'regex', label: 'Regex', description: 'Regular expression match', icon: 'regex', configFields: [{ name: 'value', label: 'Value', type: 'expression', required: true }, { name: 'pattern', label: 'Pattern', type: 'text', required: true, placeholder: '^[A-Z].*' }] },
  { kind: 'equals', label: 'Equals', description: 'Equality check', icon: 'equal', configFields: [{ name: 'left', label: 'Left Value', type: 'expression', required: true }, { name: 'right', label: 'Right Value', type: 'expression', required: true }] },
  { kind: 'greater', label: 'Greater', description: 'Greater than check', icon: 'arrow-up', configFields: [{ name: 'left', label: 'Left Value', type: 'expression', required: true }, { name: 'right', label: 'Right Value', type: 'expression', required: true }] },
  { kind: 'less', label: 'Less', description: 'Less than check', icon: 'arrow-down', configFields: [{ name: 'left', label: 'Left Value', type: 'expression', required: true }, { name: 'right', label: 'Right Value', type: 'expression', required: true }] },
  { kind: 'date', label: 'Date', description: 'Date comparison', icon: 'calendar', configFields: [{ name: 'date', label: 'Date', type: 'text', required: true }, { name: 'operator', label: 'Operator', type: 'select', required: true, options: [{ label: 'Before', value: 'before' }, { label: 'After', value: 'after' }, { label: 'Equals', value: 'equals' }] }] },
  { kind: 'time', label: 'Time', description: 'Time comparison', icon: 'clock', configFields: [{ name: 'time', label: 'Time', type: 'text', required: true, placeholder: '09:00' }, { name: 'operator', label: 'Operator', type: 'select', required: false, options: [{ label: 'Before', value: 'before' }, { label: 'After', value: 'after' }, { label: 'Between', value: 'between' }] }] },
  { kind: 'schedule', label: 'Schedule', description: 'Check if within schedule', icon: 'calendar-check', configFields: [{ name: 'days', label: 'Days of Week', type: 'multiselect', required: false, options: [{ label: 'Mon', value: '1' }, { label: 'Tue', value: '2' }, { label: 'Wed', value: '3' }, { label: 'Thu', value: '4' }, { label: 'Fri', value: '5' }, { label: 'Sat', value: '6' }, { label: 'Sun', value: '0' }] }] },
  { kind: 'model-output', label: 'Model Output', description: 'Check AI model output', icon: 'message', configFields: [{ name: 'expected', label: 'Expected Output Pattern', type: 'text', required: true }, { name: 'source', label: 'Source Node ID', type: 'text', required: true }] },
  { kind: 'llm-decision', label: 'LLM Decision', description: 'Let LLM decide the branch', icon: 'brain', configFields: [{ name: 'prompt', label: 'Decision Prompt', type: 'textarea', required: true }, { name: 'branches', label: 'Branch Names', type: 'json', required: true, defaultValue: ['yes', 'no'] }] },
]

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function createDefaultPorts(nodeId: string, type: NodeType): Port[] {
  const ports: Port[] = [
    { id: `${nodeId}-in`, nodeId, type: 'input', label: 'In', dataType: 'any' },
    { id: `${nodeId}-out`, nodeId, type: 'output', label: 'Out', dataType: 'any' },
  ]

  if (type === 'condition' || type === 'switch') {
    ports.push({ id: `${nodeId}-out-false`, nodeId, type: 'output', label: 'False', dataType: 'any' })
  }

  if (type === 'loop') {
    ports.push({ id: `${nodeId}-out-loop`, nodeId, type: 'output', label: 'Loop Body', dataType: 'any' })
  }

  return ports
}

export function createNode(
  type: NodeType,
  kind: TriggerKind | ActionKind | ConditionKind,
  label: string,
  position: Position
): WorkflowNode {
  const id = generateId()

  return {
    id,
    type,
    kind,
    label,
    description: '',
    position,
    size: { width: 200, height: 60 },
    config: { label, description: '' },
    ports: createDefaultPorts(id, type),
    status: 'idle',
  }
}

export function createConnection(sourceNodeId: string, sourcePortId: string, targetNodeId: string, targetPortId: string): Connection {
  return { id: generateId(), sourceNodeId, sourcePortId, targetNodeId, targetPortId }
}

function createDefaultWorkflow(): WorkflowDocument {
  const now = new Date().toISOString()
  const startNode = createNode('trigger', 'manual', 'Manual Trigger', { x: 300, y: 200 })

  return {
    id: generateId(),
    name: 'New Workflow',
    description: '',
    tags: [],
    owner: '',
    agentAssignment: '',
    nodes: [startNode],
    connections: [],
    variables: [],
    secrets: [],
    schedule: null,
    retryPolicy: {
      maxRetries: 3,
      retryDelay: 5,
      retryDelayUnit: 'seconds',
      backoffMultiplier: 2,
      retryOnError: true,
      maxDuration: 3600,
    },
    logging: true,
    createdAt: now,
    updatedAt: now,
    version: 1,
    enabled: false,
  }
}

export const INITIAL_WORKFLOW = createDefaultWorkflow()

export const $automation = atom<AutomationState>({
  workflows: [INITIAL_WORKFLOW],
  executions: [],
  secrets: [],
  activeWorkflowId: INITIAL_WORKFLOW.id,
  canvasScale: 1,
  canvasPan: { x: 0, y: 0 },
  selectedNodeIds: [],
  selectedConnectionIds: [],
  clipboard: null,
  history: [{ nodes: INITIAL_WORKFLOW.nodes, connections: INITIAL_WORKFLOW.connections }],
  historyIndex: 0,
  showMiniMap: true,
  snapToGrid: true,
  gridSize: 20,
  nodeSearchQuery: '',
  editingNodeId: null,
  isDragging: false,
  isPanning: false,
  showNodePalette: true,
  showVariablesPanel: false,
  showSecretsPanel: false,
  showScheduler: false,
  showHistory: false,
  showTemplates: false,
  activeTab: 'editor',
})

function patch(update: Partial<AutomationState>) {
  $automation.set({ ...$automation.get(), ...update })
}

function getActiveWorkflow(): WorkflowDocument | undefined {
  const state = $automation.get()

  return state.workflows.find(w => w.id === state.activeWorkflowId)
}

function pushHistory() {
  const state = $automation.get()
  const workflow = state.workflows.find(w => w.id === state.activeWorkflowId)

  if (!workflow) {return}
  const entry: AutomationHistoryEntry = { nodes: JSON.parse(JSON.stringify(workflow.nodes)), connections: JSON.parse(JSON.stringify(workflow.connections)) }
  const history = state.history.slice(0, state.historyIndex + 1)
  history.push(entry)
  patch({ history, historyIndex: history.length - 1 })
}

export function createWorkflow(name: string): WorkflowDocument {
  const workflow = { ...createDefaultWorkflow(), id: generateId(), name, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
  patch({ workflows: [...$automation.get().workflows, workflow], activeWorkflowId: workflow.id, activeTab: 'editor' })

  return workflow
}

export function deleteWorkflow(id: string) {
  const state = $automation.get()
  const remaining = state.workflows.filter(w => w.id !== id)
  patch({ workflows: remaining, activeWorkflowId: remaining.length > 0 ? remaining[0].id : null })
}

export function setActiveWorkflow(id: string | null) {
  patch({ activeWorkflowId: id, activeTab: 'editor' })
}

export function updateWorkflow(id: string, update: Partial<WorkflowDocument>) {
  const workflows = $automation.get().workflows.map(w => w.id === id ? { ...w, ...update, updatedAt: new Date().toISOString() } : w)
  patch({ workflows })
}

export function setActiveTab(tab: AutomationState['activeTab']) {
  patch({ activeTab: tab })
}

export function addNode(type: NodeType, kind: TriggerKind | ActionKind | ConditionKind, label: string, position: Position) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  const node = createNode(type, kind, label, position)
  updateWorkflow(workflow.id, { nodes: [...workflow.nodes, node] })
  pushHistory()

  return node
}

export function deleteNode(nodeId: string) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, {
    nodes: workflow.nodes.filter(n => n.id !== nodeId),
    connections: workflow.connections.filter(c => c.sourceNodeId !== nodeId && c.targetNodeId !== nodeId),
  })
  patch({ selectedNodeIds: $automation.get().selectedNodeIds.filter(id => id !== nodeId) })
  pushHistory()
}

export function updateNodePosition(nodeId: string, position: Position) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, {
    nodes: workflow.nodes.map(n => n.id === nodeId ? { ...n, position: { x: n.position.x + position.x, y: n.position.y + position.y } } : n),
  })
}

export function setNodePosition(nodeId: string, position: Position) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, {
    nodes: workflow.nodes.map(n => n.id === nodeId ? { ...n, position } : n),
  })
}

export function updateNodeConfig(nodeId: string, config: Partial<CanvasNodeConfig>) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, {
    nodes: workflow.nodes.map(n => n.id === nodeId ? { ...n, config: { ...n.config, ...config } } : n),
  })
}

export function setEditingNode(nodeId: string | null) {
  patch({ editingNodeId: nodeId })
}

export function addConnection(sourceNodeId: string, sourcePortId: string, targetNodeId: string, targetPortId: string) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  const exists = workflow.connections.some(c => c.sourceNodeId === sourceNodeId && c.targetNodeId === targetNodeId)

  if (exists) {return}
  const connection = createConnection(sourceNodeId, sourcePortId, targetNodeId, targetPortId)
  updateWorkflow(workflow.id, { connections: [...workflow.connections, connection] })
  pushHistory()
}

export function deleteConnection(connectionId: string) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, { connections: workflow.connections.filter(c => c.id !== connectionId) })
  patch({ selectedConnectionIds: $automation.get().selectedConnectionIds.filter(id => id !== connectionId) })
  pushHistory()
}

export function selectNode(nodeId: string, multi: boolean = false) {
  const state = $automation.get()

  if (multi) {
    const selected = state.selectedNodeIds.includes(nodeId)
      ? state.selectedNodeIds.filter(id => id !== nodeId)
      : [...state.selectedNodeIds, nodeId]

    patch({ selectedNodeIds: selected })
  } else {
    patch({ selectedNodeIds: [nodeId], selectedConnectionIds: [] })
  }
}

export function selectConnection(connectionId: string) {
  patch({ selectedConnectionIds: [connectionId], selectedNodeIds: [] })
}

export function clearSelection() {
  patch({ selectedNodeIds: [], selectedConnectionIds: [] })
}

export function selectAll() {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  patch({ selectedNodeIds: workflow.nodes.map(n => n.id), selectedConnectionIds: [] })
}

export function copySelection() {
  const state = $automation.get()
  const workflow = getActiveWorkflow()

  if (!workflow || state.selectedNodeIds.length === 0) {return}
  const nodes = workflow.nodes.filter(n => state.selectedNodeIds.includes(n.id))
  const nodeIds = new Set(nodes.map(n => n.id))
  const connections = workflow.connections.filter(c => nodeIds.has(c.sourceNodeId) && nodeIds.has(c.targetNodeId))
  patch({ clipboard: { nodes: JSON.parse(JSON.stringify(nodes)), connections: JSON.parse(JSON.stringify(connections)) } })
}

export function pasteClipboard() {
  const state = $automation.get()
  const workflow = getActiveWorkflow()

  if (!workflow || !state.clipboard) {return}
  const idMap = new Map<string, string>()

  const newNodes = state.clipboard.nodes.map(n => {
    const newId = generateId()
    idMap.set(n.id, newId)

    return { ...n, id: newId, position: { x: n.position.x + 50, y: n.position.y + 50 }, status: 'idle' as NodeExecutionStatus, ports: n.ports.map(p => ({ ...p, id: generateId(), nodeId: newId })) }
  })

  const newConnections = state.clipboard.connections.map(c => ({
    ...c,
    id: generateId(),
    sourceNodeId: idMap.get(c.sourceNodeId) || c.sourceNodeId,
    targetNodeId: idMap.get(c.targetNodeId) || c.targetNodeId,
    sourcePortId: generateId(),
    targetPortId: generateId(),
  }))

  updateWorkflow(workflow.id, { nodes: [...workflow.nodes, ...newNodes], connections: [...workflow.connections, ...newConnections] })
  patch({ selectedNodeIds: newNodes.map(n => n.id) })
  pushHistory()
}

export function duplicateSelection() {
  copySelection()
  pasteClipboard()
}

export function deleteSelection() {
  const state = $automation.get()
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  const nodeSet = new Set(state.selectedNodeIds)
  updateWorkflow(workflow.id, {
    nodes: workflow.nodes.filter(n => !nodeSet.has(n.id)),
    connections: workflow.connections.filter(c => !nodeSet.has(c.sourceNodeId) && !nodeSet.has(c.targetNodeId)),
  })
  patch({ selectedNodeIds: [] })
  pushHistory()
}

export function undo() {
  const state = $automation.get()

  if (state.historyIndex <= 0) {return}
  const newIndex = state.historyIndex - 1
  const entry = state.history[newIndex]
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, { nodes: JSON.parse(JSON.stringify(entry.nodes)), connections: JSON.parse(JSON.stringify(entry.connections)) })
  patch({ historyIndex: newIndex })
}

export function redo() {
  const state = $automation.get()

  if (state.historyIndex >= state.history.length - 1) {return}
  const newIndex = state.historyIndex + 1
  const entry = state.history[newIndex]
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, { nodes: JSON.parse(JSON.stringify(entry.nodes)), connections: JSON.parse(JSON.stringify(entry.connections)) })
  patch({ historyIndex: newIndex })
}

export function setCanvasScale(scale: number) {
  patch({ canvasScale: Math.max(0.1, Math.min(3, scale)) })
}

export function setCanvasPan(pan: Position) {
  patch({ canvasPan: pan })
}

export function setShowMiniMap(show: boolean) {
  patch({ showMiniMap: show })
}

export function setSnapToGrid(snap: boolean) {
  patch({ snapToGrid: snap })
}

export function setGridSize(size: number) {
  patch({ gridSize: size })
}

export function setNodeSearchQuery(query: string) {
  patch({ nodeSearchQuery: query })
}

export function setShowNodePalette(show: boolean) {
  patch({ showNodePalette: show })
}

export function setShowVariablesPanel(show: boolean) {
  patch({ showVariablesPanel: show })
}

export function setShowSecretsPanel(show: boolean) {
  patch({ showSecretsPanel: show })
}

export function autoLayout() {
  const workflow = getActiveWorkflow()

  if (!workflow || workflow.nodes.length === 0) {return}
  const sorted = [...workflow.nodes]
  const layers = new Map<number, WorkflowNode[]>()
  const inDegree = new Map<string, number>()
  const adjacency = new Map<string, string[]>()
  sorted.forEach(n => { inDegree.set(n.id, 0); adjacency.set(n.id, []) })
  workflow.connections.forEach(c => {
    adjacency.get(c.sourceNodeId)?.push(c.targetNodeId)
    inDegree.set(c.targetNodeId, (inDegree.get(c.targetNodeId) || 0) + 1)
  })
  let queue = sorted.filter(n => (inDegree.get(n.id) || 0) === 0)
  let layer = 0

  while (queue.length > 0) {
    layers.set(layer, queue)
    const next: string[] = []
    queue.forEach(n => {
      adjacency.get(n.id)?.forEach(child => {
        const deg = (inDegree.get(child) || 1) - 1
        inDegree.set(child, deg)

        if (deg === 0) {next.push(child)}
      })
    })
    queue = next.map(id => sorted.find(n => n.id === id)!).filter(Boolean)
    layer++
  }

  const nodeMap = new Map(sorted.map(n => [n.id, n]))

  const updated = sorted.map(n => {
    const l = [...layers.entries()].find(([_, nodes]) => nodes.some(nd => nd.id === n.id))?.[0] ?? 0
    const idx = layers.get(l)?.findIndex(nd => nd.id === n.id) ?? 0

    return { ...n, position: { x: 100 + l * 250, y: 100 + idx * 120 } }
  })

  updateWorkflow(workflow.id, { nodes: updated })
  pushHistory()
}

export function addVariable(variable: WorkflowVariable) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, { variables: [...workflow.variables, variable] })
}

export function deleteVariable(id: string) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, { variables: workflow.variables.filter(v => v.id !== id) })
}

export function updateVariable(id: string, update: Partial<WorkflowVariable>) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, { variables: workflow.variables.map(v => v.id === id ? { ...v, ...update } : v) })
}

export function addSecret(name: string, description: string): SecretEntry {
  const entry: SecretEntry = { id: generateId(), name, description, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), maskedValue: '••••••••' }
  patch({ secrets: [...$automation.get().secrets, entry] })

  return entry
}

export function deleteSecret(id: string) {
  patch({ secrets: $automation.get().secrets.filter(s => s.id !== id) })
}

export function addExecution(execution: WorkflowExecution) {
  patch({ executions: [$automation.get().executions, execution].flat() })
}

export function setWorkflowSchedule(schedule: WorkflowSchedule | null) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, { schedule })
}

export function setRetryPolicy(policy: RetryPolicy) {
  const workflow = getActiveWorkflow()

  if (!workflow) {return}
  updateWorkflow(workflow.id, { retryPolicy: policy })
}

export function duplicateWorkflow(id: string): WorkflowDocument | null {
  const original = $automation.get().workflows.find(w => w.id === id)

  if (!original) {return null}

  const copy: WorkflowDocument = {
    ...JSON.parse(JSON.stringify(original)),
    id: generateId(),
    name: `${original.name} (copy)`,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    version: 1,
    enabled: false,
  }

  patch({ workflows: [...$automation.get().workflows, copy] })

  return copy
}

export function toggleWorkflowEnabled(id: string) {
  const workflow = $automation.get().workflows.find(w => w.id === id)

  if (!workflow) {return}
  updateWorkflow(id, { enabled: !workflow.enabled })
}

export function resetCanvas() {
  patch({ canvasScale: 1, canvasPan: { x: 0, y: 0 }, selectedNodeIds: [], selectedConnectionIds: [] })
}

export function getTriggerConfigs() { return TRIGGER_CONFIGS }

export function getActionConfigs() { return ACTION_CONFIGS }

export function getConditionConfigs() { return CONDITION_CONFIGS }

export function getActionConfigByKind(kind: ActionKind): ActionConfig | undefined {
  return ACTION_CONFIGS.find(a => a.kind === kind)
}

export function getTriggerConfigByKind(kind: TriggerKind): TriggerConfig | undefined {
  return TRIGGER_CONFIGS.find(t => t.kind === kind)
}

export function getConditionConfigByKind(kind: ConditionKind): ConditionConfig | undefined {
  return CONDITION_CONFIGS.find(c => c.kind === kind)
}

export function getCategoryActions(category: ActionConfig['category']): ActionConfig[] {
  return ACTION_CONFIGS.filter(a => a.category === category)
}

export function getNodeLabel(type: NodeType, kind: string): string {
  if (type === 'trigger') {return TRIGGER_CONFIGS.find(t => t.kind === kind)?.label ?? kind}

  if (type === 'action') {return ACTION_CONFIGS.find(a => a.kind === kind)?.label ?? kind}

  if (type === 'condition') {return CONDITION_CONFIGS.find(c => c.kind === kind)?.label ?? kind}

  return kind
}

export function getNodeIcon(type: NodeType, kind: string): string {
  if (type === 'trigger') {return TRIGGER_CONFIGS.find(t => t.kind === kind)?.icon ?? 'circle'}

  if (type === 'action') {return ACTION_CONFIGS.find(a => a.kind === kind)?.icon ?? 'circle'}

  if (type === 'condition') {return CONDITION_CONFIGS.find(c => c.kind === kind)?.icon ?? 'circle'}

  return 'circle'
}
