import { useCallback, useState } from 'react'

import { Button } from '@/components/ui/button'
import { CameraCapture } from '@/components/ui/camera-capture'
import { Codicon } from '@/components/ui/codicon'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { ScreenCapture } from '@/components/ui/screen-capture'
import { useI18n } from '@/i18n'
import { Camera, Clipboard, FileText, FolderOpen, type IconComponent, ImageIcon, Link, MessageSquareText, Monitor } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { addComposerAttachment } from '@/store/composer'

import { GHOST_ICON_BTN } from './controls'
import type { ChatBarState } from './types'

const SNIPPET_KEYS = ['codeReview', 'implementationPlan', 'explainThis']

export function ContextMenu({
  state,
  onInsertText,
  onOpenUrlDialog,
  onPasteClipboardImage,
  onPickFiles,
  onPickFolders,
  onPickImages
}: ContextMenuProps) {
  const { t } = useI18n()
  const c = t.composer
  const [snippetsOpen, setSnippetsOpen] = useState(false)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [screenCaptureOpen, setScreenCaptureOpen] = useState(false)

  const handleCameraCapture = useCallback((dataUrl: string) => {
    const id = `camera-${Date.now()}`
    addComposerAttachment({
      id,
      kind: 'image',
      label: 'Camera Capture',
      previewUrl: dataUrl,
      refText: `@image:camera_capture_${Date.now()}.jpg`
    })
  }, [])

  const handleScreenCapture = useCallback((result: { dataUrl: string }) => {
    const id = `screen-${Date.now()}`
    addComposerAttachment({
      id,
      kind: 'image',
      label: 'Screen Capture',
      previewUrl: result.dataUrl,
      refText: `@image:screen_capture_${Date.now()}.png`
    })
  }, [])

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            aria-label={state.tools.label}
            className={cn(
              GHOST_ICON_BTN,
              'data-[state=open]:bg-(--chrome-action-hover) data-[state=open]:text-foreground'
            )}
            disabled={!state.tools.enabled}
            size="icon"
            title={state.tools.label}
            type="button"
            variant="ghost"
          >
            <Codicon name="add" size="1rem" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-60" side="top" sideOffset={10}>
          <DropdownMenuLabel className="text-[0.7rem] font-medium uppercase tracking-wide text-muted-foreground/85">
            {c.attachLabel}
          </DropdownMenuLabel>
          <ContextMenuItem disabled={!onPickFiles} icon={FileText} onSelect={onPickFiles}>
            {c.files}
          </ContextMenuItem>
          <ContextMenuItem disabled={!onPickFolders} icon={FolderOpen} onSelect={onPickFolders}>
            {c.folder}
          </ContextMenuItem>
          <ContextMenuItem disabled={!onPickImages} icon={ImageIcon} onSelect={onPickImages}>
            {c.images}
          </ContextMenuItem>
          <ContextMenuItem disabled={!onPasteClipboardImage} icon={Clipboard} onSelect={onPasteClipboardImage}>
            {c.pasteImage}
          </ContextMenuItem>
          <ContextMenuItem icon={Link} onSelect={onOpenUrlDialog}>
            {c.url}
          </ContextMenuItem>

          <DropdownMenuSeparator />

          <DropdownMenuLabel className="text-[0.7rem] font-medium uppercase tracking-wide text-muted-foreground/85">
            Capture
          </DropdownMenuLabel>
          <ContextMenuItem icon={Camera} onSelect={() => setCameraOpen(true)}>
            Camera
          </ContextMenuItem>
          <ContextMenuItem icon={Monitor} onSelect={() => setScreenCaptureOpen(true)}>
            Screen
          </ContextMenuItem>

          <DropdownMenuSeparator />

          <ContextMenuItem icon={MessageSquareText} onSelect={() => setSnippetsOpen(true)}>
            {c.promptSnippets}
          </ContextMenuItem>

          <DropdownMenuSeparator />

          <div className="px-2 py-1 text-[0.7rem] text-muted-foreground/80">
            {c.tipPre}
            <kbd className="rounded bg-muted/70 px-1 py-px font-mono text-[0.65rem]">@</kbd>
            {c.tipPost}
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      <PromptSnippetsDialog onInsertText={onInsertText} onOpenChange={setSnippetsOpen} open={snippetsOpen} />
      <CameraCapture
        onCapture={handleCameraCapture}
        onOpenChange={setCameraOpen}
        open={cameraOpen}
      />
      <ScreenCapture
        onCapture={handleScreenCapture}
        onOpenChange={setScreenCaptureOpen}
        open={screenCaptureOpen}
      />
    </>
  )
}

function PromptSnippetsDialog({ onInsertText, onOpenChange, open }: PromptSnippetsDialogProps) {
  const { t } = useI18n()
  const c = t.composer

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="max-w-md gap-3">
        <DialogHeader>
          <DialogTitle>{c.snippetsTitle}</DialogTitle>
          <DialogDescription>{c.snippetsDesc}</DialogDescription>
        </DialogHeader>
        <ul className="grid gap-1">
          {SNIPPET_KEYS.map(key => {
            const snippet = c.snippets[key]

            return (
              <li key={key}>
                <button
                  className="group/snippet flex w-full cursor-pointer items-start gap-2.5 rounded-md border border-transparent px-2.5 py-2 text-left transition-colors hover:border-(--ui-stroke-tertiary) hover:bg-(--ui-control-hover-background) focus-visible:border-(--ui-stroke-tertiary) focus-visible:bg-(--ui-control-hover-background) focus-visible:outline-none"
                  onClick={() => {
                    onInsertText(snippet.text)
                    onOpenChange(false)
                  }}
                  type="button"
                >
                  <MessageSquareText className="mt-0.5 size-3.5 shrink-0 text-(--ui-text-tertiary) group-hover/snippet:text-foreground" />
                  <span className="grid min-w-0 gap-0.5">
                    <span className="text-sm font-medium text-foreground">{snippet.label}</span>
                    <span className="text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)">
                      {snippet.description}
                    </span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </DialogContent>
    </Dialog>
  )
}

export function ContextMenuItem({ children, disabled, icon: Icon, onSelect }: ContextMenuItemProps) {
  return (
    <DropdownMenuItem disabled={disabled} onSelect={onSelect}>
      <Icon />
      <span>{children}</span>
    </DropdownMenuItem>
  )
}

interface ContextMenuItemProps {
  children: string
  disabled?: boolean
  icon: IconComponent
  onSelect?: () => void
}

interface ContextMenuProps {
  onInsertText: (text: string) => void
  onOpenUrlDialog: () => void
  onPasteClipboardImage?: () => void
  onPickFiles?: () => void
  onPickFolders?: () => void
  onPickImages?: () => void
  state: ChatBarState
}

interface PromptSnippetsDialogProps {
  onInsertText: (text: string) => void
  onOpenChange: (open: boolean) => void
  open: boolean
}
