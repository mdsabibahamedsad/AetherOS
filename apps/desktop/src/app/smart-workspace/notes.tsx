import { useStore } from '@nanostores/react'
import {
  IconDots,
  IconFolder,
  IconPin,
  IconPinFilled,
  IconPlus,
  IconSparkles,
  IconSticker,
  IconTag,
  IconTrash,
  IconX
} from '@tabler/icons-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  $smartWorkspace,
  addWorkspaceItem,
  removeWorkspaceItem,
  togglePinItem,
  updateWorkspaceItem,
  type WorkspaceItem
} from '@/store/smart-workspace'

let _nextNoteId = 1
const genNoteId = () => `note-${Date.now()}-${_nextNoteId++}`

const DEFAULT_TAGS = ['work', 'personal', 'ideas', 'todo', 'reference'] as const

const NOTEBOOKS = ['General', 'Work', 'Personal', 'Research', 'Archive'] as const

const EMPTY_NOTE: WorkspaceItem = {
  id: genNoteId(),
  type: 'notes',
  title: '',
  content: '',
  createdAt: Date.now(),
  updatedAt: Date.now(),
  tags: [],
  pinned: false,
  metadata: {}
}

export function Notes() {
  const state = useStore($smartWorkspace)
  const notes = state.items.filter(i => i.type === 'notes')
  const [selectedNote, setSelectedNote] = useState<string | null>(null)
  const [editingNote, setEditingNote] = useState<WorkspaceItem | null>(null)
  const [filterTag, setFilterTag] = useState<string | null>(null)
  const [filterNotebook, setFilterNotebook] = useState<string | null>(null)
  const [showNewForm, setShowNewForm] = useState(false)
  const searchQuery = state.searchQuery.toLowerCase()

  const filtered = notes.filter(n => {
    if (filterTag && !n.tags.includes(filterTag)) {return false}

    if (searchQuery && !n.title.toLowerCase().includes(searchQuery) && !n.content.toLowerCase().includes(searchQuery)) {return false}

    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    if (a.pinned !== b.pinned) {return a.pinned ? -1 : 1}

    return b.updatedAt - a.updatedAt
  })

  const allTags = [...new Set(notes.flatMap(n => n.tags))].sort()

  const activeNote = selectedNote ? notes.find(n => n.id === selectedNote) : null

  const handleCreate = () => {
    const note: WorkspaceItem = {
      ...EMPTY_NOTE,
      id: genNoteId(),
      title: 'Untitled Note',
      createdAt: Date.now(),
      updatedAt: Date.now()
    }

    addWorkspaceItem(note)
    setSelectedNote(note.id)
    setEditingNote(note)
    setShowNewForm(false)
  }

  const handleSaveEdit = () => {
    if (!editingNote) {return}
    updateWorkspaceItem(editingNote.id, {
      title: editingNote.title,
      content: editingNote.content,
      tags: editingNote.tags,
      updatedAt: Date.now()
    })
    setEditingNote(null)
  }

  const handleDelete = (id: string) => {
    removeWorkspaceItem(id)

    if (selectedNote === id) {
      setSelectedNote(null)
      setEditingNote(null)
    }
  }

  const renderNoteCard = (note: WorkspaceItem) => (
    <button
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left transition-all hover:border-(--dt-ring) hover:shadow-sm',
        selectedNote === note.id && 'border-primary/40 bg-accent/30'
      )}
      key={note.id}
      onClick={() => {
        setSelectedNote(note.id)
        setEditingNote({ ...note })
      }}
      type="button"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="flex-1 truncate text-sm font-medium text-foreground">
          {note.pinned && <IconPinFilled className="mr-1 inline size-3 text-primary" />}
          {note.title || 'Untitled'}
        </h3>
        <IconDots className="mt-0.5 size-3 shrink-0 opacity-0 text-muted-foreground group-hover:opacity-100" />
      </div>
      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
        {note.content || 'No content'}
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-1">
        {note.tags.map(tag => (
          <span
            className="inline-flex items-center rounded-full bg-primary/8 px-1.5 py-0.5 text-[0.625rem] text-primary"
            key={tag}
          >
            {tag}
          </span>
        ))}
      </div>
      <div className="mt-1.5 text-[0.625rem] text-muted-foreground/60">
        {new Date(note.updatedAt).toLocaleDateString()}
      </div>
    </button>
  )

  const renderNoteRow = (note: WorkspaceItem) => (
    <div
      className={cn(
        'flex items-center gap-3 rounded-md px-3 py-2 transition-colors hover:bg-accent/50',
        selectedNote === note.id && 'bg-accent'
      )}
      key={note.id}
    >
      <Button
        onClick={() => togglePinItem(note.id)}
        size="icon-xs"
        title={note.pinned ? 'Unpin' : 'Pin'}
        variant="ghost"
      >
        {note.pinned ? <IconPinFilled className="size-3 text-primary" /> : <IconPin className="size-3 text-muted-foreground" />}
      </Button>
      <button
        className="flex min-w-0 flex-1 items-center gap-3"
        onClick={() => {
          setSelectedNote(note.id)
          setEditingNote({ ...note })
        }}
        type="button"
      >
        <IconSticker className="size-4 shrink-0 text-muted-foreground" />
        <span className="truncate text-sm text-foreground">{note.title || 'Untitled'}</span>
        <div className="flex flex-wrap gap-1">
          {note.tags.slice(0, 2).map(tag => (
            <span
              className="inline-flex items-center rounded-full bg-primary/8 px-1.5 py-0.5 text-[0.625rem] text-primary"
              key={tag}
            >
              {tag}
            </span>
          ))}
        </div>
        <span className="ml-auto shrink-0 text-xs text-muted-foreground/60">
          {new Date(note.updatedAt).toLocaleDateString()}
        </span>
      </button>
      <Button onClick={() => handleDelete(note.id)} size="icon-xs" title="Delete" variant="ghost">
        <IconTrash className="size-3 text-muted-foreground hover:text-destructive" />
      </Button>
    </div>
  )

  const renderTimelineItem = (note: WorkspaceItem) => {
    const dateKey = new Date(note.updatedAt).toLocaleDateString()

    return (
      <div className="relative pl-6 pb-4" key={note.id}>
        <div className="absolute left-2 top-1.5 h-2 w-2 rounded-full bg-primary/40" />
        <div className="absolute bottom-0 left-[11px] top-4 w-px bg-(--ui-stroke-tertiary)" />
        <button
          className="block w-full rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left transition-colors hover:bg-accent/50"
          onClick={() => {
            setSelectedNote(note.id)
            setEditingNote({ ...note })
          }}
          type="button"
        >
          <div className="flex items-center gap-2">
            {note.pinned && <IconPinFilled className="size-3 text-primary" />}
            <h4 className="text-sm font-medium text-foreground">{note.title || 'Untitled'}</h4>
            {note.tags.map(tag => (
              <span className="rounded-full bg-primary/8 px-1.5 py-0.5 text-[0.625rem] text-primary" key={tag}>
                {tag}
              </span>
            ))}
          </div>
        </button>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      <div className="flex w-56 shrink-0 flex-col border-r border-(--ui-stroke-tertiary) bg-(--ui-bg-secondary)">
        <div className="p-3">
          <Button className="w-full" onClick={handleCreate} size="sm">
            <IconPlus className="size-3.5" />
            New Note
          </Button>
        </div>
        <div className="px-3 pb-2">
          <button
            className={cn(
              'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors',
              !filterNotebook ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
            )}
            onClick={() => setFilterNotebook(null)}
            type="button"
          >
            <IconFolder className="size-3.5" />
            All Notes
            <span className="ml-auto text-muted-foreground/60">{notes.length}</span>
          </button>
          {NOTEBOOKS.map(nb => (
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors',
                filterNotebook === nb ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
              )}
              key={nb}
              onClick={() => setFilterNotebook(filterNotebook === nb ? null : nb)}
              type="button"
            >
              <IconFolder className="size-3.5" />
              {nb}
            </button>
          ))}
        </div>
        <div className="border-t border-(--ui-stroke-tertiary) px-3 py-2">
          <h4 className="mb-1.5 text-[0.625rem] font-medium uppercase tracking-wider text-muted-foreground">Tags</h4>
          <div className="flex flex-wrap gap-1">
            {allTags.map(tag => (
              <button
                className={cn(
                  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[0.625rem] transition-colors',
                  filterTag === tag
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-primary/8 text-primary hover:bg-primary/15'
                )}
                key={tag}
                onClick={() => setFilterTag(filterTag === tag ? null : tag)}
                type="button"
              >
                <IconTag className="size-2.5" />
                {tag}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-auto border-t border-(--ui-stroke-tertiary) p-3">
          <Button className="w-full" onClick={() => {}} size="xs" variant="outline">
            <IconSparkles className="mr-1 size-3" />
            AI Organize
          </Button>
        </div>
      </div>

      <div className="flex flex-1 flex-col">
        <div className="flex-1 overflow-y-auto p-3">
          {sorted.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <IconSticker className="mx-auto mb-2 size-8 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">
                  {searchQuery ? 'No notes match your search' : 'No notes yet'}
                </p>
                <Button className="mt-3" onClick={handleCreate} size="sm">
                  <IconPlus className="size-3.5" />
                  Create your first note
                </Button>
              </div>
            </div>
          ) : (
            <div
              className={cn(
                state.notesView === 'grid' && 'grid gap-3 sm:grid-cols-2 lg:grid-cols-3',
                state.notesView === 'list' && 'space-y-0.5',
                state.notesView === 'timeline' && 'space-y-0'
              )}
            >
              {sorted.map(note =>
                state.notesView === 'list'
                  ? renderNoteRow(note)
                  : state.notesView === 'timeline'
                    ? renderTimelineItem(note)
                    : renderNoteCard(note)
              )}
            </div>
          )}
        </div>
      </div>

      {editingNote && (
        <div className="flex w-80 shrink-0 flex-col border-l border-(--ui-stroke-tertiary) bg-(--ui-bg-secondary)">
          <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-3 py-2">
            <span className="text-xs font-medium text-foreground">Edit Note</span>
            <div className="flex items-center gap-1">
              <Button onClick={() => togglePinItem(editingNote.id)} size="icon-xs" title="Pin" variant="ghost">
                {editingNote.pinned ? <IconPinFilled className="size-3 text-primary" /> : <IconPin className="size-3" />}
              </Button>
              <Button onClick={() => setEditingNote(null)} size="icon-xs" title="Close" variant="ghost">
                <IconX className="size-3" />
              </Button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            <input
              className="mb-2 w-full bg-transparent text-sm font-medium text-foreground outline-none"
              onChange={e => setEditingNote(prev => prev ? { ...prev, title: e.target.value } : null)}
              placeholder="Note title"
              value={editingNote.title}
            />
            <textarea
              className="min-h-[200px] w-full resize-none bg-transparent text-xs leading-relaxed text-foreground outline-none placeholder:text-muted-foreground/40"
              onChange={e => setEditingNote(prev => prev ? { ...prev, content: e.target.value } : null)}
              placeholder="Start writing..."
              value={editingNote.content}
            />
            <div className="mt-3">
              <h4 className="mb-1 text-[0.625rem] font-medium uppercase tracking-wider text-muted-foreground">
                Tags
              </h4>
              <div className="flex flex-wrap gap-1">
                {DEFAULT_TAGS.map(tag => {
                  const hasTag = editingNote.tags.includes(tag)

                  return (
                    <button
                      className={cn(
                        'rounded-full px-2 py-0.5 text-[0.625rem] transition-colors',
                        hasTag
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-primary/8 text-primary hover:bg-primary/15'
                      )}
                      key={tag}
                      onClick={() =>
                        setEditingNote(prev =>
                          prev
                            ? {
                                ...prev,
                                tags: hasTag
                                  ? prev.tags.filter(t => t !== tag)
                                  : [...prev.tags, tag]
                              }
                            : null
                        )
                      }
                      type="button"
                    >
                      {tag}
                    </button>
                  )
                })}
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <Button className="flex-1" onClick={handleSaveEdit} size="sm">
                Save
              </Button>
              <Button onClick={() => handleDelete(editingNote.id)} size="icon-sm" variant="ghost">
                <IconTrash className="size-3.5" />
              </Button>
              <Button onClick={() => {}} size="icon-sm" variant="ghost">
                <IconSparkles className="size-3.5 text-primary" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
