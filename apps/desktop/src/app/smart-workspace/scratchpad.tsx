import { useStore } from '@nanostores/react'
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconBold,
  IconCode,
  IconEye,
  IconEyeOff,
  IconHeading,
  IconHistory,
  IconItalic,
  IconList,
  IconListNumbers,
  IconQuote,
  IconSend,
  IconSparkles,
  IconStrikethrough
} from '@tabler/icons-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  $smartWorkspace,
  restoreScratchpadSnapshot,
  saveScratchpadSnapshot,
  setScratchpadContent
} from '@/store/smart-workspace'

function renderMarkdown(text: string): string {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  const lines = escaped.split('\n')

  const html = lines
    .map(line => {
      if (line.startsWith('### ')) {return `<h3>${line.slice(4)}</h3>`}

      if (line.startsWith('## ')) {return `<h2>${line.slice(3)}</h2>`}

      if (line.startsWith('# ')) {return `<h1>${line.slice(2)}</h1>`}

      if (line.startsWith('> ')) {return `<blockquote>${line.slice(2)}</blockquote>`}

      if (line.startsWith('- ')) {return `<li>${line.slice(2)}</li>`}

      if (line.startsWith('* ')) {return `<li>${line.slice(2)}</li>`}

      let processed = line
        .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/~~(.+?)~~/g, '<del>$1</del>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>')

      return processed || '<br>'
    })
    .join('\n')

  return `<div class="prose">${html}</div>`
}

const AI_ACTIONS = [
  { id: 'summarize', label: 'Summarize' },
  { id: 'expand', label: 'Expand' },
  { id: 'rewrite', label: 'Rewrite' },
  { id: 'translate', label: 'Translate' }
]

const TOOLBAR_ITEMS = [
  { icon: IconBold, label: 'Bold', prefix: '**', suffix: '**' },
  { icon: IconItalic, label: 'Italic', prefix: '*', suffix: '*' },
  { icon: IconStrikethrough, label: 'Strikethrough', prefix: '~~', suffix: '~~' },
  { icon: IconHeading, label: 'Heading', prefix: '## ', suffix: '' },
  { icon: IconList, label: 'Bullet list', prefix: '- ', suffix: '' },
  { icon: IconListNumbers, label: 'Numbered list', prefix: '1. ', suffix: '' },
  { icon: IconQuote, label: 'Quote', prefix: '> ', suffix: '' },
  { icon: IconCode, label: 'Code', prefix: '`', suffix: '`' }
]

export function Scratchpad() {
  const state = useStore($smartWorkspace)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [slashOpen, setSlashOpen] = useState(false)
  const [cursorPos, setCursorPos] = useState(0)
  const [undoStack, setUndoStack] = useState<string[]>([])
  const [redoStack, setRedoStack] = useState<string[]>([])
  const autoSaveTimer = useRef<number | undefined>(undefined)

  const previewHtml = useMemo(() => renderMarkdown(state.scratchpadContent), [state.scratchpadContent])

  const pushUndo = useCallback((content: string) => {
    setUndoStack(prev => [...prev.slice(-49), content])
    setRedoStack([])
  }, [])

  const handleChange = useCallback(
    (value: string) => {
      pushUndo(state.scratchpadContent)
      setScratchpadContent(value)

      if (autoSaveTimer.current) {window.clearTimeout(autoSaveTimer.current)}
      autoSaveTimer.current = window.setTimeout(() => {
        saveScratchpadSnapshot()
      }, 2000)

      const textarea = textareaRef.current

      if (textarea) {
        const pos = textarea.selectionStart
        setCursorPos(pos)
        const beforeCursor = value.slice(0, pos)

        if (beforeCursor.endsWith('/')) {
          setSlashOpen(true)
        } else if (!beforeCursor.endsWith('/') && slashOpen) {
          setSlashOpen(false)
        }
      }
    },
    [state.scratchpadContent, pushUndo, slashOpen]
  )

  useEffect(() => {
    return () => {
      if (autoSaveTimer.current) {window.clearTimeout(autoSaveTimer.current)}
    }
  }, [])

  const applyFormat = useCallback(
    (prefix: string, suffix: string) => {
      const textarea = textareaRef.current

      if (!textarea) {return}
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const selected = state.scratchpadContent.slice(start, end)
      const before = state.scratchpadContent.slice(0, start)
      const after = state.scratchpadContent.slice(end)

      pushUndo(state.scratchpadContent)
      const newContent = `${before}${prefix}${selected}${suffix}${after}`
      setScratchpadContent(newContent)

      window.requestAnimationFrame(() => {
        textarea.focus()
        textarea.setSelectionRange(start + prefix.length, start + prefix.length + selected.length)
      })
    },
    [state.scratchpadContent, pushUndo]
  )

  const handleUndo = useCallback(() => {
    if (!undoStack.length) {return}
    const previous = undoStack[undoStack.length - 1]
    setRedoStack(prev => [...prev, state.scratchpadContent])
    setUndoStack(prev => prev.slice(0, -1))
    setScratchpadContent(previous)
  }, [undoStack, state.scratchpadContent])

  const handleRedo = useCallback(() => {
    if (!redoStack.length) {return}
    const next = redoStack[redoStack.length - 1]
    setUndoStack(prev => [...prev, state.scratchpadContent])
    setRedoStack(prev => prev.slice(0, -1))
    setScratchpadContent(next)
  }, [redoStack, state.scratchpadContent])

  const handleSlashCommand = useCallback(
    (action: string) => {
      setSlashOpen(false)
      const content = state.scratchpadContent
      const before = content.slice(0, cursorPos - 1)
      const after = content.slice(cursorPos)
      const newContent = `${before}[AI: ${action}]${after}`
      pushUndo(content)
      setScratchpadContent(newContent)
    },
    [state.scratchpadContent, cursorPos, pushUndo]
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault()

        if (e.shiftKey) {handleRedo()}
        else {handleUndo()}
      }

      if (e.key === 'Escape') {setSlashOpen(false)}
    },
    [handleUndo, handleRedo]
  )

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary) px-3 py-1.5">
        {TOOLBAR_ITEMS.map(item => (
          <Button
            aria-label={item.label}
            key={item.label}
            onClick={() => applyFormat(item.prefix, item.suffix)}
            size="icon-xs"
            title={item.label}
            variant="ghost"
          >
            <item.icon className="size-3.5" />
          </Button>
        ))}
        <div className="mx-1 h-4 w-px bg-(--ui-stroke-tertiary)" />
        <Button aria-label="Undo" disabled={!undoStack.length} onClick={handleUndo} size="icon-xs" title="Undo" variant="ghost">
          <IconArrowBackUp className="size-3.5" />
        </Button>
        <Button aria-label="Redo" disabled={!redoStack.length} onClick={handleRedo} size="icon-xs" title="Redo" variant="ghost">
          <IconArrowForwardUp className="size-3.5" />
        </Button>
        <div className="mx-1 h-4 w-px bg-(--ui-stroke-tertiary)" />
        <Button
          aria-label={showPreview ? 'Edit' : 'Preview'}
          onClick={() => setShowPreview(v => !v)}
          size="icon-xs"
          title={showPreview ? 'Edit' : 'Preview'}
          variant="ghost"
        >
          {showPreview ? <IconEyeOff className="size-3.5" /> : <IconEye className="size-3.5" />}
        </Button>
        <Button
          onClick={() => setShowHistory(v => !v)}
          size="icon-xs"
          title="Version history"
          variant="ghost"
        >
          <IconHistory className="size-3.5" />
        </Button>
        <div className="ml-auto flex items-center gap-1">
          <Button onClick={() => handleSlashCommand('summarize')} size="xs" title="Ask AI" variant="ghost">
            <IconSparkles className="mr-1 size-3" />
            AI
          </Button>
          <Button onClick={() => {}} size="xs" variant="ghost">
            <IconSend className="mr-1 size-3" />
            Share
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        {showHistory ? (
          <div className="h-full overflow-y-auto p-3">
            <h3 className="mb-2 text-xs font-medium text-muted-foreground">Version History</h3>
            {state.scratchpadHistory.length === 0 ? (
              <p className="text-xs text-muted-foreground/60">No history yet</p>
            ) : (
              <div className="space-y-1">
                {state.scratchpadHistory.map((snapshot, i) => (
                  <button
                    className="w-full rounded-md px-3 py-2 text-left text-xs transition-colors hover:bg-accent"
                    key={snapshot.timestamp}
                    onClick={() => restoreScratchpadSnapshot(i)}
                    type="button"
                  >
                    <span className="text-muted-foreground">
                      {new Date(snapshot.timestamp).toLocaleString()}
                    </span>
                    <p className="mt-0.5 truncate text-foreground/70">{snapshot.content.slice(0, 80)}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : showPreview ? (
          <div
            className="h-full overflow-y-auto p-4 [&_h1]:mb-2 [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:mb-1.5 [&_h2]:text-base [&_h2]:font-medium [&_h3]:mb-1 [&_h3]:text-sm [&_h3]:font-medium [&_blockquote]:border-l-2 [&_blockquote]:border-primary/30 [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:text-xs [&_li]:ml-4 [&_li]:text-sm [&_a]:text-primary [&_a]:underline"
            dangerouslySetInnerHTML={{ __html: previewHtml }}
          />
        ) : (
          <div className="relative h-full">
            <textarea
              className="h-full w-full resize-none bg-transparent p-4 text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground/40"
              onChange={e => handleChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Start typing... Use / for AI commands"
              ref={textareaRef}
              value={state.scratchpadContent}
            />
            {slashOpen && (
              <div className="absolute left-4 top-12 z-10 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-elevated) p-1 shadow-lg">
                {AI_ACTIONS.map(action => (
                  <button
                    className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-xs text-foreground transition-colors hover:bg-accent"
                    key={action.id}
                    onClick={() => handleSlashCommand(action.id)}
                    type="button"
                  >
                    <IconSparkles className="size-3 text-primary" />
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
