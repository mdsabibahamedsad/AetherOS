import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { $contacts, addContact, getAllTags, getFilteredContacts, removeContact, selectContact, setContactSearch, setSelectedTag } from '@/store/communications-contacts'
import type { UnifiedContact } from '@/store/communications-contacts'

const PLATFORM_ICONS: Record<string, string> = {
  telegram: 'send', whatsapp: 'message-circle', discord: 'message-circle',
  slack: 'message-square-text', gmail: 'mail', sms: 'message-square-text',
}

interface ContactsViewProps {
  onSelectConversation: (conversationId: string) => void
}

export function ContactsView({ onSelectConversation }: ContactsViewProps) {
  const contacts = useStore($contacts)
  const filtered = getFilteredContacts()
  const tags = getAllTags()
  const [showAdd, setShowAdd] = useState(false)
  const [newName, setNewName] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [newPhone, setNewPhone] = useState('')
  const [mergeTarget, setMergeTarget] = useState<string | null>(null)

  const handleAdd = () => {
    if (!newName.trim()) {return}
    addContact({
      name: newName.trim(), email: newEmail, phone: newPhone,
      photoUrl: '', organization: '', tags: [], notes: '',
      links: [], conversationCount: 0, lastMessageAt: '', confidence: 1,
    })
    setNewName(''); setNewEmail(''); setNewPhone('')
    setShowAdd(false)
  }

  return (
    <div className="flex h-full">
      {/* Contact List */}
      <div className="flex w-72 shrink-0 flex-col border-r border-(--ui-stroke-tertiary)">
        <div className="shrink-0 space-y-2 border-b border-(--ui-stroke-tertiary) p-3">
          <div className="relative">
            <span className="codicon codicon-search absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-(--ui-text-tertiary)" />
            <input
              className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) pl-7 pr-3 text-xs outline-none focus:border-primary" onChange={e => setContactSearch(e.target.value)}
              placeholder="Search contacts..."
              type="text"
              value={contacts.searchQuery}
            />
          </div>
          <div className="flex flex-wrap gap-1">
            <button
              className={`rounded-md px-2 py-0.5 text-[10px] ${!contacts.selectedTag ? 'bg-primary text-white' : 'bg-(--ui-bg-quaternary) text-(--ui-text-tertiary)'}`}
              onClick={() => setSelectedTag('')}
            >
              All
            </button>
            {tags.map(tag => (
              <button
                className={`rounded-md px-2 py-0.5 text-[10px] ${contacts.selectedTag === tag ? 'bg-primary text-white' : 'bg-(--ui-bg-quaternary) text-(--ui-text-tertiary)'}`}
                key={tag}
                onClick={() => setSelectedTag(tag)}
              >
                {tag}
              </button>
            ))}
          </div>
          <button
            className="flex w-full items-center justify-center gap-1 rounded-md border border-dashed border-(--ui-stroke-tertiary) px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:text-foreground"
            onClick={() => setShowAdd(!showAdd)}
          >
            <span className="codicon codicon-add" />
            Add Contact
          </button>
          {showAdd && (
            <div className="space-y-1.5 rounded-md border border-(--ui-stroke-tertiary) p-2">
              <input className="h-7 w-full rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setNewName(e.target.value)} placeholder="Name" type="text" value={newName} />
              <input className="h-7 w-full rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setNewEmail(e.target.value)} placeholder="Email" type="email" value={newEmail} />
              <input className="h-7 w-full rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setNewPhone(e.target.value)} placeholder="Phone" type="tel" value={newPhone} />
              <button className="h-7 w-full rounded-md bg-primary text-xs text-white" onClick={handleAdd}>Save</button>
            </div>
          )}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {filtered.map(c => (
            <div
              className={`flex cursor-pointer items-center gap-3 px-3 py-2 transition-colors hover:bg-(--ui-row-hover-background) ${contacts.selectedContactId === c.id ? 'bg-(--ui-row-active-background)' : ''}`}
              key={c.id}
              onClick={() => selectContact(c.id)}
            >
              <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-(--ui-bg-quaternary) text-xs font-medium">
                {c.photoUrl ? <img className="size-8 rounded-full object-cover" src={c.photoUrl} /> : c.name[0]?.toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium">{c.name}</div>
                <div className="truncate text-[10px] text-(--ui-text-tertiary)">
                  {c.email || c.phone || c.links.map(l => l.displayName || l.username).join(', ')}
                </div>
                {c.links.length > 0 && (
                  <div className="mt-0.5 flex gap-1">
                    {c.links.map((l, i) => (
                      <span className={`codicon codicon-${PLATFORM_ICONS[l.provider] || 'comment-discussion'} text-[10px] text-(--ui-text-tertiary)`} key={i} title={l.provider} />
                    ))}
                  </div>
                )}
              </div>
              {c.tags.length > 0 && (
                <div className="flex shrink-0 gap-0.5">
                  {c.tags.slice(0, 2).map(t => (
                    <span className="rounded bg-(--ui-bg-quaternary) px-1 py-0.5 text-[10px] text-(--ui-text-tertiary)" key={t}>{t}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Contact Detail */}
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {contacts.selectedContactId ? <ContactDetail contact={contacts.contacts.find(c => c.id === contacts.selectedContactId)!} /> : (
          <div className="flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)">
            Select a contact to view details
          </div>
        )}
      </div>
    </div>
  )
}

function ContactDetail({ contact }: { contact: UnifiedContact }) {
  return (
    <div className="max-w-lg space-y-4">
      <div className="flex items-center gap-4">
        <div className="flex size-12 items-center justify-center rounded-full bg-(--ui-bg-quaternary) text-lg font-medium">
          {contact.photoUrl ? <img className="size-12 rounded-full object-cover" src={contact.photoUrl} /> : contact.name[0]?.toUpperCase()}
        </div>
        <div>
          <h2 className="text-sm font-semibold">{contact.name}</h2>
          <p className="text-xs text-(--ui-text-tertiary)">{contact.organization}</p>
        </div>
      </div>

      <div className="space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
        <h3 className="text-xs font-medium">Contact Information</h3>
        {contact.email && <div className="flex items-center gap-2 text-xs"><span className="codicon codicon-mail text-(--ui-text-tertiary)" />{contact.email}</div>}
        {contact.phone && <div className="flex items-center gap-2 text-xs"><span className="codicon codicon-call text-(--ui-text-tertiary)" />{contact.phone}</div>}
        <div className="text-xs text-(--ui-text-tertiary)">{contact.conversationCount} conversations</div>
      </div>

      {contact.links.length > 0 && (
        <div className="space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
          <h3 className="text-xs font-medium">Connected Accounts</h3>
          {contact.links.map((l, i) => (
            <div className="flex items-center gap-2 text-xs" key={i}>
              <span className={`codicon codicon-${PLATFORM_ICONS[l.provider] || 'comment-discussion'} text-(--ui-text-tertiary)`} />
              <span>{l.displayName || l.username}</span>
              <span className="text-(--ui-text-tertiary)">({l.provider})</span>
            </div>
          ))}
        </div>
      )}

      {contact.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {contact.tags.map(t => (
            <span className="rounded-md bg-(--ui-bg-quaternary) px-2 py-0.5 text-[10px]" key={t}>{t}</span>
          ))}
        </div>
      )}

      {contact.notes && (
        <div className="rounded-lg border border-(--ui-stroke-tertiary) p-3">
          <h3 className="text-xs font-medium">Notes</h3>
          <p className="mt-1 text-xs text-(--ui-text-tertiary)">{contact.notes}</p>
        </div>
      )}

      <div className="flex gap-2">
        <button className="flex items-center gap-1 rounded-md px-3 py-1.5 text-xs text-red-500 hover:bg-red-500/10" onClick={() => removeContact(contact.id)}>
          <span className="codicon codicon-trash" />
          Remove
        </button>
      </div>
    </div>
  )
}
