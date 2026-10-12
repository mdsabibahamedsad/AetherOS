import { beforeEach, describe, expect, it } from 'vitest'

import {
  $contacts, addContact, addLinkToContact, getAllTags, getFilteredContacts,
  mergeContacts, removeContact, selectContact, setContactSearch,
  setSelectedTag,
  updateContact,
} from './communications-contacts'

describe('communications-contacts store', () => {
  beforeEach(() => {
    $contacts.set({
      contacts: [],
      searchQuery: '',
      selectedContactId: null,
      loading: false,
      selectedTag: '',
    })
  })

  it('adds a contact', () => {
    addContact({ name: 'John Doe', email: 'john@example.com', phone: '+123', photoUrl: '', organization: 'Acme', tags: ['work'], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    expect($contacts.get().contacts).toHaveLength(1)
    expect($contacts.get().contacts[0].name).toBe('John Doe')
  })

  it('updates a contact', () => {
    addContact({ name: 'Jane', email: '', phone: '', photoUrl: '', organization: '', tags: [], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    const id = $contacts.get().contacts[0].id
    updateContact(id, { email: 'jane@test.com' })
    expect($contacts.get().contacts[0].email).toBe('jane@test.com')
  })

  it('removes a contact', () => {
    addContact({ name: 'Test', email: '', phone: '', photoUrl: '', organization: '', tags: [], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    const id = $contacts.get().contacts[0].id
    removeContact(id)
    expect($contacts.get().contacts).toHaveLength(0)
  })

  it('selects a contact', () => {
    addContact({ name: 'Select Me', email: '', phone: '', photoUrl: '', organization: '', tags: [], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    const id = $contacts.get().contacts[0].id
    selectContact(id)
    expect($contacts.get().selectedContactId).toBe(id)
  })

  it('filters contacts by search', () => {
    addContact({ name: 'Alice', email: 'alice@a.com', phone: '', photoUrl: '', organization: '', tags: [], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    addContact({ name: 'Bob', email: 'bob@b.com', phone: '', photoUrl: '', organization: '', tags: [], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    setContactSearch('alice')
    const filtered = getFilteredContacts()
    expect(filtered).toHaveLength(1)
    expect(filtered[0].name).toBe('Alice')
  })

  it('filters contacts by tag', () => {
    addContact({ name: 'Work Contact', email: '', phone: '', photoUrl: '', organization: '', tags: ['work'], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    addContact({ name: 'Personal', email: '', phone: '', photoUrl: '', organization: '', tags: ['personal'], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    setSelectedTag('work')
    const filtered = getFilteredContacts()
    expect(filtered).toHaveLength(1)
    expect(filtered[0].name).toBe('Work Contact')
  })

  it('gets all tags', () => {
    addContact({ name: 'A', email: '', phone: '', photoUrl: '', organization: '', tags: ['work', 'important'], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    addContact({ name: 'B', email: '', phone: '', photoUrl: '', organization: '', tags: ['personal'], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    const tags = getAllTags()
    expect(tags.sort()).toEqual(['important', 'personal', 'work'])
  })

  it('adds a link to a contact', () => {
    addContact({ name: 'Multi', email: '', phone: '', photoUrl: '', organization: '', tags: [], notes: '', links: [], conversationCount: 0, lastMessageAt: '', confidence: 1 })
    const id = $contacts.get().contacts[0].id
    addLinkToContact(id, { provider: 'telegram', accountId: 'tg_1', username: '@multi', displayName: 'Multi TG', avatarUrl: '', lastInteraction: '' })
    expect($contacts.get().contacts[0].links).toHaveLength(1)
    expect($contacts.get().contacts[0].links[0].provider).toBe('telegram')
  })

  it('merges two contacts', () => {
    addContact({ name: 'Primary', email: 'p@test.com', phone: '', photoUrl: '', organization: '', tags: ['work'], notes: 'primary notes', links: [{ provider: 'telegram', accountId: 'tg1', username: '@p', displayName: 'P TG', avatarUrl: '', lastInteraction: '' }], conversationCount: 5, lastMessageAt: '', confidence: 1 })
    addContact({ name: 'Secondary', email: '', phone: '+999', photoUrl: '', organization: '', tags: ['friend'], notes: 'secondary notes', links: [{ provider: 'slack', accountId: 'sl1', username: '@s', displayName: 'S Slack', avatarUrl: '', lastInteraction: '' }], conversationCount: 3, lastMessageAt: '', confidence: 1 })
    const primaryId = $contacts.get().contacts[0].id
    const secondaryId = $contacts.get().contacts[1].id
    mergeContacts(primaryId, secondaryId)
    expect($contacts.get().contacts).toHaveLength(1)
    const merged = $contacts.get().contacts[0]
    expect(merged.name).toBe('Primary')
    expect(merged.email).toBe('p@test.com')
    expect(merged.phone).toBe('+999')
    expect(merged.tags.sort()).toEqual(['friend', 'work'])
    expect(merged.links).toHaveLength(2)
    expect(merged.conversationCount).toBe(8)
    expect(merged.confidence).toBe(1)
  })
})
