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
  addSecret,
  removeSecret,
  type SecretEntry,
} from '@/store/security'

const CATEGORY_ICONS: Record<string, string> = {
  'api-key': 'key',
  'password': 'lock',
  'token': 'key',
  'certificate': 'shield',
  'other': 'symbol-misc',
}

const CATEGORY_LABELS: Record<string, string> = {
  'api-key': 'API Key',
  'password': 'Password',
  'token': 'Token',
  'certificate': 'Certificate',
  'other': 'Other',
}

const SAMPLE_SECRETS: SecretEntry[] = [
  { id: 'secret-1', name: 'OpenAI API Key', category: 'api-key', provider: 'OpenAI', createdAt: '2026-01-15T00:00:00Z', lastAccessed: '2026-07-21T10:30:00Z', expiresAt: null, maskedValue: 'sk-••••••••••••••••' },
  { id: 'secret-2', name: 'GitHub Personal Access Token', category: 'token', provider: 'GitHub', createdAt: '2026-03-01T00:00:00Z', lastAccessed: '2026-07-21T09:15:00Z', expiresAt: null, maskedValue: 'ghp_••••••••••••••••' },
  { id: 'secret-3', name: 'GitHub OAuth Token', category: 'token', provider: 'GitHub', createdAt: '2026-06-01T00:00:00Z', lastAccessed: '2026-07-20T18:00:00Z', expiresAt: null, maskedValue: 'gho_••••••••••••••••' },
  { id: 'secret-4', name: 'Anthropic API Key', category: 'api-key', provider: 'Anthropic', createdAt: '2026-02-10T00:00:00Z', lastAccessed: '2026-07-21T08:00:00Z', expiresAt: null, maskedValue: 'sk-ant-••••••••••••' },
  { id: 'secret-5', name: 'PostgreSQL Password', category: 'password', provider: 'Local Database', createdAt: '2026-04-01T00:00:00Z', lastAccessed: '2026-07-19T14:30:00Z', expiresAt: null, maskedValue: '••••••••••' },
  { id: 'secret-6', name: 'Docker Hub Token', category: 'token', provider: 'Docker', createdAt: '2026-05-15T00:00:00Z', lastAccessed: null, expiresAt: '2026-08-15T00:00:00Z', maskedValue: 'dckr_••••••••••••' },
  { id: 'secret-7', name: 'Google Cloud Service Account', category: 'certificate', provider: 'Google Cloud', createdAt: '2026-01-01T00:00:00Z', lastAccessed: '2026-07-18T12:00:00Z', expiresAt: '2027-01-01T00:00:00Z', maskedValue: '••••••••••••••••' },
  { id: 'secret-8', name: 'Slack Bot Token', category: 'token', provider: 'Slack', createdAt: '2026-06-20T00:00:00Z', lastAccessed: '2026-07-21T11:00:00Z', expiresAt: null, maskedValue: 'xoxb-••••••••••••••' },
]

export function SecretsManager() {
  const [secrets, setSecrets] = useState<SecretEntry[]>(SAMPLE_SECRETS)
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [selectedSecret, setSelectedSecret] = useState<SecretEntry | null>(null)
  const [showAddDialog, setShowAddDialog] = useState(false)

  const filteredSecrets = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()

    return secrets.filter(s => {
      if (q && !s.name.toLowerCase().includes(q) && !s.provider.toLowerCase().includes(q)) {return false}

      if (categoryFilter !== 'all' && s.category !== categoryFilter) {return false}

      return true
    })
  }, [secrets, searchQuery, categoryFilter])

  const handleRemove = (id: string) => {
    setSecrets(prev => prev.filter(s => s.id !== id))
    removeSecret(id)

    if (selectedSecret?.id === id) {setSelectedSecret(null)}
    notify({ kind: 'success', title: 'Secret Removed', message: 'Secret has been deleted from the vault' })
  }

  const handleReveal = (secret: SecretEntry) => {
    notify({ kind: 'info', title: 'Secret Accessed', message: `Audit log: ${secret.name} was accessed` })
  }

  return (
    <div className="flex h-full">
      <div className="w-72 shrink-0 border-r border-(--ui-stroke-tertiary) p-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Secrets Vault</span>
            <Button className="text-xs" onClick={() => setShowAddDialog(true)} size="sm">
              <Codicon className="mr-1" name="plus" size="0.75rem" /> Add
            </Button>
          </div>
          <SearchField
            containerClassName="w-full"
            onChange={setSearchQuery}
            placeholder="Search secrets..."
            value={searchQuery}
          />
          <Select onValueChange={v => setCategoryFilter(v)} value={categoryFilter}>
            <SelectTrigger className="h-7 w-full text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="api-key">API Keys</SelectItem>
              <SelectItem value="password">Passwords</SelectItem>
              <SelectItem value="token">Tokens</SelectItem>
              <SelectItem value="certificate">Certificates</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
          <div className="space-y-0.5">
            {filteredSecrets.map(secret => (
              <button
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors',
                  selectedSecret?.id === secret.id ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
                )}
                key={secret.id}
                onClick={() => setSelectedSecret(secret)}
                type="button"
              >
                <Codicon className="shrink-0 text-muted-foreground" name={CATEGORY_ICONS[secret.category]} size="0.875rem" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{secret.name}</div>
                  <div className="flex items-center gap-1.5 text-[0.6rem] text-muted-foreground">
                    <span>{secret.provider}</span>
                    <span>&middot;</span>
                    <Badge className="text-[0.5rem]" variant="outline">{CATEGORY_LABELS[secret.category]}</Badge>
                  </div>
                </div>
              </button>
            ))}
            {filteredSecrets.length === 0 && (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">
                {searchQuery ? 'No secrets match your search' : 'No secrets stored'}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="min-w-0 flex-1 overflow-y-auto p-4">
        {selectedSecret ? (
          <div className="space-y-4">
            <div className="flex items-start justify-between rounded-xl border border-(--ui-stroke-tertiary) p-4">
              <div className="flex items-center gap-3">
                <Codicon className="text-muted-foreground" name={CATEGORY_ICONS[selectedSecret.category]} size="1.25rem" />
                <div>
                  <h3 className="text-lg font-semibold">{selectedSecret.name}</h3>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline">{CATEGORY_LABELS[selectedSecret.category]}</Badge>
                    <span>{selectedSecret.provider}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <Button className="text-xs" onClick={() => handleReveal(selectedSecret)} size="sm" variant="outline">
                  <Codicon className="mr-1" name="eye" size="0.75rem" /> Reveal
                </Button>
                <Button className="text-xs text-muted-foreground hover:text-destructive" onClick={() => handleRemove(selectedSecret.id)} size="sm" variant="ghost">
                  <Codicon name="trash" size="0.875rem" />
                </Button>
              </div>
            </div>

            <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
              <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">Value</div>
              <div className="mt-1 font-mono text-sm tracking-widest">{selectedSecret.maskedValue}</div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
                <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">Created</div>
                <div className="mt-0.5 text-sm">{new Date(selectedSecret.createdAt).toLocaleDateString()}</div>
              </div>
              <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
                <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">Last Accessed</div>
                <div className="mt-0.5 text-sm">{selectedSecret.lastAccessed ? new Date(selectedSecret.lastAccessed).toLocaleString() : 'Never'}</div>
              </div>
            </div>

            {selectedSecret.expiresAt && (
              <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
                <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">Expires</div>
                <div className="mt-0.5 text-sm">{new Date(selectedSecret.expiresAt).toLocaleDateString()}</div>
              </div>
            )}
          </div>
        ) : (
          <div className="grid min-h-52 place-items-center text-center">
            <div>
              <Codicon className="text-muted-foreground/40" name="key" size="2rem" />
              <div className="mt-2 text-sm font-medium text-muted-foreground">Select a secret</div>
              <div className="mt-1 text-xs text-muted-foreground/60">Choose a secret to view details</div>
            </div>
          </div>
        )}
      </div>

      <AddSecretDialog
        onAdd={secret => {
          setSecrets(prev => [...prev, secret])
          addSecret(secret)
          setShowAddDialog(false)
          notify({ kind: 'success', title: 'Secret Added', message: `${secret.name} has been stored securely` })
        }}
        onClose={() => setShowAddDialog(false)}
        open={showAddDialog}
      />
    </div>
  )
}

function AddSecretDialog({
  onAdd,
  onClose,
  open,
}: {
  onAdd: (secret: SecretEntry) => void
  onClose: () => void
  open: boolean
}) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState<string>('api-key')
  const [provider, setProvider] = useState('')
  const [value, setValue] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim() || !value.trim()) {return}

    const secret: SecretEntry = {
      id: `secret-${Date.now()}`,
      name: name.trim(),
      category: category as SecretEntry['category'],
      provider: provider.trim() || 'Custom',
      createdAt: new Date().toISOString(),
      lastAccessed: null,
      expiresAt: null,
      maskedValue: value.trim().slice(0, 4) + '••••••••••••',
    }

    onAdd(secret)
    setName(''); setCategory('api-key'); setProvider(''); setValue('')
  }

  return (
    <Dialog onOpenChange={v => !v && onClose()} open={open}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Secret</DialogTitle>
          <DialogDescription>Store a new credential securely in the vault</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid gap-1.5">
            <label className="text-xs font-medium" htmlFor="sec-name">Secret Name</label>
            <Input autoFocus id="sec-name" onChange={e => setName(e.target.value)} placeholder="My API Key" value={name} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <label className="text-xs font-medium" htmlFor="sec-category">Category</label>
              <Select onValueChange={setCategory} value={category}>
                <SelectTrigger className="h-9" id="sec-category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="api-key">API Key</SelectItem>
                  <SelectItem value="password">Password</SelectItem>
                  <SelectItem value="token">Token</SelectItem>
                  <SelectItem value="certificate">Certificate</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <label className="text-xs font-medium" htmlFor="sec-provider">Provider</label>
              <Input id="sec-provider" onChange={e => setProvider(e.target.value)} placeholder="OpenAI, GitHub..." value={provider} />
            </div>
          </div>
          <div className="grid gap-1.5">
            <label className="text-xs font-medium" htmlFor="sec-value">Secret Value</label>
            <Input id="sec-value" onChange={e => setValue(e.target.value)} placeholder="Enter secret value" type="password" value={value} />
          </div>
          <DialogFooter>
            <Button onClick={onClose} type="button" variant="outline">Cancel</Button>
            <Button disabled={!name.trim() || !value.trim()} type="submit">Add Secret</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
