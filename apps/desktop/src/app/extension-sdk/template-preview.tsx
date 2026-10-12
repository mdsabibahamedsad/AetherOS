import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'

interface FileEntry {
  path: string
  content: string
}

interface ExtensionManifest {
  name: string
  version: string
  description: string
  author: string
  license: string
  main: string
  icon?: string
  permissions: string[]
  dependencies: string[]
  tools: string[]
  hooks: string[]
}

interface TemplatePreviewProps {
  files: FileEntry[]
  manifest: ExtensionManifest
}

export function TemplatePreview({ files, manifest }: TemplatePreviewProps) {
  const [selectedFile, setSelectedFile] = useState<string>(files[0]?.path || '')
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set(['']))

  const activeFile = files.find(f => f.path === selectedFile)

  const tree = buildTree(files)

  function toggleDir(path: string) {
    setExpandedDirs(prev => {
      const next = new Set(prev)

      if (next.has(path)) {next.delete(path)}
      else {next.add(path)}

      return next
    })
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Codicon name="file" size="0.75rem" />
          {files.length} files
        </span>
        <span className="flex items-center gap-1">
          <Codicon name="package" size="0.75rem" />
          {manifest.name || 'Unnamed'}
        </span>
        <Badge className="text-[0.55rem]" variant="outline">v{manifest.version}</Badge>
      </div>

      <div className="grid grid-cols-[1fr_2fr] gap-3">
        <div className="rounded-lg border border-(--ui-stroke-tertiary) px-2 py-1.5">
          {tree.map(node => renderTreeNode(node, '', selectedFile, setSelectedFile, expandedDirs, toggleDir))}
        </div>

        <div className="rounded-lg border border-(--ui-stroke-tertiary) overflow-hidden">
          {activeFile ? (
            <>
              <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-3 py-1.5">
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Codicon
                    name={getIconForFile(activeFile.path)}
                    size="0.75rem"
                  />
                  {activeFile.path}
                </span>
              </div>
              <pre className="overflow-x-auto p-3 font-mono text-[0.65rem] leading-relaxed text-foreground/80 [scrollbar-width:thin]">
                <code>{activeFile.content}</code>
              </pre>
            </>
          ) : (
            <div className="grid min-h-32 place-items-center text-xs text-muted-foreground">
              Select a file to preview
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface TreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: TreeNode[]
}

function buildTree(files: FileEntry[]): TreeNode[] {
  const root: TreeNode[] = []

  for (const file of files) {
    const parts = file.path.split('/')
    let current = root

    for (let i = 0; i < parts.length; i++) {
      const isLast = i === parts.length - 1
      const name = parts[i]
      const fullPath = parts.slice(0, i + 1).join('/')

      if (isLast) {
        current.push({ name, path: fullPath, type: 'file' })
      } else {
        let dir = current.find(n => n.type === 'directory' && n.name === name)

        if (!dir) {
          dir = { name, path: fullPath, type: 'directory', children: [] }
          current.push(dir)
        }

        current = dir.children!
      }
    }
  }

  return root
}

function renderTreeNode(
  node: TreeNode,
  parentPath: string,
  selectedFile: string,
  onSelect: (path: string) => void,
  expandedDirs: Set<string>,
  onToggleDir: (path: string) => void
): React.ReactNode {
  const fullPath = parentPath ? `${parentPath}/${node.name}` : node.name
  const isExpanded = expandedDirs.has(fullPath)

  if (node.type === 'directory') {
    return (
      <div key={fullPath}>
        <button
          className="flex w-full items-center gap-1 rounded-sm px-1 py-0.5 text-left text-xs hover:bg-accent/60"
          onClick={() => onToggleDir(fullPath)}
          type="button"
        >
          <Codicon
            className="text-muted-foreground transition-transform"
            name="chevron-right"
            size="0.6rem"
            style={{ transform: isExpanded ? 'rotate(90deg)' : undefined }}
          />
          <Codicon className="text-amber-500" name="folder" size="0.75rem" />
          <span className="truncate">{node.name}</span>
        </button>
        {isExpanded && node.children && (
          <div className="ml-3 border-l border-(--ui-stroke-tertiary) pl-1">
            {node.children.map(child =>
              renderTreeNode(child, fullPath, selectedFile, onSelect, expandedDirs, onToggleDir)
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <button
      className={cn(
        'flex w-full items-center gap-1.5 rounded-sm px-1 py-0.5 text-left text-xs transition-colors',
        selectedFile === fullPath ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
      )}
      key={fullPath}
      onClick={() => onSelect(fullPath)}
      type="button"
    >
      <Codicon className="text-sky-500" name={getIconForFile(node.name)} size="0.75rem" />
      <span className="truncate">{node.name}</span>
    </button>
  )
}

function getIconForFile(filename: string): string {
  if (filename.endsWith('.ts') || filename.endsWith('.tsx')) {return 'code'}

  if (filename.endsWith('.json')) {return 'json'}

  if (filename.endsWith('.md')) {return 'note'}

  if (filename.endsWith('.yaml') || filename.endsWith('.yml')) {return 'settings'}

  return 'file'
}
