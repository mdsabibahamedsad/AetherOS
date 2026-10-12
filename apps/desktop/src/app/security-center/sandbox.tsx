import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { SearchField } from '@/components/ui/search-field'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'
import {
  addSandbox,
  removeSandbox,
  type SandboxInstance,
  type SandboxMode,
} from '@/store/security'

const MODE_COLORS: Record<string, string> = {
  'read-only': 'bg-blue-500/10 text-blue-600',
  'restricted': 'bg-amber-500/10 text-amber-600',
  'standard': 'bg-emerald-500/10 text-emerald-600',
  'trusted': 'bg-purple-500/10 text-purple-600',
  'custom': 'bg-slate-500/10 text-slate-600',
}

const STATUS_DOT: Record<string, string> = {
  running: 'bg-emerald-500',
  stopped: 'bg-muted-foreground/40',
  error: 'bg-red-500',
  creating: 'bg-amber-500',
}

const TYPE_ICONS: Record<string, string> = {
  agent: 'robot',
  plugin: 'extensions',
  'mcp-server': 'server',
  python: 'symbol-misc',
  shell: 'terminal',
  browser: 'globe',
  automation: 'run-all',
}

const SAMPLE_SANDBOXES: SandboxInstance[] = [
  {
    id: 'sb-1',
    name: 'Default Agent Sandbox',
    type: 'agent',
    mode: 'standard',
    status: 'running',
    allowedFolders: ['/home/user/projects', '/tmp/aetheros'],
    blockedFolders: ['/etc', '/usr', '/bin', '/boot'],
    readOnlyFolders: ['/usr/share'],
    tempFolder: '/tmp/aetheros-sandbox',
    projectWorkspace: '/home/user/projects',
    domainAllowlist: ['*.npmjs.org', '*.github.com', '*.python.org'],
    domainBlocklist: ['*.malware.com', '*.phishing.net'],
    ipRestrictions: [],
    portRestrictions: [80, 443, 22, 5432],
    offlineMode: false,
    memoryLimit: 2048,
    cpuLimit: 80,
    timeout: 300,
    startedAt: new Date(Date.now() - 3600000).toISOString(),
    pid: 12345,
  },
  {
    id: 'sb-2',
    name: 'Plugin Isolated Runtime',
    type: 'plugin',
    mode: 'restricted',
    status: 'running',
    allowedFolders: ['/home/user/projects/plugin-data'],
    blockedFolders: ['/', '/home', '/etc', '/usr'],
    readOnlyFolders: [],
    tempFolder: '/tmp/plugin-sandbox',
    projectWorkspace: '',
    domainAllowlist: ['api.openai.com'],
    domainBlocklist: [],
    ipRestrictions: ['0.0.0.0/0'],
    portRestrictions: [443],
    offlineMode: false,
    memoryLimit: 512,
    cpuLimit: 50,
    timeout: 120,
    startedAt: new Date(Date.now() - 7200000).toISOString(),
    pid: 12346,
  },
  {
    id: 'sb-3',
    name: 'Python Execution Sandbox',
    type: 'python',
    mode: 'read-only',
    status: 'stopped',
    allowedFolders: ['/tmp/sandbox-python'],
    blockedFolders: ['/home', '/etc', '/usr', '/var'],
    readOnlyFolders: ['/usr/lib/python3'],
    tempFolder: '/tmp/sandbox-python/tmp',
    projectWorkspace: '',
    domainAllowlist: [],
    domainBlocklist: ['*'],
    ipRestrictions: ['127.0.0.1'],
    portRestrictions: [],
    offlineMode: true,
    memoryLimit: 256,
    cpuLimit: 25,
    timeout: 60,
    startedAt: new Date(Date.now() - 86400000).toISOString(),
    pid: null,
  },
  {
    id: 'sb-4',
    name: 'Browser Isolation',
    type: 'browser',
    mode: 'standard',
    status: 'creating',
    allowedFolders: ['/tmp/browser-data'],
    blockedFolders: ['/home', '/etc', '/usr'],
    readOnlyFolders: [],
    tempFolder: '/tmp/browser-sandbox',
    projectWorkspace: '',
    domainAllowlist: ['*'],
    domainBlocklist: [],
    ipRestrictions: [],
    portRestrictions: [80, 443],
    offlineMode: false,
    memoryLimit: 1024,
    cpuLimit: 60,
    timeout: 600,
    startedAt: new Date().toISOString(),
    pid: null,
  },
  {
    id: 'sb-5',
    name: 'Automation Workflow Runner',
    type: 'automation',
    mode: 'trusted',
    status: 'running',
    allowedFolders: ['/home/user/projects', '/home/user/.aetheros'],
    blockedFolders: ['/etc', '/usr/bin'],
    readOnlyFolders: [],
    tempFolder: '/tmp/aetheros-automation',
    projectWorkspace: '/home/user/projects',
    domainAllowlist: ['*'],
    domainBlocklist: [],
    ipRestrictions: [],
    portRestrictions: [],
    offlineMode: false,
    memoryLimit: 4096,
    cpuLimit: 90,
    timeout: 900,
    startedAt: new Date(Date.now() - 1800000).toISOString(),
    pid: 12347,
  },
]

const SANDBOX_MODES: SandboxMode[] = ['read-only', 'restricted', 'standard', 'trusted', 'custom']
const SANDBOX_TYPES = ['agent', 'plugin', 'mcp-server', 'python', 'shell', 'browser', 'automation']

export function SandboxManager() {
  const [sandboxes, setSandboxes] = useState<SandboxInstance[]>(SAMPLE_SANDBOXES)
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const filteredSandboxes = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()

    return sandboxes.filter(s => {
      if (q && !s.name.toLowerCase().includes(q) && !s.type.includes(q)) {return false}

      if (typeFilter !== 'all' && s.type !== typeFilter) {return false}

      if (statusFilter !== 'all' && s.status !== statusFilter) {return false}

      return true
    })
  }, [sandboxes, searchQuery, typeFilter, statusFilter])

  const selected = useMemo(() => sandboxes.find(s => s.id === selectedId) ?? null, [sandboxes, selectedId])

  const handleRemove = (id: string) => {
    setSandboxes(prev => prev.filter(s => s.id !== id))
    removeSandbox(id)

    if (selectedId === id) {setSelectedId(null)}
    notify({ kind: 'success', title: 'Sandbox Removed', message: 'Sandbox has been destroyed' })
  }

  return (
    <div className="flex h-full">
      <div className="w-72 shrink-0 border-r border-(--ui-stroke-tertiary) p-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Sandboxes</span>
            <Button className="text-xs" onClick={() => setShowCreate(true)} size="sm">
              <Codicon className="mr-1" name="plus" size="0.75rem" /> Create
            </Button>
          </div>
          <SearchField
            containerClassName="w-full"
            onChange={setSearchQuery}
            placeholder="Search sandboxes..."
            value={searchQuery}
          />
          <div className="flex gap-2">
            <Select onValueChange={v => setTypeFilter(v)} value={typeFilter}>
              <SelectTrigger className="h-7 flex-1 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {SANDBOX_TYPES.map(t => <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select onValueChange={v => setStatusFilter(v)} value={statusFilter}>
              <SelectTrigger className="h-7 flex-1 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="stopped">Stopped</SelectItem>
                <SelectItem value="error">Error</SelectItem>
                <SelectItem value="creating">Creating</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-0.5">
            {filteredSandboxes.map(sb => (
              <button
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors',
                  selected?.id === sb.id ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
                )}
                key={sb.id}
                onClick={() => setSelectedId(sb.id)}
                type="button"
              >
                <span className={cn('size-2 shrink-0 rounded-full', STATUS_DOT[sb.status])} />
                <Codicon className="shrink-0 text-muted-foreground" name={TYPE_ICONS[sb.type] || 'container'} size="0.875rem" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{sb.name}</div>
                  <div className="flex items-center gap-1.5 text-[0.6rem] text-muted-foreground">
                    <Badge className={cn('text-[0.5rem]', MODE_COLORS[sb.mode])} variant="muted">{sb.mode}</Badge>
                    <span className="capitalize">{sb.type}</span>
                  </div>
                </div>
              </button>
            ))}
            {filteredSandboxes.length === 0 && (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">
                {searchQuery ? 'No sandboxes match your search' : 'No sandboxes configured'}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="min-w-0 flex-1 overflow-y-auto p-4">
        {selected ? (
          <SandboxDetail onRemove={() => handleRemove(selected.id)} sandbox={selected} />
        ) : (
          <div className="grid min-h-52 place-items-center text-center">
            <div>
              <Codicon className="text-muted-foreground/40" name="container" size="2rem" />
              <div className="mt-2 text-sm font-medium text-muted-foreground">No sandbox selected</div>
              <div className="mt-1 text-xs text-muted-foreground/60">Select a sandbox or create a new one</div>
            </div>
          </div>
        )}
      </div>

      <CreateSandboxDialog
        onClose={() => setShowCreate(false)}
        onCreate={sb => {
          setSandboxes(prev => [...prev, sb])
          addSandbox(sb)
          setShowCreate(false)
          notify({ kind: 'success', title: 'Sandbox Created', message: `${sb.name} created in ${sb.mode} mode` })
        }}
        open={showCreate}
      />
    </div>
  )
}

function SandboxDetail({ sandbox, onRemove }: { sandbox: SandboxInstance; onRemove: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between rounded-xl border border-(--ui-stroke-tertiary) p-4">
        <div className="flex items-center gap-3">
          <span className={cn('mt-1 size-3 shrink-0 rounded-full', STATUS_DOT[sandbox.status])} />
          <Codicon className="text-muted-foreground" name={TYPE_ICONS[sandbox.type] || 'container'} size="1.25rem" />
          <div>
            <h3 className="text-lg font-semibold">{sandbox.name}</h3>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge className={cn('text-[0.55rem]', MODE_COLORS[sandbox.mode])} variant="muted">{sandbox.mode}</Badge>
              <span className="capitalize">{sandbox.type}</span>
              <span>{sandbox.status}</span>
              {sandbox.pid && <span className="font-mono">PID {sandbox.pid}</span>}
            </div>
          </div>
        </div>
        <Button className="text-xs text-muted-foreground hover:text-destructive" onClick={onRemove} size="sm" variant="ghost">
          <Codicon className="mr-1" name="trash" size="0.75rem" /> Destroy
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <DetailField label="Memory Limit" value={`${sandbox.memoryLimit} MB`} />
        <DetailField label="CPU Limit" value={`${sandbox.cpuLimit}%`} />
        <DetailField label="Timeout" value={`${sandbox.timeout}s`} />
      </div>

      <Section title="Filesystem">
        <div className="space-y-2">
          <DetailField label="Allowed Folders" mono value={sandbox.allowedFolders.length > 0 ? sandbox.allowedFolders.join(', ') : 'None'} />
          <DetailField label="Blocked Folders" mono value={sandbox.blockedFolders.length > 0 ? sandbox.blockedFolders.join(', ') : 'None'} />
          <DetailField label="Read-Only Folders" mono value={sandbox.readOnlyFolders.length > 0 ? sandbox.readOnlyFolders.join(', ') : 'None'} />
          <DetailField label="Temp Folder" mono value={sandbox.tempFolder} />
          {sandbox.projectWorkspace && <DetailField label="Project Workspace" mono value={sandbox.projectWorkspace} />}
        </div>
      </Section>

      <Section title="Network">
        <div className="space-y-2">
          <DetailField label="Domain Allowlist" value={sandbox.domainAllowlist.length > 0 ? sandbox.domainAllowlist.join(', ') : 'None'} />
          <DetailField label="Domain Blocklist" value={sandbox.domainBlocklist.length > 0 ? sandbox.domainBlocklist.join(', ') : 'None'} />
          {sandbox.ipRestrictions.length > 0 && <DetailField label="IP Restrictions" value={sandbox.ipRestrictions.join(', ')} />}
          {sandbox.portRestrictions.length > 0 && <DetailField label="Port Restrictions" value={sandbox.portRestrictions.join(', ')} />}
          <div className="flex items-center gap-2 text-xs">
            <span className="font-medium text-muted-foreground">Offline Mode:</span>
            <span>{sandbox.offlineMode ? 'Enabled' : 'Disabled'}</span>
          </div>
        </div>
      </Section>

      <DetailField label="Started At" value={new Date(sandbox.startedAt).toLocaleString()} />
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</h4>
      {children}
    </div>
  )
}

function DetailField({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="text-xs">
      <span className="font-medium text-muted-foreground">{label}: </span>
      <span className={mono ? 'font-mono' : ''}>{value}</span>
    </div>
  )
}

function CreateSandboxDialog({
  onCreate,
  onClose,
  open,
}: {
  onCreate: (sandbox: SandboxInstance) => void
  onClose: () => void
  open: boolean
}) {
  const [name, setName] = useState('')
  const [type, setType] = useState<string>('agent')
  const [mode, setMode] = useState<SandboxMode>('standard')
  const [memoryLimit, setMemoryLimit] = useState('1024')
  const [timeout, setTimeout] = useState('300')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {return}

    const sb: SandboxInstance = {
      id: `sb-${Date.now()}`,
      name: name.trim(),
      type: type as SandboxInstance['type'],
      mode,
      status: 'creating',
      allowedFolders: [],
      blockedFolders: [],
      readOnlyFolders: [],
      tempFolder: `/tmp/sandbox-${name.toLowerCase().replace(/\s+/g, '-')}`,
      projectWorkspace: '',
      domainAllowlist: [],
      domainBlocklist: [],
      ipRestrictions: [],
      portRestrictions: [],
      offlineMode: mode === 'read-only',
      memoryLimit: parseInt(memoryLimit) || 1024,
      cpuLimit: 50,
      timeout: parseInt(timeout) || 300,
      startedAt: new Date().toISOString(),
      pid: null,
    }

    onCreate(sb)
    setName(''); setType('agent'); setMode('standard'); setMemoryLimit('1024'); setTimeout('300')
  }

  return (
    <Dialog onOpenChange={v => !v && onClose()} open={open}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create Sandbox</DialogTitle>
          <DialogDescription>Configure an isolated execution environment</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid gap-1.5">
            <label className="text-xs font-medium" htmlFor="sb-name">Name</label>
            <Input autoFocus id="sb-name" onChange={e => setName(e.target.value)} placeholder="My Sandbox" value={name} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <label className="text-xs font-medium" htmlFor="sb-type">Type</label>
              <Select onValueChange={setType} value={type}>
                <SelectTrigger className="h-9" id="sb-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SANDBOX_TYPES.map(t => <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <label className="text-xs font-medium" htmlFor="sb-mode">Mode</label>
              <Select onValueChange={v => setMode(v as SandboxMode)} value={mode}>
                <SelectTrigger className="h-9" id="sb-mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SANDBOX_MODES.map(m => <SelectItem key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1).replace('-', ' ')}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <label className="text-xs font-medium" htmlFor="sb-memory">Memory Limit (MB)</label>
              <Input id="sb-memory" onChange={e => setMemoryLimit(e.target.value)} type="number" value={memoryLimit} />
            </div>
            <div className="grid gap-1.5">
              <label className="text-xs font-medium" htmlFor="sb-timeout">Timeout (s)</label>
              <Input id="sb-timeout" onChange={e => setTimeout(e.target.value)} type="number" value={timeout} />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={onClose} type="button" variant="outline">Cancel</Button>
            <Button disabled={!name.trim()} type="submit">Create Sandbox</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
