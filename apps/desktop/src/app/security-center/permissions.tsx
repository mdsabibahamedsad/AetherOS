import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Codicon } from '@/components/ui/codicon'
import { SearchField } from '@/components/ui/search-field'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'
import {
  PERMISSION_DEFINITIONS,
  type PermissionCategory,
  type PermissionDuration,
  type PermissionGrant,
  type PermissionPolicy,
  removeGrant,
} from '@/store/security'

const CATEGORY_ICONS: Record<PermissionCategory, string> = {
  filesystem: 'file-directory',
  network: 'globe',
  browser: 'globe',
  clipboard: 'clippy',
  terminal: 'terminal',
  docker: 'container',
  python: 'symbol-misc',
  database: 'database',
  cloud: 'cloud',
  system: 'settings-gear',
}

const CATEGORY_LABELS: Record<PermissionCategory, string> = {
  filesystem: 'Filesystem',
  network: 'Network',
  browser: 'Browser',
  clipboard: 'Clipboard',
  terminal: 'Terminal',
  docker: 'Docker',
  python: 'Python',
  database: 'Database',
  cloud: 'Cloud Services',
  system: 'System',
}

const POLICY_LABELS: Record<PermissionPolicy, string> = {
  allow: 'Allow',
  deny: 'Deny',
  'ask-every-time': 'Ask Every Time',
  'ask-once': 'Ask Once',
}

const POLICY_COLORS: Record<PermissionPolicy, string> = {
  allow: 'text-emerald-500',
  deny: 'text-red-500',
  'ask-every-time': 'text-amber-500',
  'ask-once': 'text-blue-500',
}

const RISK_COLORS: Record<string, string> = {
  low: 'text-emerald-500',
  medium: 'text-amber-500',
  high: 'text-orange-500',
  critical: 'text-red-500',
}

const DURATION_LABELS: Record<PermissionDuration, string> = {
  'ask-every-time': 'Ask Every Time',
  'ask-once': 'Ask Once',
  'temporary': 'Temporary',
  'session': 'Session',
  'permanent': 'Permanent',
}

const GRANTEE_TYPES = ['agent', 'plugin', 'mcp-server', 'automation', 'tool'] as const

const SAMPLE_GRANTEES = [
  { type: 'agent' as const, id: 'agent-default', name: 'Default Agent' },
  { type: 'agent' as const, id: 'agent-code', name: 'Code Assistant' },
  { type: 'agent' as const, id: 'agent-research', name: 'Research Agent' },
  { type: 'plugin' as const, id: 'plugin-filesystem', name: 'Filesystem Plugin' },
  { type: 'plugin' as const, id: 'plugin-browser', name: 'Browser Plugin' },
  { type: 'mcp-server' as const, id: 'mcp-github', name: 'GitHub MCP' },
  { type: 'mcp-server' as const, id: 'mcp-postgres', name: 'PostgreSQL MCP' },
  { type: 'automation' as const, id: 'auto-backup', name: 'Backup Workflow' },
  { type: 'automation' as const, id: 'auto-sync', name: 'Sync Workflow' },
]

const SAMPLE_GRANTS: PermissionGrant[] = [
  { id: 'g1', permissionId: 'fs-read', granteeType: 'agent', granteeId: 'agent-default', granteeName: 'Default Agent', policy: 'allow', duration: 'permanent', grantedAt: '2026-07-01T00:00:00Z', expiresAt: null, grantedBy: 'user' },
  { id: 'g2', permissionId: 'fs-write', granteeType: 'agent', granteeId: 'agent-default', granteeName: 'Default Agent', policy: 'ask-every-time', duration: 'permanent', grantedAt: '2026-07-01T00:00:00Z', expiresAt: null, grantedBy: 'user' },
  { id: 'g3', permissionId: 'net-internet', granteeType: 'agent', granteeId: 'agent-default', granteeName: 'Default Agent', policy: 'ask-every-time', duration: 'session', grantedAt: '2026-07-21T00:00:00Z', expiresAt: null, grantedBy: 'user' },
  { id: 'g4', permissionId: 'term-execute', granteeType: 'agent', granteeId: 'agent-default', granteeName: 'Default Agent', policy: 'ask-every-time', duration: 'permanent', grantedAt: '2026-07-01T00:00:00Z', expiresAt: null, grantedBy: 'user' },
  { id: 'g5', permissionId: 'fs-read', granteeType: 'plugin', granteeId: 'plugin-filesystem', granteeName: 'Filesystem Plugin', policy: 'allow', duration: 'permanent', grantedAt: '2026-07-01T00:00:00Z', expiresAt: null, grantedBy: 'user' },
  { id: 'g6', permissionId: 'fs-write', granteeType: 'plugin', granteeId: 'plugin-filesystem', granteeName: 'Filesystem Plugin', policy: 'allow', duration: 'permanent', grantedAt: '2026-07-01T00:00:00Z', expiresAt: null, grantedBy: 'user' },
  { id: 'g7', permissionId: 'net-internet', granteeType: 'mcp-server', granteeId: 'mcp-github', granteeName: 'GitHub MCP', policy: 'allow', duration: 'permanent', grantedAt: '2026-07-01T00:00:00Z', expiresAt: null, grantedBy: 'user' },
  { id: 'g8', permissionId: 'fs-read', granteeType: 'automation', granteeId: 'auto-backup', granteeName: 'Backup Workflow', policy: 'allow', duration: 'session', grantedAt: '2026-07-21T00:00:00Z', expiresAt: null, grantedBy: 'user' },
  { id: 'g9', permissionId: 'fs-delete', granteeType: 'agent', granteeId: 'agent-default', granteeName: 'Default Agent', policy: 'deny', duration: 'permanent', grantedAt: '2026-07-01T00:00:00Z', expiresAt: null, grantedBy: 'system' },
  { id: 'g10', permissionId: 'browser-cookies', granteeType: 'agent', granteeId: 'agent-default', granteeName: 'Default Agent', policy: 'deny', duration: 'permanent', grantedAt: '2026-07-01T00:00:00Z', expiresAt: null, grantedBy: 'system' },
]

export function PermissionManager() {
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [granteeFilter, setGranteeFilter] = useState<string>('all')
  const [selectedGrantee, setSelectedGrantee] = useState<{ type: string; id: string; name: string } | null>(null)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [grants, setGrants] = useState<PermissionGrant[]>(SAMPLE_GRANTS)

  const categories = [...new Set(PERMISSION_DEFINITIONS.map(p => p.category))]

  const filteredGrants = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()

    return grants.filter(g => {
      const def = PERMISSION_DEFINITIONS.find(p => p.id === g.permissionId)

      if (q && !g.granteeName.toLowerCase().includes(q) && !(def?.label.toLowerCase().includes(q))) {return false}

      if (categoryFilter !== 'all' && def?.category !== categoryFilter) {return false}

      if (granteeFilter !== 'all' && g.granteeType !== granteeFilter) {return false}

      return true
    })
  }, [grants, searchQuery, categoryFilter, granteeFilter])

  const grantsByGrantee = useMemo(() => {
    const map = new Map<string, { name: string; type: string; grants: PermissionGrant[] }>()

    for (const g of filteredGrants) {
      const key = `${g.granteeType}:${g.granteeId}`

      if (!map.has(key)) {map.set(key, { name: g.granteeName, type: g.granteeType, grants: [] })}
      map.get(key)!.grants.push(g)
    }

    return Array.from(map.entries()).sort((a, b) => a[1].name.localeCompare(b[1].name))
  }, [filteredGrants])

  return (
    <div className="flex h-full">
      <div className="w-72 shrink-0 border-r border-(--ui-stroke-tertiary) p-4">
        <div className="space-y-3">
          <SearchField
            containerClassName="w-full"
            onChange={setSearchQuery}
            placeholder="Search permissions..."
            value={searchQuery}
          />
          <div className="flex gap-2">
            <Select onValueChange={v => setCategoryFilter(v)} value={categoryFilter}>
              <SelectTrigger className="h-7 flex-1 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map(c => <SelectItem key={c} value={c}>{CATEGORY_LABELS[c]}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select onValueChange={v => setGranteeFilter(v)} value={granteeFilter}>
              <SelectTrigger className="h-7 flex-1 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {GRANTEE_TYPES.map(t => <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1).replace('-', ' ')}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-0.5">
            {grantsByGrantee.map(([key, group]) => (
              <button
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors',
                  selectedGrantee && `${selectedGrantee.type}:${selectedGrantee.id}` === key ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
                )}
                key={key}
                onClick={() => setSelectedGrantee({ type: group.type, id: key.split(':')[1]!, name: group.name })}
                type="button"
              >
                <Codicon name={CATEGORY_ICONS[group.type === 'mcp-server' ? 'cloud' : group.type as PermissionCategory] || 'lock'} size="1rem" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{group.name}</div>
                  <div className="text-[0.6rem] text-muted-foreground">
                    <span className="capitalize">{group.type}</span> &middot; {group.grants.length} permissions
                  </div>
                </div>
              </button>
            ))}
            {grantsByGrantee.length === 0 && (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">
                No matching permissions
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="min-w-0 flex-1 overflow-y-auto p-4">
        {selectedGrantee ? (
          <PermissionGranteeDetail
            granteeName={selectedGrantee.name}
            granteeType={selectedGrantee.type}
            grants={grants.filter(g => g.granteeId === selectedGrantee.id && g.granteeType === selectedGrantee.type)}
            onRemoveGrant={grantId => {
              setGrants(prev => prev.filter(g => g.id !== grantId))
              removeGrant(grantId)
              notify({ kind: 'success', title: 'Permission Removed', message: 'Grant has been revoked' })
            }}
          />
        ) : (
          <div className="grid min-h-52 place-items-center text-center">
            <div>
              <Codicon className="text-muted-foreground/40" name="lock" size="2rem" />
              <div className="mt-2 text-sm font-medium text-muted-foreground">Select a grantee</div>
              <div className="mt-1 text-xs text-muted-foreground/60">Choose an agent, plugin, or server to view permissions</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function PermissionGranteeDetail({
  grants,
  granteeName,
  granteeType,
  onRemoveGrant,
}: {
  grants: PermissionGrant[]
  granteeName: string
  granteeType: string
  onRemoveGrant: (id: string) => void
}) {
  const [editGrant, setEditGrant] = useState<{ grant: PermissionGrant; policy: PermissionPolicy; duration: PermissionDuration } | null>(null)

  const grantsByCategory = useMemo(() => {
    const map = new Map<PermissionCategory, PermissionGrant[]>()

    for (const g of grants) {
      const def = PERMISSION_DEFINITIONS.find(p => p.id === g.permissionId)

      if (!def) {continue}
      const cat = def.category

      if (!map.has(cat)) {map.set(cat, [])}
      map.get(cat)!.push(g)
    }

    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]))
  }, [grants])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Codicon name="lock" size="1.25rem" />
        <div>
          <h3 className="text-lg font-semibold">{granteeName}</h3>
          <div className="text-xs text-muted-foreground capitalize">{granteeType} &middot; {grants.length} permissions</div>
        </div>
      </div>

      {grantsByCategory.length === 0 ? (
        <div className="rounded-lg border border-dashed px-4 py-8 text-center text-xs text-muted-foreground">
          No permissions configured for {granteeName}. Default policy: Deny all.
        </div>
      ) : (
        grantsByCategory.map(([category, categoryGrants]) => (
          <div className="rounded-xl border border-(--ui-stroke-tertiary)" key={category}>
            <div className="flex items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Codicon name={CATEGORY_ICONS[category]} size="0.875rem" />
              {CATEGORY_LABELS[category]}
            </div>
            <div className="divide-y divide-(--ui-stroke-tertiary)">
              {categoryGrants.map(grant => {
                const def = PERMISSION_DEFINITIONS.find(p => p.id === grant.permissionId)

                if (!def) {return null}

                return (
                  <div className="flex items-center justify-between px-4 py-2.5" key={grant.id}>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 text-sm font-medium">{def.label}</div>
                      <div className="text-xs text-muted-foreground">{def.description}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge className={cn('text-[0.55rem]', RISK_COLORS[def.riskLevel])} variant="outline">{def.riskLevel}</Badge>
                      <span className={cn('text-xs font-medium', POLICY_COLORS[grant.policy])}>{POLICY_LABELS[grant.policy]}</span>
                      <span className="text-[0.6rem] text-muted-foreground">{DURATION_LABELS[grant.duration]}</span>
                      <button className="text-muted-foreground hover:text-destructive" onClick={() => onRemoveGrant(grant.id)} type="button">
                        <Codicon name="trash" size="0.875rem" />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
