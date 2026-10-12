import { atom } from 'nanostores'

export interface ContactLink {
  provider: string
  accountId: string
  username: string
  displayName: string
  avatarUrl: string
  lastInteraction: string
}

export interface UnifiedContact {
  id: string
  name: string
  email: string
  phone: string
  photoUrl: string
  organization: string
  tags: string[]
  notes: string
  links: ContactLink[]
  conversationCount: number
  lastMessageAt: string
  createdAt: string
  updatedAt: string
  confidence: number
}

export interface ContactsState {
  contacts: UnifiedContact[]
  searchQuery: string
  selectedContactId: string | null
  loading: boolean
  selectedTag: string
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const initialState: ContactsState = {
  contacts: [],
  searchQuery: '',
  selectedContactId: null,
  loading: false,
  selectedTag: '',
}

export const $contacts = atom<ContactsState>(initialState)

const patch = (update: Partial<ContactsState>) =>
  $contacts.set({ ...$contacts.get(), ...update })

export function setContactSearch(query: string) { patch({ searchQuery: query }) }

export function selectContact(id: string | null) { patch({ selectedContactId: id }) }

export function setContactLoading(loading: boolean) { patch({ loading }) }

export function setSelectedTag(tag: string) { patch({ selectedTag: tag }) }

export function addContact(contact: Omit<UnifiedContact, 'id' | 'createdAt' | 'updatedAt'>) {
  const newContact: UnifiedContact = {
    ...contact,
    id: generateId(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }

  patch({ contacts: [...$contacts.get().contacts, newContact] })
}

export function updateContact(id: string, updates: Partial<UnifiedContact>) {
  const contacts = $contacts.get().contacts.map(c =>
    c.id === id ? { ...c, ...updates, updatedAt: new Date().toISOString() } : c
  )

  patch({ contacts })
}

export function removeContact(id: string) {
  patch({ contacts: $contacts.get().contacts.filter(c => c.id !== id) })
}

export function getFilteredContacts(): UnifiedContact[] {
  const state = $contacts.get()
  let result = state.contacts

  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase()
    result = result.filter(c =>
      c.name.toLowerCase().includes(q) ||
      c.email.toLowerCase().includes(q) ||
      c.phone.includes(q) ||
      c.organization.toLowerCase().includes(q) ||
      c.links.some(l => l.username.toLowerCase().includes(q) || l.displayName.toLowerCase().includes(q))
    )
  }

  if (state.selectedTag) {
    result = result.filter(c => c.tags.includes(state.selectedTag))
  }

  return result.sort((a, b) => a.name.localeCompare(b.name))
}

export function getAllTags(): string[] {
  const tags = new Set<string>()

  for (const c of $contacts.get().contacts) {
    for (const t of c.tags) {tags.add(t)}
  }

  return Array.from(tags).sort()
}

export function addLinkToContact(contactId: string, link: ContactLink) {
  const contacts = $contacts.get().contacts.map(c =>
    c.id === contactId
      ? { ...c, links: [...c.links.filter(l => !(l.provider === link.provider && l.accountId === link.accountId)), link], updatedAt: new Date().toISOString() }
      : c
  )

  patch({ contacts })
}

export function mergeContacts(targetId: string, sourceId: string) {
  const state = $contacts.get()
  const target = state.contacts.find(c => c.id === targetId)
  const source = state.contacts.find(c => c.id === sourceId)

  if (!target || !source) {return}

  const merged: UnifiedContact = {
    ...target,
    links: [...target.links, ...source.links],
    conversationCount: target.conversationCount + source.conversationCount,
    email: target.email || source.email,
    phone: target.phone || source.phone,
    photoUrl: target.photoUrl || source.photoUrl,
    tags: Array.from(new Set([...target.tags, ...source.tags])),
    notes: source.notes ? `${target.notes}\n${source.notes}`.trim() : target.notes,
    confidence: Math.min(1, target.confidence + source.confidence * 0.1),
    updatedAt: new Date().toISOString(),
  }

  patch({
    contacts: state.contacts.filter(c => c.id !== sourceId).map(c => c.id === targetId ? merged : c),
  })
}
