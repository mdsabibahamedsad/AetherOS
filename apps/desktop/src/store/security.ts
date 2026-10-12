import { atom } from 'nanostores'


export type PermissionCategory =
  | 'filesystem' | 'network' | 'browser' | 'clipboard'
  | 'terminal' | 'docker' | 'python' | 'database' | 'cloud' | 'system'

export type PermissionDuration = 'ask-every-time' | 'ask-once' | 'temporary' | 'session' | 'permanent'

export type PermissionPolicy = 'allow' | 'deny' | 'ask-every-time' | 'ask-once'

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export type SandboxMode = 'read-only' | 'restricted' | 'standard' | 'trusted' | 'custom'

export type PrivacyMode = 'offline' | 'local-only' | 'no-telemetry' | 'private' | 'strict-sandbox'

export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical'

export type AlertCategory =
  | 'repeated-failures' | 'suspicious-tool-usage' | 'unexpected-network'
  | 'permission-escalation' | 'untrusted-plugin' | 'invalid-signature'
  | 'credential-failure' | 'brute-force' | 'abnormal-activity'

export type AuditEventType =
  | 'permission-granted' | 'permission-denied' | 'permission-approved'
  | 'sandbox-created' | 'sandbox-destroyed' | 'sandbox-violation'
  | 'agent-execution' | 'plugin-execution' | 'mcp-execution'
  | 'network-access' | 'filesystem-access' | 'secret-access'
  | 'device-registered' | 'device-revoked' | 'session-expired'
  | 'privacy-mode-changed' | 'threat-detected' | 'credential-accessed'

export interface PermissionDefinition {
  id: string
  category: PermissionCategory
  action: string
  label: string
  description: string
  defaultPolicy: PermissionPolicy
  riskLevel: RiskLevel
}

export interface PermissionGrant {
  id: string
  permissionId: string
  granteeType: 'agent' | 'plugin' | 'mcp-server' | 'automation' | 'tool'
  granteeId: string
  granteeName: string
  policy: PermissionPolicy
  duration: PermissionDuration
  grantedAt: string
  expiresAt: string | null
  grantedBy: 'user' | 'system' | 'auto'
}

export interface ApprovalRequest {
  id: string
  agentName: string
  agentId: string
  action: string
  reason: string
  target: string
  riskLevel: RiskLevel
  affectedFiles: string[]
  command: string
  networkDestination: string
  timestamp: string
  status: 'pending' | 'approved' | 'denied' | 'expired'
}

export interface SandboxInstance {
  id: string
  name: string
  type: 'agent' | 'plugin' | 'mcp-server' | 'python' | 'shell' | 'browser' | 'automation'
  mode: SandboxMode
  status: 'running' | 'stopped' | 'error' | 'creating'
  allowedFolders: string[]
  blockedFolders: string[]
  readOnlyFolders: string[]
  tempFolder: string
  projectWorkspace: string
  domainAllowlist: string[]
  domainBlocklist: string[]
  ipRestrictions: string[]
  portRestrictions: number[]
  offlineMode: boolean
  memoryLimit: number
  cpuLimit: number
  timeout: number
  startedAt: string
  pid: number | null
}

export interface AuditEntry {
  id: string
  timestamp: string
  agentName: string
  userId: string
  deviceId: string
  eventType: AuditEventType
  action: string
  toolName: string
  target: string
  result: 'success' | 'failure' | 'blocked'
  riskLevel: RiskLevel
  approvalRequired: boolean
  approvalStatus: 'approved' | 'denied' | 'none'
  error: string | null
  metadata: Record<string, string>
}

export interface SecurityAlert {
  id: string
  timestamp: string
  severity: AlertSeverity
  category: AlertCategory
  title: string
  message: string
  source: string
  sourceId: string
  acknowledged: boolean
  resolved: boolean
  riskLevel: RiskLevel
  count: number
}

export interface SecretEntry {
  id: string
  name: string
  category: 'api-key' | 'password' | 'token' | 'certificate' | 'other'
  provider: string
  createdAt: string
  lastAccessed: string | null
  expiresAt: string | null
  maskedValue: string
}

export interface ConnectedSession {
  id: string
  deviceName: string
  deviceId: string
  ipAddress: string
  location: string
  startedAt: string
  lastActive: string
  sessionType: 'local' | 'remote' | 'gateway'
  expiresAt: string
  scopes: string[]
}

export interface PermissionProfile {
  granteeType: 'agent' | 'plugin' | 'mcp-server' | 'automation' | 'tool'
  granteeId: string
  granteeName: string
  permissions: PermissionGrant[]
  sandboxMode: SandboxMode
  allowedFolders: string[]
  blockedFolders: string[]
  domainAllowlist: string[]
  domainBlocklist: string[]
  timeouts: {
    executionTimeout: number
    maxRetries: number
    resourceLimit: number
  }
}

export interface SecurityState {
  initialized: boolean
  zeroTrust: boolean
  version: string
  permissions: PermissionDefinition[]
  grants: PermissionGrant[]
  approvalRequests: ApprovalRequest[]
  sandboxes: SandboxInstance[]
  auditEntries: AuditEntry[]
  alerts: SecurityAlert[]
  secrets: SecretEntry[]
  sessions: ConnectedSession[]
  activeAlertsCount: number
  blockedActionsCount: number
  recentApprovals: number
  privacyMode: PrivacyMode | null
  offlineMode: boolean
  telemetryEnabled: boolean
  systemIntegrity: 'passed' | 'warning' | 'failed'
}

export const $securityState = atom<SecurityState>({
  initialized: true,
  zeroTrust: true,
  version: '0.24.0',
  permissions: [],
  grants: [],
  approvalRequests: [],
  sandboxes: [],
  auditEntries: [],
  alerts: [],
  secrets: [],
  sessions: [],
  activeAlertsCount: 0,
  blockedActionsCount: 0,
  recentApprovals: 0,
  privacyMode: null,
  offlineMode: false,
  telemetryEnabled: false,
  systemIntegrity: 'passed',
})

export const $securityLoading = atom(false)
export const $activeAlertFilter = atom<AlertSeverity | 'all'>('all')
export const $auditSearchQuery = atom('')
export const $auditEventFilter = atom<AuditEventType | 'all'>('all')
export const $auditRiskFilter = atom<RiskLevel | 'all'>('all')
export const $sandboxStatusFilter = atom<string>('all')
export const $permissionSearchQuery = atom('')
export const $permissionGranteeFilter = atom<string>('all')
export const $alertCategoryFilter = atom<AlertCategory | 'all'>('all')

export const PERMISSION_DEFINITIONS: PermissionDefinition[] = [
  { id: 'fs-read', category: 'filesystem', action: 'read', label: 'Read Files', description: 'Read files from the filesystem', defaultPolicy: 'allow', riskLevel: 'low' },
  { id: 'fs-write', category: 'filesystem', action: 'write', label: 'Write Files', description: 'Write and modify files', defaultPolicy: 'ask-every-time', riskLevel: 'medium' },
  { id: 'fs-delete', category: 'filesystem', action: 'delete', label: 'Delete Files', description: 'Permanently delete files', defaultPolicy: 'deny', riskLevel: 'critical' },
  { id: 'fs-move', category: 'filesystem', action: 'move', label: 'Move Files', description: 'Move or rename files', defaultPolicy: 'ask-every-time', riskLevel: 'medium' },
  { id: 'fs-create-dir', category: 'filesystem', action: 'create-directory', label: 'Create Directories', description: 'Create new directories', defaultPolicy: 'allow', riskLevel: 'low' },
  { id: 'net-internet', category: 'network', action: 'internet', label: 'Internet Access', description: 'Access the internet', defaultPolicy: 'ask-every-time', riskLevel: 'medium' },
  { id: 'net-domains', category: 'network', action: 'specific-domains', label: 'Specific Domains', description: 'Access only specific domains', defaultPolicy: 'allow', riskLevel: 'low' },
  { id: 'net-ports', category: 'network', action: 'specific-ports', label: 'Specific Ports', description: 'Access only specific ports', defaultPolicy: 'allow', riskLevel: 'low' },
  { id: 'net-local', category: 'network', action: 'local-network', label: 'Local Network', description: 'Access local network resources', defaultPolicy: 'deny', riskLevel: 'medium' },
  { id: 'browser-open', category: 'browser', action: 'open-pages', label: 'Open Pages', description: 'Open web pages in the browser', defaultPolicy: 'ask-every-time', riskLevel: 'medium' },
  { id: 'browser-download', category: 'browser', action: 'download', label: 'Download Files', description: 'Download files via browser', defaultPolicy: 'ask-every-time', riskLevel: 'high' },
  { id: 'browser-upload', category: 'browser', action: 'upload', label: 'Upload Files', description: 'Upload files via browser', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'browser-cookies', category: 'browser', action: 'cookies', label: 'Cookies', description: 'Access browser cookies', defaultPolicy: 'deny', riskLevel: 'critical' },
  { id: 'clipboard-read', category: 'clipboard', action: 'read', label: 'Read Clipboard', description: 'Read clipboard contents', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'clipboard-write', category: 'clipboard', action: 'write', label: 'Write Clipboard', description: 'Write to clipboard', defaultPolicy: 'ask-every-time', riskLevel: 'medium' },
  { id: 'term-execute', category: 'terminal', action: 'execute', label: 'Command Execution', description: 'Execute terminal commands', defaultPolicy: 'ask-every-time', riskLevel: 'high' },
  { id: 'term-shell', category: 'terminal', action: 'shell', label: 'Shell Access', description: 'Access interactive shell', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'term-process', category: 'terminal', action: 'process-manage', label: 'Process Management', description: 'Manage running processes', defaultPolicy: 'deny', riskLevel: 'critical' },
  { id: 'docker-create', category: 'docker', action: 'container-create', label: 'Container Creation', description: 'Create Docker containers', defaultPolicy: 'deny', riskLevel: 'critical' },
  { id: 'docker-exec', category: 'docker', action: 'container-exec', label: 'Container Execution', description: 'Execute commands in containers', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'docker-net', category: 'docker', action: 'container-network', label: 'Container Network', description: 'Configure container networking', defaultPolicy: 'deny', riskLevel: 'critical' },
  { id: 'py-exec', category: 'python', action: 'code-exec', label: 'Code Execution', description: 'Execute Python code', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'py-pkg', category: 'python', action: 'package-install', label: 'Package Installation', description: 'Install Python packages', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'db-read', category: 'database', action: 'read', label: 'Database Read', description: 'Read from databases', defaultPolicy: 'ask-every-time', riskLevel: 'medium' },
  { id: 'db-write', category: 'database', action: 'write', label: 'Database Write', description: 'Write to databases', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'db-delete', category: 'database', action: 'delete', label: 'Database Delete', description: 'Delete from databases', defaultPolicy: 'deny', riskLevel: 'critical' },
  { id: 'cloud-email', category: 'cloud', action: 'email', label: 'Email', description: 'Access email services', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'cloud-messaging', category: 'cloud', action: 'messaging', label: 'Messaging', description: 'Access messaging services', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'cloud-calendar', category: 'cloud', action: 'calendar', label: 'Calendar', description: 'Access calendar services', defaultPolicy: 'deny', riskLevel: 'medium' },
  { id: 'cloud-github', category: 'cloud', action: 'github', label: 'GitHub', description: 'Access GitHub API and repos', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'cloud-storage', category: 'cloud', action: 'storage', label: 'Storage', description: 'Access cloud storage services', defaultPolicy: 'deny', riskLevel: 'high' },
  { id: 'sys-settings', category: 'system', action: 'settings', label: 'System Settings', description: 'Modify system settings', defaultPolicy: 'deny', riskLevel: 'critical' },
  { id: 'sys-extensions', category: 'system', action: 'extensions', label: 'Extensions', description: 'Install and manage extensions', defaultPolicy: 'deny', riskLevel: 'high' },
]

export function updateSecurityState(partial: Partial<SecurityState>) {
  $securityState.set({ ...$securityState.get(), ...partial })
}

export function addGrant(grant: PermissionGrant) {
  const grants = $securityState.get().grants
  const existing = grants.findIndex(g => g.granteeId === grant.granteeId && g.permissionId === grant.permissionId)

  if (existing >= 0) {
    const updated = [...grants]
    updated[existing] = grant
    $securityState.set({ ...$securityState.get(), grants: updated })
  } else {
    $securityState.set({ ...$securityState.get(), grants: [...grants, grant] })
  }
}

export function removeGrant(grantId: string) {
  $securityState.set({
    ...$securityState.get(),
    grants: $securityState.get().grants.filter(g => g.id !== grantId),
  })
}

export function addApprovalRequest(request: ApprovalRequest) {
  $securityState.set({
    ...$securityState.get(),
    approvalRequests: [...$securityState.get().approvalRequests, request],
  })
}

export function resolveApprovalRequest(id: string, status: 'approved' | 'denied') {
  const requests = $securityState.get().approvalRequests.map(r =>
    r.id === id ? { ...r, status } : r
  )

  const recentApprovals = $securityState.get().recentApprovals + (status === 'approved' ? 1 : 0)
  $securityState.set({ ...$securityState.get(), approvalRequests: requests, recentApprovals })
}

export function addSandbox(sandbox: SandboxInstance) {
  $securityState.set({
    ...$securityState.get(),
    sandboxes: [...$securityState.get().sandboxes, sandbox],
  })
}

export function removeSandbox(id: string) {
  $securityState.set({
    ...$securityState.get(),
    sandboxes: $securityState.get().sandboxes.filter(s => s.id !== id),
  })
}

export function updateSandboxStatus(id: string, status: SandboxInstance['status']) {
  $securityState.set({
    ...$securityState.get(),
    sandboxes: $securityState.get().sandboxes.map(s =>
      s.id === id ? { ...s, status } : s
    ),
  })
}

export function addAuditEntry(entry: AuditEntry) {
  const entries = $securityState.get().auditEntries
  $securityState.set({
    ...$securityState.get(),
    auditEntries: [entry, ...entries].slice(0, 10000),
    blockedActionsCount: entry.result === 'blocked' ? $securityState.get().blockedActionsCount + 1 : $securityState.get().blockedActionsCount,
  })
}

export function addAlert(alert: SecurityAlert) {
  const alerts = $securityState.get().alerts
  const existing = alerts.find(a => a.category === alert.category && a.source === alert.source && !a.resolved)

  if (existing) {
    $securityState.set({
      ...$securityState.get(),
      alerts: alerts.map(a =>
        a.id === existing.id ? { ...a, count: a.count + 1, timestamp: alert.timestamp, message: alert.message } : a
      ),
      activeAlertsCount: $securityState.get().alerts.filter(a => !a.acknowledged).length + 1,
    })
  } else {
    $securityState.set({
      ...$securityState.get(),
      alerts: [alert, ...alerts].slice(0, 500),
      activeAlertsCount: alerts.filter(a => !a.acknowledged).length + 1,
    })
  }
}

export function acknowledgeAlert(id: string) {
  $securityState.set({
    ...$securityState.get(),
    alerts: $securityState.get().alerts.map(a =>
      a.id === id ? { ...a, acknowledged: true } : a
    ),
    activeAlertsCount: $securityState.get().alerts.filter(a => !a.acknowledged).length - 1,
  })
}

export function resolveAlert(id: string) {
  $securityState.set({
    ...$securityState.get(),
    alerts: $securityState.get().alerts.map(a =>
      a.id === id ? { ...a, resolved: true, acknowledged: true } : a
    ),
  })
}

export function addSecret(secret: SecretEntry) {
  const secrets = $securityState.get().secrets

  if (secrets.some(s => s.id === secret.id)) {return}
  $securityState.set({ ...$securityState.get(), secrets: [...secrets, secret] })
}

export function removeSecret(id: string) {
  $securityState.set({
    ...$securityState.get(),
    secrets: $securityState.get().secrets.filter(s => s.id !== id),
  })
}

export function addSession(session: ConnectedSession) {
  $securityState.set({
    ...$securityState.get(),
    sessions: [...$securityState.get().sessions, session],
  })
}

export function removeSession(id: string) {
  $securityState.set({
    ...$securityState.get(),
    sessions: $securityState.get().sessions.filter(s => s.id !== id),
  })
}

export function setPrivacyMode(mode: PrivacyMode | null) {
  $securityState.set({ ...$securityState.get(), privacyMode: mode })
}

export function setOfflineMode(enabled: boolean) {
  $securityState.set({ ...$securityState.get(), offlineMode: enabled })
}

export function setTelemetryEnabled(enabled: boolean) {
  $securityState.set({ ...$securityState.get(), telemetryEnabled: enabled })
}

export function getPermissionForGrantee(granteeType: string, granteeId: string): PermissionGrant[] {
  return $securityState.get().grants.filter(g => g.granteeType === granteeType && g.granteeId === granteeId)
}

export function getSandboxForGrantee(granteeType: string, granteeId: string): SandboxInstance | undefined {
  return $securityState.get().sandboxes.find(s =>
    (granteeType === 'agent' && s.type === 'agent') ||
    (granteeType === 'plugin' && s.type === 'plugin')
  )
}
